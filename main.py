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
    summoners_to_watch = data_manager.summoners
    if not summoners_to_watch:
        print("Aucun invoqueur à surveiller.")
        return

    for summoner in summoners_to_watch:
        try:
            riot_id, champion_name, game_mode, game_id, champion_icon = fetchGameOngoing(summoner['puuid'])
            if riot_id:
                print(f"Invoqueur trouvé en jeu: {summoner['name']}, Mode de jeu: {game_mode}, Champion: {champion_name}")
                notified_summoners = data_manager.get_notified_summoners()
                if not any(entry['puuid'] == summoner['puuid'] and entry['game_id'] == game_id for entry in notified_summoners):
                    channel = discord.utils.get(client.get_all_channels(), name='test')
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
                        print("Canal 'test' non trouvé.")
        except Exception as e:
            print(f"Erreur de vérification pour {summoner['name']}: {e}")

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

            game_result = fetchGameResult(game_id, puuid, key)
            print(f"Fetched game result for {puuid}: {game_result}")

            if not game_result or not isinstance(game_result, tuple):
                print(f"An unexpected result or None was returned for PUUID: {puuid}, Game ID: {game_id}")
                continue

            (gameResult, score, cs, champion, poste, visionScore, side, 
             totalDamages, totalDamagesMinutes, pentakills, quadrakills, 
             tripleKills, doubleKills, firstBloodKill, firstTowerKill, 
             formattedGameDuration, gameMode, killParticipationPercent, arenaTeam, placement, damageSelfMitigated, damageContributionPercent, damageContributionPercentArena, teamBaronKills, teamRiftHeraldKills, teamDragonKills, teamElderDragonKills) = game_result

            print(f"Extracted gameResult: {gameResult}, score: {score}, cs: {cs}, champion: {champion}, gameMode: {gameMode}")

            channel = discord.utils.get(client.get_all_channels(), name='test')
            if not channel:
                print("Canal 'test' non trouvé.")
                continue

            summoner_name = next((s['name'] for s in data_manager.summoners if s['puuid'] == puuid), "Unknown")
            print(f"Preparing to send notification for {summoner_name}")

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
                    f"**Test Objectif**: {teamBaronKills}(Baron)\n"
                )
                
                # Add team objectives if they are greater than 0
                team_objects = []
                if teamBaronKills > 0:
                    team_objects.append(f"{teamBaronKills} Baron(s)")
                if teamRiftHeraldKills > 0:
                    team_objects.append(f"{teamRiftHeraldKills} Herald(s)")
                if teamDragonKills > 0:
                    team_objects.append(f"{teamDragonKills} Dragon(s)")
                if teamElderDragonKills > 0:
                    team_objects.append(f"{teamElderDragonKills} Elder Dragon(s)")
                print(team_objects)
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
            else:
                title = f"Erreur lors de la récupération de la partie"
                description = ""

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
            embed.set_thumbnail(url=f'https://cdn.communitydragon.org/latest/champion/{champion}/square')

            print(f"Sending embed\nTitle: {title}\nDescription: {description}")

            try:
                await channel.send(embed=embed)
                print(f"Notification sent for {summoner_name}.")
            except Exception as e:
                print(f"An error occurred while sending the notification: {e}")

            data_manager.remove_specific_notified_summoner(puuid, game_id)
            print(f"Removed {puuid} with gameId {game_id} from notified_summoners")
        except Exception as e:
            if "Data not found - match file not found" not in str(e):
                print(f"Error checking finished games for {puuid}: {e}")

@client.event
async def on_ready():
    await tree.sync()
    check_summoners_status.start()
    check_finished_games.start()

# Initialiser les commandes
setup_commands(client, tree)

client.run(token)