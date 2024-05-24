#Riot API Arena
from asyncio import tasks
import json
from typing import Final
from dotenv import load_dotenv
import os
import discord
from discord import app_commands
from discord.ext import tasks
import requests
import aiohttp

load_dotenv()

intents = discord.Intents.default()
client = discord.Client(intents=intents)
tree = app_commands.CommandTree(client)
key = os.getenv('API_RIOT_KEY')


@client.event
async def on_ready():
    print("Bot en ligne")
    try:
        await tree.sync()
    except Exception as e:
        print(e)

#@tree.command()
#@app_commands.describe(
#    first_value='The first value you want to add something to',
#    second_value='The value you want to add to the first value',
#)
#async def add(interaction: discord.Interaction, first_value: int, second_value: int):
#    """Adds two numbers together."""
#    await interaction.response.send_message(f'{first_value} + {second_value} = {first_value + second_value}')

@tree.command(name='ping', description='Latence du bot')
async def slashPing(ctx):
    await ctx.response.send_message(f'Pong! {client.latency}!')    

#@tree.command(name='hello')
#async def hello(intrecation: discord.Integration):
#    await intrecation.response.send_message(f'Coucou')
def clearGamename(gamenameWithspaces):
    result = ""
    for n in gamenameWithspaces:
        result = result + " " + str(n)
    return result

def requestSummoner(name, tag):

    account_url = f'https://europe.api.riotgames.com/riot/account/v1/accounts/by-riot-id/{name}/{tag}?api_key={key}'
    account_response = requests.get(account_url)
    
    if account_response.status_code == 404:
        print('Account N exsite pas')
        raise ValueError("Invocateur n'exsite pas")
        
    elif account_response.status_code != 200:
        print('Erreur dans l obtention des donnes du compte')
        raise ValueError("Erreur lors de l'obtention des données")
        

    account_data = account_response.json()
    puuid = account_data['puuid']
    
    summoner_url = f'https://euw1.api.riotgames.com/lol/summoner/v4/summoners/by-puuid/{puuid}?api_key={key}'
    summoner_response = requests.get(summoner_url)
    
    if summoner_response.status_code == 404:
        print('Invocateur N exsite pas')
        raise ValueError("Invocateur n'exsite pas")
    elif summoner_response.status_code != 200:
        print('Erreur dans l obtention des donnes de l invocateur')
        raise ValueError("Erreur lors de l'obtention des données")

    summoner_data = summoner_response.json()

    summonerId = summoner_data.get('id')

    summonerTagline = account_data.get('tagLine')
    summonerGamename = account_data.get('gameName')
    summonerLevel = "Lvl." + str(summoner_data['summonerLevel'])
    profileIcon = f'https://cdn.communitydragon.org/14.10.1/profile-icon/{summoner_data["profileIconId"]}'

    totalMastery_url = f'https://euw1.api.riotgames.com/lol/champion-mastery/v4/scores/by-puuid/{puuid}?api_key={key}'
    totalMastery_response = requests.get(totalMastery_url)
    totalMastery_data = totalMastery_response.json()


    return summonerTagline, summonerGamename, summonerLevel, profileIcon, summonerId, totalMastery_data, puuid


def fetchRanks(summonerId):
    ranks_url = f'https://euw1.api.riotgames.com/lol/league/v4/entries/by-summoner/{summonerId}?api_key={key}'
    ranks_response = requests.get(ranks_url)
    ranks_data = ranks_response.json()

    calls = {0:"queueType", 1:"tier", 2:"rank", 3:"leaguePoints", 4:"wins", 5:"losses"}
    ranks = []
    try:
        for i in range(3):
            for j in range(6):
                ranks.append(ranks_data[i][calls[j]])
    except:
        pass 
    
    print(ranks)
    return ranks


@tree.command(name='invocateur', description='Profil d\'Invocateur')
@app_commands.describe(pseudo='Nom invocateur', tag='EUW')
async def invocateur(interaction: discord.Interaction, pseudo: str, tag: str):
    await interaction.response.defer()
    try:
        print('Invocateur trouvé')
        summoner = requestSummoner(pseudo, tag)
        summonerRanks = fetchRanks(summonerId=summoner[4])
        embed = discord.Embed(
            title=f"{summoner[1]} #{summoner[0]}",
            description=summoner[2],
            color=discord.Colour.gold()
        )
        embed.add_field(name='Score total de maitrise: ', value=summoner[5])
        
        embed.set_thumbnail(url=summoner[3])

         # Ajout des informations de rang
        for queue_type, rank_info in summonerRanks.items():
            if queue_type == 'RANKED_SOLO_5x5':
                embed.add_field(name='Solo/Duo', value=rank_info, inline=False)
            elif queue_type == 'RANKED_FLEX_SR':
                embed.add_field(name='Flex', value=rank_info, inline=False)
        

        await interaction.followup.send(embed=embed)
    except ValueError as e:
        await interaction.followup.send(f"Error: {str(e)}")
    except Exception as e:
        await interaction.followup.send("Une erreur inattendu est survenue.")
        # Enregistrement de l'erreur pour le débogage
        print(f"Unexpected error: {e}")




### Maitrises ###
def fetchMasteries(puuid, count=1):
    # Charger le fichier JSON local
    with open('champion.json', 'r', encoding='utf-8') as f:
        champion_data = json.load(f)

    # Créer un dictionnaire pour accéder rapidement aux informations des champions par leur ID
    champion_name_dict = {int(info['key']): info['name'] for info in champion_data['data'].values()}

    # Fonction pour obtenir le nom du champion par ID
    def get_champion_name(champion_id):
        return champion_name_dict.get(champion_id, "Unknown Champion")

    # URL pour obtenir les meilleures maîtrises de champion
    bestMasteries_url = f'https://euw1.api.riotgames.com/lol/champion-mastery/v4/champion-masteries/by-puuid/{puuid}/top?count={count}&api_key={key}'
    bestMasteries_response = requests.get(bestMasteries_url)
    bestMasteries_data = bestMasteries_response.json()

    masteries = []
    for mastery in bestMasteries_data:
        championID = mastery['championId']
        championIcon = f'https://cdn.communitydragon.org/14.10.1/champion/{championID}/square'
        championName = get_champion_name(championID)
        championLevel = mastery['championLevel']
        championPoints = mastery['championPoints']
        masteries.append((championIcon, championName, championLevel, championPoints))

    return masteries




# Commande discord Maitrises
@tree.command(name='maitrises', description='Meilleures Maitrises d\'un Invocateur')
@app_commands.describe(pseudo='Nom invocateur', tag='EUW', count='Nombre de champions à afficher (1-5)')
async def maitrises(interaction: discord.Interaction, pseudo: str, tag: str, count: int):
    await interaction.response.defer()
    try:
        if not 1 <= count <= 5:
            await interaction.followup.send("Veuillez spécifier un nombre entre 1 et 5.")
            return

        summoner = requestSummoner(pseudo, tag)
        summonerMasteries = fetchMasteries(puuid=summoner[6], count=count)  # Utilisez l'index correct pour puuid

        embeds = []

        for icon, name, level, points in summonerMasteries:
            embed = discord.Embed(
                title=name,
                color=discord.Colour.dark_green()
            )
            embed.set_thumbnail(url=icon)
            embed.add_field(name='Niveau de maîtrise', value=level, inline=False)
            embed.add_field(name='Points de maîtrise', value=points, inline=False)
            embeds.append(embed)

        # Envoyer les embeds un par un
        for embed in embeds:
            await interaction.followup.send(embed=embed)

    except ValueError as e:
        await interaction.followup.send(f"Error: {str(e)}")
    except Exception as e:
        await interaction.followup.send("Une erreur inattendue est survenue.")
        # Enregistrement de l'erreur pour le débogage
        print(f"Unexpected error: {e}")


    

###Game en cours###
 # Charger le fichier JSON local
with open('champion.json', 'r', encoding='utf-8') as f:
    champion_data = json.load(f)

# Créer un dictionnaire pour accéder rapidement aux informations des champions par leur ID
champion_name_dict = {int(info['key']): info['name'] for info in champion_data['data'].values()}

# Fonction pour obtenir le nom du champion par ID
def get_champion_name(champion_id):
    return champion_name_dict.get(champion_id, "Unknown Champion")   
# Fonction pour récupérer les informations de la partie en cours

# Fonction pour récupérer les informations de la partie en cours
def fetchGameOngoing(puuid):
    spectatorGame_url = f'https://euw1.api.riotgames.com/lol/spectator/v5/active-games/by-summoner/{puuid}?api_key={key}'
    spectatorGame_response = requests.get(spectatorGame_url)
    spectatorGame_data = spectatorGame_response.json()

    if spectatorGame_response.status_code == 404:
        raise ValueError("L'invocateur n'est pas en jeu")
    elif spectatorGame_response.status_code != 200:
        print(spectatorGame_response)
        raise ValueError("Une erreur est sruveneue en voulant recuperer les données de la game")

    queueId = spectatorGame_data['gameQueueConfigId']

    if queueId == 420:
        gameMode = 'Solo/Duo'
    elif queueId == 440:
        gameMode = 'Flex'
    elif queueId == 450:
        gameMode = 'ARAM'
    elif queueId == 900:
        gameMode = 'ARURF'
    elif queueId == 1300:
        gameMode = 'Siège du Nexus'
    elif queueId == 1900:
        gameMode = 'URF'
    elif queueId == 1710:
        gameMode = 'Arena'
    else:
        gameMode = f'Mode non référencé: {queueId}'

    players = spectatorGame_data['participants']

    for player in players:
        if player['puuid'] == puuid:
            championGameId = player['championId']
            championName = get_champion_name(championGameId)
            return player['riotId'], championName, gameMode

    return None, None, None

# Charger la liste des invocateurs à surveiller à partir d'un fichier JSON
try:
    with open('summoners_to_watch.json', 'r', encoding='utf-8') as f:
        summoners_to_watch = json.load(f)
except FileNotFoundError:
    summoners_to_watch = []


# Tâche de fond pour vérifier l'état des invocateurs
@tasks.loop(minutes=1)
async def check_summoners_status():
    for summoner in summoners_to_watch:
        try:
            riot_id, champion_name, game_mode = fetchGameOngoing(summoner['puuid'])
            if riot_id:
                channel = discord.utils.get(client.get_all_channels(), name='test')
                if channel:
                    await channel.send(f"{riot_id} est en {game_mode} et joue {champion_name}.")
        except Exception as e:
            print(f"Error checking status for {summoner['name']}: {e}")


# Démarrer la tâche de fond lors du démarrage du bot
@client.event
async def on_ready():
    print(f"Logged in as {client.user.name}")
    check_summoners_status.start()




# Commande pour ajouter un invocateur à la liste
@tree.command(name='addsummoner', description=('Ajouter un invocateur à la liste pour être notifié quand celui-ci est en game'))
@app_commands.describe(pseudo='Nom invocateur', tag='EUW')
async def addsummoner(interaction: discord.Interaction, pseudo: str, tag: str):
    try:
        name, puuid = await requestSummoner(pseudo, tag)  # Assurez-vous que l'appel est attendu avec await
        summoners_to_watch.append({'name': name, 'puuid': puuid})
        with open('summoners_to_watch.json', 'w', encoding='utf-8') as f:
            json.dump(summoners_to_watch, f, ensure_ascii=False, indent=4)
        await interaction.response.send_message(f"Summoner {name} a été ajouté à la liste.")
    except ValueError as e:
        await interaction.response.send_message(f"Error: {str(e)}")
    except Exception as e:
        await interaction.response.send_message("Une erreur inattendue est survenue.")
        print(f"Unexpected error: {e}")



# Commande discord Game en cours
@tree.command(name='ingame', description='Savoir si un joueur est en jeu')
@app_commands.describe(pseudo='Nom invocateur', tag='EUW')
async def maitrises(interaction: discord.Interaction, pseudo: str, tag: str):
    try:
        summoner = requestSummoner(pseudo, tag)
        summonerInGame = fetchGameOngoing(puuid=summoner[6])

        embed = discord.Embed(
            title=f"{summonerInGame[0]} est en {summonerInGame[2]}",
            description=f"Il joue {summonerInGame[1]}",
            color=discord.Colour.blue()
        )
        await interaction.response.send_message(embed=embed)  # Envoyer la réponse sans différer

    except ValueError as e:
        await interaction.response.send_message(f"Error: {str(e)}", ephemeral=True)
    except Exception as e:
        await interaction.response.send_message("Une erreur inattendue est survenue.", ephemeral=True)
        # Enregistrement de l'erreur pour le débogage
        print(f"Unexpected error: {e}")





### Synchro ###
@tree.command(name='sync', description='Owner Only')
async def sync(interaction: discord.Interaction):
    idumi = os.getenv('ID_IDUMI')
    
    owner_id = int(idumi)  # Assurez-vous que l'ID dans 'id.txt' est un entier et convertissez-le
    
    if interaction.user.id == owner_id:
        await interaction.response.send_message('Synchronization in progress...')
        try:
            await tree.sync()
            await interaction.followup.send('Command tree synced')
            print('Command tree synced')
        except Exception as e:
            await interaction.followup.send(f'Failed to sync commands: {e}')
            print(f'Failed to sync commands: {e}')
    else:
        id = interaction.user.id
        await interaction.response.send_message(f'Seul le développeur peut utiliser cette commande -> {id} / {owner_id}')


token = os.getenv('TOKEN_DISCORD')

client.run(token=token)

