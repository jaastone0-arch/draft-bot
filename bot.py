# CWHL Draft Bot

A Discord bot for running snake drafts for your EA NHL league.

## Commands

| Command | Who | Description |
|---|---|---|
| `/startdraft` | Admin | Start a new draft, paste the signup list |
| `/pick [player]` | Current owner | Pick a player from the pool |
| `/draftpool` | Anyone | Show the current draft pool by position |
| `/rosters` | Anyone | Show all team rosters |
| `/draftorder` | Anyone | Show the full snake draft order |
| `/skipturn` | Admin | Skip the current owner's turn |
| `/enddraft` | Admin | Cancel and reset the draft |

## Signup List Format

When prompted after `/startdraft`, paste in this format:

```
LW: Maytag72
LW: mchallsy
C: Shaquille
C: Lew'Neal
C: Toppy
C: Morphius
RW: kittyking69
RW: AmoSs_71
RW: J Whipzz
LD: jsizzle_379
LD: Jonnnn
LD: Pc3poseidon
RD: xNuggzy
RD: KennyPow
G: VCity420
G: Irishoddity
G: DaBirdMan27
OWNERS: Arks8888, NowYoDead, PUTRIDBEAST, Stubby, LAMBOx22, LUYEYEP123, k-parks88, tho92mp19son
```

## Setup

### 1. Create a Discord Bot

1. Go to https://discord.com/developers/applications
2. Click **New Application** → name it (e.g. `CWHL Draft Bot`)
3. Go to **Bot** → click **Add Bot**
4. Under **Privileged Gateway Intents**, enable:
   - Server Members Intent
   - Message Content Intent
5. Click **Reset Token** → copy the token (you'll need this)
6. Go to **OAuth2 → URL Generator**:
   - Scopes: `bot`, `applications.commands`
   - Bot Permissions: `Send Messages`, `Embed Links`, `Read Message History`
7. Copy the generated URL → open it → add the bot to your server

### 2. Deploy to Railway

1. Go to https://railway.app and sign up (free)
2. Click **New Project → Deploy from GitHub repo**
   - Push this folder to a GitHub repo first, OR
   - Use **New Project → Empty Project** and drag the files in
3. Go to your project → **Variables** → add:
   - `DISCORD_TOKEN` = your bot token from step 1
4. Railway will auto-deploy. Your bot will stay online 24/7.

### 3. You're done!

Go to your Discord server and run `/startdraft` to kick things off.
