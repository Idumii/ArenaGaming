from dataclasses import dataclass
from typing import Optional, List, Dict, Any
from datetime import datetime

@dataclass
class Summoner:
    """Modèle pour un invocateur"""
    puuid: str
    summoner_id: str
    name: str
    tag_line: str
    profile_icon_id: int
    summoner_level: int
    
    def __str__(self) -> str:
        return f"{self.name}#{self.tag_line}"

@dataclass
class RankedInfo:
    """Informations de rang pour un joueur"""
    queue_type: str  # RANKED_SOLO_5x5, RANKED_TFT, etc.
    tier: str
    rank: str
    league_points: int
    wins: int
    losses: int
    veteran: bool = False
    inactive: bool = False
    fresh_blood: bool = False
    hot_streak: bool = False
    
    @property
    def winrate(self) -> float:
        total_games = self.wins + self.losses
        return (self.wins / total_games * 100) if total_games > 0 else 0.0

@dataclass
class MatchInfo:
    """Informations basiques d'une partie"""
    match_id: str
    game_creation: datetime
    game_duration: int
    game_mode: str
    game_type: str
    queue_id: int
    
@dataclass
class Participant:
    """Participant dans une partie avec toutes les statistiques"""
    puuid: str
    summoner_name: str
    champion_id: int
    champion_name: str
    kills: int
    deaths: int
    assists: int
    win: bool
    
    # Informations de base
    summoner_level: int = 0
    champ_level: int = 0
    riot_id_game_name: str = ""
    riot_id_tagline: str = ""
    
    # Économie et farm
    gold_earned: int = 0
    gold_spent: int = 0
    total_minions_killed: int = 0
    neutral_minions_killed: int = 0
    
    # Combat et dégâts
    total_damage_dealt_to_champions: int = 0
    total_damage_taken: int = 0
    magic_damage_dealt_to_champions: int = 0
    physical_damage_dealt_to_champions: int = 0
    true_damage_dealt_to_champions: int = 0
    
    # Vision et utilité
    vision_score: int = 0
    wards_placed: int = 0
    wards_killed: int = 0
    detector_wards_placed: int = 0
    
    # Objectifs
    dragon_kills: int = 0
    baron_kills: int = 0
    turret_kills: int = 0
    inhibitor_kills: int = 0
    nexus_kills: int = 0
    
    # Multikills et achievements
    double_kills: int = 0
    triple_kills: int = 0
    quadra_kills: int = 0
    penta_kills: int = 0
    first_blood_kill: bool = False
    first_blood_assist: bool = False
    largest_killing_spree: int = 0
    largest_multi_kill: int = 0
    
    # Items
    item0: int = 0
    item1: int = 0
    item2: int = 0
    item3: int = 0
    item4: int = 0
    item5: int = 0
    item6: int = 0
    
    # Temps et divers
    time_ccing_others: int = 0
    total_time_spent_dead: int = 0
    longest_time_spent_living: int = 0
    
    @property
    def kda_ratio(self) -> float:
        return (self.kills + self.assists) / max(self.deaths, 1)

@dataclass
@dataclass
@dataclass
class TFTParticipant:
    """Participant TFT avec ses spécificités"""
    puuid: str
    summoner_name: str
    placement: int
    level: int
    last_round: int
    players_eliminated: int
    total_damage_to_players: int
    traits: List[Dict[str, Any]]
    units: List[Dict[str, Any]]
    augments: Optional[List[str]] = None  # Peut être None dans certaines versions
    companion: Optional[Dict[str, Any]] = None
    
@dataclass
class GameResult:
    """Résultat d'une partie complète"""
    match_info: MatchInfo
    participants: List[Participant]
    is_ranked: bool
    
@dataclass
@dataclass
class TFTGameResult:
    """Résultat d'une partie TFT"""
    match_info: MatchInfo
    participants: List[TFTParticipant]
    set_number: str
    queue_id: int
