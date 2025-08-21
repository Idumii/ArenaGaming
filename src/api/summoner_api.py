"""
Client API pour les endpoints Riot Games - Summoner
"""
import aiohttp
import asyncio
from typing import Optional, Dict, Any
from urllib.parse import quote
import structlog
from ..models.game_models import Summoner, RankedInfo
from ..utils.rate_limiter import RateLimiter
from ..config.settings import get_settings
import json
import os

logger = structlog.get_logger()

class SummonerAPI:
    """Client pour les endpoints liés aux invocateurs"""
    
    def __init__(self):
        self.settings = get_settings()
        self.rate_limiter = RateLimiter()
        self.base_url = "https://{region}.api.riotgames.com"
        self.champion_data = self._load_champion_data()
        
    def _load_champion_data(self) -> Dict[int, str]:
        """Charger les données des champions depuis le fichier JSON"""
        try:
            champion_path = os.path.join(os.path.dirname(__file__), "..", "..", "data", "champion.json")
            with open(champion_path, 'r', encoding='utf-8') as f:
                champion_data = json.load(f)
            
            # Créer un dictionnaire ID -> nom
            champion_name_dict = {}
            for info in champion_data['data'].values():
                champion_name_dict[int(info['key'])] = info['name']
            
            logger.info(f"Chargement de {len(champion_name_dict)} champions")
            return champion_name_dict
        except Exception as e:
            logger.error(f"Erreur chargement champion.json: {e}")
            return {}
        
    async def get_summoner_by_riot_id(self, game_name: str, tag_line: str, region: str = "europe") -> Optional[Summoner]:
        """
        Récupérer un invocateur par son Riot ID (nom#tag)
        """
        try:
            # D'abord récupérer le PUUID via l'API Account
            # Encoder correctement les caractères spéciaux dans l'URL
            encoded_game_name = quote(game_name, safe='')
            encoded_tag_line = quote(tag_line, safe='')
            account_url = f"https://{region}.api.riotgames.com/riot/account/v1/accounts/by-riot-id/{encoded_game_name}/{encoded_tag_line}"
            
            async with aiohttp.ClientSession() as session:
                await self.rate_limiter.wait()
                
                async with session.get(
                    account_url,
                    params={"api_key": self.settings.riot_api_key}
                ) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        if response.status == 404:
                            logger.warning(f"Joueur non trouvé: {game_name}#{tag_line}")
                        else:
                            logger.warning(f"Erreur récupération compte {game_name}#{tag_line}: {response.status} - {error_text}")
                        return None
                    
                    account_data = await response.json()
                    puuid = account_data["puuid"]
                    
                # Ensuite récupérer les infos summoner via l'endpoint PUUID
                summoner_url = f"https://euw1.api.riotgames.com/lol/summoner/v4/summoners/by-puuid/{puuid}"
                
                await self.rate_limiter.wait()
                async with session.get(
                    summoner_url,
                    headers={"X-Riot-Token": self.settings.riot_api_key}
                ) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        logger.warning(f"Erreur récupération summoner pour PUUID {puuid}: {response.status} - {error_text}")
                        return None
                    
                    summoner_data = await response.json()
                    
                    # Vérifier si 'id' existe, sinon utiliser une valeur par défaut
                    summoner_id = summoner_data.get("id", summoner_data.get("accountId", puuid[:22]))
                    
                    return Summoner(
                        puuid=puuid,
                        summoner_id=summoner_id,
                        name=game_name,
                        tag_line=tag_line,
                        profile_icon_id=summoner_data["profileIconId"],
                        summoner_level=summoner_data["summonerLevel"]
                    )
                    
        except Exception as e:
            logger.error(f"Erreur récupération summoner {game_name}#{tag_line}: {e}")
            return None
    
    async def get_summoner_by_puuid(self, puuid: str) -> Optional[Summoner]:
        """Récupérer un invocateur par son PUUID"""
        try:
            summoner_url = f"https://euw1.api.riotgames.com/lol/summoner/v4/summoners/by-puuid/{puuid}"
            
            async with aiohttp.ClientSession() as session:
                await self.rate_limiter.wait()
                
                async with session.get(
                    summoner_url,
                    params={"api_key": self.settings.riot_api_key}
                ) as response:
                    if response.status != 200:
                        return None
                    
                    data = await response.json()
                    
                    # Récupérer aussi le Riot ID
                    account_url = f"https://europe.api.riotgames.com/riot/account/v1/accounts/by-puuid/{puuid}"
                    
                    await self.rate_limiter.wait()
                    async with session.get(
                        account_url,
                        params={"api_key": self.settings.riot_api_key}
                    ) as response:
                        if response.status == 200:
                            account_data = await response.json()
                            game_name = account_data.get("gameName", "Unknown")
                            tag_line = account_data.get("tagLine", "NA1")
                        else:
                            game_name = "Unknown"
                            tag_line = "NA1"
                    
                    return Summoner(
                        puuid=puuid,
                        summoner_id=data.get("id", data.get("accountId", puuid[:22])),
                        name=game_name,
                        tag_line=tag_line,
                        profile_icon_id=data["profileIconId"],
                        summoner_level=data["summonerLevel"]
                    )
                    
        except Exception as e:
            logger.error(f"Erreur récupération summoner par PUUID {puuid}: {e}")
            return None

    async def get_summoner_by_riot_id_tft(self, game_name: str, tag_line: str, region: str = "europe") -> Optional[Summoner]:
        """
        Récupérer un invocateur par son Riot ID en utilisant la clé TFT (pour obtenir le PUUID TFT)
        """
        try:
            # Récupérer le PUUID via l'API Account avec la clé TFT
            encoded_game_name = quote(game_name, safe='')
            encoded_tag_line = quote(tag_line, safe='')
            account_url = f"https://{region}.api.riotgames.com/riot/account/v1/accounts/by-riot-id/{encoded_game_name}/{encoded_tag_line}"
            
            async with aiohttp.ClientSession() as session:
                await self.rate_limiter.wait()
                
                async with session.get(
                    account_url,
                    params={"api_key": self.settings.riot_tft_api_key}  # Utiliser la clé TFT
                ) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        if response.status == 404:
                            logger.warning(f"Joueur TFT non trouvé: {game_name}#{tag_line}")
                        else:
                            logger.warning(f"Erreur récupération compte TFT {game_name}#{tag_line}: {response.status} - {error_text}")
                        return None
                    
                    account_data = await response.json()
                    puuid = account_data["puuid"]
                    logger.info(f"PUUID TFT récupéré: {puuid}")
                
                # Récupérer les détails du summoner via TFT API
                summoner_url = f"https://euw1.api.riotgames.com/tft/summoner/v1/summoners/by-puuid/{puuid}"
                
                await self.rate_limiter.wait()
                async with session.get(
                    summoner_url,
                    params={"api_key": self.settings.riot_tft_api_key}
                ) as response:
                    if response.status != 200:
                        logger.warning(f"Erreur récupération summoner TFT: {response.status}")
                        return None
                    
                    summoner_data = await response.json()
                    logger.info(f"DEBUG TFT summoner data complet: {summoner_data}")
                    
                    # Les données TFT summoner ne contiennent pas toujours d'ID
                    summoner_id = summoner_data.get("id", puuid[:22])  # Fallback au PUUID tronqué
                    
                    return Summoner(
                        puuid=puuid,
                        summoner_id=summoner_id,
                        name=account_data["gameName"],
                        tag_line=account_data["tagLine"],
                        profile_icon_id=summoner_data["profileIconId"],
                        summoner_level=summoner_data["summonerLevel"]
                    )
                    
        except Exception as e:
            logger.error(f"Erreur récupération summoner TFT {game_name}#{tag_line}: {e}")
            return None
    
    async def get_ranked_info(self, summoner_id: str) -> Dict[str, RankedInfo]:
        """Récupérer les informations de rang d'un joueur (ancienne méthode)"""
        try:
            url = f"https://euw1.api.riotgames.com/lol/league/v4/entries/by-summoner/{summoner_id}"
            
            async with aiohttp.ClientSession() as session:
                await self.rate_limiter.wait()
                
                async with session.get(
                    url,
                    params={"api_key": self.settings.riot_api_key}
                ) as response:
                    logger.info(f"DEBUG: Statut API rangs pour {summoner_id}: {response.status}")
                    if response.status != 200:
                        error_text = await response.text()
                        logger.warning(f"Erreur récupération rangs: {response.status} - {error_text}")
                        return {}
                    
                    data = await response.json()
                    logger.info(f"DEBUG: Données brutes rangs reçues: {data}")
                    return self._process_ranked_data(data)
                    
        except Exception as e:
            logger.error(f"Erreur récupération rang pour {summoner_id}: {e}")
            return {}

    async def get_ranked_info_by_puuid(self, puuid: str) -> Dict[str, RankedInfo]:
        """Récupérer les informations de rang d'un joueur via PUUID"""
        try:
            url = f"https://euw1.api.riotgames.com/lol/league/v4/entries/by-puuid/{puuid}"
            
            async with aiohttp.ClientSession() as session:
                await self.rate_limiter.wait()
                
                async with session.get(
                    url,
                    params={"api_key": self.settings.riot_api_key}
                ) as response:
                    logger.info(f"DEBUG: Statut API rangs PUUID pour {puuid[:20]}...: {response.status}")
                    if response.status != 200:
                        error_text = await response.text()
                        logger.warning(f"Erreur récupération rangs PUUID: {response.status} - {error_text}")
                        return {}
                    
                    data = await response.json()
                    logger.info(f"DEBUG: Données brutes rangs PUUID reçues: {data}")
                    return self._process_ranked_data(data)
                    
        except Exception as e:
            logger.error(f"Erreur récupération rang PUUID pour {puuid}: {e}")
            return {}

    def _process_ranked_data(self, data: list) -> Dict[str, RankedInfo]:
        """Traiter les données de rang reçues de l'API"""
        ranked_info = {}
        
        for entry in data:
            queue_type = entry["queueType"]
            ranked_info[queue_type] = RankedInfo(
                queue_type=queue_type,
                tier=entry["tier"],
                rank=entry["rank"],
                league_points=entry["leaguePoints"],
                wins=entry["wins"],
                losses=entry["losses"],
                veteran=entry.get("veteran", False),
                inactive=entry.get("inactive", False),
                fresh_blood=entry.get("freshBlood", False),
                hot_streak=entry.get("hotStreak", False)
            )
        
        return ranked_info

    async def get_champion_masteries(self, puuid: str, count: int = 5) -> list:
        """
        Récupérer les meilleures maîtrises de champions d'un joueur
        """
        try:
            mastery_url = f"https://euw1.api.riotgames.com/lol/champion-mastery/v4/champion-masteries/by-puuid/{puuid}/top"
            
            async with aiohttp.ClientSession() as session:
                await self.rate_limiter.wait()
                
                async with session.get(
                    mastery_url,
                    params={
                        "count": count,
                        "api_key": self.settings.riot_api_key
                    }
                ) as response:
                    if response.status != 200:
                        logger.warning(f"Erreur récupération maîtrises pour {puuid}: {response.status}")
                        return []
                    
                    data = await response.json()
                    masteries = []
                    
                    for mastery in data:
                        champion_id = mastery['championId']
                        champion_name = self.champion_data.get(champion_id, f"Champion {champion_id}")
                        champion_icon = f'https://cdn.communitydragon.org/latest/champion/{champion_id}/tile'
                        
                        masteries.append({
                            'championId': champion_id,
                            'championName': champion_name,
                            'championIcon': champion_icon,
                            'championLevel': mastery['championLevel'],
                            'championPoints': mastery['championPoints'],
                            'tokensEarned': mastery.get('tokensEarned', 0)
                        })
                    
                    return masteries
                    
        except Exception as e:
            logger.error(f"Erreur récupération maîtrises pour {puuid}: {e}")
            return []

    async def get_mastery_score(self, puuid: str) -> int:
        """
        Récupérer le score total de maîtrise d'un joueur
        """
        try:
            score_url = f"https://euw1.api.riotgames.com/lol/champion-mastery/v4/scores/by-puuid/{puuid}"
            
            async with aiohttp.ClientSession() as session:
                await self.rate_limiter.wait()
                
                async with session.get(
                    score_url,
                    params={"api_key": self.settings.riot_api_key}
                ) as response:
                    if response.status != 200:
                        logger.warning(f"Erreur récupération score maîtrise pour {puuid}: {response.status}")
                        return 0
                    
                    score = await response.json()
                    return score
                    
        except Exception as e:
            logger.error(f"Erreur récupération score maîtrise pour {puuid}: {e}")
            return 0

    async def get_tft_ranked_info(self, puuid: str) -> Dict[str, RankedInfo]:
        """
        Récupérer les informations de rang TFT d'un joueur via son PUUID
        """
        try:
            logger.info(f"DEBUG TFT: Récupération rangs pour PUUID: {puuid}")
            url = f"https://euw1.api.riotgames.com/tft/league/v1/by-puuid/{puuid}"
            
            async with aiohttp.ClientSession() as session:
                await self.rate_limiter.wait()
                
                async with session.get(
                    url,
                    params={"api_key": self.settings.riot_tft_api_key}
                ) as response:
                    logger.info(f"DEBUG TFT: Statut API rangs TFT pour {puuid[:20]}...: {response.status}")
                    if response.status != 200:
                        error_text = await response.text()
                        logger.warning(f"Erreur récupération rangs TFT: {response.status} - {error_text}")
                        return {}
                    
                    data = await response.json()
                    logger.info(f"DEBUG TFT: Données brutes rangs TFT reçues: {data}")
                    return self._process_ranked_data(data)
                    
        except Exception as e:
            logger.error(f"Erreur récupération rang TFT pour {puuid}: {e}")
            return {}

    async def get_puuid_tft(self, game_name: str, tag_line: str, region: str = "europe") -> Optional[str]:
        """
        Récupérer le PUUID TFT d'un joueur via l'API Account avec la clé TFT
        """
        try:
            # Encoder correctement les caractères spéciaux dans l'URL
            encoded_game_name = quote(game_name, safe='')
            encoded_tag_line = quote(tag_line, safe='')
            account_url = f"https://{region}.api.riotgames.com/riot/account/v1/accounts/by-riot-id/{encoded_game_name}/{encoded_tag_line}"
            
            async with aiohttp.ClientSession() as session:
                await self.rate_limiter.wait()
                
                async with session.get(
                    account_url,
                    headers={"X-Riot-Token": self.settings.riot_tft_api_key}
                ) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        if response.status == 404:
                            logger.warning(f"Compte TFT non trouvé: {game_name}#{tag_line}")
                        else:
                            logger.warning(f"Erreur récupération compte TFT {game_name}#{tag_line}: {response.status} - {error_text}")
                        return None
                    
                    account_data = await response.json()
                    puuid_tft = account_data["puuid"]
                    logger.debug(f"PUUID TFT récupéré pour {game_name}#{tag_line}: {puuid_tft}")
                    return puuid_tft
                    
        except Exception as e:
            logger.error(f"Erreur récupération PUUID TFT {game_name}#{tag_line}: {e}")
            return None

    async def get_tft_summoner_by_puuid(self, puuid: str) -> Optional[str]:
        """
        Récupérer l'ID summoner TFT d'un joueur via son PUUID
        """
        try:
            summoner_url = f"https://euw1.api.riotgames.com/tft/summoner/v1/summoners/by-puuid/{puuid}"
            
            async with aiohttp.ClientSession() as session:
                await self.rate_limiter.wait()
                
                async with session.get(
                    summoner_url,
                    params={"api_key": self.settings.riot_tft_api_key}
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        return data.get("id")
                    elif response.status in [400, 404]:
                        # Joueur n'existe pas en TFT ou pas de données
                        logger.debug(f"Pas de données TFT summoner pour {puuid} (status: {response.status})")
                        return None
                    else:
                        logger.warning(f"Erreur récupération summoner TFT pour {puuid}: {response.status}")
                        return None
                    
        except Exception as e:
            logger.error(f"Erreur récupération summoner TFT pour {puuid}: {e}")
            return None
