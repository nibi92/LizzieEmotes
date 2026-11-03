import unittest
from unittest.mock import Mock

try:
    import discord
    from scripts.discord_bot import permitted
except ModuleNotFoundError:
    discord = None


@unittest.skipIf(discord is None, 'Install requirements-bot.txt for bot permission tests')
class PermissionsTest(unittest.TestCase):
    def interaction(self, **permissions):
        member = Mock(spec=discord.Member)
        member.roles = [discord.Object(id=42)]
        # Reproduce an incomplete cache: member-computed permissions are empty.
        member.guild_permissions = discord.Permissions.none()
        return Mock(guild_id=123, user=member,
                    permissions=discord.Permissions(**permissions))

    def test_manage_server_uses_interaction_permissions(self):
        self.assertTrue(permitted(self.interaction(manage_guild=True), 123))
        self.assertTrue(permitted(self.interaction(administrator=True), 123))

    def test_allowlist_does_not_allow_beta_release(self):
        interaction = self.interaction()
        self.assertTrue(permitted(interaction, 123, {42}))
        self.assertFalse(permitted(interaction, 123))
        self.assertFalse(permitted(interaction, 123, {43}))

    def test_wrong_server_and_dm_denied(self):
        interaction = self.interaction(manage_guild=True)
        self.assertFalse(permitted(interaction, 456, {42}))
        interaction.guild_id = None
        self.assertFalse(permitted(interaction, 123, {42}))
