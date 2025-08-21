"""
Commandes slash Discord pour les parties
"""
import discord
from discord.ext import commands
from discord import app_commands
from typing import Optional
import structlog
from ..api.summoner_api import SummonerAPI
from ..api.match_api import MatchAPI
from ..api.tft_api import TFTAPI
from ..utils.discord_embeds import (
    create_game_result_embed, 
    create_tft_result_embed,
    create_error_embed
)

logger = structlog.get_logger()

class MatchCommands(commands.Cog):
    """Commandes liées aux parties"""
    
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.summoner_api = SummonerAPI()
        self.match_api = MatchAPI()
        self.tft_api = TFTAPI()
    
    @app_commands.command(name="lastgame", description="Afficher la dernière partie d'un joueur")
    @app_commands.describe(
        summoner_name="Nom du joueur",
        tag_line="Tag du joueur (ex: EUW1)",
        game_type="Type de jeu"
    )
    @app_commands.choices(game_type=[
        app_commands.Choice(name="League of Legends", value="lol"),
        app_commands.Choice(name="Teamfight Tactics", value="tft")
    ])
    async def last_game(
        self,
        interaction: discord.Interaction,
        summoner_name: str,
        tag_line: str = "EUW1",
        game_type: str = "lol"
    ):
        """Afficher la dernière partie d'un joueur"""
        await interaction.response.defer()
        
        try:
            # Récupérer le summoner
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
            
            if game_type == "tft":
                # Récupérer la dernière partie TFT
                match_ids = await self.tft_api.get_recent_tft_matches(summoner.puuid, 1)
                
                if not match_ids:
                    embed = create_error_embed(
                        "Aucune partie trouvée",
                        "Aucune partie TFT récente trouvée pour ce joueur"
                    )
                    await interaction.followup.send(embed=embed)
                    return
                
                match_details = await self.tft_api.get_tft_match_details(match_ids[0])
                
                if not match_details:
                    embed = create_error_embed(
                        "Erreur",
                        "Impossible de récupérer les détails de la partie"
                    )
                    await interaction.followup.send(embed=embed)
                    return
                
                embed = create_tft_result_embed(match_details, summoner.puuid)
                
            else:  # LoL
                # Récupérer la dernière partie LoL
                match_ids = await self.match_api.get_recent_matches(summoner.puuid, 1)
                
                if not match_ids:
                    embed = create_error_embed(
                        "Aucune partie trouvée",
                        "Aucune partie LoL récente trouvée pour ce joueur"
                    )
                    await interaction.followup.send(embed=embed)
                    return
                
                match_details = await self.match_api.get_match_details(match_ids[0])
                
                if not match_details:
                    embed = create_error_embed(
                        "Erreur",
                        "Impossible de récupérer les détails de la partie"
                    )
                    await interaction.followup.send(embed=embed)
                    return
                
                embed, items_file = await create_game_result_embed(match_details, summoner.puuid)
                
                # Envoyer avec le fichier d'items si disponible
                if items_file:
                    await interaction.followup.send(embed=embed, file=items_file)
                else:
                    await interaction.followup.send(embed=embed)
                return
            
            # Pour TFT (pas de fichier items)
            await interaction.followup.send(embed=embed)
            
        except Exception as e:
            logger.error(f"Erreur commande lastgame: {e}")
            embed = create_error_embed(
                "Erreur",
                "Une erreur est survenue lors de la récupération de la partie"
            )
            await interaction.followup.send(embed=embed)
    
    @app_commands.command(name="ingame", description="Vérifier si un joueur est en partie")
    @app_commands.describe(
        summoner_name="Nom du joueur",
        tag_line="Tag du joueur (ex: EUW1)"
    )
    async def in_game(
        self,
        interaction: discord.Interaction,
        summoner_name: str,
        tag_line: str = "EUW1"
    ):
        """Vérifier si un joueur est actuellement en partie"""
        await interaction.response.defer()
        
        try:
            # Récupérer le summoner
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
            
            # Vérifier LoL
            lol_game = await self.match_api.get_current_game(summoner.puuid)
            tft_game = await self.tft_api.get_current_tft_game(summoner.puuid)
            
            if lol_game:
                embed = discord.Embed(
                    title=f"🎮 {summoner.name}#{summoner.tag_line} est en partie !",
                    description=f"**Mode:** {lol_game.get('gameMode', 'Inconnu')}\n"
                               f"**Durée:** {lol_game.get('gameLength', 0) // 60}m",
                    color=discord.Color.green()
                )
            elif tft_game:
                embed = discord.Embed(
                    title=f"🎮 {summoner.name}#{summoner.tag_line} est en partie TFT !",
                    description="Partie TFT en cours",
                    color=discord.Color.green()
                )
            else:
                embed = discord.Embed(
                    title=f"😴 {summoner.name}#{summoner.tag_line} n'est pas en partie",
                    color=discord.Color.blue()
                )
            
            await interaction.followup.send(embed=embed)
            
        except Exception as e:
            logger.error(f"Erreur commande ingame: {e}")
            embed = create_error_embed(
                "Erreur",
                "Une erreur est survenue lors de la vérification"
            )
            await interaction.followup.send(embed=embed)

async def setup(bot: commands.Bot):
    """Fonction pour ajouter le cog au bot"""
    await bot.add_cog(MatchCommands(bot))
