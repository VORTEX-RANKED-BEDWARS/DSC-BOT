require('dotenv').config();
const { Client, Events, GatewayIntentBits } = require('discord.js');

const TOKEN = process.env.DISCORD_TOKEN;
const TARGET_GUILD_ID = process.env.TARGET_GUILD_ID || '1443680950952394784';
const AUTO_ROLE_ID = process.env.AUTO_ROLE_ID || '1444126866746245253';

if (!TOKEN) {
  throw new Error('Missing DISCORD_TOKEN in environment.');
}

const client = new Client({
  intents: [
    GatewayIntentBits.Guilds,
    GatewayIntentBits.GuildMembers,
  ],
});

client.once(Events.ClientReady, (c) => {
  console.log(`🤖 Logged in as ${c.user.tag}`);
});

client.on(Events.GuildMemberAdd, async (member) => {
  try {
    if (member?.guild?.id !== TARGET_GUILD_ID) {
      return;
    }

    const hasRole = member.roles.cache.has(AUTO_ROLE_ID);
    if (hasRole) {
      return;
    }

    const role = member.guild.roles.cache.get(AUTO_ROLE_ID)
      || await member.guild.roles.fetch(AUTO_ROLE_ID).catch(() => null);

    if (!role) {
      console.warn(`Role ${AUTO_ROLE_ID} not found in guild ${member.guild.name}`);
      return;
    }

    await member.roles.add(role, 'Auto-role assignment on member join');
    console.log(`Assigned role ${role.name} to ${member.user.tag}`);
  } catch (error) {
    console.error('Failed to assign auto-role:', error);
  }
});

client.login(TOKEN);
