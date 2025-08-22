"""
Service de détection automatique des parties
"""
import asyncio
from datetime import datetime, timedelta
from typing import Set, Dict, List, Optional
import structlog
import discord
from discord.ext import tasks
import json
import os

logger = structlog.get_logger()

class GameDetectionService:
    """Service pour détecter automatiquement les nouvelles parties"""
    
    def __init__(self, bot):
        self.bot = bot
        
        # Import des modules seulement quand nécessaire pour éviter les imports circulaires
        self._summoner_api = None
        self._match_api = None
        self._tft_api = None
        self._data_persistence = None
        self._daily_stats = None
        
        # Stockage en mémoire organisé par serveur Discord
        self.watched_summoners: Dict[int, List] = {}  # guild_id -> [summoners]
        self.notified_games: Set[str] = set()
        self.last_match_ids: Dict[str, str] = {}  # puuid -> last_match_id
        self.initialized: bool = False  # Flag pour éviter les notifications au démarrage
        
        # Task loop pour la surveillance automatique
        self.monitoring_task = tasks.loop(seconds=30)(self._check_all_summoners)
        self.monitoring_task.add_exception_type(Exception)
        
        # Callback pour gérer les erreurs de la tâche
        @self.monitoring_task.error
        async def on_monitoring_error(task, exception):
            logger.error(f"Erreur dans la tâche de surveillance: {exception}")
            import traceback
            traceback.print_exc()
    
    @property
    def summoner_api(self):
        """Lazy loading de SummonerAPI"""
        if self._summoner_api is None:
            from ..api.summoner_api import SummonerAPI
            self._summoner_api = SummonerAPI()
        return self._summoner_api
    
    @property
    def match_api(self):
        """Lazy loading de MatchAPI"""
        if self._match_api is None:
            from ..api.match_api import MatchAPI
            self._match_api = MatchAPI()
        return self._match_api
    
    @property
    def tft_api(self):
        """Lazy loading de TFTAPI"""
        if self._tft_api is None:
            from ..api.tft_api import TFTAPI
            self._tft_api = TFTAPI()
        return self._tft_api
    
    @property
    def data_persistence(self):
        """Lazy loading de DataPersistence"""
        if self._data_persistence is None:
            from ..utils.data_persistence import DataPersistence
            self._data_persistence = DataPersistence()
        return self._data_persistence
    
    @property
    def daily_stats(self):
        """Lazy loading de DailyStatsService"""
        if self._daily_stats is None:
            from .daily_stats_service import DailyStatsService
            self._daily_stats = DailyStatsService(self.bot)
        return self._daily_stats
    
    @property
    def is_running(self) -> bool:
        """Vérifier si la surveillance est active"""
        return self.monitoring_task.is_running()
    
    def add_watched_summoner(self, summoner, guild_id: int) -> bool:
        """Ajouter un invocateur à surveiller pour un serveur"""
        # Initialiser la liste pour ce serveur si nécessaire
        if guild_id not in self.watched_summoners:
            self.watched_summoners[guild_id] = []
        
        # Éviter les doublons
        for existing in self.watched_summoners[guild_id]:
            if existing.puuid == summoner.puuid:
                return False
        
        self.watched_summoners[guild_id].append(summoner)
        logger.info(f"Ajout surveillance: {summoner.summoner_name}#{summoner.tag_line} (serveur {guild_id})")
        
        # Sauvegarder immédiatement
        self.data_persistence.save_watched_summoners(guild_id, self.watched_summoners[guild_id])
        return True
    
    def remove_watched_summoner(self, puuid: str, guild_id: Optional[int] = None):
        """Retirer un invocateur de la surveillance"""
        if guild_id is not None:
            # Retirer d'un serveur spécifique
            if guild_id in self.watched_summoners:
                original_count = len(self.watched_summoners[guild_id])
                self.watched_summoners[guild_id] = [s for s in self.watched_summoners[guild_id] if s.puuid != puuid]
                
                if len(self.watched_summoners[guild_id]) < original_count:
                    # Sauvegarder les modifications
                    self.data_persistence.save_watched_summoners(guild_id, self.watched_summoners[guild_id])
                    logger.info(f"🗑️ Suppression surveillance puuid {puuid} du serveur {guild_id}")
        else:
            # Retirer de tous les serveurs
            for gid in list(self.watched_summoners.keys()):
                original_count = len(self.watched_summoners[gid])
                self.watched_summoners[gid] = [s for s in self.watched_summoners[gid] if s.puuid != puuid]
                
                if len(self.watched_summoners[gid]) < original_count:
                    self.data_persistence.save_watched_summoners(gid, self.watched_summoners[gid])
        
        # Nettoyer les données associées
        if puuid in self.last_match_ids:
            del self.last_match_ids[puuid]
    
    def load_all_watched_summoners(self):
        """Charger toutes les surveillances depuis les fichiers"""
        self.watched_summoners = self.data_persistence.load_all_watched_summoners()
        total = sum(len(summoners) for summoners in self.watched_summoners.values())
        logger.info(f"📂 Chargement terminé: {total} surveillances sur {len(self.watched_summoners)} serveurs")
    
    def get_watched_summoners(self, guild_id: Optional[int] = None):
        """Obtenir la liste des invocateurs surveillés"""
        if guild_id is not None:
            return self.watched_summoners.get(guild_id, [])
        else:
            # Retourner tous les invocateurs de tous les serveurs
            all_summoners = []
            for summoners in self.watched_summoners.values():
                all_summoners.extend(summoners)
            return all_summoners
    
    def clear_watched_summoners(self, guild_id: int):
        """Purger complètement la liste de surveillance d'un serveur"""
        if guild_id in self.watched_summoners:
            count = len(self.watched_summoners[guild_id])
            self.watched_summoners[guild_id] = []
            
            # Sauvegarder la liste vide
            self.data_persistence.save_watched_summoners(guild_id, [])
            logger.info(f"🧹 Purge complète: {count} surveillances supprimées du serveur {guild_id}")
        else:
            logger.info(f"🧹 Purge: aucune surveillance sur le serveur {guild_id}")
    
    def start_monitoring(self):
        """Démarrer la surveillance automatique"""
        if not self.monitoring_task.is_running():
            self.monitoring_task.start()
            # Démarrer aussi les tâches du service de stats quotidiennes
            self.daily_stats.start_tasks()
            logger.info("🔍 Surveillance automatique démarrée")
            logger.info(f"📋 Tâche configurée pour vérifier toutes les 30 secondes")
        else:
            logger.warning("⚠️ Surveillance déjà en cours")
    
    def stop_monitoring(self):
        """Arrêter la surveillance automatique"""
        if self.monitoring_task.is_running():
            self.monitoring_task.cancel()
            # Arrêter aussi les tâches du service de stats quotidiennes
            self.daily_stats.stop_tasks()
            logger.info("⏹️ Surveillance automatique arrêtée")
    
    def _get_notification_channel(self, guild_id: int, summoner_channel_id: Optional[int] = None) -> Optional[discord.TextChannel]:
        """Récupérer le salon de notification approprié"""
        guild = self.bot.get_guild(guild_id)
        if not guild:
            return None
        
        # 1. Priorité : salon spécifique du joueur
        if summoner_channel_id:
            channel = guild.get_channel(summoner_channel_id)
            if channel and isinstance(channel, discord.TextChannel):
                return channel
        
        # 2. Salon par défaut du serveur 
        try:
            config_dir = os.path.join(os.path.dirname(__file__), "..", "..", "data", "guild_configs")
            config_file = os.path.join(config_dir, f"guild_{guild_id}_config.json")
            
            if os.path.exists(config_file):
                with open(config_file, 'r', encoding='utf-8') as f:
                    config_data = json.load(f)
                    default_channel_id = config_data.get("default_notification_channel_id")
                    if default_channel_id:
                        channel = guild.get_channel(default_channel_id)
                        if channel and isinstance(channel, discord.TextChannel):
                            return channel
        except Exception as e:
            logger.warning(f"Erreur lecture config serveur {guild_id}: {e}")
        
        # 3. Fallback : salon 'general' ou premier salon disponible
        for channel in guild.text_channels:
            if channel.name.lower() in ['general', 'général']:
                return channel
        
        # Dernier recours : premier salon où on peut écrire
        for channel in guild.text_channels:
            if channel.permissions_for(guild.me).send_messages:
                return channel
        
        return None
    
    async def _check_all_summoners(self):
        """Vérifier tous les invocateurs surveillés"""
        if not self.initialized:
            logger.info("🔍 Première vérification - initialisation en cours...")
            await self._initialize_last_matches()
            self.initialized = True
            logger.info("✅ Initialisation terminée")
            return
        
        all_summoners = self.get_watched_summoners()
        if not all_summoners:
            logger.info("🔍 Aucun invocateur à surveiller")
            return
        
        logger.info(f"🔍 Vérification de {len(all_summoners)} invocateurs...")
        
        for summoner in all_summoners:
            try:
                await self._check_summoner_matches(summoner)
                # Petite pause pour éviter de surcharger l'API
                await asyncio.sleep(0.1)
            except Exception as e:
                logger.error(f"Erreur vérification {summoner.summoner_name}: {e}")
        
        logger.info(f"✅ Cycle de vérification terminé ({len(all_summoners)} invocateurs)")
    
    async def _initialize_last_matches(self):
        """Initialiser les derniers matchs pour éviter les notifications de parties anciennes"""
        all_summoners = self.get_watched_summoners()
        
        for summoner in all_summoners:
            try:
                # LoL matches - utiliser la méthode correcte
                lol_puuid = summoner.get_puuid_for_game_type("lol")
                if lol_puuid:
                    lol_matches = await self.match_api.get_recent_matches(lol_puuid, count=1)
                    if lol_matches:
                        self.last_match_ids[f"{lol_puuid}_lol"] = lol_matches[0]
                
                # TFT matches - utiliser la méthode correcte avec le bon PUUID TFT
                tft_puuid = summoner.get_puuid_for_game_type("tft")
                if tft_puuid:
                    tft_matches = await self.tft_api.get_recent_tft_matches(tft_puuid, count=1)
                    if tft_matches:
                        self.last_match_ids[f"{tft_puuid}_tft"] = tft_matches[0]
                
                await asyncio.sleep(0.1)  # Rate limiting
            except Exception as e:
                logger.warning(f"Erreur initialisation {summoner.summoner_name}: {e}")
    
    async def _check_summoner_matches(self, summoner):
        """Vérifier les nouveaux matchs d'un invocateur et les parties en cours"""
        try:
            logger.info(f"🔍 Vérification complète pour {summoner.summoner_name}#{summoner.tag_line}")
            
            # D'abord vérifier les parties EN COURS
            await self.check_current_games(summoner)
            
            # Puis vérifier les parties LoL terminées
            await self._check_lol_matches(summoner)
            
            # Puis vérifier les parties TFT terminées
            await self._check_tft_matches(summoner)
            
        except Exception as e:
            logger.error(f"Erreur vérification matches pour {summoner.summoner_name}: {e}")
    
    async def _check_lol_matches(self, summoner):
        """Vérifier les nouveaux matchs LoL"""
        try:
            puuid_lol = summoner.get_puuid_for_game_type("lol")
            if not puuid_lol:
                logger.warning(f"Pas de PUUID LoL pour {summoner.summoner_name}")
                return
                
            matches = await self.match_api.get_recent_matches(puuid_lol, count=5)
            if not matches:
                return
            
            last_match_key = f"{puuid_lol}_lol"
            last_known_match = self.last_match_ids.get(last_match_key)
            
            # Traiter les nouveaux matchs dans l'ordre chronologique
            new_matches = []
            for match_id in matches:
                if match_id == last_known_match:
                    break
                new_matches.append(match_id)
            
            if new_matches:
                # Mettre à jour le dernier match connu
                self.last_match_ids[last_match_key] = matches[0]
                
                # Traiter les nouveaux matchs (du plus ancien au plus récent)
                for match_id in reversed(new_matches):
                    await self._process_lol_match(summoner, match_id)
        
        except Exception as e:
            logger.error(f"Erreur vérification LoL pour {summoner.summoner_name}: {e}")
    
    async def _check_tft_matches(self, summoner):
        """Vérifier les nouveaux matchs TFT"""
        try:
            puuid_tft = summoner.get_puuid_for_game_type("tft")
            if not puuid_tft:
                logger.warning(f"Pas de PUUID TFT pour {summoner.summoner_name}")
                return
                
            matches = await self.tft_api.get_recent_tft_matches(puuid_tft, count=5)
            if not matches:
                return
            
            last_match_key = f"{puuid_tft}_tft"
            last_known_match = self.last_match_ids.get(last_match_key)
            
            # Traiter les nouveaux matchs dans l'ordre chronologique
            new_matches = []
            for match_id in matches:
                if match_id == last_known_match:
                    break
                new_matches.append(match_id)
            
            if new_matches:
                # Mettre à jour le dernier match connu
                self.last_match_ids[last_match_key] = matches[0]
                
                # Traiter les nouveaux matchs (du plus ancien au plus récent)
                for match_id in reversed(new_matches):
                    await self._process_tft_match(summoner, match_id)
        
        except Exception as e:
            logger.error(f"Erreur vérification TFT pour {summoner.summoner_name}: {e}")
    
    async def _process_lol_match(self, summoner, match_id: str):
        """Traiter un nouveau match LoL"""
        try:
            # Utiliser une clé unique pour éviter les doublons
            lol_puuid = summoner.get_puuid_for_game_type("lol")
            if not lol_puuid:
                logger.warning(f"Pas de PUUID LoL pour {summoner.summoner_name}")
                return
                
            notification_key = f"lol_end_{lol_puuid}_{match_id}"
            
            if notification_key in self.notified_games:
                logger.debug(f"🔄 Match LoL déjà notifié: {match_id} pour {summoner.summoner_name}")
                return
            
            game_result = await self.match_api.get_match_details(match_id)
            if not game_result:
                return
            
            # Enregistrer dans les statistiques quotidiennes
            await self.daily_stats.record_game_lol(game_result, lol_puuid)
            
            # Envoyer la notification Discord
            await self._send_game_notification(summoner, game_result, "lol")
            
            # Marquer comme notifié avec la clé unique
            self.notified_games.add(notification_key)
            
            logger.info(f"✅ Match LoL traité: {summoner.summoner_name} - {game_result.match_info.game_mode}")
        
        except Exception as e:
            logger.error(f"Erreur traitement match LoL {match_id}: {e}")
    
    async def _process_tft_match(self, summoner, match_id: str):
        """Traiter un nouveau match TFT"""
        try:
            # Utiliser une clé unique pour éviter les doublons
            tft_puuid = summoner.get_puuid_for_game_type("tft")
            if not tft_puuid:
                logger.warning(f"Pas de PUUID TFT pour {summoner.summoner_name}")
                return
                
            notification_key = f"tft_end_{tft_puuid}_{match_id}"
            
            if notification_key in self.notified_games:
                logger.debug(f"🔄 Match TFT déjà notifié: {match_id} pour {summoner.summoner_name}")
                return
            
            game_result = await self.tft_api.get_tft_match_details(match_id)
            if not game_result:
                return
            
            # Trouver le participant correspondant à notre joueur (utiliser le PUUID TFT)
            tft_puuid = summoner.get_puuid_for_game_type("tft")
            player_data = None
            for participant in game_result.participants:
                if participant.puuid == tft_puuid:
                    player_data = participant
                    break
            
            if not player_data:
                logger.warning(f"Joueur {summoner.summoner_name} non trouvé dans le match TFT {match_id} (PUUID TFT: {tft_puuid[:20]}...)")
                return
            
            # Enregistrer dans les statistiques quotidiennes
            await self.daily_stats.record_game_tft(game_result, tft_puuid)
            
            # Envoyer la notification Discord
            await self._send_game_notification(summoner, game_result, "tft")
            
            # Marquer comme notifié avec la clé unique
            self.notified_games.add(notification_key)
            
            logger.info(f"✅ Match TFT traité: {summoner.summoner_name} - Position {player_data.placement}")
        
        except Exception as e:
            logger.error(f"Erreur traitement match TFT {match_id}: {e}")
    
    async def _send_game_notification(self, summoner, game_result, game_type: str):
        """Envoyer une notification Discord pour une partie terminée"""
        try:
            # Import des fonctions d'embed seulement quand nécessaire
            from ..utils.discord_embeds import create_game_result_embed, create_tft_result_embed
            
            # Trouver le serveur Discord approprié
            guild_id = None
            for gid, summoners in self.watched_summoners.items():
                if any(s.puuid == summoner.puuid for s in summoners):
                    guild_id = gid
                    break
            
            if guild_id is None:
                logger.warning(f"Aucun serveur trouvé pour {summoner.summoner_name}")
                return
            
            # Utiliser notre nouvelle fonction pour obtenir le salon approprié
            channel = self._get_notification_channel(
                guild_id, 
                getattr(summoner, 'notification_channel_id', None)
            )
            
            if not channel:
                logger.warning(f"Aucun channel de notification trouvé pour le serveur {guild_id}")
                return
            
            # Créer l'embed approprié
            if game_type == "lol":
                lol_puuid = summoner.get_puuid_for_game_type("lol")
                embed, file = await create_game_result_embed(game_result, lol_puuid)
            else:  # tft
                tft_puuid = summoner.get_puuid_for_game_type("tft")
                # Passer les informations du summoner pour un affichage plus riche
                summoner_info = {
                    'summoner_name': summoner.summoner_name,
                    'tag_line': summoner.tag_line
                }
                embed = create_tft_result_embed(game_result, tft_puuid, summoner_info)
                file = None
            
            # Essayer de mentionner l'utilisateur s'il est défini
            content = None
            if hasattr(summoner, 'discord_user_id') and summoner.discord_user_id:
                user = self.bot.get_user(summoner.discord_user_id)
                if user:
                    guild = self.bot.get_guild(guild_id)
                    if guild:
                        member = guild.get_member(summoner.discord_user_id)
                        if member:
                            content = f"<@{summoner.discord_user_id}>"
            
            if file:
                await channel.send(content=content, embed=embed, file=file)
            else:
                await channel.send(content=content, embed=embed)
            logger.info(f"✅ Notification envoyée pour {summoner.summoner_name} dans {channel.name}")
        
        except Exception as e:
            logger.error(f"Erreur envoi notification: {e}")
            import traceback
            traceback.print_exc()
    
    async def check_current_games(self, summoner):
        """Vérifier si un joueur est actuellement en partie (LoL ou TFT)"""
        try:
            logger.debug(f"🔍 Vérification {summoner.summoner_name} - LoL: {getattr(summoner, 'watch_lol', True)}, TFT: {getattr(summoner, 'watch_tft', True)}")
            
            # Vérifier LoL si activé
            if getattr(summoner, 'watch_lol', True):
                lol_puuid = summoner.get_puuid_for_game_type("lol")
                logger.debug(f"   PUUID LoL: {lol_puuid[:20] if lol_puuid else 'None'}...")
                if lol_puuid:
                    current_game = await self.match_api.get_current_game(lol_puuid)
                    if current_game:
                        # Vérifier si cette partie a déjà été notifiée
                        game_id = str(current_game.get('gameId', ''))
                        notification_key = f"lol_{lol_puuid}_{game_id}"
                        
                        if notification_key not in self.notified_games:
                            logger.info(f"🎮 NOUVELLE PARTIE LOL DÉTECTÉE pour {summoner.summoner_name} (Game ID: {game_id})")
                            self.notified_games.add(notification_key)
                            await self.notify_current_game(summoner, current_game, "LoL", summoner.guild_id)
                        else:
                            logger.debug(f"🔄 Partie LoL déjà notifiée pour {summoner.summoner_name} (Game ID: {game_id})")
                        return
            
            # Vérifier TFT si activé
            if getattr(summoner, 'watch_tft', True):
                tft_puuid = summoner.get_puuid_for_game_type("tft")
                logger.debug(f"   PUUID TFT: {tft_puuid[:20] if tft_puuid else 'None'}...")
                if tft_puuid:
                    current_tft_game = await self.tft_api.get_current_tft_game(tft_puuid)
                    if current_tft_game:
                        # Vérifier si cette partie a déjà été notifiée
                        game_id = str(current_tft_game.get('gameId', ''))
                        notification_key = f"tft_{tft_puuid}_{game_id}"
                        
                        if notification_key not in self.notified_games:
                            logger.info(f"🎮 NOUVELLE PARTIE TFT DÉTECTÉE pour {summoner.summoner_name} (Game ID: {game_id})")
                            self.notified_games.add(notification_key)
                            await self.notify_current_game(summoner, current_tft_game, "TFT", summoner.guild_id)
                        else:
                            logger.debug(f"🔄 Partie TFT déjà notifiée pour {summoner.summoner_name} (Game ID: {game_id})")
                        return
                    
        except Exception as e:
            logger.error(f"Erreur vérification parties en cours pour {summoner.summoner_name}: {e}")
    
    async def notify_current_game(self, summoner, current_game: dict, game_type: str = "LoL", guild_id: Optional[int] = None):
        """Notifier qu'un joueur est actuellement en partie"""
        try:
            # Utiliser le guild_id fourni ou chercher dans la surveillance
            if guild_id is None:
                # Trouver le serveur Discord approprié
                for gid, summoners in self.watched_summoners.items():
                    if any(s.puuid == summoner.puuid for s in summoners):
                        guild_id = gid
                        break
            
            if guild_id is None:
                logger.warning(f"Aucun serveur trouvé pour {summoner.summoner_name}")
                return
            
            guild = self.bot.get_guild(guild_id)
            if not guild:
                logger.warning(f"Serveur {guild_id} non trouvé")
                return
            
            # Trouver le channel
            channel = None
            
            # CONFIGURATION SPÉCIFIQUE : Channel de notifications pour le serveur
            notification_channels = {
                1220706693294325790: 1310956948627263541  # Le gaming -> bon channel
            }
            
            # Utiliser le channel configuré en priorité
            if guild_id in notification_channels:
                channel = guild.get_channel(notification_channels[guild_id])
                logger.info(f"📺 Channel configuré utilisé: {channel.name if channel else 'Introuvable'}")
            
            # Fallback sur l'ancien système
            if not channel and hasattr(summoner, 'notification_channel_id') and summoner.notification_channel_id:
                channel = guild.get_channel(summoner.notification_channel_id)
                logger.info(f"📺 Channel spécifique trouvé: {channel.name if channel else 'Introuvable'}")
            
            if not channel:
                # Chercher un channel par défaut
                logger.info(f"📺 Recherche channel gaming dans: {[ch.name for ch in guild.text_channels]}")
                for ch in guild.text_channels:
                    if ch.name.lower() in ['arena-gaming', 'gaming', 'games', 'bot']:
                        channel = ch
                        logger.info(f"✅ Channel gaming trouvé: {ch.name}")
                        break
            
            if not channel:
                # Prendre le premier channel accessible
                for ch in guild.text_channels:
                    if ch.permissions_for(guild.me).send_messages:
                        channel = ch
                        logger.info(f"📺 Channel par défaut utilisé: {channel.name}")
                        break
            
            if not channel:
                logger.warning(f"❌ Aucun channel trouvé sur {guild.name}")
                return
            
            # Créer un embed simple pour la partie en cours
            embed = discord.Embed(
                title=f"🎮 Partie {game_type} en cours",
                description=f"**{summoner.summoner_name}** est actuellement en partie !",
                color=discord.Color.blue()
            )
            
            if current_game.get('gameMode'):
                embed.add_field(name="Mode", value=current_game['gameMode'], inline=True)
            
            if current_game.get('gameLength'):
                minutes = current_game['gameLength'] // 60
                embed.add_field(name="Durée", value=f"{minutes} min", inline=True)
            
            embed.add_field(name="Type", value=game_type, inline=True)
            
            # Essayer de mentionner l'utilisateur s'il existe
            content = f"🎮 **{summoner.summoner_name}** est en partie !"
            
            # Essayer de trouver l'utilisateur pour la mention
            if hasattr(summoner, 'discord_user_id') and summoner.discord_user_id:
                user = self.bot.get_user(summoner.discord_user_id)
                if user:
                    member = guild.get_member(summoner.discord_user_id)
                    if member:
                        content = f"<@{summoner.discord_user_id}> est en partie !"
            
            await channel.send(content=content, embed=embed)
            logger.info(f"✅ Notification partie en cours envoyée pour {summoner.summoner_name}")
            
        except Exception as e:
            logger.error(f"Erreur notification partie en cours: {e}")
            import traceback
            traceback.print_exc()
