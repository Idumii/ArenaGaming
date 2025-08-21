"""
Modèles pour les statistiques journalières
"""
from dataclasses import dataclass, field
from typing import Dict, List, Optional
from datetime import datetime, date
from enum import Enum

class GameMode(Enum):
    """Types de modes de jeu"""
    RANKED_SOLO = "ranked_solo"
    RANKED_FLEX = "ranked_flex"
    NORMAL = "normal"
    ARAM = "aram"
    TFT_RANKED = "tft_ranked"
    TFT_NORMAL = "tft_normal"
    OTHER = "other"

@dataclass
class GameRecord:
    """Enregistrement d'une partie jouée"""
    match_id: str
    puuid: str
    summoner_name: str
    game_mode: GameMode
    queue_id: int
    is_win: bool
    game_duration: int
    timestamp: datetime
    kills: Optional[int] = None
    deaths: Optional[int] = None
    assists: Optional[int] = None
    placement: Optional[int] = None  # Pour TFT
    
    def to_dict(self) -> Dict:
        """Convertir en dictionnaire pour JSON"""
        return {
            'match_id': self.match_id,
            'puuid': self.puuid,
            'summoner_name': self.summoner_name,
            'game_mode': self.game_mode.value,
            'queue_id': self.queue_id,
            'is_win': self.is_win,
            'game_duration': self.game_duration,
            'timestamp': self.timestamp.isoformat(),
            'kills': self.kills,
            'deaths': self.deaths,
            'assists': self.assists,
            'placement': self.placement
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'GameRecord':
        """Créer depuis un dictionnaire JSON"""
        return cls(
            match_id=data['match_id'],
            puuid=data['puuid'],
            summoner_name=data['summoner_name'],
            game_mode=GameMode(data['game_mode']),
            queue_id=data['queue_id'],
            is_win=data['is_win'],
            game_duration=data['game_duration'],
            timestamp=datetime.fromisoformat(data['timestamp']),
            kills=data.get('kills'),
            deaths=data.get('deaths'),
            assists=data.get('assists'),
            placement=data.get('placement')
        )

@dataclass
class PlayerDayStats:
    """Statistiques d'un joueur pour une journée"""
    puuid: str
    summoner_name: str
    total_games: int = 0
    total_wins: int = 0
    
    # Par mode de jeu
    ranked_solo_games: int = 0
    ranked_solo_wins: int = 0
    ranked_flex_games: int = 0
    ranked_flex_wins: int = 0
    normal_games: int = 0
    normal_wins: int = 0
    aram_games: int = 0
    aram_wins: int = 0
    tft_ranked_games: int = 0
    tft_ranked_wins: int = 0
    tft_normal_games: int = 0
    tft_normal_wins: int = 0
    
    total_playtime: int = 0  # En secondes
    
    @property
    def win_rate(self) -> float:
        """Taux de victoire global"""
        if self.total_games == 0:
            return 0.0
        return (self.total_wins / self.total_games) * 100
    
    @property
    def average_game_duration(self) -> int:
        """Durée moyenne des parties en minutes"""
        if self.total_games == 0:
            return 0
        return (self.total_playtime // self.total_games) // 60

@dataclass
class DayRecap:
    """Récapitulatif d'une journée"""
    date: date
    guild_id: int
    players_stats: List[PlayerDayStats] = field(default_factory=list)
    total_guild_games: int = 0
    total_guild_playtime: int = 0
    
    @property
    def most_active_player(self) -> Optional[PlayerDayStats]:
        """Joueur le plus actif du jour"""
        if not self.players_stats:
            return None
        return max(self.players_stats, key=lambda p: p.total_games)
    
    @property
    def best_win_rate_player(self) -> Optional[PlayerDayStats]:
        """Joueur avec le meilleur taux de victoire (min 3 parties)"""
        eligible_players = [p for p in self.players_stats if p.total_games >= 3]
        if not eligible_players:
            return None
        return max(eligible_players, key=lambda p: p.win_rate)
