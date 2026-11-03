"""Run with python -m scripts.discord_bot on a paid PythonAnywhere Always-on task."""
import asyncio
import logging
import os

import discord
from discord import app_commands
from dotenv import load_dotenv

from scripts.add_emote import MAX_BYTES, Publisher


def main():
    load_dotenv(os.environ.get('EMOTE_BOT_ENV', os.path.expanduser('~/.config/lizzie-emotes.env')))
    guild_id = int(os.environ['DISCORD_GUILD_ID'])
    allowed_roles = {int(x.strip()) for x in os.environ.get('DISCORD_ALLOWED_ROLE_IDS', '').split(',') if x.strip()}
    publisher = Publisher(os.environ.get('GITHUB_REPOSITORY', 'nibi92/LizzieEmotes'),
                          os.environ.get('GITHUB_BRANCH', 'main'), os.environ['GITHUB_TOKEN'])
    guild = discord.Object(id=guild_id)

    class Bot(discord.Client):
        def __init__(self):
            super().__init__(intents=discord.Intents.none())
            self.tree = app_commands.CommandTree(self)
            self.import_lock = asyncio.Lock()

        async def setup_hook(self):
            await self.tree.sync(guild=guild)
            logging.info('Registered /addemote in guild %s', guild_id)

    bot = Bot()

    @bot.tree.command(name='addemote', description='Convert an image into an addon emote and push it to GitHub.', guild=guild)
    @app_commands.describe(name='Emote name (letters, numbers, underscores)', media='PNG, GIF, WebP or JPEG, up to 8 MiB')
    async def addemote(interaction: discord.Interaction, name: str, media: discord.Attachment):
        member = interaction.user
        if (interaction.guild_id != guild_id or not isinstance(member, discord.Member)
                or not (member.guild_permissions.manage_guild or any(r.id in allowed_roles for r in member.roles))):
            await interaction.response.send_message('You need Manage Server or an allowed role.', ephemeral=True)
            return
        if media.size > MAX_BYTES:
            await interaction.response.send_message('Upload an image smaller than 8 MiB.', ephemeral=True)
            return
        await interaction.response.defer(ephemeral=True, thinking=True)
        if bot.import_lock.locked():
            await interaction.followup.send('Another upload is processing. Try again shortly.', ephemeral=True)
            return
        async with bot.import_lock:
            try:
                data = await media.read()
                url, key = await asyncio.to_thread(publisher.publish, name, data)
            except ValueError as error:
                await interaction.followup.send(str(error), ephemeral=True)
            except Exception:
                # Avoid exposing tokens, attachment URLs or HTTP bodies in Discord/logs.
                logging.error('Emote import failed for interaction %s; check repository state before retrying.', interaction.id)
                await interaction.followup.send('Import failed. Check GitHub before retrying; no success was confirmed.', ephemeral=True)
            else:
                await interaction.followup.send(f'Added `{key}`: {url}\nPlayers need the updated addon installed.', ephemeral=True)

    bot.run(os.environ['DISCORD_BOT_TOKEN'])


if __name__ == '__main__':
    main()
