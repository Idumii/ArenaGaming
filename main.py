from datetime import datetime, timedelta
import traceback
import discord
from discord.ext import tasks, commands
from discord import app_commands
from dotenv import load_dotenv
import os
from commands import setup_commands
from data_manager import DataManager
from riot_api import fetchGameOngoing, fetchGameResult, key, fetchRanks, requestSummoner
import urllib.parse


# Charger les variables d'environnement depuis le fichier .env
load_dotenv()

# Initialiser une instance unique de DataManager
data_manager = DataManager()

token = os.getenv('TOKEN_DISCORD')
key = os.getenv('API_RIOT_KEY')

if not token:
    raise ValueError("TOKEN_DISCORD n'est pas bien défini")

intents = discord.Intents.default()
intents.guilds = True
intents.messages = True
intents.message_content = True

client = discord.Client(intents=intents)
tree = app_commands.CommandTree(client)


@tasks.loop(seconds=30)
async def check_summoners_status():
    try:
        active_games = {}  # {game_id: {players: [], notified_guilds: set()}}
        notified_games = data_manager.get_notified_summoners()

        # First pass: collect all active games and players
        for guild_id in data_manager.summoners_data:
            summoners = data_manager.load_summoners_to_watch(guild_id)

            for summoner in summoners:
                try:
                    game_info = fetchGameOngoing(puuid=summoner['puuid'])
                    
                    # Validate game info
                    if (not game_info or 
                        not all(game_info) or
                        game_info[1] == "None" or  
                        game_info[2] == "None" or  
                        not game_info[3]):  
                        continue

                    riot_id, champion_name, game_mode, game_id, champion_icon = game_info

                    # Check if already globally notified
                    already_notified = any(
                        game['puuid'] == summoner['puuid'] and 
                        game['game_id'] == game_id 
                        for game in notified_games
                    )

                    if not already_notified:
                        if game_id not in active_games:
                            active_games[game_id] = {
                                'players': [],
                                'notified_guilds': set(),
                                'game_mode': game_mode
                            }
                        
                        # Add player if not already added
                        if not any(p['puuid'] == summoner['puuid'] for p in active_games[game_id]['players']):
                            active_games[game_id]['players'].append({
                                **summoner,
                                'champion_name': champion_name,
                                'champion_icon': champion_icon,
                                'tracking_guilds': {guild_id}
                            })
                        else:
                            # Add this guild to player's tracking guilds
                            for player in active_games[game_id]['players']:
                                if player['puuid'] == summoner['puuid']:
                                    player['tracking_guilds'].add(guild_id)

                except Exception as e:
                    print(f"Error checking summoner {summoner['name']}: {str(e)}")
                    continue

        # Second pass: process each active game
        for game_id, game_data in active_games.items():
            game_mode = game_data['game_mode']
            
            print(f"Debug - Processing game {game_id}")
            print(f"Debug - Players in game: {[p['name'] for p in game_data['players']]}")

            # Process each player
            for player in game_data['players']:
                try:
                    # Get summoner data for all game modes
                    summoner_data = await requestSummoner(player['name'], player['tag'], key)
                    if not summoner_data:
                        print(f"Debug - Could not get summoner data for {player['name']}")
                        continue

                    summoner_id = summoner_data[4]

                    # Store LP data only for ranked games
                    if "RANKED" in game_mode.upper() or game_mode in ["Solo/Duo", "Flex"]:
                        ranks = fetchRanks(summoner_id)
                        print(f"Debug - Storing LP for {player['name']}")
                        
                        for queue_type, rank_data in ranks.items():
                            if queue_type in ["RANKED_SOLO_5x5", "RANKED_FLEX_SR"]:
                                data_manager.store_temp_lp(
                                    summoner_id,
                                    queue_type,
                                    rank_data['lp'],
                                    rank_data['tier'],
                                    rank_data['rank']
                                )

                    # Create and send notifications
                    encoded_name = urllib.parse.quote(player['name'])
                    encoded_tag = urllib.parse.quote(player['tag'])
                    porofessor_url = f"https://porofessor.gg/fr/live/euw/{encoded_name}-{encoded_tag}"

                    embed = discord.Embed(
                        title="En jeu",
                        url=porofessor_url,
                        description=f"**{player['name']}** est en **{game_mode}**. Il joue **{player['champion_name']}**",
                        color=discord.Colour.yellow()
                    )
                    embed.set_thumbnail(url=player['champion_icon'])

                    # Send to each guild tracking this player
                    for guild_id in player['tracking_guilds']:
                        channel_id = data_manager.get_notification_channel(guild_id)
                        if not channel_id:
                            continue
                        channel = client.get_channel(channel_id)
                        if not channel:
                            continue

                        await channel.send(embed=embed)
                        print(f"Notification envoyée pour: {player['name']} dans le serveur: {guild_id}")

                    # Add to notified games
                    data_manager.add_notified_summoner(player['puuid'], game_id, summoner_id)
                    print(f"Debug - Added to notified games: {player['name']}, Game ID: {game_id}")

                except Exception as e:
                    print(f"Error processing player {player['name']}: {str(e)}")
                    continue

    except Exception as e:
        print(f"Error in check_summoners_status: {str(e)}")
        import traceback
        print(f"Debug - Full error traceback:\n{traceback.format_exc()}")





@tasks.loop(seconds=60)
async def check_finished_games():
    try:
        notified_games = data_manager.get_notified_summoners()
        print(f"Fetching notified summoners...")
        print(f"Debug - Current notified games: {notified_games}")  # Debug print
        if not notified_games:
            print("No notified summoners found.")
            return

        for game in notified_games:
            puuid = game['puuid']
            game_id = game['game_id']
            print(f"Debug - Processing game_id: {game_id} for puuid: {puuid}")  # Debug print

            # Fetch game result
            game_result = fetchGameResult(game_id, puuid)
            if game_result:
                print(f"Debug - Game result found for {game_id}")  # Debug print
                print(f"Debug - Game mode: {game_result[16]}")  # Debug print for game mode

                # Find the summoner in all guilds
                found_summoner = None
                found_channel = None
                
                # Search through all guilds
                for guild_id in data_manager.summoners_data:
                    try:
                        print(f"Debug - Processing guild: {guild_id}")
                        summoners = data_manager.load_summoners_to_watch(guild_id)
                        print(f"Debug - Loaded summoners: {summoners}")
                        channel_id = data_manager.get_notification_channel(guild_id)
                        
                        if not channel_id:
                            continue
                            
                        channel = client.get_channel(channel_id)
                        if not channel:
                            continue

                        # Find the summoner in this guild
                        summoner = next((s for s in summoners if s['puuid'] == puuid), None)
                        if summoner:
                            print(f"Debug - Found summoner in guild: {summoner}")
                            found_summoner = summoner
                            found_channel = channel
                            
                            # Get summoner data to get ranks
                            try:
                                summoner_data = await requestSummoner(summoner['name'], summoner['tag'], key)
                                print(f"Debug - Summoner data received: {summoner_data}")
                                
                                if not summoner_data:
                                    print(f"No summoner data received for {summoner['name']}")
                                    continue

                                summoner_id = summoner_data[4]
                                print(f"Debug - Extracted summoner ID: {summoner_id}")
                                print(f"Debug - Type of summoner_id: {type(summoner_id)}")

                                # Get current ranks
                                ranks = fetchRanks(summoner_id)
                                print(f"Debug - Ranks data: {ranks}")
                                print(f"Debug - Type of ranks: {type(ranks)}")
                                lp_changes = []

                                # Check stored LP
                                stored_lp_data = data_manager.get_stored_lp(summoner_id, "RANKED_SOLO_5x5")
                                print(f"Debug - Stored Solo/Duo LP data: {stored_lp_data}")
                                stored_lp_data_flex = data_manager.get_stored_lp(summoner_id, "RANKED_FLEX_SR")
                                print(f"Debug - Stored Flex LP data: {stored_lp_data_flex}")

                                # Process LP changes
                                lp_changes = []
                                for queue_type, rank_data in ranks.items():
                                    if queue_type in ["RANKED_SOLO_5x5", "RANKED_FLEX_SR"]:
                                        stored_lp = data_manager.get_stored_lp(summoner_id, queue_type)
                                        print(f"Debug - Queue: {queue_type}")
                                        print(f"Debug - Current rank data: {rank_data}")
                                        print(f"Debug - Stored LP data: {stored_lp}")
                                        
                                        if stored_lp:
                                            queue_name = "**Solo/duo**" if queue_type == "RANKED_SOLO_5x5" else "**Flex**"
                                            current_lp = rank_data['lp']
                                            current_tier = rank_data['tier']
                                            current_rank = rank_data['rank']
                                            
                                            if stored_lp['tier'] != current_tier or stored_lp['rank'] != current_rank:
                                                change_msg = f"{queue_name}: {stored_lp['tier']} {stored_lp['rank']} → {current_tier} {current_rank}"
                                                print(f"Debug - Division change detected: {change_msg}")
                                                lp_changes.append(change_msg)
                                            else:
                                                lp_diff = current_lp - stored_lp['lp']
                                                if lp_diff != 0:
                                                    lp_change_str = f"({'+' if lp_diff > 0 else ''}{lp_diff})"
                                                    change_msg = f"{queue_name}: **{current_tier}** {current_rank} {stored_lp['lp']} -> {current_lp} LP {lp_change_str}"
                                                    print(f"Debug - LP change detected: {change_msg}")
                                                    lp_changes.append(change_msg)
                                        else:
                                            print(f"Debug - No stored LP data found for {queue_type}")

                                    print(f"Debug - Final LP changes to display: {lp_changes}")

                            except Exception as e:
                                print(f"Error processing summoner data: {str(e)}")
                                import traceback
                                print(f"Debug - Full error traceback:\n{traceback.format_exc()}")
                                continue

                            # Rest of the embed creation code...
                            game_result = fetchGameResult(game_id, puuid)
                            if not game_result or not isinstance(game_result, tuple):
                                print(
                                    f"Invalid game result returned for PUUID: {puuid}, Game ID: {game_id}")
                                continue

                            (gameResult, score, cs, champion, poste, visionScore, side,
                            totalDamages, totalDamagesMinutes, pentakills, quadrakills,
                            tripleKills, doubleKills, firstBloodKill, firstTowerKill,
                            formattedGameDuration, gameMode, killParticipationPercent, arenaTeam, placement,
                            damageSelfMitigated, damageContributionPercent, damageContributionPercentArena,
                            teamBaronKills, teamRiftHeraldKills, teamDragonKills, teamElderDragonKills) = game_result




                            if gameMode == "CLASSIC":
                                title = f"{gameResult} sur la Faille de l'invocateur pour {summoner_data[1]} - {formattedGameDuration}"

                                # Start description with LP changes if available
                                description = ""
                                if lp_changes:
                                    # Add LP changes without a header, just the changes themselves
                                    description = "\n".join(lp_changes) + "\n\n" + description
                                    description += "\n"  # Add extra newline for spacing

                                print(f"Debug - Final description start: {description[:200]}")  # Show start of description

                                description += (
                                    f"**Champion:** {champion}\n"
                                    f"**Side:** {side}\n"
                                    f"**Poste:** {poste}\n"
                                    f"**Score:** {score}\n"
                                    f"**KP:** {killParticipationPercent}%\n"
                                    f"**CS:** {cs}\n"
                                    f"**Dégâts:** {totalDamages} - {totalDamagesMinutes}/min | **Contribution aux dégâts de l'équipe:** {damageContributionPercent}%\n"
                                    f"**Score de vision:** {visionScore}\n"
                                )

                                team_objects = []
                                if teamBaronKills > 0:
                                    team_objects.append(f"{teamBaronKills} Baron(s)")
                                if teamDragonKills > 0:
                                    team_objects.append(f"{teamDragonKills} Dragon(s)")
                                if teamRiftHeraldKills > 0:
                                    team_objects.append(
                                        f"{teamRiftHeraldKills} Herald(s)")
                                if teamElderDragonKills > 0:
                                    team_objects.append(
                                        f"{teamElderDragonKills} Elder Dragon(s)")
                                if team_objects:
                                    description += f"**Objectifs de l'équipe:** {', '.join(team_objects)}\n"

                            elif gameMode == "ARAM":
                                title = f"{gameResult} en ARAM pour {summoner_data[1]} - {formattedGameDuration}"
                                description = (
                                    f"**Champion:** {champion}\n"
                                    f"**Side:** {side}\n"
                                    f"**Score:** {score}\n"
                                    f"**KP:** {killParticipationPercent}%\n"
                                    f"**CS:** {cs}\n"
                                    f"**Dégâts:** {totalDamages} - {totalDamagesMinutes}/min | **Contribution aux dégâts de l'équipe:** {damageContributionPercent}%\n"
                                )
                            elif gameMode == "CHERRY":
                                title = f"{gameResult} en Arena pour {summoner_data[1]} - {formattedGameDuration}"
                                description = (
                                    f"**Top {placement}**\n"
                                    f"**Equipe {arenaTeam}**\n"
                                    f"**Champion:** {champion}\n"
                                    f"**Score:** {score}\n"
                                    f"**Dégâts:** {totalDamages} - {totalDamagesMinutes}/min | **Contribution aux dégâts de l'équipe:** {damageContributionPercentArena}%\n"
                                    f"**Dégâts Subis:** {damageSelfMitigated}\n"
                                )

                            if pentakills > 0:
                                description += f"**Nombre de pentakills:** {pentakills}\n"
                            if quadrakills > 0:
                                if gameMode == "ARAM":
                                    description += f"**OMG {quadrakills} EXPLOITS DU QUADRAKILL** \n"
                                else:
                                    description += f"**Nombre de quadrakills:** {quadrakills}\n"
                            if tripleKills > 0:
                                description += f"**Nombre de triple kills:** {tripleKills}\n"
                            if doubleKills > 0:
                                description += f"**Nombre de double kills:** {doubleKills}\n"
                            if firstBloodKill:
                                description += f"**Premier sang:** :white_check_mark: \n"
                            if firstTowerKill:
                                description += f"**Première tour tuée:** :white_check_mark: \n"




                            embed = discord.Embed(
                            title=title,
                            description=description,
                            color=discord.Colour.green() if gameResult == "Victoire" else discord.Colour.red()
                            )
                            embed.set_thumbnail(
                                url=f'https://cdn.communitydragon.org/latest/champion/{champion}/tile')

                            await channel.send(embed=embed)
                            print(f"Notification sent for {summoner_data[2]}.")




                    except Exception as e:
                        print(f"Error processing guild {guild_id}: {str(e)}")
                        import traceback
                        print(f"Debug - Full error traceback:\n{traceback.format_exc()}")
                        continue

                # Cleanup after processing all guilds
                data_manager.remove_specific_notified_summoner(puuid, game_id)
                if found_summoner:
                    data_manager.clear_temp_lp(summoner_id)
                    print(f"Processed and cleaned up game data for {found_summoner['name']}")

    except Exception as e:
        print(f"Error in check_finished_games: {str(e)}")
        import traceback
        print(f"Debug - Full error traceback:\n{traceback.format_exc()}")


# Add to main.py

@tasks.loop(hours=24)
async def check_daily_ranks():
    try:
        # Wait until 9 AM
        now = datetime.now()
        next_run = now.replace(hour=9, minute=0, second=0, microsecond=0)
        if now >= next_run:
            next_run = next_run + timedelta(days=1)
        await discord.utils.sleep_until(next_run)
        
        print("Starting daily rank check...")
        processed_summoners = set()  # Track processed summoners to avoid duplicates

        for guild_id in data_manager.summoners_data:
            summoners = data_manager.load_summoners_to_watch(guild_id)
            channel_id = data_manager.get_notification_channel(guild_id)
            if not channel_id:
                continue
            channel = client.get_channel(channel_id)
            if not channel:
                continue

            for summoner in summoners:
                if summoner['puuid'] in processed_summoners:
                    continue

                try:
                    # Get current ranks
                    summoner_data = await requestSummoner(summoner['name'], summoner['tag'], key)
                    if not summoner_data:
                        continue

                    summoner_id = summoner_data[4]
                    ranks = fetchRanks(summoner_id)
                    
                    # Store today's ranks
                    data_manager.store_daily_rank(summoner_id, ranks)
                    
                    # Check for changes
                    changes = data_manager.get_daily_rank_changes(summoner_id)
                    if changes:
                        # Create embed for rank changes
                        embed = discord.Embed(
                            title=f"Évolution du rang - {summoner['name']}",
                            color=discord.Color.blue(),
                            timestamp=datetime.now()
                        )

                        for change in changes:
                            if change['change_type'] == 'division':
                                value = f"**{change['old']}** → **{change['new']}**"
                                if change['lp_change'] != 0:
                                    value += f"\nLP: {'+' if change['lp_change'] > 0 else ''}{change['lp_change']}"
                            else:
                                value = f"**{change['tier']} {change['rank']}**\nLP: {'+' if change['lp_change'] > 0 else ''}{change['lp_change']}"
                            
                            embed.add_field(
                                name=f"Queue {change['queue']}",
                                value=value,
                                inline=False
                            )

                        # Send to all guilds tracking this summoner
                        for guild_id in data_manager.summoners_data:
                            guild_summoners = data_manager.load_summoners_to_watch(guild_id)
                            if any(s['puuid'] == summoner['puuid'] for s in guild_summoners):
                                channel_id = data_manager.get_notification_channel(guild_id)
                                if channel_id:
                                    channel = client.get_channel(channel_id)
                                    if channel:
                                        await channel.send(embed=embed)

                    processed_summoners.add(summoner['puuid'])

                except Exception as e:
                    print(f"Error processing daily ranks for {summoner['name']}: {str(e)}")
                    continue

    except Exception as e:
        print(f"Error in daily rank check: {str(e)}")
        import traceback
        print(f"Debug - Full error traceback:\n{traceback.format_exc()}")





@client.event
async def on_guild_join(guild):
    """Handle new guild joins"""
    guild_id = str(guild.id)
    if guild_id not in data_manager.summoners_data:  # Changed from summoners
        data_manager.summoners_data[guild_id] = []  # Changed from summoners
        data_manager.save_summoners_to_watch([], guild_id)
        print(f"Initialized empty summoner list for new guild {guild.id}")

    # Initialize notification channel setting
    settings = data_manager.load_settings()
    if 'notification_channels' not in settings:
        settings['notification_channels'] = {}
    if guild_id not in settings['notification_channels']:
        settings['notification_channels'][guild_id] = None
        data_manager.save_settings(settings)
        print(
            f"Initialized notification channel setting for new guild {guild.id}")


@client.event
async def on_ready():
    print(f'Bot is ready as {client.user}')
    try:
        synced = await tree.sync()
        print(f"Synced {len(synced)} command(s)")
    except Exception as e:
        print(f"Failed to sync commands: {e}")
    check_summoners_status.start()
    check_finished_games.start()

    settings = data_manager.load_settings()
    if 'notification_channels' not in settings:
        settings['notification_channels'] = {}

    # Only initialize guilds that don't have settings yet
    for guild in client.guilds:
        guild_id = str(guild.id)
        if guild_id not in data_manager.summoners_data:
            data_manager.summoners_data[guild_id] = []
            data_manager.save_summoners_to_watch([], guild_id)
            print(f"Initialized empty summoner list for new guild {guild.id}")

        if guild_id not in settings['notification_channels']:
            settings['notification_channels'][guild_id] = None
            print(
                f"Initialized notification channel setting for guild {guild.id}")

    if any(guild_id not in settings['notification_channels'] for guild_id in [str(g.id) for g in client.guilds]):
        data_manager.save_settings(settings)

    check_daily_ranks.start()
    
# Initialiser les commandes
setup_commands(client, tree)

client.run(token)
