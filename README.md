# Discord Auto Role Bot

A lightweight Discord bot that automatically assigns a role to anyone who joins your server. This repo is preconfigured for guild `1443680950952394784` and role `1444126866746245253`, but you can change both via environment variables at runtime.

## Features
- Listens for member join events and assigns the configured role.
- Uses `discord.js` v14 with the required privileged intents.
- Simple `.env`-driven configuration so you never hardcode secrets.

## Prerequisites
- Node.js 18+ and npm.
- A Discord application with a bot token.
- `Server Members Intent` enabled for the bot in the Discord Developer Portal.
- The bot invited to the target server with the `Manage Roles` permission and a role that sits **above** the auto-role in the role hierarchy.

## Setup
1. Install dependencies (already done in this workspace):
   ```bash
   npm install
   ```
2. Copy the example environment file and fill in your secrets:
   ```bash
   cp .env.example .env
   ```
   - `DISCORD_TOKEN`: Your bot token.
   - `TARGET_GUILD_ID`: Defaults to `1443680950952394784` but configurable.
   - `AUTO_ROLE_ID`: Defaults to `1444126866746245253` but configurable.
3. Start the bot:
   ```bash
   npm start
   ```
4. Watch the logs for `🤖 Logged in as ...` to confirm the bot connected successfully.

## How It Works
The bot listens for the `guildMemberAdd` event, checks that the join happened in the configured guild, fetches the configured role, and assigns it to the new member. Any failures (missing permissions, missing role, etc.) are logged to the console for quick debugging.

## Deploying
- Keep your `.env` private and never commit it.
- Use a process manager such as PM2 or a hosting platform (Railway, Fly.io, etc.) to keep the bot online.
- Ensure the bot token is rotated if you suspect it has been exposed.

## Scripts
- `npm start` – Runs the bot via `node src/index.js`.
