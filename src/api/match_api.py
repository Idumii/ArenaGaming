"""
Client API pour les endpoints Riot Games - Match (LoL)
"""
import aiohttp
from typing import Optional, List, Dict, Any
from datetime import datetime
import structlog
from ..models.game_models import MatchInfo, GameResult, Participant
from ..utils.rate_limiter import RateLimiter
from ..config.settings import get_settings

logger = structlog.get_logger()

class MatchAPI:
    """Client pour les endpoints de matchs LoL"""
    
    def __init__(self):
        self.settings = get_settings()
        self.rate_limiter = RateLimiter()
        
    async def get_current_game(self, puuid: str) -> Optional[Dict[str, Any]]:
        """Vérifier si un joueur est en partie"""
        try:
            logger.debug(f"🔍 Vérification partie en cours pour PUUID: {puuid[:20]}...")
            
            # Utiliser directement le PUUID avec l'endpoint v5
            spectator_url = f"https://euw1.api.riotgames.com/lol/spectator/v5/active-games/by-summoner/{puuid}"
            logger.debug(f"🌐 Appel endpoint spectator v5: {spectator_url}")
            
            async with aiohttp.ClientSession() as session:
                await self.rate_limiter.wait()
                async with session.get(
                    spectator_url,
                    params={"api_key": self.settings.riot_api_key}
                ) as response:
                    logger.debug(f"📡 Réponse spectator: {response.status}")
                    if response.status == 200:
                        game_data = await response.json()
                        logger.info(f"🎮 PARTIE EN COURS TROUVÉE ! Game ID: {game_data.get('gameId')}")
                        return game_data
                    elif response.status == 404:
                        logger.debug("👤 Joueur pas en partie (404 normal)")
                        return None
                    else:
                        logger.warning(f"⚠️ Erreur spectator API: {response.status}")
                        return None
                    
        except Exception as e:
            logger.error(f"Erreur vérification partie en cours pour {puuid}: {e}")
            return None
    
    async def get_current_tft_game(self, puuid: str, region: str = "euw1") -> Optional[Dict[str, Any]]:
        """
        Récupérer la partie TFT en cours d'un joueur
        
        Args:
            puuid: PUUID du joueur
            region: Région du serveur (par défaut: euw1)
            
        Returns:
            Dictionnaire avec les informations de la partie TFT ou None
        """
        try:
            logger.debug(f"🔍 Vérification partie TFT en cours pour PUUID: {puuid[:20]}...")
            
            base_url = f"https://{region}.api.riotgames.com"
            endpoint = f"/lol/spectator/tft/v5/active-games/by-puuid/{puuid}"
            
            async with aiohttp.ClientSession() as session:
                await self.rate_limiter.wait()
                async with session.get(
                    f"{base_url}{endpoint}",
                    params={"api_key": self.settings.riot_tft_api_key}
                ) as response:
                    
                    logger.debug(f"📡 Réponse TFT spectator: {response.status}")
                    
                    if response.status == 200:
                        data = await response.json()
                        logger.info(f"🎮 PARTIE TFT EN COURS TROUVÉE ! Game ID: {data.get('gameId', 'Unknown')}")
                        return data
                    elif response.status == 404:
                        logger.debug("👤 Joueur pas en partie TFT (404 normal)")
                        return None
                    else:
                        logger.warning(f"⚠️ Erreur TFT spectator API {response.status}: {await response.text()}")
                        return None
                        
        except Exception as e:
            logger.error(f"Erreur récupération partie TFT en cours: {e}")
            return None
    
    async def get_recent_matches(self, puuid: str, count: int = 10) -> List[str]:
        """Récupérer les IDs des parties récentes"""
        try:
            url = f"https://europe.api.riotgames.com/lol/match/v5/matches/by-puuid/{puuid}/ids"
            params = {"count": count}
            
            async with aiohttp.ClientSession() as session:
                await self.rate_limiter.wait()
                
                async with session.get(
                    url,
                    params={**params, "api_key": self.settings.riot_api_key}
                ) as response:
                    if response.status == 200:
                        return await response.json()
                    return []
                    
        except Exception as e:
            logger.error(f"Erreur récupération matches récents pour {puuid}: {e}")
            return []
    
    async def get_match_details(self, match_id: str) -> Optional[GameResult]:
        """Récupérer les détails d'une partie"""
        try:
            url = f"https://europe.api.riotgames.com/lol/match/v5/matches/{match_id}"
            
            async with aiohttp.ClientSession() as session:
                await self.rate_limiter.wait()
                
                async with session.get(
                    url,
                    params={"api_key": self.settings.riot_api_key}
                ) as response:
                    if response.status != 200:
                        return None
                    
                    data = await response.json()
                    info = data["info"]
                    
                    # Créer MatchInfo
                    match_info = MatchInfo(
                        match_id=match_id,
                        game_creation=datetime.fromtimestamp(info["gameCreation"] / 1000),
                        game_duration=info["gameDuration"],
                        game_mode=info["gameMode"],
                        game_type=info["gameType"],
                        queue_id=info["queueId"]
                    )
                    
                    # Créer les participants avec toutes les statistiques
                    participants = []
                    for participant in info["participants"]:
                        participants.append(Participant(
                            puuid=participant["puuid"],
                            summoner_name=participant.get("summonerName", ""),
                            champion_id=participant["championId"],
                            champion_name=participant["championName"],
                            kills=participant["kills"],
                            deaths=participant["deaths"],
                            assists=participant["assists"],
                            win=participant["win"],
                            
                            # Informations de base
                            summoner_level=participant.get("summonerLevel", 0),
                            champ_level=participant.get("champLevel", 0),
                            riot_id_game_name=participant.get("riotIdGameName", ""),
                            riot_id_tagline=participant.get("riotIdTagline", ""),
                            
                            # Économie et farm
                            gold_earned=participant.get("goldEarned", 0),
                            gold_spent=participant.get("goldSpent", 0),
                            total_minions_killed=participant.get("totalMinionsKilled", 0),
                            neutral_minions_killed=participant.get("neutralMinionsKilled", 0),
                            
                            # Combat et dégâts
                            total_damage_dealt_to_champions=participant.get("totalDamageDealtToChampions", 0),
                            total_damage_taken=participant.get("totalDamageTaken", 0),
                            magic_damage_dealt_to_champions=participant.get("magicDamageDealtToChampions", 0),
                            physical_damage_dealt_to_champions=participant.get("physicalDamageDealtToChampions", 0),
                            true_damage_dealt_to_champions=participant.get("trueDamageDealtToChampions", 0),
                            
                            # Vision et utilité
                            vision_score=participant.get("visionScore", 0),
                            wards_placed=participant.get("wardsPlaced", 0),
                            wards_killed=participant.get("wardsKilled", 0),
                            detector_wards_placed=participant.get("detectorWardsPlaced", 0),
                            
                            # Objectifs
                            dragon_kills=participant.get("dragonKills", 0),
                            baron_kills=participant.get("baronKills", 0),
                            turret_kills=participant.get("turretKills", 0),
                            inhibitor_kills=participant.get("inhibitorKills", 0),
                            nexus_kills=participant.get("nexusKills", 0),
                            
                            # Multikills et achievements
                            double_kills=participant.get("doubleKills", 0),
                            triple_kills=participant.get("tripleKills", 0),
                            quadra_kills=participant.get("quadraKills", 0),
                            penta_kills=participant.get("pentaKills", 0),
                            first_blood_kill=participant.get("firstBloodKill", False),
                            first_blood_assist=participant.get("firstBloodAssist", False),
                            largest_killing_spree=participant.get("largestKillingSpree", 0),
                            largest_multi_kill=participant.get("largestMultiKill", 0),
                            
                            # Items
                            item0=participant.get("item0", 0),
                            item1=participant.get("item1", 0),
                            item2=participant.get("item2", 0),
                            item3=participant.get("item3", 0),
                            item4=participant.get("item4", 0),
                            item5=participant.get("item5", 0),
                            item6=participant.get("item6", 0),
                            
                            # Temps et divers
                            time_ccing_others=participant.get("timeCCingOthers", 0),
                            total_time_spent_dead=participant.get("totalTimeSpentDead", 0),
                            longest_time_spent_living=participant.get("longestTimeSpentLiving", 0)
                        ))
                    
                    # Déterminer si c'est une partie classée
                    is_ranked = info["queueId"] in [420, 440]  # Solo/Duo et Flex
                    
                    return GameResult(
                        match_info=match_info,
                        participants=participants,
                        is_ranked=is_ranked
                    )
                    
        except Exception as e:
            logger.error(f"Erreur récupération détails match {match_id}: {e}")
            return None
