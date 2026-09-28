# LizzieEmotes

Install the `LizzieEmotes` folder inside WoW's `Interface/AddOns` directory.
Use the ZIP produced by the packaging script or GitHub Actions, **not** GitHub's
"Download ZIP" source archive (which adds a `-main` folder suffix).

## Packaging

With Python 3.12 or later:

```powershell
python -m pip install -r requirements.txt
python -m unittest discover -s tests -v
python scripts/package_addon.py --flavor Retail --version v2
```

The result is `dist/LizzieEmotes-v2-Retail.zip`. Its only top-level folder is
`LizzieEmotes`, containing `LizzieEmotes.toc`. The builder selects one client TOC
and gives it the exact base filename inside the ZIP. Available clients: Retail,
Vanilla, TBC, Wrath, Cata, Mists. Existing Interface numbers are preserved; validate
compatibility in the intended WoW client before publishing. Nested library TOCs
belong to bundled libraries and should retain their names.

## Connect a Discord server

1. Choose a server where you can authorize a bot. In Discord's Settings > Advanced,
   enable Developer Mode, right-click the server, and select **Copy Server ID**.
2. Create an application in the [Discord Developer Portal](https://discord.com/developers/applications).
   Open **Bot** and generate/reset its bot token. Store it securely.
3. In the application's installation settings, enable guild installation with the
   `bot` scope and invite it to that server. Listing emojis does not need
   administrator permissions, message access, or privileged gateway intents.
4. In this GitHub repository, open **Settings > Secrets and variables > Actions**.
   Add a secret named `DISCORD_BOT_TOKEN` and a variable named `DISCORD_GUILD_ID`.
   Do not commit tokens or paste them into chat.
5. Open **Actions > Sync emotes and package addon > Run workflow**, select `main`,
   enable **sync_discord**, select the WoW client, and run.

The workflow downloads custom server emojis through the
[Discord emoji API](https://docs.discord.com/developers/resources/emoji), converts
PNG/GIF images to TGA, commits `DiscordEmotes.lua` and `Emotes/discord`, then packages
the addon. It runs on demand; there is no background bot process or in-game network
connection. Stickers and standard Unicode emojis are not imported.

Imported names are `:discord_NAME:` to preserve existing emotes; duplicate names
get an ID suffix. Animated images are sampled at up to 25 FPS and 64 frames into
64px frames, preserving overall duration. Deleted emojis disappear from the
generated lookup/menu on the next sync; old texture files are retained.
Downloads finish before existing addon files change. A failed request stops the
workflow before committing or publishing. Your original `Emotes.lua` is untouched.

To run locally, supply `DISCORD_BOT_TOKEN` and `DISCORD_GUILD_ID` as environment
variables, then run `python scripts/sync_discord.py`. Local sync does not push or
upload; the GitHub workflow handles those steps. Everyone using the emotes needs
the updated addon installed.

## CurseForge publishing

The workflow targets project **1631926**. Configure:

| GitHub setting | Kind | Value |
| --- | --- | --- |
| `CF_API_TOKEN` | Secret | Token from the [CurseForge author portal](https://authors.curseforge.com/account/api-tokens) |
| `CF_GAME_VERSIONS_Retail` | Variable | JSON array of CurseForge version IDs, e.g. `[12345]` (example only) |
| `CF_GAME_VERSIONS_Mists`, etc. | Variable | Version IDs for each additional client you publish |

Find actual version IDs using authenticated GET
`https://wow.curseforge.com/api/game/versions` with the `X-Api-Token` header.
These are CurseForge IDs, **not** WoW Interface numbers. Select IDs corresponding
to the packaged client's tested game versions. The
[official upload API documentation](https://support.curseforge.com/support/solutions/articles/9000197321)
describes authentication and version lookup.

Run the same workflow with **publish** enabled to upload after building and pushing
any synced emotes. Default release type is beta; choose release when ready.
Publishing also works with Discord syncing disabled. Download the artifact and
extract the addon ZIP inside it for a manual upload. CurseForge may review uploaded
files before making them available. A successful upload prints its file ID.

GitHub Actions needs permission to push to the selected branch. If branch protection
blocks it, run on an allowed branch and merge normally; failed pushes prevent the
CurseForge upload. Build numbers identify packages. Retrying a completed publication
can create another upload; check CurseForge before retrying after an upload timeout.
