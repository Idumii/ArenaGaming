"""
Service de gestion des statistiques journalières
"""
import json
import asyncio
from datetime import datetime, date, timedelta, time
from pathlib import Path
from typing import Dict, List, Optional
import structlog
from discord.ext import tasks
from ..models.daily_stats_models import GameRecord, PlayerDayStats, DayRecap, GameMode
from ..models.game_models import GameResult, TFTGameResult
from ..utils.discord_embeds import create_daily_recap_embed

logger = structlog.get_logger()

class DailyStatsService:
    """Service pour gérer les statistiques journalières"""
    
    def __init__(self, bot):
        self.bot = bot
        self.data_dir = Path("data/daily_stats")
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        # Task pour le recap quotidien à 8h00
        self.daily_recap_task = tasks.loop(time=time(8, 0))(self._send_daily_recap)
        
        # Task pour le nettoyage des anciennes données (minuit)
        self.cleanup_task = tasks.loop(time=time(0, 0))(self._cleanup_old_data)
    
    def start_tasks(self):
        """Démarrer les tâches automatiques"""
        if not self.daily_recap_task.is_running():
            self.daily_recap_task.start()
            logger.info("📊 Tâche de recap quotidien démarrée (8h00)")
        
        if not self.cleanup_task.is_running():
            self.cleanup_task.start()
            logger.info("🧹 Tâche de nettoyage démarrée (minuit)")
    
    def stop_tasks(self):
        """Arrêter les tâches automatiques"""
        if self.daily_recap_task.is_running():
            self.daily_recap_task.cancel()
        if self.cleanup_task.is_running():
            self.cleanup_task.cancel()
    
    def _get_daily_file_path(self, target_date: date) -> Path:
        """Obtenir le chemin du fichier pour une date donnée"""
        return self.data_dir / f"{target_date.isoformat()}.json"
    
    def _determine_game_mode(self, queue_id: int, is_tft: bool = False) -> GameMode:
        """Déterminer le mode de jeu à partir du queue_id"""
        if is_tft:
            if queue_id in [1100, 1130]:  # TFT Ranked
                return GameMode.TFT_RANKED
            else:
                return GameMode.TFT_NORMAL
        
        # LoL modes
        queue_mapping = {
            420: GameMode.RANKED_SOLO,  # Ranked Solo/Duo
            440: GameMode.RANKED_FLEX,  # Ranked Flex
            450: GameMode.ARAM,         # ARAM
            400: GameMode.NORMAL,       # Normal Draft
            430: GameMode.NORMAL,       # Normal Blind
        }
        
        return queue_mapping.get(queue_id, GameMode.OTHER)
    
    async def record_game_lol(self, game_result: GameResult, target_puuid: str):
        """Enregistrer une partie LoL"""
        try:
            # Trouver le participant cible
            target_participant = None
            for participant in game_result.participants:
                if participant.puuid == target_puuid:
                    target_participant = participant
                    break
            
            if not target_participant:
                return
            
            game_mode = self._determine_game_mode(game_result.match_info.queue_id)
            
            record = GameRecord(
                match_id=game_result.match_info.match_id,
                puuid=target_puuid,
                summoner_name=target_participant.riot_id_game_name,
                game_mode=game_mode,
                queue_id=game_result.match_info.queue_id,
                is_win=target_participant.win,
                game_duration=game_result.match_info.game_duration,
                timestamp=game_result.match_info.game_creation,
                kills=target_participant.kills,
                deaths=target_participant.deaths,
                assists=target_participant.assists
            )
            
            await self._save_game_record(record)
            logger.debug(f"📊 Partie LoL enregistrée: {target_participant.riot_id_game_name} - {game_mode.value}")
            
        except Exception as e:
            logger.error(f"Erreur enregistrement partie LoL: {e}")
    
    async def record_game_tft(self, tft_result: TFTGameResult, target_puuid: str):
        """Enregistrer une partie TFT"""
        try:
            # Trouver le participant cible
            target_participant = None
            for participant in tft_result.participants:
                if participant.puuid == target_puuid:
                    target_participant = participant
                    break
            
            if not target_participant:
                return
            
            game_mode = self._determine_game_mode(tft_result.queue_id, is_tft=True)
            
            # TFT : victoire = top 4
            is_win = target_participant.placement <= 4
            
            record = GameRecord(
                match_id=tft_result.match_info.match_id,
                puuid=target_puuid,
                summoner_name=target_participant.summoner_name,
                game_mode=game_mode,
                queue_id=tft_result.queue_id,
                is_win=is_win,
                game_duration=tft_result.match_info.game_duration,
                timestamp=tft_result.match_info.game_creation,
                placement=target_participant.placement
            )
            
            await self._save_game_record(record)
            logger.debug(f"📊 Partie TFT enregistrée: {target_participant.summoner_name} - {game_mode.value}")
            
        except Exception as e:
            logger.error(f"Erreur enregistrement partie TFT: {e}")
    
    async def _save_game_record(self, record: GameRecord):
        """Sauvegarder un enregistrement de partie"""
        target_date = record.timestamp.date()
        file_path = self._get_daily_file_path(target_date)
        
        # Charger les données existantes
        existing_records = []
        if file_path.exists():
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    existing_records = data.get('games', [])
            except Exception as e:
                logger.warning(f"Erreur lecture fichier stats {file_path}: {e}")
        
        # Vérifier si la partie n'est pas déjà enregistrée
        for existing in existing_records:
            if existing.get('match_id') == record.match_id and existing.get('puuid') == record.puuid:
                logger.debug(f"Partie déjà enregistrée: {record.match_id}")
                return
        
        # Ajouter la nouvelle partie
        existing_records.append(record.to_dict())
        
        # Sauvegarder
        data = {
            'date': target_date.isoformat(),
            'games': existing_records
        }
        
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    
    async def generate_day_recap(self, target_date: date, guild_id: int) -> Optional[DayRecap]:
        """Générer le récapitulatif d'une journée"""
        file_path = self._get_daily_file_path(target_date)
        
        if not file_path.exists():
            return None
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                games_data = data.get('games', [])
            
            # Convertir en objets GameRecord
            games = [GameRecord.from_dict(game_data) for game_data in games_data]
            
            # Grouper par joueur
            players_data: Dict[str, PlayerDayStats] = {}
            
            for game in games:
                puuid = game.puuid
                
                if puuid not in players_data:
                    players_data[puuid] = PlayerDayStats(
                        puuid=puuid,
                        summoner_name=game.summoner_name
                    )
                
                player_stats = players_data[puuid]
                player_stats.total_games += 1
                player_stats.total_playtime += game.game_duration
                
                if game.is_win:
                    player_stats.total_wins += 1
                
                # Compter par mode
                if game.game_mode == GameMode.RANKED_SOLO:
                    player_stats.ranked_solo_games += 1
                    if game.is_win:
                        player_stats.ranked_solo_wins += 1
                elif game.game_mode == GameMode.RANKED_FLEX:
                    player_stats.ranked_flex_games += 1
                    if game.is_win:
                        player_stats.ranked_flex_wins += 1
                elif game.game_mode == GameMode.NORMAL:
                    player_stats.normal_games += 1
                    if game.is_win:
                        player_stats.normal_wins += 1
                elif game.game_mode == GameMode.ARAM:
                    player_stats.aram_games += 1
                    if game.is_win:
                        player_stats.aram_wins += 1
                elif game.game_mode == GameMode.TFT_RANKED:
                    player_stats.tft_ranked_games += 1
                    if game.is_win:
                        player_stats.tft_ranked_wins += 1
                elif game.game_mode == GameMode.TFT_NORMAL:
                    player_stats.tft_normal_games += 1
                    if game.is_win:
                        player_stats.tft_normal_wins += 1
            
            # Créer le récapitulatif
            recap = DayRecap(
                date=target_date,
                guild_id=guild_id,
                players_stats=list(players_data.values()),
                total_guild_games=len(games),
                total_guild_playtime=sum(game.game_duration for game in games)
            )
            
            return recap
            
        except Exception as e:
            logger.error(f"Erreur génération recap {target_date}: {e}")
            return None
    
    async def _send_daily_recap(self):
        """Envoyer le récapitulatif quotidien à 8h00"""
        yesterday = date.today() - timedelta(days=1)
        logger.info(f"📊 Génération du récapitulatif quotidien pour {yesterday}")
        
        # Pour chaque serveur surveillé (vous devrez adapter selon votre logique)
        for guild in self.bot.guilds:
            try:
                recap = await self.generate_day_recap(yesterday, guild.id)
                
                if not recap or not recap.players_stats:
                    logger.debug(f"Pas de données pour {guild.name} le {yesterday}")
                    continue
                
                # Créer l'embed
                embed = create_daily_recap_embed(recap)
                
                # Trouver le channel approprié
                channel = None
                for ch in guild.text_channels:
                    if "arena" in ch.name.lower() or "gaming" in ch.name.lower() or "bot" in ch.name.lower():
                        channel = ch
                        break
                
                if not channel:
                    channel = guild.text_channels[0] if guild.text_channels else None
                
                if channel:
                    await channel.send(embed=embed)
                    logger.info(f"📊 Récap quotidien envoyé sur {guild.name}")
                
            except Exception as e:
                logger.error(f"Erreur envoi recap pour {guild.name}: {e}")
    
    async def _cleanup_old_data(self):
        """Nettoyer les anciennes données (garde 30 jours)"""
        try:
            cutoff_date = date.today() - timedelta(days=30)
            deleted_count = 0
            
            for file_path in self.data_dir.glob("*.json"):
                try:
                    file_date = date.fromisoformat(file_path.stem)
                    if file_date < cutoff_date:
                        file_path.unlink()
                        deleted_count += 1
                except ValueError:
                    # Fichier avec nom non-conforme, ignorer
                    continue
            
            if deleted_count > 0:
                logger.info(f"🧹 Nettoyage terminé: {deleted_count} fichiers supprimés")
                
        except Exception as e:
            logger.error(f"Erreur nettoyage données: {e}")
