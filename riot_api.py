import requests
from dotenv import load_dotenv
import os
import json
from data_manager import DataManager

data_manager = DataManager()

# Charger les variables d'environnement depuis le fichier .env
load_dotenv()
key = os.getenv("API_RIOT_KEY")

if not key:
    raise ValueError("API_RIOT_KEY n'est pas bien défini")

# Fonction pour demander les informations de l'invocateur
async def requestSummoner(name, tag):
    account_url = f'https://europe.api.riotgames.com/riot/account/v1/accounts/by-riot-id/{name}/{tag}?api_key={key}'
    account_response = requests.get(account_url)

    if account_response.status_code == 404:
        print('Compte n\'existe pas')
        raise ValueError("Invocateur n'existe pas")
    elif account_response.status_code != 200:
        print('Erreur dans l\'obtention des données du compte')
        raise ValueError("Erreur lors de l'obtention des données")

    account_data = account_response.json()
    puuid = account_data['puuid']

    summoner_url = f'https://euw1.api.riotgames.com/lol/summoner/v4/summoners/by-puuid/{puuid}?api_key={key}'
    summoner_response = requests.get(summoner_url)

    if summoner_response.status_code == 404:
        print('Invocateur n\'existe pas')
        raise ValueError("Invocateur n'existe pas")
    elif summoner_response.status_code != 200:
        print('Erreur dans l\'obtention des données de l\'invocateur')
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

# Récupérer les rangs des invocateurs
def fetchRanks(summonerId):
    ranks_url = f'https://euw1.api.riotgames.com/lol/league/v4/entries/by-summoner/{summonerId}?api_key={key}'
    ranks_response = requests.get(ranks_url)

    if ranks_response.status_code != 200:
        raise ValueError(f"Erreur lors de la récupération des rangs: {ranks_response.status_code} - {ranks_response.json().get('status', {}).get('message', '')}")

    ranks_data = ranks_response.json()
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

# Récupérer les meilleures maîtrises d'un invocateur
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
        championIcon = f'https://cdn.communitydragon.org/14.10.1/champion/{championID}/tile'
        championName = get_champion_name(championID)
        championLevel = mastery['championLevel']
        championPoints = mastery['championPoints']
        masteries.append((championIcon, championName, championLevel, championPoints))

    return masteries

# Fonction pour récupérer les informations de la partie en cours
def fetchGameOngoing(puuid):
    spectatorGame_url = f'https://euw1.api.riotgames.com/lol/spectator/v5/active-games/by-summoner/{puuid}?api_key={key}'
    try:
        spectatorGame_response = requests.get(spectatorGame_url)
        
        if spectatorGame_response.status_code == 404:
            return None, None, None, None, None
        elif spectatorGame_response.status_code != 200:
            print(f"Erreur lors de la récupération des données de la partie pour l'invocateur avec puuid {puuid}: {spectatorGame_response.status_code}")
            return None, None, None, None, None
        
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
                championName = data_manager.get_champion_name(champion_id=championGameId)
                championIcon = f'https://cdn.communitydragon.org/14.10.1/champion/{championGameId}/square'
                riotId = player.get('summonerName', 'UnknownSummoner')
                return riotId, championName, gameMode, gameId, championIcon
                
    except Exception as e:
        print(f"Une erreur s'est produite lors de la récupération des informations de jeu en cours pour puuid {puuid}: {e}")
        return None, None, None, None, None

    return None, None, None, None, None

def fetchGameResult(gameId, puuid, key):
    import requests
    
    match_url = f"https://europe.api.riotgames.com/lol/match/v5/matches/EUW1_{gameId}?api_key={key}"
    match_response = requests.get(match_url)
    if match_response.status_code != 200:
        print(f"Failed to fetch match data, status code: {match_response.status_code}, response: {match_response.text}")
        return None

    match_data = match_response.json()
    if 'info' not in match_data:
        print(f"Error fetching game results: {match_data.get('status', {}).get('message', 'Unknown error')}")
        return None
    
    globalInfo = match_data['info']
    players = globalInfo['participants']
    gameDuration = globalInfo['gameDuration']
    gameMode = globalInfo['gameMode']

    if gameDuration > 3600:
        gameDuration = gameDuration // 1000

    gameDurationMinutes = gameDuration // 60
    gameDurationSeconds = gameDuration % 60
    formattedGameDuration = f"{gameDurationMinutes:02}:{gameDurationSeconds:02}"

    for player in players:
        if player['puuid'] == puuid:
            gameResult = 'Victoire' if player['win'] else 'Défaite'
            score = f"{player['kills']}/{player['deaths']}/{player['assists']}"
            cs = (player['totalMinionsKilled'] + player['neutralMinionsKilled'])
            champion = player['championName']
            poste = player['individualPosition']
            visionScore = player['visionScore']
            side = 'Bleu' if player['teamId'] == 100 else 'Rouge'
            totalDamages = player['totalDamageDealtToChampions']
            totalDamagesMinutes = round(totalDamages / gameDurationMinutes, 0)
            pentakills = player['pentaKills']
            quadrakills = player['quadraKills']
            tripleKills = player['tripleKills']
            doubleKills = player['doubleKills']
            firstBloodKill = player.get('firstBloodKill', False)
            firstTowerKill = player.get('firstTowerKill', False)
            killParticipation = player.get('challenges', {}).get('killParticipation', 0)
            killParticipationPercent = round(killParticipation * 100, 2)
            damageSelfMitigated = player.get('damageSelfMitigated', 0)
            placement = player.get('placement', '?')
            playerSubteamId = player.get('playerSubteamId', '?')
            teamBaronKills = player.get('teamBaronKills', '?')
            teamdragonKills = totalTeamDamage = sum([p.get('teamDragonKills', '?') for p in players if p['teamId'] == player['teamId']])
            teamRiftHeraldKills = player.get('teamRiftHeraldKills', '?')
            teamElderDragonKills = player.get('teamElderDragonKills', '?')
            
            # Calculate total team damage
            totalTeamDamage = sum([p['totalDamageDealtToChampions'] for p in players if p['teamId'] == player['teamId']])
            damageContributionPercent = round((totalDamages / totalTeamDamage) * 100, 2)
            
            totalTeamDamageArena = sum([p['totalDamageDealtToChampions'] for p in players if p['playerSubteamId'] == player['playerSubteamId']])
            damageContributionPercentArena = round((totalDamages / totalTeamDamageArena) * 100, 2)

            arena_teams = {
                1: 'Poro',
                2: 'Carapateur',
                3: 'Loup',
                4: 'Sentinelle',
                5: 'Corbin',
                6: 'Krug',
                7: 'Gromp',
                8: 'Sbire'
            }
            arenaTeam = arena_teams.get(playerSubteamId, '?')

            print(f"Game result for player {puuid} in game {gameId}: {gameResult}, {score}, {cs}, {champion}")

            if poste == "TOP":
                poste = "Top"
            elif poste == "JUNGLE":
                poste = "Jungle"
            elif poste == "MIDDLE":
                poste = "Mid"
            elif poste == "BOTTOM":
                poste = "ADC"
            elif poste == "UTILITY":
                poste = "Support"

            return (gameResult, score, cs, champion, poste, visionScore, side, 
                    totalDamages, totalDamagesMinutes, pentakills, quadrakills,
                    tripleKills, doubleKills, firstBloodKill, firstTowerKill,
                    formattedGameDuration, gameMode, killParticipationPercent, arenaTeam,
                    placement, damageSelfMitigated, damageContributionPercent, damageContributionPercentArena, teamBaronKills,teamdragonKills, teamRiftHeraldKills, teamElderDragonKills)

    print(f"Player {puuid} not found in game {gameId}.")
    return (None, None, None, None, None, None, None, None, None, 
            None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None)