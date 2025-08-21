"""
Bot simple pour diagnostiquer les problèmes de synchronisation
"""
import asyncio
import discord
from discord.ext import commands
from discord import app_commands
from src.config.settings import get_settings

class SimpleBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        
        super().__init__(
            command_prefix='!',
            intents=intents,
            help_command=None
        )
        
        self.settings = get_settings()

    async def setup_hook(self):
        print("🔄 Configuration du bot...")
        
        # Ajouter une commande simple
        @self.tree.command(name="test", description="Commande de test")
        async def test_command(interaction: discord.Interaction):
            await interaction.response.send_message("✅ Le bot fonctionne !", ephemeral=True)
        
        @self.tree.command(name="sync", description="Synchroniser les commandes")
        async def sync_command(interaction: discord.Interaction):
            await interaction.response.defer()
            try:
                synced = await self.tree.sync()
                await interaction.followup.send(f"✅ {len(synced)} commandes synchronisées")
            except Exception as e:
                await interaction.followup.send(f"❌ Erreur: {e}")
        
        # Synchronisation
        try:
            synced = await self.tree.sync()
            print(f"✅ {len(synced)} commandes synchronisées")
        except Exception as e:
            print(f"❌ Erreur sync: {e}")

    async def on_ready(self):
        print(f"🤖 Bot connecté: {self.user}")
        print(f"📊 Serveurs: {len(self.guilds)}")
        
        # Lister les serveurs
        for guild in self.guilds:
            print(f"  - {guild.name} (ID: {guild.id})")

async def main():
    settings = get_settings()
    bot = SimpleBot()
    
    try:
        await bot.start(settings.discord_token)
    except KeyboardInterrupt:
        print("🛑 Arrêt du bot")
    except Exception as e:
        print(f"❌ Erreur: {e}")
    finally:
        if not bot.is_closed():
            await bot.close()

if __name__ == "__main__":
    asyncio.run(main())
