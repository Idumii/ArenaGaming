"""
Commandes slash Discord pour les profils utilisateurs
"""
import discord
from discord.ext import commands
from discord import app_commands
from typing import Optional
from datetime import datetime
import structlog
from ..api.summoner_api import SummonerAPI
from ..api.tft_api import TFTAPI
from ..utils.discord_embeds import create_basic_profile_embed, create_lol_ranked_embed, create_tft_ranked_embed, create_error_embed

logger = structlog.get_logger()

class ProfileCommands(commands.Cog):
    """Commandes liées aux profils de joueurs"""
    
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.summoner_api = SummonerAPI()
        self.tft_api = TFTAPI()
    
    @app_commands.command(name="profile", description="Afficher le profil d'un joueur")
    @app_commands.describe(
        summoner_name="Nom du joueur",
        tag_line="Tag du joueur (ex: EUW1)"
    )
    async def profile(
        self,
        interaction: discord.Interaction,
        summoner_name: str,
        tag_line: str = "EUW1"
    ):
        """Afficher le profil d'un joueur avec ses rangs"""
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
            
            # Récupérer les informations de rang via PUUID
            ranked_info = await self.summoner_api.get_ranked_info_by_puuid(summoner.puuid)
            logger.info(f"Rangs LoL récupérés pour {summoner_name}: {ranked_info}")
            
            # Récupérer le score de maîtrise total
            mastery_score = await self.summoner_api.get_mastery_score(summoner.puuid)
            
            # Récupérer les top maîtrises
            top_masteries = await self.summoner_api.get_champion_masteries(summoner.puuid, 3)
            
            # Récupérer les informations TFT (optionnel) - utiliser la clé TFT pour obtenir le bon PUUID
            tft_ranked_info = {}
            try:
                # Récupérer le PUUID TFT avec la clé TFT (peut être différent du PUUID LoL)
                tft_summoner = await self.summoner_api.get_summoner_by_riot_id_tft(summoner_name, tag_line)
                if tft_summoner:
                    logger.info(f"PUUID TFT trouvé: {tft_summoner.puuid}")
                    tft_ranked_info = await self.summoner_api.get_tft_ranked_info(tft_summoner.puuid)
                    logger.info(f"Rangs TFT récupérés pour {summoner_name}: {tft_ranked_info}")
                else:
                    logger.info(f"Aucun PUUID TFT trouvé pour {summoner_name}")
            except Exception as e:
                logger.warning(f"Impossible de récupérer les infos TFT pour {summoner_name}: {e}")
                # Continue sans les infos TFT
            
            # Créer les 3 embeds séparés
            basic_embed = create_basic_profile_embed(summoner, mastery_score, top_masteries)
            lol_embed = create_lol_ranked_embed(summoner, ranked_info)
            tft_embed = create_tft_ranked_embed(summoner, tft_ranked_info)
            
            # Envoyer les 3 embeds
            await interaction.followup.send(embed=basic_embed)
            await interaction.followup.send(embed=lol_embed)
            await interaction.followup.send(embed=tft_embed)
            
        except Exception as e:
            logger.error(f"Erreur commande profile: {e}")
            embed = create_error_embed(
                "Erreur",
                "Une erreur est survenue lors de la récupération du profil"
            )
            await interaction.followup.send(embed=embed)

    @app_commands.command(name="maitrises", description="Afficher les meilleures maîtrises d'un joueur")
    @app_commands.describe(
        summoner_name="Nom du joueur",
        tag_line="Tag du joueur (ex: EUW1)",
        count="Nombre de champions à afficher (1-5)"
    )
    async def masteries(
        self,
        interaction: discord.Interaction,
        summoner_name: str,
        tag_line: str = "EUW1",
        count: int = 5
    ):
        """Afficher les meilleures maîtrises d'un joueur avec images"""
        await interaction.response.defer()
        
        if not 1 <= count <= 5:
            embed = create_error_embed(
                "Paramètre invalide",
                "Veuillez spécifier un nombre entre 1 et 5 pour le nombre de champions."
            )
            await interaction.followup.send(embed=embed)
            return
        
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
            
            # Récupérer les maîtrises
            masteries = await self.summoner_api.get_champion_masteries(summoner.puuid, count)
            
            if not masteries:
                embed = create_error_embed(
                    "Aucune maîtrise",
                    f"Aucune maîtrise trouvée pour {summoner_name}#{tag_line}"
                )
                await interaction.followup.send(embed=embed)
                return
            
            # Créer l'embed avec les maîtrises
            embed = discord.Embed(
                title=f"Top {count} Maîtrises de {summoner_name}#{tag_line}",
                color=discord.Color.dark_green(),
                timestamp=datetime.now()
            )
            
            # Préparer les informations en colonnes
            champions_info = []
            masteries_info = []
            points_info = []
            
            for i, mastery in enumerate(masteries, 1):
                champions_info.append(f"#{i} - {mastery['championName']}")
                masteries_info.append(f"Niveau {mastery['championLevel']}")
                points_info.append(f"{mastery['championPoints']:,} pts")
            
            embed.add_field(
                name="🏅 Champions",
                value="\n".join(champions_info),
                inline=True
            )
            embed.add_field(
                name="📊 Maîtrise",
                value="\n".join(masteries_info),
                inline=True
            )
            embed.add_field(
                name="💎 Points",
                value="\n".join(points_info),
                inline=True
            )
            
            # TODO: Ajouter la création d'image combinée des champions
            # Pour l'instant, utilisons juste l'icône du premier champion
            if masteries:
                embed.set_thumbnail(url=masteries[0]['championIcon'])
            
            await interaction.followup.send(embed=embed)
            
        except Exception as e:
            logger.error(f"Erreur commande maitrises: {e}")
            embed = create_error_embed(
                "Erreur",
                "Une erreur est survenue lors de la récupération des maîtrises"
            )
            await interaction.followup.send(embed=embed)
    
    @app_commands.command(name="me", description="Afficher votre profil lié")
    async def my_profile(self, interaction: discord.Interaction):
        """Afficher le profil du joueur lié à cet utilisateur Discord"""
        await interaction.response.defer()
        
        # TODO: Implémenter le système de liaison des comptes
        embed = create_error_embed(
            "Fonctionnalité non disponible",
            "Le système de liaison des comptes n'est pas encore implémenté.\n"
            "Utilisez `/profile` avec votre nom de joueur en attendant."
        )
        await interaction.followup.send(embed=embed)

async def setup(bot: commands.Bot):
    """Fonction pour ajouter le cog au bot"""
    await bot.add_cog(ProfileCommands(bot))
