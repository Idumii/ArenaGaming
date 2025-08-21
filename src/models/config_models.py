"""
Modèles pour les données de configuration et de suivi
"""
from dataclasses import dataclass, field
from typing import Dict, List, Set, Optional
from datetime import datetime

@dataclass
class LPTracking:
    """Suivi des LP pour un joueur"""
    puuid: str
    summoner_name: str
    queue_type: str
    current_lp: int
    tier: str
    rank: str
    last_updated: datetime
    lp_history: List[Dict] = field(default_factory=list)
    
    def add_lp_change(self, old_lp: int, new_lp: int, match_id: str):
        """Ajouter un changement de LP à l'historique"""
        change = {
            'match_id': match_id,
            'old_lp': old_lp,
            'new_lp': new_lp,
            'change': new_lp - old_lp,
            'timestamp': datetime.now()
        }
        self.lp_history.append(change)

@dataclass
@dataclass
class WatchedSummoner:
    """Invocateur surveillé pour les notifications"""
    summoner_name: str
    tag_line: str
    discord_user_id: int
    guild_id: int
    puuid_lol: str = ""  # PUUID pour League of Legends
    puuid_tft: str = ""  # PUUID pour Teamfight Tactics
    puuid: str = ""  # Ancien champ pour compatibilité, utilise puuid_lol par défaut
    watch_lol: bool = True
    watch_tft: bool = True
    notify_game_start: bool = True
    notify_game_end: bool = True
    notification_channel_id: Optional[int] = None  # Salon spécifique pour ce joueur
    
    def __post_init__(self):
        """Assurer la compatibilité avec l'ancien format"""
        # Si on a l'ancien format avec un seul puuid, l'utiliser pour LoL
        if self.puuid and not self.puuid_lol:
            self.puuid_lol = self.puuid
        # Si on a puuid_lol mais pas l'ancien puuid, le mettre à jour
        if self.puuid_lol and not self.puuid:
            self.puuid = self.puuid_lol
    
    def get_puuid_for_game_type(self, game_type: str) -> str:
        """Récupérer le bon PUUID selon le type de jeu"""
        if game_type.lower() == "tft":
            return self.puuid_tft or self.puuid_lol
        else:
            return self.puuid_lol or self.puuid
    
@dataclass
class ServerConfig:
    """Configuration pour un serveur Discord"""
    guild_id: int
    notification_channel_id: int
    admin_role_ids: List[int] = field(default_factory=list)
    watched_summoners: List[WatchedSummoner] = field(default_factory=list)
    auto_detect_games: bool = True
    
@dataclass
class NotifiedGame:
    """Partie déjà notifiée pour éviter les doublons"""
    match_id: str
    puuid: str
    notified_at: datetime
    game_start_time: datetime
