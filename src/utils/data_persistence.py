"""
Gestionnaire de persistance des données de surveillance
"""
import os
import json
from pathlib import Path
from typing import List, Dict, Any
import structlog
from ..models.config_models import WatchedSummoner

logger = structlog.get_logger()

class DataPersistence:
    """Gestionnaire de sauvegarde/chargement des données par serveur Discord"""
    
    def __init__(self, data_dir: str = "data"):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(exist_ok=True)
        
        # Créer le dossier pour les données de surveillance
        self.watch_dir = self.data_dir / "watch_data"
        self.watch_dir.mkdir(exist_ok=True)
    
    def _get_watch_file(self, guild_id: int) -> Path:
        """Obtenir le chemin du fichier de surveillance pour un serveur"""
        return self.watch_dir / f"guild_{guild_id}_watched.json"
    
    def save_watched_summoners(self, guild_id: int, summoners: List[WatchedSummoner]) -> bool:
        """Sauvegarder la liste des invocateurs surveillés pour un serveur"""
        try:
            file_path = self._get_watch_file(guild_id)
            
            # Convertir les objets WatchedSummoner en dictionnaires
            data = []
            for summoner in summoners:
                data.append({
                    "puuid": summoner.puuid,
                    "summoner_name": summoner.summoner_name,
                    "tag_line": summoner.tag_line,
                    "discord_user_id": summoner.discord_user_id,
                    "watch_lol": summoner.watch_lol,
                    "watch_tft": summoner.watch_tft,
                    "notify_game_start": summoner.notify_game_start,
                    "notify_game_end": summoner.notify_game_end,
                    "guild_id": guild_id  # Ajouter l'ID du serveur
                })
            
            # Sauvegarder dans le fichier JSON
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            
            logger.info(f"💾 Sauvegarde {len(summoners)} surveillances pour le serveur {guild_id}")
            return True
            
        except Exception as e:
            logger.error(f"Erreur sauvegarde surveillance serveur {guild_id}: {e}")
            return False
    
    def load_watched_summoners(self, guild_id: int) -> List[WatchedSummoner]:
        """Charger la liste des invocateurs surveillés pour un serveur"""
        try:
            file_path = self._get_watch_file(guild_id)
            
            if not file_path.exists():
                logger.info(f"📂 Pas de données de surveillance pour le serveur {guild_id}")
                return []
            
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Convertir les dictionnaires en objets WatchedSummoner
            summoners = []
            for item in data:
                summoner = WatchedSummoner(
                    summoner_name=item["summoner_name"],
                    tag_line=item["tag_line"],
                    discord_user_id=item["discord_user_id"],
                    guild_id=item.get("guild_id", guild_id),  # Utiliser guild_id du fichier ou paramètre
                    puuid_lol=item.get("puuid_lol", ""),
                    puuid_tft=item.get("puuid_tft", ""),
                    puuid=item.get("puuid", ""),  # Compatibilité ancien format
                    watch_lol=item.get("watch_lol", True),
                    watch_tft=item.get("watch_tft", True),
                    notify_game_start=item.get("notify_game_start", True),
                    notify_game_end=item.get("notify_game_end", True)
                )
                summoners.append(summoner)
            
            logger.info(f"📂 Chargement {len(summoners)} surveillances pour le serveur {guild_id}")
            return summoners
            
        except Exception as e:
            logger.error(f"Erreur chargement surveillance serveur {guild_id}: {e}")
            return []
    
    def load_all_watched_summoners(self) -> Dict[int, List[WatchedSummoner]]:
        """Charger toutes les surveillances de tous les serveurs"""
        all_watched = {}
        
        try:
            # Parcourir tous les fichiers de surveillance
            for file_path in self.watch_dir.glob("guild_*_watched.json"):
                try:
                    # Extraire l'ID du serveur depuis le nom du fichier
                    guild_id_str = file_path.stem.split('_')[1]
                    guild_id = int(guild_id_str)
                    
                    # Charger les données de ce serveur
                    summoners = self.load_watched_summoners(guild_id)
                    if summoners:
                        all_watched[guild_id] = summoners
                        
                except (ValueError, IndexError) as e:
                    logger.warning(f"Fichier de surveillance invalide {file_path}: {e}")
                    continue
                    
        except Exception as e:
            logger.error(f"Erreur chargement toutes les surveillances: {e}")
        
        total_summoners = sum(len(summoners) for summoners in all_watched.values())
        logger.info(f"📂 Chargement total: {total_summoners} surveillances sur {len(all_watched)} serveurs")
        
        return all_watched
    
    def remove_watched_summoner(self, guild_id: int, puuid: str) -> bool:
        """Retirer un invocateur de la surveillance d'un serveur"""
        try:
            summoners = self.load_watched_summoners(guild_id)
            original_count = len(summoners)
            
            # Filtrer pour retirer l'invocateur
            summoners = [s for s in summoners if s.puuid != puuid]
            
            if len(summoners) < original_count:
                # Sauvegarder la liste modifiée
                self.save_watched_summoners(guild_id, summoners)
                logger.info(f"🗑️ Suppression surveillance puuid {puuid} du serveur {guild_id}")
                return True
            else:
                logger.warning(f"⚠️ Invocateur puuid {puuid} non trouvé dans le serveur {guild_id}")
                return False
                
        except Exception as e:
            logger.error(f"Erreur suppression surveillance: {e}")
            return False
    
    def get_guild_file_info(self) -> Dict[str, Any]:
        """Obtenir des informations sur les fichiers de surveillance"""
        info = {
            "total_files": 0,
            "total_summoners": 0,
            "files": []
        }
        
        try:
            for file_path in self.watch_dir.glob("guild_*_watched.json"):
                try:
                    guild_id_str = file_path.stem.split('_')[1]
                    guild_id = int(guild_id_str)
                    
                    summoners = self.load_watched_summoners(guild_id)
                    file_info = {
                        "guild_id": guild_id,
                        "file_path": str(file_path),
                        "summoner_count": len(summoners),
                        "file_size": file_path.stat().st_size
                    }
                    
                    info["files"].append(file_info)
                    info["total_summoners"] += len(summoners)
                    
                except Exception as e:
                    logger.warning(f"Erreur lecture fichier {file_path}: {e}")
                    continue
            
            info["total_files"] = len(info["files"])
            
        except Exception as e:
            logger.error(f"Erreur obtention infos fichiers: {e}")
        
        return info
