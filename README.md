# Discord Auto-Role Bot

A Discord bot that automatically assigns a role to new members when they join your server.

## Features

- 🎭 **Automatic Role Assignment**: Assigns a specified role to all new members joining the server
- 💬 **Welcome Messages**: Sends a welcome DM to new members (if they have DMs enabled)
- 🧪 **Test Command**: `/test_autorole` - Test the auto-role functionality on yourself
- ℹ️ **Info Command**: `/info` - Display bot configuration and status
- 🔒 **Error Handling**: Comprehensive error handling and logging

## Configuration

The bot is pre-configured for:
- **Server ID**: `1443680950952394784`
- **Role ID**: `1444126866746245253`

## Setup Instructions

### 1. Prerequisites

- Python 3.8 or higher
- A Discord bot token ([Create one here](https://discord.com/developers/applications))

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. Configure Bot Token

1. Copy the `.env.example` file to `.env`:
   ```bash
   cp .env.example .env
   ```

2. Edit `.env` and add your Discord bot token:
   ```
   DISCORD_BOT_TOKEN=your_actual_bot_token_here
   ```

### 4. Bot Permissions

Your bot needs the following permissions in your Discord server:

**Required Permissions:**
- ✅ Manage Roles
- ✅ Send Messages
- ✅ Use Slash Commands

**Required Intents (enable in Discord Developer Portal):**
- ✅ Server Members Intent (Privileged)
- ✅ Message Content Intent (Privileged)

**Invite Link Template:**
```
https://discord.com/api/oauth2/authorize?client_id=YOUR_BOT_CLIENT_ID&permissions=268435456&scope=bot%20applications.commands
```

Replace `YOUR_BOT_CLIENT_ID` with your bot's actual client ID.

### 5. Run the Bot

```bash
python bot.py
```

## Usage

### Automatic Role Assignment

The bot will automatically assign the configured role to any new member who joins the server. No manual action required!

### Slash Commands

- **`/test_autorole`** - Test the auto-role assignment on yourself
- **`/info`** - Display bot configuration and status information

## Customization

### Changing Server or Role

Edit the `config.json` file:

```json
{
  "guild_id": "YOUR_SERVER_ID",
  "auto_role_id": "YOUR_ROLE_ID"
}
```

**How to get IDs:**
1. Enable Developer Mode in Discord (User Settings → Advanced → Developer Mode)
2. Right-click on the server or role and select "Copy ID"

## Troubleshooting

### Bot doesn't assign roles

1. **Check bot permissions**: Ensure the bot has "Manage Roles" permission
2. **Role hierarchy**: The bot's role must be higher than the role it's trying to assign
3. **Check intents**: Ensure "Server Members Intent" is enabled in the Discord Developer Portal

### Bot doesn't respond to commands

1. **Check if bot is online**: Look for the bot in the member list
2. **Wait for sync**: Slash commands may take up to an hour to sync globally
3. **Try in the configured server**: Some commands only work in the configured server

### "Server Members Intent" error

Go to your [Discord Developer Portal](https://discord.com/developers/applications), select your bot, go to the "Bot" tab, and enable the "Server Members Intent" under "Privileged Gateway Intents".

## File Structure

```
.
├── bot.py              # Main bot script
├── config.json         # Server and role configuration
├── requirements.txt    # Python dependencies
├── .env.example        # Example environment variables
└── README.md          # This file
```

## Support

If you encounter any issues:
1. Check the console output for error messages
2. Verify all configuration settings
3. Ensure the bot has proper permissions
4. Make sure privileged intents are enabled

## License

This bot is provided as-is for personal use.
