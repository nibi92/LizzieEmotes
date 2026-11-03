"""Run with python -m scripts.discord_bot on a paid PythonAnywhere Always-on task."""
import asyncio
import logging
import os
import time

import discord
from discord import app_commands
from dotenv import load_dotenv

from scripts.add_emote import MAX_BYTES, Publisher, ImportFailure
from scripts.package_addon import FLAVORS


def permitted(interaction, guild_id, allowed_roles=()):
    if interaction.guild_id != guild_id or not isinstance(interaction.user, discord.Member):
        return False
    # Discord supplies effective permissions with the interaction. Computing
    # Member.guild_permissions instead depends on a populated server role cache.
    permissions = interaction.permissions
    return (permissions.administrator or permissions.manage_guild
            or any(role.id in allowed_roles for role in interaction.user.roles))


def main():
    load_dotenv(os.environ.get('EMOTE_BOT_ENV', os.path.expanduser('~/.config/lizzie-emotes.env')))
    guild_id = int(os.environ['DISCORD_GUILD_ID'])
    allowed_roles = {int(x.strip()) for x in os.environ.get('DISCORD_ALLOWED_ROLE_IDS', '').split(',') if x.strip()}
    publisher = Publisher(os.environ.get('GITHUB_REPOSITORY', 'nibi92/LizzieEmotes'),
                          os.environ.get('GITHUB_BRANCH', 'main'), os.environ['GITHUB_TOKEN'])
    guild = discord.Object(id=guild_id)

    class Bot(discord.Client):
        def __init__(self):
            intents = discord.Intents.none()
            intents.guilds = True  # Cache server roles for the upload role allowlist.
            super().__init__(intents=intents)
            self.tree = app_commands.CommandTree(self)
            self.import_lock = asyncio.Lock()
            self.last_release = 0

        async def setup_hook(self):
            await self.tree.sync(guild=guild)
            logging.info('Registered emote commands in guild %s', guild_id)

    bot = Bot()

    @bot.tree.command(name='addemote', description='Convert an image into an addon emote and push it to GitHub.', guild=guild)
    @app_commands.describe(name='Emote name (letters, numbers, underscores)', media='PNG, GIF, WebP or JPEG, up to 8 MiB')
    async def addemote(interaction: discord.Interaction, name: str, media: discord.Attachment):
        if not permitted(interaction, guild_id, allowed_roles):
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
            except (ValueError, ImportFailure) as error:
                await interaction.followup.send(str(error), ephemeral=True)
            except Exception as error:
                # Avoid exposing tokens, attachment URLs or HTTP bodies in Discord/logs.
                logging.error('Emote import failed for interaction %s (%s); check repository state before retrying.',
                              interaction.id, type(error).__name__)
                await interaction.followup.send(
                    f'Import failed ({type(error).__name__}). Check GitHub before retrying; '
                    'no success was confirmed.', ephemeral=True)
            else:
                await interaction.followup.send(f'Added `{key}`: {url}\nPlayers need the updated addon installed.', ephemeral=True)

    @bot.tree.command(name='releasebeta', description='Build the addon and publish a CurseForge beta.', guild=guild)
    @app_commands.default_permissions(manage_guild=True)
    @app_commands.choices(flavor=[app_commands.Choice(name=f, value=f) for f in FLAVORS])
    async def releasebeta(interaction: discord.Interaction, flavor: str = 'Retail'):
        if not permitted(interaction, guild_id):
            await interaction.response.send_message('You need Manage Server to publish a beta.', ephemeral=True)
            return
        await interaction.response.defer(ephemeral=True, thinking=True)
        # Share the upload lock so a release cannot overtake an in-progress import.
        if bot.import_lock.locked():
            await interaction.followup.send('Another operation is processing. Try again shortly.', ephemeral=True)
            return
        async with bot.import_lock:
            if time.monotonic() - bot.last_release < 60:
                await interaction.followup.send('Wait a minute between release requests.', ephemeral=True)
                return
            bot.last_release = time.monotonic()
            try:
                url = await asyncio.to_thread(publisher.release_beta, flavor)
            except ImportFailure as error:
                await interaction.followup.send(str(error), ephemeral=True)
            except Exception:
                await interaction.followup.send(
                    'Release request was not confirmed. Check GitHub Actions before retrying; '
                    'the token needs Actions read/write permission.', ephemeral=True)
            else:
                await interaction.followup.send(
                    f'Beta workflow requested for {flavor}: {url}\n'
                    'Check the run for completion and CurseForge upload status.', ephemeral=True)

    bot.run(os.environ['DISCORD_BOT_TOKEN'])


if __name__ == '__main__':
    main()
