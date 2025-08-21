"""
Client API pour les endpoints Riot Games - TFT
"""
import aiohttp
from typing import Optional, List, Dict, Any
from datetime import datetime
import structlog
from ..models.game_models import MatchInfo, TFTGameResult, TFTParticipant
from ..utils.rate_limiter import RateLimiter
from ..config.settings import get_settings

logger = structlog.get_logger()

class TFTAPI:
    """Client pour les endpoints TFT"""
    
    def __init__(self):
        self.settings = get_settings()
        self.rate_limiter = RateLimiter()
        
    async def get_current_tft_game(self, puuid: str) -> Optional[Dict[str, Any]]:
        """Vérifier si un joueur est en partie TFT"""
        try:
            # Utiliser le bon endpoint TFT spectator avec PUUID directement
            spectator_url = f"https://euw1.api.riotgames.com/lol/spectator/tft/v5/active-games/by-puuid/{puuid}"
            
            async with aiohttp.ClientSession() as session:
                await self.rate_limiter.wait()
                
                async with session.get(
                    spectator_url,
                    headers={"X-Riot-Token": self.settings.riot_tft_api_key}
                ) as response:
                    if response.status == 200:
                        return await response.json()
                    elif response.status == 404:
                        logger.debug(f"Joueur pas en partie TFT: {puuid}")
                        return None
                    else:
                        error_text = await response.text()
                        logger.warning(f"Erreur TFT spectator {puuid}: {response.status} - {error_text}")
                        return None
                    
        except Exception as e:
            logger.error(f"Erreur vérification partie TFT pour {puuid}: {e}")
            return None
    
    async def get_recent_tft_matches(self, puuid: str, count: int = 5) -> List[str]:
        """Récupérer les IDs des matches TFT récents d'un joueur"""
        try:
            url = f"https://europe.api.riotgames.com/tft/match/v1/matches/by-puuid/{puuid}/ids"
            params = {"count": count}
            
            async with aiohttp.ClientSession() as session:
                await self.rate_limiter.wait()
                
                async with session.get(
                    url,
                    params=params,
                    headers={"X-Riot-Token": self.settings.riot_tft_api_key}
                ) as response:
                    if response.status == 200:
                        return await response.json()
                    elif response.status == 404:
                        logger.debug(f"Pas de matches TFT pour {puuid}")
                        return []
                    else:
                        error_text = await response.text()
                        logger.warning(f"Erreur récupération matches TFT {puuid}: {response.status} - {error_text}")
                        return []
                    
        except Exception as e:
            logger.error(f"Erreur récupération matches TFT récents pour {puuid}: {e}")
            return []
    
    async def get_tft_match_details(self, match_id: str) -> Optional[TFTGameResult]:
        """Récupérer les détails d'une partie TFT"""
        try:
            url = f"https://europe.api.riotgames.com/tft/match/v1/matches/{match_id}"
            
            async with aiohttp.ClientSession() as session:
                await self.rate_limiter.wait()
                
                async with session.get(
                    url,
                    headers={"X-Riot-Token": self.settings.riot_tft_api_key}
                ) as response:
                    if response.status != 200:
                        return None
                    
                    data = await response.json()
                    info = data["info"]
                    
                    # Créer MatchInfo avec le bon match_id depuis metadata
                    match_info = MatchInfo(
                        match_id=data["metadata"]["match_id"],
                        game_creation=datetime.fromtimestamp(info["game_datetime"] / 1000),
                        game_duration=info["game_length"],
                        game_mode=info.get("tft_game_type", "TFT"),
                        game_type="TFT", 
                        queue_id=info["queue_id"]
                    )
                    
                    # Créer les participants TFT
                    participants = []
                    for participant in info["participants"]:
                        participants.append(TFTParticipant(
                            puuid=participant["puuid"],
                            placement=participant["placement"],
                            level=participant["level"],
                            last_round=participant["last_round"],
                            players_eliminated=participant["players_eliminated"],
                            total_damage_to_players=participant["total_damage_to_players"],
                            companion=participant.get("companion", {}),
                            traits=participant.get("traits", []),
                            units=participant.get("units", [])
                        ))
                    
                    return TFTGameResult(
                        match_info=match_info,
                        participants=participants
                    )
                    
        except Exception as e:
            logger.error(f"Erreur récupération détails match TFT {match_id}: {e}")
            return None
            
    async def get_player_placement_in_match(self, match_id: str, puuid: str) -> Optional[int]:
        """Récupérer le placement d'un joueur dans une partie TFT"""
        try:
            match_details = await self.get_tft_match_details(match_id)
            if not match_details:
                return None
            
            for participant in match_details.participants:
                if participant.puuid == puuid:
                    return participant.placement
            
            logger.warning(f"Joueur {puuid} non trouvé dans le match TFT {match_id}")
            return None
            
        except Exception as e:
            logger.error(f"Erreur récupération placement {puuid} dans {match_id}: {e}")
            return None
