"""
Commandes d'administration pour la surveillance des parties
"""
import discord
from discord.ext import commands
from discord import app_commands
from typing import Optional
from datetime import datetime
import structlog
from ..api.summoner_api import SummonerAPI
from ..models.config_models import WatchedSummoner
from ..services.game_detection import GameDetectionService
from ..utils.discord_embeds import create_error_embed

logger = structlog.get_logger()

class AdminCommands(commands.Cog):
    """Commandes d'administration du bot"""
    
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.summoner_api = SummonerAPI()
        self.detection_service = GameDetectionService(bot)
    
    async def cog_load(self):
        """Démarrer la surveillance au chargement du cog"""
        # Charger les données de surveillance sauvegardées
        self.detection_service.load_all_watched_summoners()
        # Démarrer la surveillance automatique
        self.detection_service.start_monitoring()
    
    async def cog_unload(self):
        """Arrêter la surveillance au déchargement du cog"""
        self.detection_service.stop_monitoring()
    
    @app_commands.command(name="watch", description="Surveiller un joueur pour les notifications automatiques")
    @app_commands.describe(
        summoner_name="Nom du joueur à surveiller",
        tag_line="Tag du joueur",
        user="Utilisateur Discord à notifier (optionnel)"
    )
    async def watch_summoner(
        self,
        interaction: discord.Interaction,
        summoner_name: str,
        tag_line: str = "EUW1",
        user: Optional[discord.Member] = None
    ):
        """Ajouter un joueur à la surveillance automatique"""
        await interaction.response.defer()
        
        # Vérifier qu'on est dans un serveur Discord
        if not interaction.guild_id:
            embed = create_error_embed(
                "Commande serveur uniquement",
                "Cette commande ne peut être utilisée qu'dans un serveur Discord."
            )
            await interaction.followup.send(embed=embed)
            return
        
        try:
            # Récupérer le PUUID LoL (avec clé LoL)
            summoner = await self.summoner_api.get_summoner_by_riot_id(
                summoner_name, tag_line
            )
            
            if not summoner:
                embed = create_error_embed(
                    "Joueur non trouvé",
                    f"Aucun joueur trouvé avec le nom `{summoner_name}#{tag_line}`"
                )
                await interaction.followup.send(embed=embed)
                return
            
            # Récupérer le PUUID TFT (avec clé TFT)
            puuid_tft = await self.summoner_api.get_puuid_tft(summoner_name, tag_line)
            
            if not puuid_tft:
                logger.warning(f"PUUID TFT non trouvé pour {summoner_name}#{tag_line}")
                puuid_tft = ""  # Sera rempli ultérieurement si nécessaire
            
            # Utilisateur à notifier (celui qui lance la commande par défaut)
            target_user = user if user else interaction.user
            
            # Créer l'objet WatchedSummoner avec les deux PUUID
            watched = WatchedSummoner(
                summoner_name=summoner.name,
                tag_line=summoner.tag_line,
                discord_user_id=target_user.id,
                guild_id=interaction.guild_id,
                puuid_lol=summoner.puuid,  # PUUID LoL
                puuid_tft=puuid_tft,       # PUUID TFT
                puuid=summoner.puuid,      # Compatibilité (LoL par défaut)
                watch_lol=True,
                watch_tft=True,
                notify_game_start=True,
                notify_game_end=True
            )
            
            # Ajouter à la surveillance
            if self.detection_service.add_watched_summoner(watched, interaction.guild_id):
                embed = discord.Embed(
                    title="✅ Surveillance activée",
                    description=(
                        f"**{summoner.name}#{summoner.tag_line}** est maintenant surveillé.\n"
                        f"Notifications envoyées à {target_user.mention}\n\n"
                        f"🎮 **PUUID LoL:** {summoner.puuid[:20]}...\n"
                        f"🏆 **PUUID TFT:** {puuid_tft[:20] if puuid_tft else 'Non trouvé'}..."
                    ),
                    color=discord.Color.green()
                )
            else:
                embed = create_error_embed(
                    "Déjà surveillé",
                    f"**{summoner.name}#{summoner.tag_line}** est déjà dans la liste de surveillance."
                )
            
            await interaction.followup.send(embed=embed)
            
        except Exception as e:
            logger.error(f"Erreur commande watch: {e}")
            embed = create_error_embed(
                "Erreur",
                "Une erreur est survenue lors de l'ajout de la surveillance"
            )
            await interaction.followup.send(embed=embed)
    
    @app_commands.command(name="unwatch", description="Arrêter la surveillance d'un joueur")
    @app_commands.describe(
        summoner_name="Nom du joueur à retirer de la surveillance",
        tag_line="Tag du joueur"
    )
    async def unwatch_summoner(
        self,
        interaction: discord.Interaction,
        summoner_name: str,
        tag_line: str = "EUW1"
    ):
        """Retirer un joueur de la surveillance"""
        await interaction.response.defer()
        
        # Vérifier qu'on est dans un serveur Discord
        if not interaction.guild_id:
            embed = create_error_embed(
                "Commande serveur uniquement",
                "Cette commande ne peut être utilisée qu'dans un serveur Discord."
            )
            await interaction.followup.send(embed=embed)
            return
        
        try:
            # Récupérer le summoner pour avoir son PUUID
            summoner = await self.summoner_api.get_summoner_by_riot_id(
                summoner_name, tag_line
            )
            
            if not summoner:
                embed = create_error_embed(
                    "Joueur non trouvé",
                    f"Aucun joueur trouvé avec le nom `{summoner_name}#{tag_line}`"
                )
                await interaction.followup.send(embed=embed)
                return
            
            # Retirer de la surveillance pour ce serveur
            self.detection_service.remove_watched_summoner(summoner.puuid, interaction.guild_id)
            
            embed = discord.Embed(
                title="✅ Surveillance désactivée",
                description=f"**{summoner.name}#{summoner.tag_line}** n'est plus surveillé sur ce serveur.",
                color=discord.Color.orange()
            )
            
            await interaction.followup.send(embed=embed)
            
        except Exception as e:
            logger.error(f"Erreur commande unwatch: {e}")
            embed = create_error_embed(
                "Erreur",
                "Une erreur est survenue lors de la suppression de la surveillance"
            )
            await interaction.followup.send(embed=embed)
    
    @app_commands.command(name="watchlist", description="Afficher la liste des joueurs surveillés")
    async def watch_list(self, interaction: discord.Interaction):
        """Afficher la liste des joueurs surveillés"""
        await interaction.response.defer()
        
        # Obtenir la liste pour ce serveur Discord
        guild_id = interaction.guild_id if interaction.guild_id else 0
        watched = self.detection_service.get_watched_summoners(guild_id)
        
        if not watched:
            embed = discord.Embed(
                title="📋 Liste de surveillance",
                description="Aucun joueur n'est actuellement surveillé sur ce serveur.",
                color=discord.Color.blue()
            )
        else:
            embed = discord.Embed(
                title="📋 Liste de surveillance",
                description=f"{len(watched)} joueur(s) surveillé(s) sur ce serveur",
                color=discord.Color.blue()
            )
            
            for summoner in watched:
                user = self.bot.get_user(summoner.discord_user_id)
                user_name = user.display_name if user else "Utilisateur inconnu"
                
                games = []
                if summoner.watch_lol:
                    games.append("LoL")
                if summoner.watch_tft:
                    games.append("TFT")
                
                embed.add_field(
                    name=f"{summoner.summoner_name}#{summoner.tag_line}",
                    value=f"Notifie: {user_name}\nJeux: {', '.join(games)}",
                    inline=True
                )
        
        await interaction.followup.send(embed=embed)
    
    @app_commands.command(name="purge", description="[ADMIN] Purger complètement la liste de surveillance")
    async def purge_watchlist(self, interaction: discord.Interaction):
        """Purger complètement la liste de surveillance"""
        await interaction.response.defer()
        
        # Vérifier les permissions admin
        if not isinstance(interaction.user, discord.Member) or not interaction.user.guild_permissions.administrator:
            embed = discord.Embed(
                title="❌ Erreur",
                description="Commande réservée aux administrateurs",
                color=discord.Color.red()
            )
            await interaction.followup.send(embed=embed)
            return
        
        guild_id = interaction.guild_id if interaction.guild_id else 0
        watched = self.detection_service.get_watched_summoners(guild_id)
        
        if not watched:
            embed = discord.Embed(
                title="🧹 Purge de la surveillance",
                description="Aucun joueur n'est surveillé sur ce serveur.",
                color=discord.Color.blue()
            )
        else:
            # Purger la liste
            self.detection_service.clear_watched_summoners(guild_id)
            
            embed = discord.Embed(
                title="🧹 Purge de la surveillance",
                description=f"✅ {len(watched)} joueur(s) supprimé(s) de la surveillance.\n\nVous pouvez maintenant utiliser `/watch` pour refaire la liste proprement.",
                color=discord.Color.green()
            )
        
        await interaction.followup.send(embed=embed)
    
    @app_commands.command(name="sync", description="[ADMIN] Forcer la synchronisation des commandes slash")
    async def force_sync(self, interaction: discord.Interaction):
        """Forcer la synchronisation des commandes slash"""
        # Vérifier les permissions pour les membres du serveur
        if interaction.guild:
            member = interaction.guild.get_member(interaction.user.id)
            if member and not member.guild_permissions.administrator:
                embed = create_error_embed(
                    "Permission refusée",
                    "Seuls les administrateurs peuvent utiliser cette commande."
                )
                await interaction.response.send_message(embed=embed, ephemeral=True)
                return
            
        await interaction.response.defer()
        
        try:
            synced = await self.bot.tree.sync()
            embed = discord.Embed(
                title="✅ Synchronisation réussie",
                description=f"{len(synced)} commandes slash synchronisées",
                color=discord.Color.green()
            )
            await interaction.followup.send(embed=embed)
            
        except Exception as e:
            logger.error(f"Erreur sync forcée: {e}")
            embed = create_error_embed(
                "Erreur de synchronisation",
                f"Impossible de synchroniser: {str(e)}"
            )
            await interaction.followup.send(embed=embed)

    @app_commands.command(name="clearcommands", description="[ADMIN] Nettoyer toutes les commandes slash (DANGER)")
    async def clear_commands(self, interaction: discord.Interaction):
        """Nettoyer toutes les commandes slash - ATTENTION"""
        # Vérifier les permissions administrateur
        if interaction.guild:
            member = interaction.guild.get_member(interaction.user.id)
            if member and not member.guild_permissions.administrator:
                embed = create_error_embed(
                    "Permission refusée",
                    "Seuls les administrateurs peuvent utiliser cette commande."
                )
                await interaction.response.send_message(embed=embed, ephemeral=True)
                return
            
        await interaction.response.defer()
        
        try:
            # Clear et resync
            self.bot.tree.clear_commands(guild=None)
            await self.bot.tree.sync()
            
            embed = discord.Embed(
                title="✅ Nettoyage effectué",
                description="Toutes les commandes ont été supprimées. Redémarrez le bot pour les restaurer.",
                color=discord.Color.orange()
            )
            await interaction.followup.send(embed=embed)
            
        except Exception as e:
            logger.error(f"Erreur clear commands: {e}")
            embed = create_error_embed(
                "Erreur de nettoyage",
                f"Impossible de nettoyer: {str(e)}"
            )
            await interaction.followup.send(embed=embed)

    @app_commands.command(name="setchannel", description="Définir le salon pour les notifications automatiques")
    @app_commands.describe(
        channel="Le salon où envoyer les notifications automatiques"
    )
    async def set_notification_channel(
        self,
        interaction: discord.Interaction,
        channel: discord.TextChannel
    ):
        """Définir le salon de notification pour le serveur"""
        # Vérifier les permissions d'admin
        if not isinstance(interaction.user, discord.Member) or not interaction.user.guild_permissions.administrator:
            embed = create_error_embed(
                "Permission refusée",
                "Seuls les administrateurs peuvent utiliser cette commande."
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
            
        await interaction.response.defer()
        
        try:
            # Vérifier que le bot peut écrire dans le salon
            guild = interaction.guild
            if not guild:
                embed = create_error_embed("Erreur", "Commande non disponible en DM")
                await interaction.followup.send(embed=embed)
                return
                
            if not channel.permissions_for(guild.me).send_messages:
                embed = create_error_embed(
                    "Permission insuffisante",
                    f"Je n'ai pas la permission d'écrire dans {channel.mention}"
                )
                await interaction.followup.send(embed=embed)
                return
            
            # Mettre à jour tous les joueurs surveillés de ce serveur
            guild_id = guild.id
            updated_count = 0
            
            if guild_id in self.detection_service.watched_summoners:
                for summoner in self.detection_service.watched_summoners[guild_id]:
                    summoner.notification_channel_id = channel.id
                    updated_count += 1
                
                # Sauvegarder les modifications
                self.detection_service.data_persistence.save_watched_summoners(
                    guild_id, 
                    self.detection_service.watched_summoners[guild_id]
                )
            
            embed = discord.Embed(
                title="✅ Salon de notification configuré",
                description=f"Les notifications automatiques seront maintenant envoyées dans {channel.mention}\n\n"
                           f"**Joueurs mis à jour :** {updated_count}",
                color=discord.Color.green()
            )
            
            # Envoyer un message de test dans le nouveau salon
            test_embed = discord.Embed(
                title="🎮 Salon de notification configuré",
                description="Ce salon recevra désormais toutes les notifications automatiques de début et fin de partie !",
                color=discord.Color.blue()
            )
            await channel.send(embed=test_embed)
            
            await interaction.followup.send(embed=embed)
            
        except Exception as e:
            logger.error(f"Erreur set notification channel: {e}")
            embed = create_error_embed(
                "Erreur de configuration",
                f"Impossible de configurer le salon: {str(e)}"
            )
            await interaction.followup.send(embed=embed)

    @app_commands.command(name="setdefaultchannel", description="Définir le salon par défaut pour TOUS les joueurs")
    @app_commands.describe(
        channel="Le salon par défaut pour toutes les notifications du serveur"
    )
    async def set_default_notification_channel(
        self,
        interaction: discord.Interaction,
        channel: discord.TextChannel
    ):
        """Définir le salon de notification par défaut pour le serveur entier"""
        # Vérifier les permissions d'admin
        if not isinstance(interaction.user, discord.Member) or not interaction.user.guild_permissions.administrator:
            embed = create_error_embed(
                "Permission refusée",
                "Seuls les administrateurs peuvent utiliser cette commande."
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
            
        await interaction.response.defer()
        
        try:
            guild = interaction.guild
            if not guild:
                embed = create_error_embed("Erreur", "Commande non disponible en DM")
                await interaction.followup.send(embed=embed)
                return
                
            # Vérifier que le bot peut écrire dans le salon
            if not channel.permissions_for(guild.me).send_messages:
                embed = create_error_embed(
                    "Permission insuffisante",
                    f"Je n'ai pas la permission d'écrire dans {channel.mention}"
                )
                await interaction.followup.send(embed=embed)
                return
            
            # Sauvegarder le salon par défaut dans un fichier config serveur
            guild_id = guild.id
            config_data = {
                "guild_id": guild_id,
                "default_notification_channel_id": channel.id,
                "updated_at": datetime.now().isoformat()
            }
            
            # Utiliser la persistance pour sauvegarder la config serveur
            import json
            import os
            config_dir = os.path.join(os.path.dirname(__file__), "..", "..", "data", "guild_configs")
            os.makedirs(config_dir, exist_ok=True)
            
            config_file = os.path.join(config_dir, f"guild_{guild_id}_config.json")
            with open(config_file, 'w', encoding='utf-8') as f:
                json.dump(config_data, f, indent=2, ensure_ascii=False)
            
            embed = discord.Embed(
                title="✅ Salon par défaut configuré",
                description=f"Le salon par défaut pour ce serveur est maintenant {channel.mention}\n\n"
                           f"**Note:** Les joueurs avec un salon spécifique (via `/setchannel`) garderont leur salon personnel.",
                color=discord.Color.green()
            )
            
            # Message de test
            test_embed = discord.Embed(
                title="🏠 Salon par défaut configuré",
                description="Ce salon est maintenant le salon par défaut pour les notifications automatiques de ce serveur !",
                color=discord.Color.blue()
            )
            await channel.send(embed=test_embed)
            
            await interaction.followup.send(embed=embed)
            
        except Exception as e:
            logger.error(f"Erreur set default channel: {e}")
            embed = create_error_embed(
                "Erreur de configuration",
                f"Impossible de configurer le salon par défaut: {str(e)}"
            )
            await interaction.followup.send(embed=embed)

async def setup(bot: commands.Bot):
    """Fonction pour ajouter le cog au bot"""
    await bot.add_cog(AdminCommands(bot))
