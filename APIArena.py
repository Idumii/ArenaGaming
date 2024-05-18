#Riot API Arena
from typing import Final
import os
import discord
from discord import app_commands
import requests


intents = discord.Intents.default()
client = discord.Client(intents=intents)
tree = app_commands.CommandTree(client)
key = ('RGAPI-db92ee73-346a-4561-9fdd-cf12fac0815e')


@client.event
async def on_ready():
    print("Bot en ligne")
    try:
        await tree.sync()
    except Exception as e:
        print(e)

@tree.command()
@app_commands.describe(
    first_value='The first value you want to add something to',
    second_value='The value you want to add to the first value',
)
async def add(interaction: discord.Interaction, first_value: int, second_value: int):
    """Adds two numbers together."""
    await interaction.response.send_message(f'{first_value} + {second_value} = {first_value + second_value}')

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
        raise ValueError("Summoner not found")
    elif account_response.status_code != 200:
        raise ValueError("An error occurred while fetching summoner data")

    account_data = account_response.json()
    puuid = account_data['puuid']
    
    summoner_url = f'https://euw1.api.riotgames.com/lol/summoner/v4/summoners/by-puuid/{puuid}?api_key={key}'
    summoner_response = requests.get(summoner_url)
    
    if summoner_response.status_code == 404:
        raise ValueError("Summoner not found")
    elif summoner_response.status_code != 200:
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


    return summonerTagline, summonerGamename, summonerLevel, profileIcon, summonerId, totalMastery_data


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

    return ranks


@tree.command(name='invocateur', description='Profil d\'Invocateur')
@app_commands.describe(pseudo='Nom invocateur', tag='EUW')
async def invocateur(interaction: discord.Interaction, pseudo: str, tag: str):
    await interaction.response.defer()
    try:
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
            tmp = f"{summonerRanks[7]} {summonerRanks[8]} • LP:{summonerRanks[9]} • Victoires: {summonerRanks[10]} • Defaites: {summonerRanks[11]}"
            embed.add_field(name='Solo/Duo', value=tmp, inline=False)
        except:
            embed.add_field(name="Solo/Duo", value="Le joueur n'est pas classé dans ce mode.", inline=False)

            # flex
        try:
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










@tree.command(name='sync', description='Owner Only')
async def sync(interaction: discord.Interaction):
    with open('id.txt') as file:
        idumi = file.read().strip()  # Suppression des espaces et des retours à la ligne éventuels
    
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

with open('token.txt') as file:
    token = file.read()

client.run(token=token)




'''
@bot.event
async def on_ready():
    await tree.sync(guild=discord.Object(id=900706930404769822))
    print("Ready!")

@bot.command(description="Ping")
async def ping(ctx):
    await ctx.send(f'Pong! {bot.latency}!')    








@tree.command(name="Invocateur", description="Donne le profils de l'invocateur souhaité en EUW")
@app_commands.describe(Pseudo="", Tag="")
async def summoner(ctx, *gamename, tagline):
    name = clearGamename(gamename)
    summoner = requestSummoner(name, tagline)
    embed = discord.Embed(title=summoner[1] + " " + summoner[0], description=summoner[2], color=discord.Color.gold)
    embed.set_thumbnail(url=summoner[4])
    await ctx.send(embed=embed)


'''






 






#API Riot + DATA DRAGON

#response = requests.get('https://developer.riotgames.com/apis')
#print(response.status_code)


#tagline = ('EUW')
#gamename = ('Ch Pain Perdu')

#account = requests.get('https://europe.api.riotgames.com/riot/account/v1/accounts/by-riot-id/' + gamename + '/' + tagline + '?api_key=' + key)
#print(account.json())


#puuid = account.json()['puuid']
#print(puuid)

#summoner = requests.get('https://euw1.api.riotgames.com/lol/summoner/v4/summoners/by-puuid/' + puuid + '?api_key=' + key)

#print(summoner.json())
#summonerLevel = summoner.json()['summonerLevel']
#profileIconId = summoner.json()['profileIconId']
#profileIcon = ('https://cdn.communitydragon.org/14.10.1/profile-icon/' + str(profileIconId))
#print(profileIcon)

#summonerDesc = (gamename + ' est au niveau ' + str(summonerLevel)) #Ajouter l'icone et maitrise

#print(summonerDesc)

 

#print("{name} is a level {level} summoner on the {region} server.".format(name=account.name_with_tagline,level=account.level,region=account.region))