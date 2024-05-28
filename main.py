import discord
from discord.ext import tasks
from discord import app_commands
from dotenv import load_dotenv
import os
from commands import setup_commands
from data_manager import load_summoners_to_watch, summoners_to_watch, notified_summoners, notified_games
from riot_api import fetchGameOngoing, fetchGameResult
import urllib.parse


# Charger les variables d'environnement depuis le fichier .env
load_dotenv()
load_summoners_to_watch()
token = os.getenv("TOKEN_DISCORD")

intents = discord.Intents.default()
client = discord.Client(intents=intents)
tree = app_commands.CommandTree(client)

if not token:
    raise ValueError("TOKEN_DISCORD n'est pas bien définit")


### Loops ###
#Verifie toutes les minutes si un invocateur de la liste est en jeu
@tasks.loop(minutes=1)
async def check_summoners_status():
    global notified_summoners
    for summoner in summoners_to_watch:
        try:
            riot_id, champion_name, game_mode, game_id, champion_icon = fetchGameOngoing(summoner['puuid'])
            if riot_id:
                if summoner['puuid'] not in notified_summoners or notified_summoners[summoner['puuid']] != game_id:
                    channel = discord.utils.get(client.get_all_channels(), name='test')
                    if channel:
                        encoded_name = urllib.parse.quote(summoner['name'])
                        encoded_tag = urllib.parse.quote(summoner['tag'])
                        url = f"https://porofessor.gg/fr/live/euw/{encoded_name}%20-{encoded_tag}"
                        link_text = f"**[En jeu]({url})**"
                        embed = discord.Embed(
                            description=f"{link_text}\n\n{summoner['name']} est en **{game_mode}**. Il joue **{champion_name}**",
                            color=discord.Colour.yellow()
                        )
                        embed.set_thumbnail(url=champion_icon)
                        await channel.send(embed=embed)
                    notified_summoners[summoner['puuid']] = game_id
                    print(f"Added {summoner['name']} to notified_summoners with gameId: {game_id}")
            else:
                if summoner['puuid'] in notified_summoners:
                    del notified_summoners[summoner['puuid']]
        except Exception as e:
            print(f"Erreur de vérification pour {summoner['name']}: {e}")

#Vérifie toutes les 2 minutes si un invocateur de la liste a finit une partie que l'on a annoncée
@tasks.loop(minutes=2)
async def check_finished_games():
    global notified_summoners
    for puuid, game_id in list(notified_summoners.items()):
        try:
            game_result = fetchGameResult(game_id, puuid)
            if game_result:
                channel = discord.utils.get(client.get_all_channels(), name='test')
                gameResult, score, cs, champion, poste, visionScore, side = game_result
                if channel:
                    summoner_name = next((s['name'] for s in summoners_to_watch if s['puuid'] == puuid), "Unknown")
                    embed = discord.Embed(
                        title=f"Partie terminée pour {summoner_name}",
                        description=(
                            f"**Résultat:** {gameResult}\n"
                            f"**Score:** {score}\n"
                            f"**CS:** {cs}\n"
                            f"**Champion:** {champion}\n"
                            f"**Poste:** {poste}\n"
                            f"**Vision Score:** {visionScore}\n"
                            f"**Side:** {side}"
                        ),
                        color=discord.Colour.green() if gameResult == 'Victoire' else discord.Colour.red()
                    )
                    embed.set_thumbnail(url=f'https://cdn.communitydragon.org/latest/champion/{champion}/square')
                    await channel.send(embed=embed)
                del notified_summoners[puuid]
                print(f"Removed {puuid} from notified_summoners after gameId: {game_id}")
        except ValueError as e:
            print(f"Erreur lors de la récupération de la partie: {e}")
        except Exception as e:
            print(f"Unexpected error: {e}")




@client.event
async def on_ready():
    await tree.sync()
    check_summoners_status.start()
    check_finished_games.start()
    print("Bot en ligne")

# Initialiser les commandes
setup_commands(client, tree)

client.run(token)