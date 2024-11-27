import discord
from discord.ext import tasks, commands
from discord import app_commands
from dotenv import load_dotenv
import os
from commands import setup_commands
from data_manager import DataManager
from riot_api import fetchGameOngoing, fetchGameResult, key
import urllib.parse

# Charger les variables d'environnement depuis le fichier .env
load_dotenv()

# Initialiser une instance unique de DataManager
data_manager = DataManager()

token = os.getenv('TOKEN_DISCORD')

if not token:
    raise ValueError("TOKEN_DISCORD n'est pas bien défini")

intents = discord.Intents.default()
intents.guilds = True
intents.messages = True
intents.message_content = True

client = discord.Client(intents=intents)
tree = app_commands.CommandTree(client)

@tasks.loop(minutes=1)
async def check_summoners_status():
    try:
        for guild_id in data_manager.summoners_data:
            guild_summoners = data_manager.load_summoners_to_watch(str(guild_id))
            
            if not guild_summoners:
                continue
                
            for summoner in guild_summoners:
                try:
                    if not isinstance(summoner, dict):
                        print(f"Invalid summoner data format: {summoner}")
                        continue
                        
                    riot_id, champion_name, game_mode, game_id, champion_icon = fetchGameOngoing(summoner.get('puuid'))
                    
                    if game_id:
                        print(f"Invoqueur trouvé en jeu: {summoner['name']}, Mode de jeu: {game_mode}, Champion: {champion_name}")
                        notified_summoners = data_manager.get_notified_summoners()
                        if not any(entry['puuid'] == summoner['puuid'] and entry['game_id'] == game_id for entry in notified_summoners):
                            # Move this line inside the if block
                            notification_channel_id = data_manager.get_notification_channel(guild_id)
                            if notification_channel_id:
                                channel = client.get_channel(notification_channel_id)
                                if channel:
                                    encoded_name = urllib.parse.quote(summoner['name'])
                                    url = f"https://porofessor.gg/fr/live/euw/{encoded_name}"
                                    link_text = f"**[En jeu]({url})**"
                                    embed = discord.Embed(
                                        description=f"{link_text}\n\n{summoner['name']} est en **{game_mode}**. Il joue **{champion_name}**",
                                        color=discord.Colour.yellow()
                                    )
                                    embed.set_thumbnail(url=champion_icon)
                                    await channel.send(embed=embed)
                                    data_manager.add_notified_summoner(summoner['puuid'], game_id)
                                    print(f"Notification envoyée pour: {summoner['name']}")
                                else:
                                    print("Canal de notification non trouvé.")
                            else:
                                print("Aucun canal de notification défini.")
                except Exception as e:
                    print(f"Erreur de vérification pour {summoner['name']}: {e}")
    except Exception as e:
            print(f"Erreur générale dans check_summoners_status: {e}")


@tasks.loop(minutes=2)
async def check_finished_games():
    print("Fetching notified summoners...")
    notified_summoners = data_manager.get_notified_summoners()
    if not notified_summoners:
        print("No notified summoners found.")
        return

    for entry in list(notified_summoners):
        puuid = entry['puuid']
        game_id = entry['game_id']
        try:
            print(f"Checking game result for PUUID: {puuid}, Game ID: {game_id}")

            # Find the guild_id and summoner info
            guild_id = None
            summoner_name = None
            for gid, guild_summoners in data_manager.summoners_data.items():
                for s in guild_summoners:
                    if s.get('puuid') == puuid:
                        guild_id = gid
                        summoner_name = s.get('name', 'Unknown')
                        break
                if guild_id:
                    break

            if guild_id is None:
                print(f"Could not find guild_id for PUUID: {puuid}")
                continue

            game_result = fetchGameResult(game_id, puuid, key)
            print(f"Game result for player {puuid} in game {game_id}: {game_result}")

            if not game_result or not isinstance(game_result, tuple):
                print(f"An unexpected result or None was returned for PUUID: {puuid}, Game ID: {game_id}")
                continue

            (gameResult, score, cs, champion, poste, visionScore, side, 
             totalDamages, totalDamagesMinutes, pentakills, quadrakills, 
             tripleKills, doubleKills, firstBloodKill, firstTowerKill, 
             formattedGameDuration, gameMode, killParticipationPercent, arenaTeam, placement, 
             damageSelfMitigated, damageContributionPercent, damageContributionPercentArena, 
             teamBaronKills, teamRiftHeraldKills, teamDragonKills, teamElderDragonKills) = game_result

            print(f"Extracted gameResult: {gameResult}, score: {score}, cs: {cs}, champion: {champion}, gameMode: {gameMode}")

            channel_id = data_manager.get_notification_channel(guild_id)
            if channel_id:
                channel = client.get_channel(channel_id)
                if not channel:
                    print("Canal non trouvé.")
                    continue

                if gameMode == "CLASSIC":
                    title = f"{gameResult} sur la Faille de l'invocateur pour {summoner_name} - {formattedGameDuration}"
                    description = (
                        f"**Champion:** {champion}\n"
                        f"**Side:** {side}\n"   
                        f"**Poste:** {poste}\n"
                        f"**Score:** {score}\n"
                        f"**KP:** {killParticipationPercent}%\n"
                        f"**CS:** {cs}\n"
                        f"**Dégâts:** {totalDamages} - {totalDamagesMinutes}/min | **Contribution aux dégâts de l'équipe:** {damageContributionPercent}%\n"
                        f"**Score de vision:** {visionScore}\n"
                    )
                    
                    # Add team objectives if they are greater than 0
                    team_objects = []
                    if teamBaronKills > 0:
                        team_objects.append(f"{teamBaronKills} Baron(s)")
                    if teamDragonKills > 0:
                        team_objects.append(f"{teamDragonKills} Dragon(s)")
                    if teamRiftHeraldKills > 0:
                        team_objects.append(f"{teamRiftHeraldKills} Herald(s)")
                    if teamElderDragonKills > 0:
                        team_objects.append(f"{teamElderDragonKills} Elder Dragon(s)")
                    if team_objects:
                        description += f"**Objectifs de l'équipe:** {', '.join(team_objects)}\n"

                elif gameMode == "ARAM":
                    title = f"{gameResult} en ARAM pour {summoner_name} - {formattedGameDuration}"
                    description = (
                        f"**Champion:** {champion}\n"
                        f"**Side:** {side}\n"   
                        f"**Score:** {score}\n"
                        f"**KP:** {killParticipationPercent}%\n"
                        f"**CS:** {cs}\n"
                        f"**Dégâts:** {totalDamages} - {totalDamagesMinutes}/min | **Contribution aux dégâts de l'équipe:** {damageContributionPercent}%\n"
                    )
                elif gameMode == "CHERRY":
                    title = f"{gameResult} en Arena pour {summoner_name} - {formattedGameDuration}"
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
                embed.set_thumbnail(url=f'https://cdn.communitydragon.org/latest/champion/{champion}/tile')

                try:
                    await channel.send(embed=embed)
                    print(f"Notification sent for {summoner_name}.")
                except Exception as e:
                    print(f"An error occurred while sending the notification: {e}")

                data_manager.remove_specific_notified_summoner(puuid, game_id)
                print(f"Removed {puuid} with gameId {game_id} from notified_summoners")

        except Exception as e:
            print(f"Error checking finished games for {puuid}: {e}")




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
        print(f"Initialized notification channel setting for new guild {guild.id}")

@client.event
async def on_ready():
    await tree.sync()
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
            print(f"Initialized notification channel setting for guild {guild.id}")
    
    if any(guild_id not in settings['notification_channels'] for guild_id in [str(g.id) for g in client.guilds]):
        data_manager.save_settings(settings)

# Initialiser les commandes
setup_commands(client, tree)

client.run(token)
