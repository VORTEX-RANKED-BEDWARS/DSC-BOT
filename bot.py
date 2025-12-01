import os
import discord
from discord.ext import commands
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Bot configuration
TOKEN = os.getenv('DISCORD_TOKEN')
GUILD_ID = 1443680950952394784  # Server ID
AUTO_ROLE_ID = 1444126866746245253  # Role ID to assign

# Set up bot with intents
intents = discord.Intents.default()
intents.members = True  # Required for member events
intents.message_content = True  # Required for message content

bot = commands.Bot(command_prefix='!', intents=intents)


@bot.event
async def on_ready():
    """Called when the bot is ready and connected to Discord"""
    print(f'{bot.user} has connected to Discord!')
    print(f'Bot is in {len(bot.guilds)} guild(s)')
    
    # Verify the guild exists
    guild = bot.get_guild(GUILD_ID)
    if guild:
        print(f'Connected to guild: {guild.name}')
        role = guild.get_role(AUTO_ROLE_ID)
        if role:
            print(f'Auto-role configured: {role.name}')
        else:
            print(f'Warning: Role {AUTO_ROLE_ID} not found in guild!')
    else:
        print(f'Warning: Guild {GUILD_ID} not found!')


@bot.event
async def on_member_join(member):
    """Automatically assign role when a member joins the server"""
    if member.guild.id == GUILD_ID:
        role = member.guild.get_role(AUTO_ROLE_ID)
        if role:
            try:
                await member.add_roles(role, reason="Auto-role assignment")
                print(f'Assigned role {role.name} to {member.display_name}')
            except discord.Forbidden:
                print(f'Error: Bot does not have permission to assign role {role.name}')
            except discord.HTTPException as e:
                print(f'Error assigning role: {e}')
        else:
            print(f'Error: Role {AUTO_ROLE_ID} not found')


@bot.command(name='ping')
async def ping(ctx):
    """Simple ping command to test bot responsiveness"""
    await ctx.send(f'Pong! Latency: {round(bot.latency * 1000)}ms')


@bot.command(name='autorole')
async def autorole_info(ctx):
    """Display current auto-role configuration"""
    if ctx.guild.id == GUILD_ID:
        role = ctx.guild.get_role(AUTO_ROLE_ID)
        if role:
            await ctx.send(f'Auto-role is set to: **{role.name}** (ID: {AUTO_ROLE_ID})')
        else:
            await ctx.send(f'Error: Role {AUTO_ROLE_ID} not found in this server.')
    else:
        await ctx.send('This command can only be used in the configured server.')


@bot.command(name='assignrole')
@commands.has_permissions(manage_roles=True)
async def assign_role(ctx, member: discord.Member = None):
    """Manually assign the auto-role to a member (requires Manage Roles permission)"""
    if ctx.guild.id != GUILD_ID:
        await ctx.send('This command can only be used in the configured server.')
        return
    
    if member is None:
        member = ctx.author
    
    role = ctx.guild.get_role(AUTO_ROLE_ID)
    if role:
        if role in member.roles:
            await ctx.send(f'{member.mention} already has the role {role.name}')
        else:
            try:
                await member.add_roles(role, reason="Manual role assignment")
                await ctx.send(f'Successfully assigned {role.name} to {member.mention}')
            except discord.Forbidden:
                await ctx.send('Error: Bot does not have permission to assign this role.')
            except discord.HTTPException as e:
                await ctx.send(f'Error assigning role: {e}')
    else:
        await ctx.send(f'Error: Role {AUTO_ROLE_ID} not found in this server.')


@bot.event
async def on_command_error(ctx, error):
    """Handle command errors"""
    if isinstance(error, commands.MissingPermissions):
        await ctx.send('You do not have permission to use this command.')
    elif isinstance(error, commands.CommandNotFound):
        pass  # Ignore unknown commands
    else:
        print(f'Error: {error}')


# Run the bot
if __name__ == '__main__':
    if not TOKEN:
        print('Error: DISCORD_TOKEN not found in environment variables!')
        print('Please create a .env file with your Discord bot token.')
    else:
        bot.run(TOKEN)
