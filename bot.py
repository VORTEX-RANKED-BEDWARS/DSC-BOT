"""Discord autorole bot.

This bot assigns the configured role to every new member who joins the
specified guild. It also exposes a manual command for administrators to
re-assign the autorole to all members.
"""
from __future__ import annotations

import logging
import os
from dataclasses import dataclass

import discord
from discord.ext import commands
from dotenv import load_dotenv


load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] %(levelname)s %(name)s: %(message)s",
)
LOGGER = logging.getLogger("autorole")

_config: BotConfig | None = None


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

    @classmethod
    def from_env(cls) -> "BotConfig":
        try:
            token = os.environ["DISCORD_TOKEN"].strip()
            guild_id = int(os.environ.get("DISCORD_GUILD_ID", "0"))
            role_id = int(os.environ.get("DISCORD_ROLE_ID", "0"))
            welcome_channel_raw = os.environ.get("DISCORD_WELCOME_CHANNEL_ID")
        except KeyError as exc:  # Missing token
            raise RuntimeError(
                "Missing DISCORD_TOKEN in environment."
            ) from exc
        except ValueError as exc:  # Failed int conversion
            raise RuntimeError(
                "DISCORD_GUILD_ID and DISCORD_ROLE_ID must be integers."
            ) from exc

        if not guild_id or not role_id:
            raise RuntimeError(
                "DISCORD_GUILD_ID and DISCORD_ROLE_ID env vars are required."
            )

        welcome_channel_id = None
        if welcome_channel_raw:
            try:
                welcome_channel_id = int(welcome_channel_raw)
            except ValueError as exc:
                raise RuntimeError(
                    "DISCORD_WELCOME_CHANNEL_ID must be an integer if provided."
                ) from exc

        return cls(
            token=token,
            guild_id=guild_id,
            role_id=role_id,
            welcome_channel_id=welcome_channel_id,
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


@bot.event
async def on_ready() -> None:
    config = _require_config()
    guild = bot.get_guild(config.guild_id)
    guild_info = f" guild={guild.name} ({guild.id})" if guild else ""
    LOGGER.info("Bot connected as %s.%s", bot.user, guild_info)


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


@bot.command(name="autorole_refresh", help="Force reapply autorole to all members")
@commands.has_permissions(manage_roles=True)
async def autorole_refresh(ctx: commands.Context) -> None:
    config = _require_config()
    if ctx.guild is None or ctx.guild.id != config.guild_id:
        await ctx.send("This command can only be used in the configured guild.")
        return

    try:
        role = await _resolve_role(ctx.guild)
    except RuntimeError as exc:
        await ctx.send(f"Autorole is not configured correctly: {exc}")
        return

    updated = 0
    for member in ctx.guild.members:
        if role not in member.roles:
            try:
                await member.add_roles(role, reason="Autorole refresh command")
            except discord.HTTPException as exc:  # Continue updating others
                LOGGER.error("Failed to add role to %s: %s", member, exc)
                continue
            updated += 1

    await ctx.send(f"Autorole applied to {updated} member(s).")


@autorole_refresh.error
async def autorole_refresh_error(ctx: commands.Context, error: Exception) -> None:
    if isinstance(error, commands.MissingPermissions):
        await ctx.send("You need manage_roles permission to run this command.")
    else:
        LOGGER.exception("autorole_refresh command error: %s", error)
        await ctx.send("An unexpected error occurred. Check the bot logs for details.")


if __name__ == "__main__":
    _config = BotConfig.from_env()
    bot.run(_config.token)
