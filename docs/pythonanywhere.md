# Discord /addemote on PythonAnywhere

This is a separate Always-on task on the paid account `chrisba92`; it does not
replace any existing web app. PNG, JPEG, GIF and WebP are supported, including
animated GIF/WebP. Video is not supported. Output uses 64px TGA frames with at
most 64 animation frames and preserves total animation duration.

## Install

First upload the updated repository files, or push these changes to GitHub and
clone that branch. The deployed branch must include `UploadedEmotes.lua` in all
addon TOCs before users invoke the bot.

In a PythonAnywhere Bash console (use a fresh directory for this bot):

```bash
git clone https://github.com/nibi92/LizzieEmotes.git /home/chrisba92/lizzie-emote-bot
cd /home/chrisba92/lizzie-emote-bot
python3 -m venv /home/chrisba92/.virtualenvs/lizzie-emote-bot
/home/chrisba92/.virtualenvs/lizzie-emote-bot/bin/pip install -r requirements-bot.txt
mkdir -p /home/chrisba92/.config
umask 077
touch /home/chrisba92/.config/lizzie-emotes.env
chmod 600 /home/chrisba92/.config/lizzie-emotes.env
```

Edit `/home/chrisba92/.config/lizzie-emotes.env` privately in the Files editor:

```dotenv
DISCORD_BOT_TOKEN=your_bot_token
DISCORD_GUILD_ID=your_numeric_server_id
DISCORD_ALLOWED_ROLE_IDS=
GITHUB_TOKEN=your_fine_grained_github_token
GITHUB_REPOSITORY=nibi92/LizzieEmotes
GITHUB_BRANCH=main
```

Keep this file outside the repository. Never paste secrets into chat, console
commands, Git URLs, or GitHub. The bot reads it automatically.

Create a Discord application and bot in the Discord Developer Portal, then
install it into the intended server with the `bot` and `applications.commands`
scopes. No privileged gateway intents or Administrator permission are needed.
The bot registers the command only in `DISCORD_GUILD_ID`. At runtime, users
need Manage Server or one of the comma-separated numeric role IDs configured
in `DISCORD_ALLOWED_ROLE_IDS`; leaving it empty permits only Manage Server.

Use a fine-grained GitHub token restricted to this repository with Contents
read/write permission. Branch protection must permit the token owner to push
to the chosen branch; the bot does not bypass it. Use a dedicated branch if
you prefer to merge changes yourself. Only grant credentials after reviewing
their permissions.

## Start and verify

### Publish a beta from Discord

For a full CurseForge release, use `/release flavor:Retail`. It uses the same
workflow, configuration, cooldown and Manage Server permission as `/releasebeta`,
but sets the release type to `release`.

`/releasebeta flavor:Retail` starts the existing packaging workflow on
`GITHUB_BRANCH`, with `publish=true`, `release_type=beta`, and server emoji sync
disabled. Uploaded emotes already committed to that branch are included.
Select another client from the command choices if needed. Only members with
Manage Server can publish; upload-only allowed roles cannot. Requests are
limited to one per minute per bot process.

For this command, also grant the bot's fine-grained GitHub token **Actions:
Read and write** on this repository. In GitHub Actions settings, configure the
`CF_API_TOKEN` secret and the corresponding `CF_GAME_VERSIONS_Retail` (or other
client) variable as described in the README. The reply confirms workflow
submission, not a finished release. Follow the Actions link to verify success.
After an error or timeout, inspect Actions before retrying to avoid duplicate
CurseForge uploads.

Under **Tasks > Always-on tasks**, create a task with this command:

```bash
cd /home/chrisba92/lizzie-emote-bot && /home/chrisba92/.virtualenvs/lizzie-emote-bot/bin/python -u -m scripts.discord_bot
```

Check that the task is Running and the log reports command registration. In
the configured server, use `/addemote name:wave media:<image>`. Confirm the reply
links to a GitHub commit containing a TGA, `UploadedEmotes.json`, and
`UploadedEmotes.lua`. The in-game trigger is exactly `wave`. Capitalization is
preserved: uploading `PepeWave` creates the trigger `PepeWave`.

Duplicate names are rejected even if their capitalization differs. Names must
start with a letter and contain 1–32 letters, numbers or underscores.
Use `/editemote name:PepeWave media:<replacement image>` to replace an uploaded
emote. It keeps the original name and works with static or animated images.
To rename it, use `/editemote name:PepeWave new_name:HappyWave`. Media is optional
when renaming, and you can provide both a new name and replacement media together.
The new name is the exact in-game trigger; the old trigger is removed on rename.
It requires the same permissions as `/addemote`; bundled original emotes cannot
be edited with it. Existing legacy uploads keep their `:uploaded_name:` triggers;
use the bare name (`name`) to select those in `/editemote`.
Writes are one
atomic, non-forced Git update. Concurrent branch changes cause a failure;
check the repository and retry. A network timeout can occur after GitHub has
accepted a commit, so check the repository before retrying any failed upload.

The command commits source assets. To build an installable addon, run the
existing **Sync emotes and package addon** workflow on that branch, with
`sync_discord` disabled unless you also want to import server emojis. Publishing
to CurseForge remains an explicit workflow option. Everyone needs the updated
addon installed, and WoW may need restarting to load new textures.

To update bot code, stop its Always-on task, pull the deployment branch in its
checkout, install requirements again, and restart the task. Do not run multiple
instances for the same Discord application.
