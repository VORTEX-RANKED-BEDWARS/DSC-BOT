import discord
from discord.ext import commands
import json
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Load configuration
with open('config.json', 'r') as f:
    config = json.load(f)

# Bot setup
intents = discord.Intents.default()
intents.members = True  # Required for member join events
intents.message_content = True

bot = commands.Bot(command_prefix='!', intents=intents)

GUILD_ID = int(config['guild_id'])
AUTO_ROLE_ID = int(config['auto_role_id'])


@bot.event
async def on_ready():
    """Called when the bot is ready and connected to Discord."""
    print(f'{bot.user} has connected to Discord!')
    print(f'Bot is ready to assign auto-roles in guild: {GUILD_ID}')
    print(f'Auto-role ID: {AUTO_ROLE_ID}')
    
    # Sync slash commands
    try:
        synced = await bot.tree.sync()
        print(f'Synced {len(synced)} command(s)')
    except Exception as e:
        print(f'Failed to sync commands: {e}')


@bot.event
async def on_member_join(member: discord.Member):
    """
    Automatically assign a role when a new member joins the server.
    """
    # Check if the member joined the configured guild
    if member.guild.id != GUILD_ID:
        return
    
    try:
        # Get the role object
        role = member.guild.get_role(AUTO_ROLE_ID)
        
        if role is None:
            print(f'Error: Role with ID {AUTO_ROLE_ID} not found in guild {member.guild.name}')
            return
        
        # Assign the role to the member
        await member.add_roles(role)
        print(f'Successfully assigned role "{role.name}" to {member.name} ({member.id})')
        
        # Optional: Send a welcome message to the member
        try:
            await member.send(
                f'Welcome to {member.guild.name}! '
                f'You have been automatically assigned the "{role.name}" role.'
            )
        except discord.Forbidden:
            print(f'Could not send welcome DM to {member.name} (DMs disabled)')
            
    except discord.Forbidden:
        print(f'Error: Bot lacks permissions to assign roles to {member.name}')
    except Exception as e:
        print(f'Error assigning role to {member.name}: {e}')


@bot.tree.command(name='test_autorole', description='Test the auto-role assignment on yourself')
async def test_autorole(interaction: discord.Interaction):
    """
    Slash command to test the auto-role functionality.
    """
    if interaction.guild.id != GUILD_ID:
        await interaction.response.send_message(
            'This command can only be used in the configured server.',
            ephemeral=True
        )
        return
    
    try:
        role = interaction.guild.get_role(AUTO_ROLE_ID)
        
        if role is None:
            await interaction.response.send_message(
                f'Error: Role with ID {AUTO_ROLE_ID} not found.',
                ephemeral=True
            )
            return
        
        # Check if user already has the role
        if role in interaction.user.roles:
            await interaction.response.send_message(
                f'You already have the "{role.name}" role!',
                ephemeral=True
            )
            return
        
        # Assign the role
        await interaction.user.add_roles(role)
        await interaction.response.send_message(
            f'Successfully assigned the "{role.name}" role to you!',
            ephemeral=True
        )
        print(f'Test: Assigned role "{role.name}" to {interaction.user.name}')
        
    except discord.Forbidden:
        await interaction.response.send_message(
            'Error: I lack permissions to assign roles.',
            ephemeral=True
        )
    except Exception as e:
        await interaction.response.send_message(
            f'Error: {e}',
            ephemeral=True
        )


@bot.tree.command(name='info', description='Display bot information')
async def info(interaction: discord.Interaction):
    """
    Slash command to display bot information.
    """
    role = interaction.guild.get_role(AUTO_ROLE_ID) if interaction.guild else None
    role_name = role.name if role else 'Unknown'
    
    embed = discord.Embed(
        title='Auto-Role Bot Information',
        description='This bot automatically assigns roles to new members.',
        color=discord.Color.blue()
    )
    embed.add_field(name='Configured Server ID', value=str(GUILD_ID), inline=False)
    embed.add_field(name='Auto-Role ID', value=str(AUTO_ROLE_ID), inline=False)
    embed.add_field(name='Auto-Role Name', value=role_name, inline=False)
    embed.add_field(name='Bot Status', value='✅ Online and Running', inline=False)
    
    await interaction.response.send_message(embed=embed, ephemeral=True)


# Error handling
@bot.event
async def on_error(event, *args, **kwargs):
    """Handle errors that occur during events."""
    print(f'Error in {event}:')
    import traceback
    traceback.print_exc()


# Run the bot
if __name__ == '__main__':
    TOKEN = os.getenv('DISCORD_BOT_TOKEN')
    
    if not TOKEN:
        print('Error: DISCORD_BOT_TOKEN not found in environment variables.')
        print('Please create a .env file with your bot token.')
        exit(1)
    
    try:
        bot.run(TOKEN)
    except discord.LoginFailure:
        print('Error: Invalid bot token. Please check your DISCORD_BOT_TOKEN in .env file.')
    except Exception as e:
        print(f'Error starting bot: {e}')
