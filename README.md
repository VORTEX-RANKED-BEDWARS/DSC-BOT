# Discord Auto-Role Bot

A Discord bot that automatically assigns a role to new members when they join the server.

## Configuration

- **Server ID**: 1443680950952394784
- **Auto-Role ID**: 1444126866746245253

## Setup Instructions

### 1. Create a Discord Application

1. Go to [Discord Developer Portal](https://discord.com/developers/applications)
2. Click "New Application" and give it a name
3. Go to the "Bot" section
4. Click "Add Bot" and confirm
5. Under "Privileged Gateway Intents", enable:
   - **Server Members Intent** (Required for member events)
   - **Message Content Intent** (Required for message commands)
6. Copy the bot token (you'll need this later)

### 2. Invite Bot to Server

1. Go to the "OAuth2" → "URL Generator" section
2. Select scopes:
   - `bot`
   - `applications.commands` (optional, for slash commands)
3. Select bot permissions:
   - `Manage Roles`
   - `Send Messages`
   - `Read Messages/View Channels`
4. Copy the generated URL and open it in your browser
5. Select your server and authorize the bot

### 3. Configure Bot Role Position

**IMPORTANT**: The bot's role must be positioned HIGHER than the role it's trying to assign in the server's role hierarchy.

1. Go to your Discord server settings
2. Navigate to "Roles"
3. Find your bot's role
4. Drag it above the auto-role (1444126866746245253)
5. Make sure the bot role has "Manage Roles" permission enabled

### 4. Install Dependencies

```bash
pip install -r requirements.txt
```

### 5. Configure Environment Variables

1. Copy `.env.example` to `.env`:
   ```bash
   cp .env.example .env
   ```

2. Edit `.env` and add your Discord bot token:
   ```
   DISCORD_TOKEN=your_actual_bot_token_here
   ```

### 6. Run the Bot

```bash
python bot.py
```

## Commands

- `!ping` - Check bot latency
- `!autorole` - Display current auto-role configuration
- `!assignrole [member]` - Manually assign the auto-role to a member (requires Manage Roles permission)

## Features

- ✅ Automatically assigns role when members join
- ✅ Manual role assignment command
- ✅ Error handling and logging
- ✅ Permission checks

## Troubleshooting

- **Bot doesn't assign roles**: Make sure the bot's role is positioned above the target role in the role hierarchy
- **Missing permissions**: Ensure the bot has "Manage Roles" permission
- **Role not found**: Verify the role ID is correct and the bot is in the right server
- **Intents error**: Make sure Server Members Intent is enabled in the Discord Developer Portal
