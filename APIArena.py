#Riot API Arena
import json
from typing import Final
from dotenv import load_dotenv
import os
import discord
from discord import app_commands
import requests

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
        raise ValueError("Summoner not found")
        
    elif account_response.status_code != 200:
        print('Erreur dans l obtention des donnes du compte')
        raise ValueError("An error occurred while fetching summoner data")
        

    account_data = account_response.json()
    puuid = account_data['puuid']
    
    summoner_url = f'https://euw1.api.riotgames.com/lol/summoner/v4/summoners/by-puuid/{puuid}?api_key={key}'
    summoner_response = requests.get(summoner_url)
    
    if summoner_response.status_code == 404:
        print('Invocateur N exsite pas')
        raise ValueError("Summoner not found")
    elif summoner_response.status_code != 200:
        print('Erreur dans l obtention des donnes de l invocateur')
        raise ValueError("An error occurred while fetching summoner data")

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
        

        # solo duo
        try:
            print('Rang trouvé')
            tmp = f"{summonerRanks[7]} {summonerRanks[8]} • LP:{summonerRanks[9]} • Victoires: {summonerRanks[10]} • Defaites: {summonerRanks[11]}"
            embed.add_field(name='Solo/Duo', value=tmp, inline=False)
        except:
            embed.add_field(name="Solo/Duo", value="Le joueur n'est pas classé dans ce mode.", inline=False)

            # flex
        try:
            print('Rang trouvé')
            tmp = f"{summonerRanks[1]} {summonerRanks[2]} • LP:{summonerRanks[3]} • Victoires: {summonerRanks[4]} • Defaites: {summonerRanks[5]}"
            embed.add_field(name='Flex', value=tmp, inline=False)
        except:
            embed.add_field(name="Flex", value="Le joueur n'est pas classé dans ce mode.", inline=False)




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




# Commande discord
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

