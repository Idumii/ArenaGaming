"""
Bot principal Discord Arena Gaming
"""
import asyncio
import os
import structlog
import discord
from discord.ext import commands
from src.config.settings import get_settings

# Configuration du logging
structlog.configure(
    processors=[
        structlog.dev.ConsoleRenderer()
    ],
    wrapper_class=structlog.make_filtering_bound_logger(10),  # DEBUG level
    logger_factory=structlog.PrintLoggerFactory(),
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger()

class ArenaBot(commands.Bot):
    """Bot Discord principal"""
    
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        
        super().__init__(
            command_prefix='!',
            intents=intents,
            help_command=None
        )
        
        self.settings = get_settings()
        self.commands_synced = False  # Flag pour éviter les doubles syncs
    
    async def setup_hook(self):
        """Configuration initiale du bot"""
        logger.info("Chargement des extensions...")
        
        # Charger les commandes une par une pour identifier les erreurs
        extensions = [
            "src.commands.profile_commands",
            "src.commands.match_commands", 
            "src.commands.admin_commands"
        ]
        
        for extension in extensions:
            try:
                await self.load_extension(extension)
                logger.info(f"✅ Extension {extension} chargée")
            except Exception as e:
                logger.error(f"❌ Erreur chargement {extension}: {e}")
                import traceback
                traceback.print_exc()
        
        # Les commandes seront synchronisées dans on_ready()
        commands = self.tree.get_commands()
        logger.info(f"📋 {len(commands)} commandes chargées dans l'arbre")
    
    async def on_ready(self):
        """Événement quand le bot est prêt"""
        logger.info(f"Bot connecté en tant que {self.user}")
        logger.info(f"Connecté à {len(self.guilds)} serveur(s)")
        
        # Synchroniser seulement si pas déjà fait
        if not self.commands_synced:
            logger.info("🔄 Première synchronisation des commandes...")
            
            # Synchroniser vers chaque serveur individuellement (sans global)
            for guild in self.guilds:
                try:
                    logger.info(f"🔄 Synchronisation pour le serveur '{guild.name}'...")
                    # Copier les commandes de l'arbre vers le serveur spécifique
                    self.tree.copy_global_to(guild=guild)
                    synced_guild = await self.tree.sync(guild=guild)
                    logger.info(f"✅ {len(synced_guild)} commandes synchronisées pour '{guild.name}'")
                except Exception as guild_error:
                    logger.error(f"❌ Erreur sync serveur '{guild.name}': {guild_error}")
            
            self.commands_synced = True
            logger.info("🎉 Synchronisation terminée !")
        else:
            logger.info("ℹ️ Commandes déjà synchronisées, pas de re-sync")
        
        # Vérifier les permissions dans chaque serveur
        for guild in self.guilds:
            if self.user:
                bot_member = guild.get_member(self.user.id)
                if bot_member:
                    perms = bot_member.guild_permissions
                    logger.info(f"Serveur '{guild.name}': "
                               f"admin={perms.administrator}, "
                               f"send_messages={perms.send_messages}")
                    
                    if not perms.send_messages:
                        logger.warning(f"⚠️ Permissions limitées sur {guild.name}")
                else:
                    logger.warning(f"Bot membre introuvable sur {guild.name}")
        
        # Définir le statut du bot
        activity = discord.Activity(
            type=discord.ActivityType.watching,
            name="vos parties LoL et TFT"
        )
        await self.change_presence(activity=activity)
    
    async def on_command_error(self, ctx, error):
        """Gestion des erreurs de commandes"""
        logger.error(f"Erreur commande: {error}")

    async def on_app_command_error(self, interaction: discord.Interaction, error):
        """Gestion des erreurs spécifiques aux slash commands"""
        logger.error(f"Erreur slash command '{interaction.command}': {error}")
        try:
            if not interaction.response.is_done():
                await interaction.response.send_message(f"❌ Erreur: {error}", ephemeral=True)
            else:
                await interaction.followup.send(f"❌ Erreur: {error}", ephemeral=True)
        except Exception as e:
            logger.error(f"Impossible d'envoyer l'erreur à l'utilisateur: {e}")

async def main():
    """Fonction principale"""
    settings = get_settings()
    
    bot = ArenaBot()
    
    try:
        await bot.start(settings.discord_token)
    except KeyboardInterrupt:
        logger.info("Arrêt du bot...")
    except Exception as e:
        logger.error(f"Erreur fatale: {e}")
    finally:
        if not bot.is_closed():
            await bot.close()

if __name__ == "__main__":
    asyncio.run(main())
