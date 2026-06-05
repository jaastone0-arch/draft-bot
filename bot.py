import discord
from discord.ext import commands
from discord import app_commands
import random
import os

intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)

draft = {
    "active": False,
    "pool": {"LW": [], "C": [], "RW": [], "LD": [], "RD": [], "G": []},
    "owners": [],
    "order": [],
    "current_pick": 0,
    "rosters": {},
    "pool_message": None,
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
POSITION_EMOJI = {"LW": "🟢", "C": "🔴", "RW": "🔵", "LD": "⚪", "RD": "🟡", "G": "🟣"}
POSITION_LABEL = {"LW": "LEFT WING", "C": "CENTER", "RW": "RIGHT WING", "LD": "LEFT D", "RD": "RIGHT D", "G": "GOALIE"}


def build_snake_order(owners, rounds):
    order = []
    for r in range(rounds):
        if r % 2 == 0:
            order.extend(owners)
        else:
            order.extend(reversed(owners))
    return order


def build_pool_embed():
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

    order_preview = " → ".join(draft["owners"])
    desc += f"━━━━━━━━━━━━━━━━━━\n📋 **Draft Order:** {order_preview}\n"

    if draft["active"] and draft["current_pick"] < len(draft["order"]):
        current_owner = draft["order"][draft["current_pick"]]
        desc += f"🎯 **NOW PICKING:** {current_owner}"
    else:
        desc += "✅ **Draft complete!**"

    embed = discord.Embed(title="🏒 DRAFT POOL", description=desc, color=0x1a73e8)
    return embed


def build_rosters_embed():
    embed = discord.Embed(title="📋 Draft Rosters", color=0x2ecc71)
    for owner, roster in draft["rosters"].items():
        value = ""
        for pos in POSITIONS:
            emoji = POSITION_EMOJI[pos]
            label = POSITION_LABEL[pos]
            player = roster.get(pos) or "*empty*"
            value += f"{emoji} {label}: **{player}**\n"
        embed.add_field(name=f"🏒 {owner}", value=value, inline=True)
    return embed


def get_all_pool_players():
    players = []
    for pos in POSITIONS:
        for p in draft["pool"][pos]:
            players.append(f"[{pos}] {p}")
    return players


async def player_autocomplete(interaction: discord.Interaction, current: str):
    choices = []
    for pos in POSITIONS:
        for p in draft["pool"][pos]:
            label = f"[{pos}] {p}"
            if current.lower() in label.lower():
                choices.append(app_commands.Choice(name=label, value=p))
    return choices[:25]


def do_pick(current_owner, found_player, found_pos):
    draft["pool"][found_pos].remove(found_player)
    draft["rosters"][current_owner][found_pos] = found_player
    draft["current_pick"] += 1
    draft["picks_this_round"] += 1


@bot.event
async def on_ready():
    await bot.tree.sync()
    print(f"Logged in as {bot.user}")


@bot.tree.command(name="startdraft", description="Start a new draft. Paste the signup list when prompted.")
@app_commands.checks.has_permissions(manage_guild=True)
async def startdraft(interaction: discord.Interaction):
    if draft["active"]:
        await interaction.response.send_message("❌ A draft is already active. Use `/enddraft` to cancel it first.", ephemeral=True)
        return

    await interaction.response.send_message(
        "📋 **Starting draft setup!**\n\n"
        "Please paste the signup list in this format:\n"
        "```\n"
        "LW: Maytag72\n"
        "LW: mchallsy\n"
        "C: Shaquille\n"
        "RW: kittyking69\n"
        "LD: jsizzle_379\n"
        "RD: xNuggzy\n"
        "G: VCity420\n"
        "OWNERS: Arks8888, NowYoDead, PUTRIDBEAST, Stubby\n"
        "```\n"
        "Type `cancel` to abort."
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

    pool = {p: [] for p in POSITIONS}
    owners = []
    errors = []

    for line in msg.content.strip().splitlines():
        line = line.strip()
        if not line or ":" not in line:
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
        await interaction.followup.send("❌ No owners found. Include a line like `OWNERS: Name1, Name2, ...`")
        return

    random.shuffle(owners)
    snake_order = build_snake_order(owners, len(POSITIONS))

    draft["active"] = True
    draft["pool"] = pool
    draft["owners"] = owners
    draft["order"] = snake_order
    draft["current_pick"] = 0
    draft["round"] = 1
    draft["picks_this_round"] = 0
    draft["rosters"] = {owner: {pos: None for pos in POSITIONS} for owner in owners}
    draft["pool_message"] = None

    embed = build_pool_embed()
    pool_msg = await interaction.channel.send(embed=embed)
    draft["pool_message"] = pool_msg

    first_owner = draft["order"][0]
    await interaction.channel.send(
        f"✅ Draft started! Order randomized.\n"
        f"🎯 **{first_owner}** — you're up first! Use `/pick` to make your pick."
    )

    if errors:
        await interaction.channel.send("⚠️ Some lines couldn't be parsed:\n" + "\n".join(errors))


@bot.tree.command(name="pick", description="Pick a player from the draft pool.")
@app_commands.describe(player="Start typing a name or position to filter")
@app_commands.autocomplete(player=player_autocomplete)
async def pick(interaction: discord.Interaction, player: str):
    if not draft["active"]:
        await interaction.response.send_message("❌ No draft is active.", ephemeral=True)
        return

    current_owner = draft["order"][draft["current_pick"]]
    caller = interaction.user.display_name
    is_admin = interaction.user.guild_permissions.manage_guild

    if caller.lower() != current_owner.lower() and not is_admin:
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
            f"❌ `{player}` not found in the draft pool. Use the dropdown or `/draftpool` to see available players.",
            ephemeral=True
        )
        return

    roster = draft["rosters"][current_owner]
    if roster[found_pos] is not None:
        await interaction.response.send_message(
            f"❌ **{current_owner}** already has a **{POSITION_LABEL[found_pos]}** ({roster[found_pos]}). Pick a different position.",
            ephemeral=True
        )
        return

    # Admin picking on behalf of owner
    picking_for = f" (picking for **{current_owner}**)" if is_admin and caller.lower() != current_owner.lower() else ""

    do_pick(current_owner, found_player, found_pos)

    # Check if owner now has 5 picks — auto-fill the last empty slot with themselves
    roster = draft["rosters"][current_owner]
    filled = [p for p in POSITIONS if roster.get(p)]
    autofill_msg = ""
    if len(filled) == 5:
        empty_pos = next((p for p in POSITIONS if not roster.get(p)), None)
        if empty_pos:
            roster[empty_pos] = current_owner
            autofill_msg = f"\n🤖 **{current_owner}** has been auto-filled into **{POSITION_EMOJI[empty_pos]} {POSITION_LABEL[empty_pos]}**!"

    total_picks = len(draft["owners"]) * len(POSITIONS)
    if draft["current_pick"] >= total_picks:
        draft["active"] = False
        await interaction.response.send_message(
            f"✅ **{current_owner}** picks **{found_player}** ({POSITION_EMOJI[found_pos]} {POSITION_LABEL[found_pos]}){picking_for}!{autofill_msg}\n\n"
            f"🏆 **Draft is complete!**"
        )
        if draft["pool_message"]:
            await draft["pool_message"].edit(embed=build_pool_embed())
        await interaction.channel.send(embed=build_rosters_embed())
        return

    next_owner = draft["order"][draft["current_pick"]]
    await interaction.response.send_message(
        f"✅ **{current_owner}** picks **{found_player}** ({POSITION_EMOJI[found_pos]} {POSITION_LABEL[found_pos]}){picking_for}!{autofill_msg}\n"
        f"🎯 **{next_owner}** — you're up! Use `/pick`"
    )

    if draft["pool_message"]:
        await draft["pool_message"].edit(embed=build_pool_embed())


@bot.tree.command(name="draftpool", description="Show the current draft pool.")
async def draftpool(interaction: discord.Interaction):
    if not draft["rosters"] and not draft["active"]:
        await interaction.response.send_message("❌ No draft has been started.", ephemeral=True)
        return
    await interaction.response.send_message(embed=build_pool_embed())


@bot.tree.command(name="rosters", description="Show all team rosters.")
async def rosters(interaction: discord.Interaction):
    if not draft["rosters"]:
        await interaction.response.send_message("❌ No draft has been started.", ephemeral=True)
        return
    await interaction.response.send_message(embed=build_rosters_embed())


@bot.tree.command(name="draftorder", description="Show the full snake draft order.")
async def draftorder(interaction: discord.Interaction):
    if not draft["order"]:
        await interaction.response.send_message("❌ No draft has been started.", ephemeral=True)
        return

    lines = []
    for i, owner in enumerate(draft["order"]):
        marker = "🎯 " if i == draft["current_pick"] and draft["active"] else f"{i+1}. "
        lines.append(f"{marker}{owner}")

    embed = discord.Embed(title="📋 Snake Draft Order", description="\n".join(lines), color=0x9b59b6)
    await interaction.response.send_message(embed=embed)


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
    await interaction.response.send_message(f"⏭️ Skipped **{skipped}**'s turn.\n🎯 **{next_owner}** — you're up!")
    if draft["pool_message"]:
        await draft["pool_message"].edit(embed=build_pool_embed())


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


TOKEN = os.getenv("DISCORD_TOKEN")
if not TOKEN:
    raise ValueError("DISCORD_TOKEN environment variable not set!")

bot.run(TOKEN)
