"""Discord autorole bot.

This bot assigns the configured role to every new member who joins the
specified guild. It also exposes a manual command for administrators to
re-assign the autorole to all members.
"""
from __future__ import annotations

import enum
import json
import logging
import os
import re
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List

import discord
from discord import app_commands
from discord.ext import commands
from dotenv import load_dotenv


load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] %(levelname)s %(name)s: %(message)s",
)
LOGGER = logging.getLogger("autorole")

_config: BotConfig | None = None

DEFAULT_CONFIG = {
    "token": "MTQ0NDk0MzA5NjY4NDIyMDQ1OA.G9Yxsm.gc6zhnrmK6bbOFyLJGEaiP8Fz8Fkx5tjt9gk0Q",
    "guild_id": 1443680950952394784,
    "role_id": 1444126866746245253,
    "welcome_channel_id": 1444126854553403442,
    "support_channel_id": 1444126841811112006,
}

try:
    GUILD_SCOPE_ID = int(os.environ.get("DISCORD_GUILD_ID", "0")) or DEFAULT_CONFIG["guild_id"]
except ValueError:
    GUILD_SCOPE_ID = DEFAULT_CONFIG["guild_id"]
GUILD_OBJECT = discord.Object(id=GUILD_SCOPE_ID)
_TREE_SYNCED = False

DATA_DIR = Path("data")
WARNINGS_FILE = DATA_DIR / "warnings.json"

FORBIDDEN_WORDS = [
    "nga",
    "ngr",
    "nigga",
    "nigger",
    "n1gger",
    "n1gga",
    "n!gger",
    "n!gga",
    "retard",
    "fucking",
]

FORBIDDEN_MESSAGE = (
    "Your message was removed because it contained language that violates our guidelines."
)


def _load_warning_store() -> Dict[str, Dict[str, List[dict[str, Any]]]]:
    DATA_DIR.mkdir(exist_ok=True)
    if WARNINGS_FILE.exists():
        try:
            with WARNINGS_FILE.open("r", encoding="utf-8") as handle:
                data = json.load(handle)
                if isinstance(data, dict):
                    return data  # type: ignore[return-value]
        except json.JSONDecodeError as exc:
            LOGGER.warning("Failed to parse warnings file: %s", exc)
    return {}


_WARNINGS: Dict[str, Dict[str, List[dict[str, Any]]]] = _load_warning_store()


def _save_warning_store() -> None:
    DATA_DIR.mkdir(exist_ok=True)
    with WARNINGS_FILE.open("w", encoding="utf-8") as handle:
        json.dump(_WARNINGS, handle, indent=2)


def _record_warning(
    guild_id: int,
    user_id: int,
    moderator_id: int,
    reason: str,
) -> int:
    guild_key = str(guild_id)
    user_key = str(user_id)
    entry = {
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "moderator_id": moderator_id,
        "reason": reason,
    }
    guild_warnings = _WARNINGS.setdefault(guild_key, {})
    user_warnings = guild_warnings.setdefault(user_key, [])
    user_warnings.append(entry)
    _save_warning_store()
    return len(user_warnings)


def _get_warnings(guild_id: int, user_id: int) -> List[dict[str, Any]]:
    return _WARNINGS.get(str(guild_id), {}).get(str(user_id), [])


def _contains_forbidden_text(message: str) -> tuple[bool, str | None]:
    lowered = message.lower()
    collapsed = re.sub(r"[^a-z0-9]+", "", lowered)
    for word in FORBIDDEN_WORDS:
        if word in lowered or word in collapsed:
            return True, word
    return False, None


_DURATION_PATTERN = re.compile(r"(\d+)([smhd])")
_MAX_TIMEOUT = timedelta(days=28)


def _parse_duration(duration: str) -> timedelta:
    matches = _DURATION_PATTERN.findall(duration.lower())
    if not matches:
        raise ValueError(
            "Invalid duration. Use formats like 30m, 2h, or 1h30m (s/m/h/d)."
        )
    total = timedelta()
    for amount, unit in matches:
        value = int(amount)
        if unit == "s":
            total += timedelta(seconds=value)
        elif unit == "m":
            total += timedelta(minutes=value)
        elif unit == "h":
            total += timedelta(hours=value)
        elif unit == "d":
            total += timedelta(days=value)
    if total <= timedelta(seconds=0) or total > _MAX_TIMEOUT:
        raise ValueError("Duration must be between 1 second and 28 days.")
    return total


def _assert_actionable(actor: discord.Member, target: discord.Member) -> None:
    if actor == target:
        raise app_commands.AppCommandError("You cannot target yourself.")
    if target == target.guild.owner:
        raise app_commands.AppCommandError("You cannot target the server owner.")
    if actor != actor.guild.owner and target.top_role >= actor.top_role:
        raise app_commands.AppCommandError(
            "You cannot target someone with an equal or higher role."
        )


def _require_config() -> BotConfig:
    if _config is None:
        raise RuntimeError(
            "Bot configuration not loaded. Did you run bot.py as a script?"
        )
    return _config


@dataclass(frozen=True)
class BotConfig:
    token: str
    guild_id: int
    role_id: int
    welcome_channel_id: int | None = None
    support_channel_id: int | None = None

    @classmethod
    def from_env(cls) -> "BotConfig":
        token = os.environ.get("DISCORD_TOKEN", DEFAULT_CONFIG["token"]).strip()
        if not token:
            raise RuntimeError("DISCORD_TOKEN is required.")

        def _coerce_int(name: str, *, default: int | None, required: bool) -> int | None:
            value = os.environ.get(name)
            if value is None or value.strip() == "":
                value = str(default) if default is not None else None
            if value is None:
                if required:
                    raise RuntimeError(f"{name} is required.")
                return None
            try:
                return int(value)
            except ValueError as exc:
                raise RuntimeError(f"{name} must be an integer.") from exc

        guild_id = _coerce_int(
            "DISCORD_GUILD_ID", default=DEFAULT_CONFIG["guild_id"], required=True
        )
        role_id = _coerce_int(
            "DISCORD_ROLE_ID", default=DEFAULT_CONFIG["role_id"], required=True
        )
        welcome_channel_id = _coerce_int(
            "DISCORD_WELCOME_CHANNEL_ID",
            default=DEFAULT_CONFIG["welcome_channel_id"],
            required=False,
        )
        support_channel_id = _coerce_int(
            "DISCORD_SUPPORT_CHANNEL_ID",
            default=DEFAULT_CONFIG["support_channel_id"],
            required=False,
        )

        return cls(
            token=token,
            guild_id=guild_id or 0,
            role_id=role_id or 0,
            welcome_channel_id=welcome_channel_id,
            support_channel_id=support_channel_id,
        )


intents = discord.Intents.default()
intents.members = True
intents.guilds = True

bot = commands.Bot(command_prefix="!", intents=intents)


async def _resolve_role(guild: discord.Guild) -> discord.Role:
    """Fetch the autorole for the guild, raising if it cannot be found."""
    config = _require_config()
    if guild.id != config.guild_id:
        raise RuntimeError("Bot is configured for a different guild.")

    role = guild.get_role(config.role_id)
    if role is None:
        try:
            role = await guild.fetch_role(config.role_id)
        except discord.HTTPException as exc:
            raise RuntimeError(
                f"Unable to fetch role {config.role_id} in guild {guild.id}."
            ) from exc
    if role is None:
        raise RuntimeError(
            f"Role id {config.role_id} is not available in guild {guild.id}."
        )
    return role


async def _resolve_welcome_channel(
    guild: discord.Guild,
) -> discord.TextChannel | None:
    """Resolve the welcome channel with fallbacks."""
    config = _require_config()
    me = guild.me
    permissions_for = (
        (lambda channel: channel.permissions_for(me) if me else None)
    )

    async def _ensure_text_channel(
        channel: discord.abc.GuildChannel | None,
    ) -> discord.TextChannel | None:
        if isinstance(channel, discord.TextChannel):
            perms = permissions_for(channel)
            if perms and perms.send_messages:
                return channel
        return None

    candidate: discord.TextChannel | None = None
    if config.welcome_channel_id:
        channel = guild.get_channel(config.welcome_channel_id)
        if channel is None:
            try:
                channel = await guild.fetch_channel(config.welcome_channel_id)
            except discord.HTTPException as exc:
                LOGGER.error(
                    "Failed to fetch welcome channel %s: %s",
                    config.welcome_channel_id,
                    exc,
                )
        candidate = await _ensure_text_channel(channel)
        if candidate:
            return candidate

    candidate = await _ensure_text_channel(guild.system_channel)
    if candidate:
        return candidate

    for text_channel in guild.text_channels:
        perms = permissions_for(text_channel)
        if perms and perms.send_messages:
            return text_channel
    return None


async def _resolve_support_channel(
    guild: discord.Guild,
) -> discord.TextChannel | None:
    config = _require_config()
    if not config.support_channel_id:
        return None
    channel = guild.get_channel(config.support_channel_id)
    if channel is None:
        try:
            channel = await guild.fetch_channel(config.support_channel_id)
        except discord.HTTPException as exc:
            LOGGER.error(
                "Unable to fetch support channel %s: %s",
                config.support_channel_id,
                exc,
            )
            return None
    if isinstance(channel, discord.TextChannel):
        return channel
    LOGGER.error(
        "Support channel %s is not a text channel.", config.support_channel_id
    )
    return None


def _format_ordinal(value: int) -> str:
    if 10 <= value % 100 <= 20:
        suffix = "th"
    else:
        suffix = {1: "st", 2: "nd", 3: "rd"}.get(value % 10, "th")
    return f"{value}{suffix}"


async def _send_welcome_message(member: discord.Member) -> None:
    channel = await _resolve_welcome_channel(member.guild)
    if channel is None:
        LOGGER.warning(
            "No suitable welcome channel found in guild %s", member.guild.id
        )
        return

    member_count = member.guild.member_count or len(member.guild.members)
    ordinal = _format_ordinal(member_count)
    embed = discord.Embed(
        title="Welcome to the server!",
        description=(
            f"{member.mention}, we're excited to have you here!\n"
            f"You are the {ordinal} member in this community (#{member_count:,})."
        ),
        color=discord.Color.blurple(),
    )
    embed.set_thumbnail(url=member.display_avatar.url)
    embed.add_field(
        name="Getting started",
        value="Check out the info channels and say hi to everyone!",
        inline=False,
    )
    embed.set_footer(text=member.guild.name)

    try:
        await channel.send(embed=embed)
        LOGGER.info("Welcome message sent for %s in %s", member, channel)
    except discord.HTTPException as exc:
        LOGGER.error("Failed to send welcome message for %s: %s", member, exc)


async def _guard_interaction_in_guild(
    interaction: discord.Interaction,
) -> BotConfig | None:
    config = _require_config()
    if interaction.guild is None or interaction.guild.id != config.guild_id:
        message = "This command can only be used inside the configured guild."
        if interaction.response.is_done():
            await interaction.followup.send(message, ephemeral=True)
        else:
            await interaction.response.send_message(message, ephemeral=True)
        return None
    return config


async def _guard_interaction_moderator(
    interaction: discord.Interaction,
) -> tuple[BotConfig, discord.Member] | None:
    config = await _guard_interaction_in_guild(interaction)
    if config is None:
        return None
    if not isinstance(interaction.user, discord.Member):
        message = "This command can only be used inside the guild."
        if interaction.response.is_done():
            await interaction.followup.send(message, ephemeral=True)
        else:
            await interaction.response.send_message(message, ephemeral=True)
        return None
    return config, interaction.user


class TicketType(str, enum.Enum):
    GENERAL = "general"
    PARTNER = "partner"
    REPORT = "report"
    APPLICATION = "application"


TICKET_DETAILS: dict[TicketType, dict[str, object]] = {
    TicketType.GENERAL: {
        "label": "General Support",
        "emoji": "💬",
        "description": "Ask questions or get help from staff.",
        "color": discord.Color.blurple(),
    },
    TicketType.PARTNER: {
        "label": "Partnership Inquiry",
        "emoji": "🤝",
        "description": "Discuss partnership opportunities.",
        "color": discord.Color.green(),
    },
    TicketType.REPORT: {
        "label": "Report User / Issue",
        "emoji": "🚨",
        "description": "Report rule breaks or technical problems.",
        "color": discord.Color.red(),
    },
    TicketType.APPLICATION: {
        "label": "Staff / Creator Application",
        "emoji": "📝",
        "description": "Apply for staff or content roles.",
        "color": discord.Color.gold(),
    },
}

SUPPORT_PANEL_FOOTER = "Support Ticket Panel • Autorole Bot"


def _ticket_label(ticket_type: TicketType) -> str:
    return TICKET_DETAILS[ticket_type]["label"]  # type: ignore[index]


def _ticket_color(ticket_type: TicketType) -> discord.Color:
    return TICKET_DETAILS[ticket_type]["color"]  # type: ignore[index]


def _sanitize_thread_name(name: str) -> str:
    sanitized = re.sub(r"[^a-z0-9-]+", "-", name.lower())
    sanitized = re.sub(r"-{2,}", "-", sanitized).strip("-")
    if len(sanitized) < 3:
        sanitized = "ticket"
    return sanitized[:90]


async def _create_ticket_thread(
    member: discord.Member,
    ticket_type: TicketType,
    responses: dict[str, str],
) -> discord.Thread:
    if member.guild is None:
        raise RuntimeError("Cannot create ticket outside of a guild.")
    channel = await _resolve_support_channel(member.guild)
    if channel is None:
        raise RuntimeError("Support channel is not configured.")

    base_name = f"{ticket_type.value}-{member.name}"
    thread_name = _sanitize_thread_name(base_name)
    thread = await channel.create_thread(
        name=thread_name,
        type=discord.ChannelType.private_thread,
        auto_archive_duration=1440,
        invitable=False,
        reason=f"{_ticket_label(ticket_type)} ticket for {member}",
    )
    try:
        await thread.add_user(member)
    except discord.HTTPException:
        LOGGER.warning("Unable to add %s to thread %s", member, thread.id)

    embed = discord.Embed(
        title=f"{_ticket_label(ticket_type)} Ticket",
        color=_ticket_color(ticket_type),
        description=f"Ticket opened by {member.mention}",
    )
    for field_name, value in responses.items():
        display_value = value.strip() if value and value.strip() else "No response provided."
        embed.add_field(name=field_name, value=display_value, inline=False)
    embed.set_footer(text=f"User ID: {member.id}")

    await thread.send(content=member.mention, embed=embed)
    LOGGER.info(
        "Created %s ticket for user %s in thread %s",
        ticket_type.value,
        member,
        thread.id,
    )
    return thread


class TicketReasonModal(discord.ui.Modal):
    def __init__(self, ticket_type: TicketType):
        super().__init__(title=f"{_ticket_label(ticket_type)} Request")
        self.ticket_type = ticket_type
        prompt = "Share a short summary so staff know how to help."
        if ticket_type is TicketType.REPORT:
            prompt = "Describe what happened and who was involved."
        self.details = discord.ui.TextInput(
            label="Details",
            placeholder=prompt,
            style=discord.TextStyle.paragraph,
            max_length=1000,
            required=True,
        )
        self.add_item(self.details)

    async def on_submit(self, interaction: discord.Interaction) -> None:
        if interaction.guild is None or not isinstance(
            interaction.user, discord.Member
        ):
            await interaction.response.send_message(
                "Tickets can only be created inside the server.",
                ephemeral=True,
            )
            return
        await interaction.response.defer(ephemeral=True, thinking=True)
        try:
            thread = await _create_ticket_thread(
                interaction.user,
                self.ticket_type,
                {"Summary": self.details.value},
            )
        except RuntimeError as exc:
            LOGGER.error("Ticket creation failed: %s", exc)
            await interaction.followup.send(
                "Sorry, I couldn't create your ticket. Please alert the admins.",
                ephemeral=True,
            )
            return
        await interaction.followup.send(
            f"Your {_ticket_label(self.ticket_type)} ticket is ready: {thread.mention}",
            ephemeral=True,
        )


class StaffApplicationModal(discord.ui.Modal):
    username = discord.ui.TextInput(
        label="Primary username / IGN",
        placeholder="e.g. horisont1",
        max_length=64,
        required=True,
    )
    age = discord.ui.TextInput(
        label="Age",
        placeholder="Provide your age",
        max_length=32,
        required=True,
    )
    staff_experience = discord.ui.TextInput(
        label="Staff experience",
        placeholder="Where have you moderated? List roles and durations.",
        style=discord.TextStyle.paragraph,
        max_length=500,
        required=True,
    )
    general_experience = discord.ui.TextInput(
        label="Community experience",
        placeholder="Relevant achievements, strengths, specialties.",
        style=discord.TextStyle.paragraph,
        max_length=500,
        required=True,
    )
    creator_presence = discord.ui.TextInput(
        label="Content creator stats",
        placeholder=(
            "Links + metrics. Min: 1k subs & 500 avg views or 20+ live viewers."
        ),
        style=discord.TextStyle.paragraph,
        max_length=500,
        required=True,
    )
    availability = discord.ui.TextInput(
        label="Availability",
        placeholder="Hours per week and time zones you can help.",
        style=discord.TextStyle.short,
        max_length=200,
        required=True,
    )

    def __init__(self) -> None:
        super().__init__(title="Staff & Content Application")

    async def on_submit(self, interaction: discord.Interaction) -> None:
        if interaction.guild is None or not isinstance(
            interaction.user, discord.Member
        ):
            await interaction.response.send_message(
                "Applications can only be submitted inside the server.",
                ephemeral=True,
            )
            return
        await interaction.response.defer(ephemeral=True, thinking=True)
        responses = {
            "Username": self.username.value,
            "Age": self.age.value,
            "Staff experience": self.staff_experience.value,
            "Community experience": self.general_experience.value,
            "Creator stats": self.creator_presence.value,
            "Availability": self.availability.value,
        }
        try:
            thread = await _create_ticket_thread(
                interaction.user, TicketType.APPLICATION, responses
            )
        except RuntimeError as exc:
            LOGGER.error("Application ticket failed: %s", exc)
            await interaction.followup.send(
                "Sorry, I couldn't submit your application. Please contact staff.",
                ephemeral=True,
            )
            return
        await interaction.followup.send(
            f"Thanks! Your application ticket is open: {thread.mention}",
            ephemeral=True,
        )


class TicketTypeSelect(discord.ui.Select):
    def __init__(self) -> None:
        options = []
        for ticket_type in (
            TicketType.GENERAL,
            TicketType.PARTNER,
            TicketType.REPORT,
        ):
            details = TICKET_DETAILS[ticket_type]
            options.append(
                discord.SelectOption(
                    label=details["label"],
                    value=ticket_type.value,
                    description=details["description"],
                    emoji=details["emoji"],
                )
            )
        super().__init__(
            placeholder="Choose a ticket type",
            min_values=1,
            max_values=1,
            custom_id="support_panel:select",
            options=options,
        )

    async def callback(self, interaction: discord.Interaction) -> None:
        value = self.values[0]
        ticket_type = TicketType(value)
        await interaction.response.send_modal(TicketReasonModal(ticket_type))


class StaffApplicationButton(discord.ui.Button):
    def __init__(self) -> None:
        super().__init__(
            label="Staff / Creator Application",
            style=discord.ButtonStyle.primary,
            emoji=TICKET_DETAILS[TicketType.APPLICATION]["emoji"],
            custom_id="support_panel:application",
        )

    async def callback(self, interaction: discord.Interaction) -> None:  # type: ignore[override]
        await interaction.response.send_modal(StaffApplicationModal())


class SupportPanelView(discord.ui.View):
    def __init__(self) -> None:
        super().__init__(timeout=None)
        self.add_item(TicketTypeSelect())
        self.add_item(StaffApplicationButton())


async def ensure_support_panel(guild: discord.Guild) -> None:
    channel = await _resolve_support_channel(guild)
    if channel is None:
        LOGGER.warning("Support channel not configured; skipping ticket panel.")
        return

    embed = discord.Embed(
        title="How can we help you?",
        description=(
            "Use the menu below to open a ticket for general help, partnerships, "
            "or reports. Need to join the team? Submit a staff/content application "
            "with the button."
        ),
        color=discord.Color.dark_teal(),
    )
    embed.add_field(
        name="Ticket options",
        value="\n".join(
            f"{details['emoji']} **{details['label']}** – {details['description']}"
            for key, details in TICKET_DETAILS.items()
            if key is not TicketType.APPLICATION
        ),
        inline=False,
    )
    embed.add_field(
        name="Application requirements",
        value=(
            "• Minimum 1k subscribers & 500 avg views (or 20+ live viewers)\n"
            "• Strong moderation or community experience\n"
            "• Professional and respectful conduct at all times"
        ),
        inline=False,
    )
    embed.set_footer(text=SUPPORT_PANEL_FOOTER)

    panel_message: discord.Message | None = None
    try:
        pinned = await channel.pins()
    except discord.HTTPException as exc:
        LOGGER.error("Failed to fetch pinned messages: %s", exc)
        pinned = []
    for message in pinned:
        if (
            message.author == guild.me
            and message.embeds
            and SUPPORT_PANEL_FOOTER
            in (message.embeds[0].footer.text if message.embeds[0].footer else "")
        ):
            panel_message = message
            break

    view = SupportPanelView()
    if panel_message:
        try:
            await panel_message.edit(embed=embed, view=view)
            LOGGER.info("Updated existing ticket panel in %s", channel.id)
        except discord.HTTPException as exc:
            LOGGER.error("Failed to edit ticket panel: %s", exc)
    else:
        try:
            panel_message = await channel.send(embed=embed, view=view)
            await panel_message.pin()
            LOGGER.info("Created and pinned ticket panel in %s", channel.id)
        except discord.HTTPException as exc:
            LOGGER.error("Failed to create ticket panel: %s", exc)


bot.add_view(SupportPanelView())


@bot.event
async def on_message(message: discord.Message) -> None:
    if message.author.bot:
        return

    try:
        config = _require_config()
    except RuntimeError:
        await bot.process_commands(message)
        return

    if message.guild is None or message.guild.id != config.guild_id:
        await bot.process_commands(message)
        return

    flagged, banned_word = _contains_forbidden_text(message.content)
    if flagged:
        reason = (
            f"Automod caught prohibited term '{banned_word}'" if banned_word else ""
        )
        try:
            await message.delete()
        except discord.HTTPException:
            LOGGER.warning("Failed to delete flagged message from %s", message.author)
        count = _record_warning(
            guild_id=message.guild.id,
            user_id=message.author.id,
            moderator_id=bot.user.id if bot.user else 0,
            reason=reason or "Automated language filter",
        )
        try:
            await message.channel.send(
                f"{message.author.mention} {FORBIDDEN_MESSAGE} "
                f"(warning #{count}).",
                delete_after=15,
            )
        except discord.HTTPException:
            LOGGER.warning("Failed to send automod notice in %s", message.channel.id)

    await bot.process_commands(message)


@bot.event
async def on_ready() -> None:
    config = _require_config()
    guild = bot.get_guild(config.guild_id)
    guild_info = f" guild={guild.name} ({guild.id})" if guild else ""
    LOGGER.info("Bot connected as %s.%s", bot.user, guild_info)
    if guild:
        await ensure_support_panel(guild)
    global _TREE_SYNCED
    if not _TREE_SYNCED:
        try:
            await bot.tree.sync(guild=discord.Object(id=config.guild_id))
            _TREE_SYNCED = True
            LOGGER.info("Slash commands synced for guild %s", config.guild_id)
        except discord.HTTPException as exc:
            LOGGER.error("Failed to sync slash commands: %s", exc)


@bot.event
async def on_member_join(member: discord.Member) -> None:
    config = _require_config()
    if member.guild.id != config.guild_id:
        return

    try:
        role = await _resolve_role(member.guild)
    except RuntimeError as exc:
        LOGGER.error("Autorole resolution failed: %s", exc)
        return

    if role in member.roles:
        LOGGER.debug("%s already has autorole", member)
        return

    try:
        await member.add_roles(role, reason="Auto role assignment")
        LOGGER.info("Assigned autorole to %s", member)
    except discord.HTTPException as exc:
        LOGGER.error("Failed to assign role to %s: %s", member, exc)
    finally:
        await _send_welcome_message(member)


@bot.tree.command(
    name="autorole_refresh",
    description="Force reapply the configured autorole to every member.",
)
@app_commands.guilds(GUILD_OBJECT)
@app_commands.guild_only()
@app_commands.checks.has_permissions(manage_roles=True)
async def autorole_refresh_slash(interaction: discord.Interaction) -> None:
    config = await _guard_interaction_in_guild(interaction)
    if config is None or interaction.guild is None:
        return

    await interaction.response.defer(thinking=True, ephemeral=True)
    try:
        role = await _resolve_role(interaction.guild)
    except RuntimeError as exc:
        await interaction.followup.send(
            f"Autorole is not configured correctly: {exc}", ephemeral=True
        )
        return

    updated = 0
    for member in interaction.guild.members:
        if role not in member.roles:
            try:
                await member.add_roles(role, reason="Autorole refresh command")
            except discord.HTTPException as exc:  # Continue updating others
                LOGGER.error("Failed to add role to %s: %s", member, exc)
                continue
            updated += 1

    await interaction.followup.send(
        f"Autorole applied to {updated} member(s).", ephemeral=True
    )


@bot.tree.command(name="ban", description="Ban a member from the server.")
@app_commands.guilds(GUILD_OBJECT)
@app_commands.guild_only()
@app_commands.describe(member="Member to ban", reason="Reason for the ban")
@app_commands.checks.has_permissions(ban_members=True)
@app_commands.checks.bot_has_permissions(ban_members=True)
async def slash_ban(
    interaction: discord.Interaction,
    member: discord.Member,
    reason: str | None = None,
) -> None:
    guarded = await _guard_interaction_moderator(interaction)
    if guarded is None:
        return
    _, actor = guarded
    reason_text = reason or "No reason provided."
    _assert_actionable(actor, member)
    await member.ban(reason=f"{actor} - {reason_text}", delete_message_days=0)
    await interaction.response.send_message(
        f"{member.mention} has been banned. Reason: {reason_text}",
        ephemeral=False,
    )


@bot.tree.command(name="kick", description="Kick a member from the server.")
@app_commands.guilds(GUILD_OBJECT)
@app_commands.guild_only()
@app_commands.describe(member="Member to kick", reason="Reason for the kick")
@app_commands.checks.has_permissions(kick_members=True)
@app_commands.checks.bot_has_permissions(kick_members=True)
async def slash_kick(
    interaction: discord.Interaction,
    member: discord.Member,
    reason: str | None = None,
) -> None:
    guarded = await _guard_interaction_moderator(interaction)
    if guarded is None:
        return
    _, actor = guarded
    reason_text = reason or "No reason provided."
    _assert_actionable(actor, member)
    await member.kick(reason=f"{actor} - {reason_text}")
    await interaction.response.send_message(
        f"{member.mention} has been kicked. Reason: {reason_text}", ephemeral=False
    )


@bot.tree.command(
    name="mute",
    description="Timeout a member. Duration supports s/m/h/d (e.g. 30m).",
)
@app_commands.guilds(GUILD_OBJECT)
@app_commands.guild_only()
@app_commands.describe(
    member="Member to mute",
    duration="Examples: 30m, 2h, 1h30m",
    reason="Reason for the mute",
)
@app_commands.checks.has_permissions(moderate_members=True)
@app_commands.checks.bot_has_permissions(moderate_members=True)
async def slash_mute(
    interaction: discord.Interaction,
    member: discord.Member,
    duration: str,
    reason: str | None = None,
) -> None:
    guarded = await _guard_interaction_moderator(interaction)
    if guarded is None:
        return
    _, actor = guarded
    _assert_actionable(actor, member)
    try:
        delta = _parse_duration(duration)
    except ValueError as exc:
        if interaction.response.is_done():
            await interaction.followup.send(str(exc), ephemeral=True)
        else:
            await interaction.response.send_message(str(exc), ephemeral=True)
        return
    until = discord.utils.utcnow() + delta
    reason_text = reason or "No reason provided."
    await member.timeout(until, reason=f"{actor} - {reason_text}")
    await interaction.response.send_message(
        f"{member.mention} has been muted for {duration}. Reason: {reason_text}",
        ephemeral=False,
    )


@bot.tree.command(name="warn", description="Issue a formal warning to a member.")
@app_commands.guilds(GUILD_OBJECT)
@app_commands.guild_only()
@app_commands.describe(member="Member to warn", reason="Reason for the warning")
@app_commands.checks.has_permissions(manage_messages=True)
async def slash_warn(
    interaction: discord.Interaction,
    member: discord.Member,
    reason: str | None = None,
) -> None:
    guarded = await _guard_interaction_moderator(interaction)
    if guarded is None:
        return
    config, actor = guarded
    _assert_actionable(actor, member)
    reason_text = reason or "No reason provided."
    count = _record_warning(
        guild_id=config.guild_id,
        user_id=member.id,
        moderator_id=actor.id,
        reason=reason_text,
    )
    await interaction.response.send_message(
        f"{member.mention} has been warned (warning #{count}). Reason: {reason_text}",
        ephemeral=True,
    )


@bot.tree.command(name="warnings", description="Show warnings recorded for a member.")
@app_commands.guilds(GUILD_OBJECT)
@app_commands.guild_only()
@app_commands.describe(member="Member whose warnings you want to view")
@app_commands.checks.has_permissions(manage_messages=True)
async def slash_warnings(
    interaction: discord.Interaction, member: discord.Member
) -> None:
    config = await _guard_interaction_in_guild(interaction)
    if config is None or interaction.guild is None:
        return
    entries = _get_warnings(config.guild_id, member.id)
    if not entries:
        await interaction.response.send_message(
            f"{member.mention} has no warnings on record.", ephemeral=True
        )
        return
    embed = discord.Embed(
        title=f"Warnings for {member}",
        color=discord.Color.orange(),
        description=f"{len(entries)} warning(s) on file.",
    )
    for entry in entries[-5:]:
        timestamp = entry.get("timestamp", "unknown time")
        reason = entry.get("reason", "No reason provided.")
        moderator_id = entry.get("moderator_id")
        moderator_ref = f"<@{moderator_id}>" if moderator_id else "Unknown mod"
        embed.add_field(
            name=timestamp,
            value=f"{moderator_ref}: {reason}",
            inline=False,
        )
    await interaction.response.send_message(embed=embed, ephemeral=True)


@bot.tree.error
async def on_app_command_error(
    interaction: discord.Interaction, error: app_commands.AppCommandError
) -> None:
    if isinstance(error, app_commands.errors.MissingPermissions):
        message = "You are missing the required permissions for this command."
    elif isinstance(error, app_commands.errors.BotMissingPermissions):
        missing = ", ".join(error.missing_permissions)
        message = f"I am missing required permissions: {missing}"
    elif isinstance(error, app_commands.errors.CheckFailure):
        message = "You cannot run this command in this context."
    elif isinstance(error, app_commands.errors.CommandInvokeError):
        LOGGER.exception("Slash command raised: %s", error)
        message = "An unexpected error occurred while running this command."
    else:
        LOGGER.exception("Unhandled slash command error: %s", error)
        message = "Something went wrong while handling that command."

    if interaction.response.is_done():
        await interaction.followup.send(message, ephemeral=True)
    else:
        await interaction.response.send_message(message, ephemeral=True)


if __name__ == "__main__":
    _config = BotConfig.from_env()
    bot.run(_config.token)
