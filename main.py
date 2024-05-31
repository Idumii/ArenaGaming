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
intents.messages = True  # Assurez-vous que les intents sont correctement définis
intents.message_content = True

client = discord.Client(intents=intents)
tree = app_commands.CommandTree(client)

@tasks.loop(minutes=1)
async def check_summoners_status():
    summoners_to_watch = data_manager.summoners
    if not summoners_to_watch:
        return

    print(f"Number of summoners to watch: {len(summoners_to_watch)}")
    for summoner in summoners_to_watch:
        try:
            riot_id, champion_name, game_mode, game_id, champion_icon = fetchGameOngoing(summoner['puuid'])
            if riot_id:
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
            else:
                if any(entry['puuid'] == summoner['puuid'] for entry in data_manager.get_notified_summoners()):
                    data_manager.remove_notified_summoner(summoner['puuid'])
        except Exception as e:
            print(f"Erreur de vérification pour {summoner['name']}: {e}")


@tasks.loop(minutes=2)
async def check_finished_games():
    notified_summoners = data_manager.get_notified_summoners()
    print(notified_summoners)
    if not notified_summoners:
        print("No notified summoners found.")
        return

    for entry in list(notified_summoners):
        puuid = entry['puuid']
        game_id = entry['game_id']
        try:
            print(f"Fetching game result for gameId: {game_id}, puuid: {puuid}")
            game_result = fetchGameResult(game_id, puuid, key)
            if not game_result:
                print(f"No result for finished game check for puuid: {puuid}, game_id: {game_id}")
                continue

            print(f"Game result for puuid: {puuid}, game_id: {game_id}: {game_result}")
            (gameResult, score, cs, champion, poste, visionScore, side, 
             totalDamages, totalDamagesMinutes, pentakills, quadrakills, 
             tripleKills, doubleKills, firstBloodKill, firstTowerKill, 
             formattedGameDuration, gameMode) = game_result

            channel = discord.utils.get(client.get_all_channels(), name='test')
            if channel:
                summoner_name = next((s['name'] for s in data_manager.summoners if s['puuid'] == puuid), "Unknown")
                
                if gameMode == "CLASSIC":
                    title = f"{gameResult} sur la Faille de l'invocateur pour {summoner_name} - {formattedGameDuration}"
                    description = (
                        f"**Champion:** {champion}\n"
                        f"**Side:** {side}\n"   
                        f"**Poste:** {poste}\n"
                        f"**Score:** {score}\n"
                        f"**CS:** {cs}\n"
                        f"**Dégâts:** {totalDamages} - {totalDamagesMinutes}/min\n"
                        f"**Score de vision:** {visionScore}\n"
                        f"**Nombre de pentakills:** {pentakills}\n"
                        f"**Nombre de quadrakills:** {quadrakills}\n"
                        f"**Nombre de triple kills:** {tripleKills}\n"
                        f"**Nombre de double kills:** {doubleKills}\n"
                        f"**Première effusion de sang:** {firstBloodKill}\n"
                        f"**Première tour tuée:** {firstTowerKill}\n"
                    )
                elif gameMode == "ARAM":
                    title = f"{gameResult} en ARAM pour {summoner_name} - {formattedGameDuration}"
                    description = (
                        f"**Champion:** {champion}\n"
                        f"**Side:** {side}\n"   
                        f"**Score:** {score}\n"
                        f"**CS:** {cs}\n"
                        f"**Dégâts:** {totalDamages} - {totalDamagesMinutes}/min\n"
                        f"**Score de vision:** {visionScore}\n"
                    )
                elif gameMode == "CHERRY":
                    title = f"{gameResult} en Arena pour {summoner_name} - {formattedGameDuration}"
                    description = (
                        f"**Champion:** {champion}\n"
                        f"**Score:** {score}\n"
                        f"**Dégâts:** {totalDamages} - {totalDamagesMinutes}/min\n"
                    )
                else:
                    title= f"Erreur en récupérant la partie"

                embed = discord.Embed(
                    title=title,
                    description=description,
                    color=discord.Colour.blue() if gameResult == "Victoire" else discord.Colour.red()
                )
                embed.set_thumbnail(url=f'https://cdn.communitydragon.org/latest/champion/{champion}/square')
                await channel.send(embed=embed)

            data_manager.remove_specific_notified_summoner(puuid, game_id)

        except Exception as e:
            if "Data not found - match file not found" not in str(e):
                print(f"Erreur lors de la vérification des jeux finis pour {puuid}: {e}")


@client.event
async def on_ready():
    await tree.sync()
    print(f"Logged in as {client.user}")
    check_summoners_status.start()
    print("Started check_summoners_status loop")
    check_finished_games.start()
    print("Started check_finished_games loop")

# Initialiser les commandes
setup_commands(client, tree)

client.run(token)