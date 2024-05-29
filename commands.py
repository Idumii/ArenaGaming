import discord
from discord.ext import tasks
from discord import app_commands
from riot_api import fetchGameOngoing, fetchGameResult, requestSummoner, fetchRanks, fetchMasteries
from data_manager import DataManager, print_summoners_to_watch
import urllib.parse
import json

# Initialiser DataManager
data_manager = DataManager()

# Charger les données initiales
summoners_to_watch = data_manager.load_summoners_to_watch()

def setup_commands(client, tree):
    @tree.command(name='invocateur', description='Profil d\'Invocateur')
    @app_commands.describe(pseudo='Nom invocateur', tag='EUW')
    async def invocateur(interaction: discord.Interaction, pseudo: str, tag: str):
        await interaction.response.defer()
        try:
            print('Invocateur trouvé')
            summoner = await requestSummoner(pseudo, tag)
            summoner_id, puuid = summoner[4], summoner[6]
            summonerRanks = fetchRanks(summonerId=summoner_id)
            embed = discord.Embed(
                title=f"{summoner[1]} #{tag}",
                description=f"Niveau: {summoner[2]}",
                color=discord.Colour.gold()
            )
            embed.set_thumbnail(url=summoner[3])

            # Ajout des informations de rang
            for queue_type, rank_info in summonerRanks.items():
                if queue_type == 'RANKED_SOLO_5x5':
                    embed.add_field(name='Solo/Duo', value=rank_info, inline=False)
                elif queue_type == 'RANKED_FLEX_SR':
                    embed.add_field(name='Flex', value=rank_info, inline=False)
                elif queue_type == 'CHERRY':
                    embed.add_field(name='Arena', value=rank_info, inline=False)

            await interaction.followup.send(embed=embed)
        except ValueError as e:
            await interaction.followup.send(f"Error: {str(e)}")
        except Exception as e:
            await interaction.followup.send("Une erreur inattendue est survenue.")
            print(f"Unexpected error: {e}")

    @tree.command(name='maitrises', description='Meilleures Maitrises d\'un Invocateur')
    @app_commands.describe(pseudo='Nom invocateur', tag='EUW', count='Nombre de champions à afficher (1-5)')
    async def maitrises(interaction: discord.Interaction, pseudo: str, tag: str, count: int):
        await interaction.response.defer()
        try:
            if not 1 <= count <= 5:
                await interaction.followup.send("Veuillez spécifier un nombre entre 1 et 5.")
                return

            summoner = await requestSummoner(pseudo, tag)
            summonerMasteries = fetchMasteries(puuid=summoner[6], count=count)

            embeds = []

            for icon, name, level, points in summonerMasteries:
                embed = discord.Embed(
                    title=name,
                    color=discord.Colour.dark_green()
                )
                embed.set_thumbnail(url=icon)
                embed.add_field(name='Niveau de maîtrise', value=level, inline=False)
                embed.add_field(name='Points de maîtrise', value=points, inline=False)
                embeds.append(embed)

            for embed in embeds:
                await interaction.followup.send(embed=embed)
        except ValueError as e:
            await interaction.followup.send(f"Error: {str(e)}")
        except Exception as e:
            await interaction.followup.send("Une erreur inattendue est survenue.")
            print(f"Unexpected error: {e}")

    @tree.command(name='addsummoner', description='Ajouter un invocateur à la liste pour être notifié quand celui-ci est en game')
    @app_commands.describe(pseudo='Nom invocateur', tag='EUW')
    async def addsummoner(interaction: discord.Interaction, pseudo: str, tag: str):
        global summoners_to_watch
        try:
            print(f"Requesting summoner with pseudo: {pseudo}, tag: {tag}")
            summoner = await requestSummoner(pseudo, tag)
            print(f"Summoner information: {summoner}")
            if summoner:
                summoner_id = len(summoners_to_watch) + 1
                (summonerTagline, summonerGamename, summonerLevel, profileIcon, summonerId, totalMastery_data, puuid) = summoner
                new_summoner = {
                    'id': summoner_id, 
                    'name': summonerGamename, 
                    'tag': summonerTagline, 
                    'puuid': puuid
                }
                summoners_to_watch.append(new_summoner)
                data_manager.save_summoners_to_watch(summoners_to_watch)
                await interaction.response.send_message(f"Summoner {summonerGamename}#{tag} a été ajouté à la liste avec l'ID {summoner_id}.")
            else:
                await interaction.response.send_message("Erreur: L'invocateur n'a pas pu être trouvé.")
        except ValueError as e:
            print(f"Value error: {e}")
            await interaction.response.send_message(f"Error: {str(e)}")
        except Exception as e:
            print(f"Unexpected error: {e}")
            await interaction.response.send_message("Une erreur inattendue est survenue.")

    @tree.command(name='removesummoner', description='Supprimer un invocateur de la liste des suivis par ID')
    @app_commands.describe(summoner_id='ID de l\'invocateur')
    async def removesummoner(interaction: discord.Interaction, summoner_id: int):
        global summoners_to_watch
        initial_count = len(summoners_to_watch)
        summoners_to_watch = [s for s in summoners_to_watch if s['id'] != summoner_id]
        if len(summoners_to_watch) < initial_count:
            data_manager.save_summoners_to_watch(summoners_to_watch)
            await interaction.response.send_message(f"Invocateur avec l'ID {summoner_id} a été supprimé de la liste.")
        else:
            await interaction.response.send_message(f"Aucun invocateur trouvé avec l'ID {summoner_id}.")

    @tree.command(name='listsummoners', description='Afficher la liste des invocateurs suivis')
    async def listsummoners(interaction: discord.Interaction):
        global summoners_to_watch
        try:
            if not summoners_to_watch:
                await interaction.response.send_message("Aucun invocateur n'est suivi pour le moment.")
            else:
                summoner_list = "\n".join([f"ID: **{summoner['id']}** - {summoner['name']}#{summoner['tag']}" for summoner in summoners_to_watch])
                embed = discord.Embed(description=f"Liste des invocateurs suivis :\n{summoner_list}")
                await interaction.response.send_message(embed=embed)
        except Exception as e:
            await interaction.response.send_message("Une erreur inattendue est survenue.")
            print(f"Unexpected error: {e}")

    # Ajoutez d'autres commandes ici