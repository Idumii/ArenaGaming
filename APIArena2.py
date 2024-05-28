import discord
from discord.ext import tasks
from discord import app_commands
import os
import requests
import json
import uuid
import urllib.parse
from dotenv import load_dotenv

# Charger les variables d'environnement depuis le fichier .env
load_dotenv()

key = os.getenv("API_RIOT_KEY")
token = os.getenv("TOKEN_DISCORD")

if not key or not token:
    raise ValueError("API_RIOT_KEY or TOKEN_DISCORD environment variables are not set properly")

intents = discord.Intents.default()
client = discord.Client(intents=intents)
tree = app_commands.CommandTree(client)

    

# Charger la liste des invocateurs à surveiller à partir d'un fichier JSON
try:
    with open('summoners_to_watch.json', 'r', encoding='utf-8') as f:
        summoners_to_watch = json.load(f)
except FileNotFoundError:
    summoners_to_watch = []


# Fonction pour générer un identifiant simple
def generate_simple_id():
    return max([s['id'] for s in summoners_to_watch], default=0) + 1

# Fonction pour demander les informations de l'invocateur
async def requestSummoner(name, tag):
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


def clearGamename(gamenameWithspaces):
    result = ""
    for n in gamenameWithspaces:
        result = result + " " + str(n)
    return result

def fetchRanks(summonerId):
    ranks_url = f'https://euw1.api.riotgames.com/lol/league/v4/entries/by-summoner/{summonerId}?api_key={key}'
    ranks_response = requests.get(ranks_url)

    if ranks_response.status_code != 200:
        raise ValueError(f"Erreur lors de la récupération des rangs: {ranks_response.status_code} - {ranks_response.json().get('status', {}).get('message', '')}")

    ranks_data = ranks_response.json()
    print(ranks_data)
    ranks = {}
    for entry in ranks_data:
        queue_type = entry['queueType']
        tier = entry.get('tier', 'Unranked')
        rank = entry.get('rank', '')
        wins = entry.get('wins', 0)
        losses = entry.get('losses', 0)
        win_rate = round(wins / (wins + losses) * 100, 2) if (wins + losses) > 0 else 0
        ranks[queue_type] = f"{tier} {rank} - {wins}W/{losses}L ({win_rate}% WR)"

    return ranks


@tree.command(name='invocateur', description='Profil d\'Invocateur')
@app_commands.describe(pseudo='Nom invocateur', tag='EUW')
async def invocateur(interaction: discord.Interaction, pseudo: str, tag: str):
    await interaction.response.defer()
    try:
        print('Invocateur trouvé')
        summoner = await requestSummoner(pseudo, tag)
        print(f"Summoner ID: {summoner[4]}, PUUID: {summoner[6]}")  # Debugging
        summonerRanks = fetchRanks(summonerId=summoner[4])
        embed = discord.Embed(
            title=f"{summoner[1]} #{tag}",
            description=f"Niveau: {summoner[2]}",
            color=discord.Colour.gold()
        )
        embed.set_thumbnail(url=summoner[3])

        print("Summoner Ranks:", summonerRanks)  # Ajouter cette ligne pour déboguer

        # Ajout des informations de rang
        for queue_type, rank_info in summonerRanks.items():
            if queue_type == 'RANKED_SOLO_5x5':
                embed.add_field(name='Solo/Duo', value=rank_info, inline=False)
            elif queue_type == 'RANKED_FLEX_SR':
                embed.add_field(name='Flex', value=rank_info, inline=False)
            elif queue_type == 'CHERRY':
                embed.add_field(name='Arena', value=rank_info, inline=False)

        await interaction.followup.send(embed=embed)
    except ValueError as e:
        await interaction.followup.send(f"Error: {str(e)}")
    except Exception as e:
        await interaction.followup.send("Une erreur inattendue est survenue.")
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

        summoner = await requestSummoner(pseudo, tag)
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

        for embed in embeds:
            await interaction.followup.send(embed=embed)

    except ValueError as e:
        await interaction.followup.send(f"Error: {str(e)}")
    except Exception as e:
        await interaction.followup.send("Une erreur inattendue est survenue.")
        print(f"Unexpected error: {e}")


summoners_to_watch = []
notified_summoners = {}
notified_games = {}

# Charger le fichier JSON local
with open('champion.json', 'r', encoding='utf-8') as f:
    champion_data = json.load(f)

# Créer un dictionnaire pour accéder rapidement aux informations des champions par leur ID
champion_name_dict = {int(info['key']): info['name'] for info in champion_data['data'].values()}

# Fonction pour obtenir le nom du champion par ID
def get_champion_name(champion_id):
    return champion_name_dict.get(champion_id, "Unknown Champion")

# Fonction pour récupérer les informations de la partie en cours
def fetchGameOngoing(puuid):
    spectatorGame_url = f'https://euw1.api.riotgames.com/lol/spectator/v5/active-games/by-summoner/{puuid}?api_key={key}'
    spectatorGame_response = requests.get(spectatorGame_url)
    if spectatorGame_response.status_code == 404:
        raise ValueError("L'invocateur n'est pas en jeu")
    elif spectatorGame_response.status_code != 200:
        print(spectatorGame_response)
        raise ValueError("Une erreur est survenue en voulant récupérer les données de la game")
    
    spectatorGame_data = spectatorGame_response.json()
    queueId = spectatorGame_data['gameQueueConfigId']
    gameId = spectatorGame_data['gameId']

    game_modes = {
        420: 'Solo/Duo',
        440: 'Flex',
        450: 'ARAM',
        900: 'ARURF',
        1300: 'Siège du Nexus',
        1900: 'URF',
        1700: 'Arena',
        400: 'Normal',
        490: 'Normal',
        0: 'Perso'
    }
    gameMode = game_modes.get(queueId, f'Mode non référencé: {queueId}')

    players = spectatorGame_data['participants']

    for player in players:
        if player['puuid'] == puuid:
            championGameId = player['championId']
            championName = get_champion_name(championGameId)
            championIcon = f'https://cdn.communitydragon.org/latest/champion/{championGameId}/square'
            return player['riotId'], championName, gameMode, gameId, championIcon

    return None, None, None, None, None

# Fonction pour récupérer les résultats de la partie
def fetchGameResult(gameId, puuid):
    match_url = f"https://europe.api.riotgames.com/lol/match/v5/matches/EUW1_{gameId}?api_key={key}"
    match_response = requests.get(match_url)
    match_data = match_response.json()
    
    if 'info' not in match_data:
        raise ValueError(f"Erreur lors de la récupération des résultats de la partie: {match_data.get('status', {}).get('message', 'Unknown error')}")
    
    players = match_data['info']['participants']

    for player in players:
        if player['puuid'] == puuid:
            gameResult = 'Victoire' if player['win'] else 'Défaite'
            score = f"{player['kills']}/{player['deaths']}/{player['assists']}"
            cs = (player['totalMinionsKilled'] + player['neutralMinionsKilled'] + 
                  player['totalAllyJungleMinionsKilled'] + player['totalEnemyJungleMinionsKilled'])
            champion = player['championName']
            poste = player['lane']
            visionScore = player['visionScore']
            side = 'Bleu' if player['teamId'] == 100 else 'Rouge'
            return gameResult, score, cs, champion, poste, visionScore, side

    return None, None, None, None, None, None, None


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


# Charger les invocateurs à surveiller depuis un fichier
def load_summoners_to_watch():
    global summoners_to_watch
    try:
        with open('summoners_to_watch.json', 'r', encoding='utf-8') as f:
            summoners_to_watch = json.load(f)
        print("Summoners to watch loaded successfully.")
    except Exception as e:
        print(f"Failed to load summoners to watch: {e}")

# Commande pour ajouter un invocateur à la liste
@tree.command(name='addsummoner', description='Ajouter un invocateur à la liste pour être notifié quand celui-ci est en game')
@app_commands.describe(pseudo='Nom invocateur', tag='EUW')
async def addsummoner(interaction: discord.Interaction, pseudo: str, tag: str):
    try:
        summoner = await requestSummoner(pseudo, tag)
        summoner_id = len(summoners_to_watch) + 1  # Utiliser un ID numérique simple
        summoners_to_watch.append({'id': summoner_id, 'name': summoner[1], 'tag': tag, 'puuid': summoner[6]})
        with open('summoners_to_watch.json', 'w', encoding='utf-8') as f:
            json.dump(summoners_to_watch, f, ensure_ascii=False, indent=4)
        await interaction.response.send_message(f"Summoner {summoner[1]}#{tag} a été ajouté à la liste avec l'ID {summoner_id}.")
    except ValueError as e:
        await interaction.response.send_message(f"Error: {str(e)}")
    except Exception as e:
        await interaction.response.send_message("Une erreur inattendue est survenue.")
        print(f"Unexpected error: {e}")

# Commande pour supprimer un invocateur de la liste par ID
@tree.command(name='removesummoner', description='Supprimer un invocateur de la liste des suivis par ID')
@app_commands.describe(summoner_id='ID de l\'invocateur')
async def removesummoner(interaction: discord.Interaction, summoner_id: int):
    initial_count = len(summoners_to_watch)
    summoners_to_watch[:] = [s for s in summoners_to_watch if s['id'] != summoner_id]
    if len(summoners_to_watch) < initial_count:
        with open('summoners_to_watch.json', 'w', encoding='utf-8') as f:
            json.dump(summoners_to_watch, f, ensure_ascii=False, indent=4)
        await interaction.response.send_message(f"Invocateur avec l'ID {summoner_id} a été supprimé de la liste.")
    else:
        await interaction.response.send_message(f"Aucun invocateur trouvé avec l'ID {summoner_id}.")



# Commande pour afficher la liste des invocateurs suivis
@tree.command(name='listsummoners', description='Afficher la liste des invocateurs suivis')
async def listsummoners(interaction: discord.Interaction):
    try:
        if not summoners_to_watch:
            await interaction.response.send_message("Aucun invocateur n'est suivi pour le moment.")
        else:
            summoner_list = "\n".join([f"ID: **{summoner['id']}** - {summoner['name']}#{summoner['tag']}" for summoner in summoners_to_watch])
            embed = discord.Embed(description=f"Liste des invocateurs suivis :\n{summoner_list}")
            await interaction.response.send_message(embed=embed)
    except Exception as e:
        await interaction.response.send_message("Une erreur inattendue est survenue.")
        print(f"Unexpected error: {e}")

# Commande discord Game en cours
@tree.command(name='ingame', description='Savoir si un joueur est en jeu')
@app_commands.describe(pseudo='Nom invocateur', tag='EUW')
async def ingame(interaction: discord.Interaction, pseudo: str, tag: str):
    try:
        summoner = await requestSummoner(pseudo, tag)
        summonerInGame = fetchGameOngoing(puuid=summoner[6])

        encoded_name = urllib.parse.quote(summoner[1])
        encoded_tag = urllib.parse.quote(summoner[0])
        url = f"https://porofessor.gg/fr/live/euw/{encoded_name}%20-{encoded_tag}"
        link_text = f"**[En jeu]({url})**"

        embed = discord.Embed(
            description=f"{link_text}\n\n{summoner[1]} est en **{summonerInGame[2]}**. Il joue **{summonerInGame[1]}**",
            color=discord.Colour.blue()
        )
        await interaction.response.send_message(embed=embed)  # Envoyer la réponse sans différer

    except ValueError as e:
        await interaction.response.send_message(f"Error: {str(e)}", ephemeral=True)
    except Exception as e:
        await interaction.response.send_message("Une erreur inattendue est survenue.", ephemeral=True)
        # Enregistrement de l'erreur pour le débogage
        print(f"Unexpected error: {e}")

# Charger les invocateurs à surveiller au démarrage
load_summoners_to_watch()

@client.event
async def on_ready():
    await tree.sync()
    check_summoners_status.start()
    check_finished_games.start()
    print("Bot en ligne")

client.run(token)
