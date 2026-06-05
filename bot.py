import discord
from discord.ext import commands
from discord import app_commands
import random
import json
import os

intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)

# Draft state
draft = {
    "active": False,
    "pool": {
        "LW": [],
        "C": [],
        "RW": [],
        "LD": [],
        "RD": [],
        "G": []
    },
    "owners": [],          # list of owner display names in draft order
    "order": [],           # snake order for the full draft
    "current_pick": 0,     # index into order[]
    "rosters": {},         # { owner: { "LW": None, "C": None, ... } }
    "pool_message": None,  # the live-updated pool message
    "round": 1,
    "picks_this_round": 0,
}

POSITIONS = ["LW", "C", "RW", "LD", "RD", "G"]
POSITION_ALIASES = {
    "LW": "LW", "LEFT WING": "LW", "LEFTWING": "LW",
    "C": "C", "CENTER": "C", "CENTRE": "C",
    "RW": "RW", "RIGHT WING": "RW", "RIGHTWING": "RW",
    "LD": "LD", "LEFT D": "LD", "LEFT DEFENSE": "LD", "LEFT DEFENCE": "LD",
    "RD": "RD", "RIGHT D": "RD", "RIGHT DEFENSE": "RD", "RIGHT DEFENCE": "RD",
    "G": "G", "GOALIE": "G", "GOALTENDER": "G", "GK": "G",
}
POSITION_EMOJI = {
    "LW": "🔵", "C": "🔴", "RW": "🟢",
    "LD": "🟡", "RD": "🟠", "G": "🟣"
}
POSITION_LABEL = {
    "LW": "LEFT WING", "C": "CENTER", "RW": "RIGHT WING",
    "LD": "LEFT D", "RD": "RIGHT D", "G": "GOALIE"
}

# Helpers────

def build_snake_order(owners, rounds):
    """Build a full snake draft order list."""
    order = []
    for r in range(rounds):
        if r % 2 == 0:
            order.extend(owners)
        else:
            order.extend(reversed(owners))
    return order


def build_pool_embed():
    """Build the draft pool embed."""
    desc = ""
    for pos in POSITIONS:
        players = draft["pool"][pos]
        emoji = POSITION_EMOJI[pos]
        label = POSITION_LABEL[pos]
        desc += f"{emoji} **{label}** ({len(players)})\n"
        if players:
            for p in players:
                desc += f"  • {p}\n"
        else:
            desc += "  *(empty)*\n"
        desc += "\n"

    # Draft order line
    order_preview = " → ".join(draft["owners"])
    desc += f"━━━━━━━━━━━━━━━━━━\n📋 **Draft Order:** {order_preview}\n"

    if draft["active"] and draft["current_pick"] < len(draft["order"]):
        current_owner = draft["order"][draft["current_pick"]]
        desc += f"🎯 **NOW PICKING:** {current_owner}"
    else:
        desc += "✅ **Draft complete!**"

    embed = discord.Embed(
        title="🏒 CWHL DRAFT POOL",
        description=desc,
        color=0x1a73e8
    )
    return embed


def build_rosters_embed():
    """Build the rosters embed."""
    embed = discord.Embed(title="📋 CWHL Draft Rosters", color=0x2ecc71)
    for owner, roster in draft["rosters"].items():
        value = ""
        for pos in POSITIONS:
            emoji = POSITION_EMOJI[pos]
            label = POSITION_LABEL[pos]
            player = roster.get(pos) or "*empty*"
            value += f"{emoji} {label}: **{player}**\n"
        embed.add_field(name=f"🏒 {owner}", value=value, inline=True)
    return embed


def current_owner_needs_pos(owner):
    """Return list of positions the current owner still needs."""
    roster = draft["rosters"].get(owner, {})
    return [p for p in POSITIONS if not roster.get(p)]


# Events─────

@bot.event
async def on_ready():
    await bot.tree.sync()
    print(f"✅ Logged in as {bot.user}")


# /startdraft

@bot.tree.command(name="startdraft", description="Start a new draft. Paste the signup list when prompted.")
@app_commands.checks.has_permissions(manage_guild=True)
async def startdraft(interaction: discord.Interaction):
    if draft["active"]:
        await interaction.response.send_message("❌ A draft is already active. Use `/enddraft` to cancel it first.", ephemeral=True)
        return

    await interaction.response.send_message(
        "📋 **Starting draft setup!**\n\n"
        "Please paste the signup list in this format (one player per line):\n"
        "```\n"
        "LW: Maytag72\n"
        "LW: mchallsy\n"
        "C: Shaquille\n"
        "C: Lew'Neal\n"
        "RW: kittyking69\n"
        "LD: jsizzle_379\n"
        "RD: xNuggzy\n"
        "G: VCity420\n"
        "OWNERS: Arks8888, NowYoDead, PUTRIDBEAST, Stubby, LAMBOx22, LUYEYEP123, k-parks88, tho92mp19son\n"
        "```\n"
        "Type `cancel` to abort.",
        ephemeral=False
    )

    def check(m):
        return m.author == interaction.user and m.channel == interaction.channel

    try:
        msg = await bot.wait_for("message", check=check, timeout=120)
    except Exception:
        await interaction.followup.send("⏰ Timed out. Run `/startdraft` again.")
        return

    if msg.content.strip().lower() == "cancel":
        await interaction.followup.send("❌ Draft setup cancelled.")
        return

    # Parse the pasted list
    pool = {p: [] for p in POSITIONS}
    owners = []
    errors = []

    for line in msg.content.strip().splitlines():
        line = line.strip()
        if not line:
            continue
        if ":" not in line:
            continue
        key, _, value = line.partition(":")
        key = key.strip().upper()
        value = value.strip()

        if key == "OWNERS":
            owners = [o.strip() for o in value.split(",") if o.strip()]
        elif key in POSITION_ALIASES:
            pos = POSITION_ALIASES[key]
            players = [p.strip() for p in value.split(",") if p.strip()]
            pool[pos].extend(players)
        else:
            errors.append(f"Unknown key: `{key}`")

    if not owners:
        await interaction.followup.send("❌ No owners found. Make sure you include a line like `OWNERS: Name1, Name2, ...`")
        return

    # Randomize draft order
    random.shuffle(owners)
    snake_order = build_snake_order(owners, len(POSITIONS))

    # Initialize draft state
    draft["active"] = True
    draft["pool"] = pool
    draft["owners"] = owners
    draft["order"] = snake_order
    draft["current_pick"] = 0
    draft["round"] = 1
    draft["picks_this_round"] = 0
    draft["rosters"] = {owner: {pos: None for pos in POSITIONS} for owner in owners}
    draft["pool_message"] = None

    # Post the pool
    embed = build_pool_embed()
    pool_msg = await interaction.channel.send(embed=embed)
    draft["pool_message"] = pool_msg

    first_owner = draft["order"][0]
    await interaction.channel.send(
        f"✅ Draft started! Order randomized.\n"
        f"🎯 **{first_owner}** — you're up first! Use `/pick [player name]` to make your pick."
    )

    if errors:
        await interaction.channel.send("⚠️ Some lines couldn't be parsed:\n" + "\n".join(errors))


# /pick──────

@bot.tree.command(name="pick", description="Pick a player from the draft pool.")
@app_commands.describe(player="The player's name to pick")
async def pick(interaction: discord.Interaction, player: str):
    if not draft["active"]:
        await interaction.response.send_message("❌ No draft is active.", ephemeral=True)
        return

    current_owner = draft["order"][draft["current_pick"]]
    caller = interaction.user.display_name

    if caller.lower() != current_owner.lower():
        await interaction.response.send_message(
            f"❌ It's **{current_owner}**'s turn, not yours.", ephemeral=True
        )
        return

    # Find the player in the pool
    found_pos = None
    found_player = None
    for pos in POSITIONS:
        for p in draft["pool"][pos]:
            if p.lower() == player.lower():
                found_pos = pos
                found_player = p
                break
        if found_pos:
            break

    if not found_pos:
        await interaction.response.send_message(
            f"❌ `{player}` not found in the draft pool. Check the spelling or use `/draftpool` to see available players.",
            ephemeral=True
        )
        return

    # Check position slot
    roster = draft["rosters"][current_owner]
    if roster[found_pos] is not None:
        await interaction.response.send_message(
            f"❌ You already have a **{POSITION_LABEL[found_pos]}** ({roster[found_pos]}). Pick a different position.",
            ephemeral=True
        )
        return

    # Make the pick
    draft["pool"][found_pos].remove(found_player)
    roster[found_pos] = found_player
    draft["current_pick"] += 1
    draft["picks_this_round"] += 1

    # Check if draft is complete
    total_picks = len(draft["owners"]) * len(POSITIONS)
    if draft["current_pick"] >= total_picks:
        draft["active"] = False
        await interaction.response.send_message(
            f"✅ **{current_owner}** picked **{found_player}** ({POSITION_LABEL[found_pos]})!\n\n"
            f"🏆 **Draft is complete!**"
        )
        if draft["pool_message"]:
            await draft["pool_message"].edit(embed=build_pool_embed())
        await interaction.channel.send(embed=build_rosters_embed())
        return

    # Next owner
    next_owner = draft["order"][draft["current_pick"]]

    await interaction.response.send_message(
        f"✅ **{current_owner}** picks **{found_player}** ({POSITION_EMOJI[found_pos]} {POSITION_LABEL[found_pos]})!\n"
        f"🎯 **{next_owner}** — you're up! Use `/pick [player name]`"
    )

    # Update pool embed
    if draft["pool_message"]:
        await draft["pool_message"].edit(embed=build_pool_embed())


# /draftpool─

@bot.tree.command(name="draftpool", description="Show the current draft pool.")
async def draftpool(interaction: discord.Interaction):
    if not draft["rosters"] and not draft["active"]:
        await interaction.response.send_message("❌ No draft has been started.", ephemeral=True)
        return
    await interaction.response.send_message(embed=build_pool_embed())


# /rosters───

@bot.tree.command(name="rosters", description="Show all team rosters.")
async def rosters(interaction: discord.Interaction):
    if not draft["rosters"]:
        await interaction.response.send_message("❌ No draft has been started.", ephemeral=True)
        return
    await interaction.response.send_message(embed=build_rosters_embed())


# /draftorder

@bot.tree.command(name="draftorder", description="Show the full snake draft order.")
async def draftorder(interaction: discord.Interaction):
    if not draft["order"]:
        await interaction.response.send_message("❌ No draft has been started.", ephemeral=True)
        return

    lines = []
    for i, owner in enumerate(draft["order"]):
        marker = "🎯 " if i == draft["current_pick"] and draft["active"] else f"{i+1}. "
        lines.append(f"{marker}{owner}")

    embed = discord.Embed(
        title="📋 Snake Draft Order",
        description="\n".join(lines),
        color=0x9b59b6
    )
    await interaction.response.send_message(embed=embed)


# /skipturn──

@bot.tree.command(name="skipturn", description="Admin: skip the current owner's turn.")
@app_commands.checks.has_permissions(manage_guild=True)
async def skipturn(interaction: discord.Interaction):
    if not draft["active"]:
        await interaction.response.send_message("❌ No draft is active.", ephemeral=True)
        return

    skipped = draft["order"][draft["current_pick"]]
    draft["current_pick"] += 1

    if draft["current_pick"] >= len(draft["order"]):
        draft["active"] = False
        await interaction.response.send_message(f"⏭️ Skipped **{skipped}**. Draft is now complete.")
        return

    next_owner = draft["order"][draft["current_pick"]]
    await interaction.response.send_message(
        f"⏭️ Skipped **{skipped}**'s turn.\n🎯 **{next_owner}** — you're up!"
    )
    if draft["pool_message"]:
        await draft["pool_message"].edit(embed=build_pool_embed())


# /enddraft──

@bot.tree.command(name="enddraft", description="Admin: cancel and reset the current draft.")
@app_commands.checks.has_permissions(manage_guild=True)
async def enddraft(interaction: discord.Interaction):
    draft["active"] = False
    draft["pool"] = {p: [] for p in POSITIONS}
    draft["owners"] = []
    draft["order"] = []
    draft["current_pick"] = 0
    draft["rosters"] = {}
    draft["pool_message"] = None
    await interaction.response.send_message("🗑️ Draft has been reset.")


# Run────────

TOKEN = os.getenv("DISCORD_TOKEN")
if not TOKEN:
    raise ValueError("DISCORD_TOKEN environment variable not set!")

bot.run(TOKEN)
