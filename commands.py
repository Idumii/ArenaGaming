import discord
from discord.ext import tasks  # Apparemment inutilisé, donc à supprimer si non nécessaire.
from discord import app_commands
from riot_api import fetchGameOngoing, fetchGameResult, requestSummoner, fetchRanks, fetchMasteries
from data_manager import DataManager  # Assurez-vous qu'il n'y a plus d'import inutile.
import urllib.parse
import os

# Initialiser DataManager
data_manager = DataManager()

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

            for queue_type, rank_info in summonerRanks.items():
                if queue_type == 'RANKED_SOLO_5x5':
                    embed.add_field(name='Solo/Duo', value=rank_info, inline=False)
                elif queue_type == 'RANKED_FLEX_SR':
                    embed.add_field(name='Flex', value=rank_info, inline=False)
                elif queue_type == 'CHERRY':
                    embed.add_field(name='Arena', value=rank_info, inline=False)

            await interaction.followup.send(embed=embed)
        except ValueError as e:
            await interaction.followup.send(f"Erreur : {str(e)}")
        except Exception as e:
            await interaction.followup.send("Une erreur inattendue est survenue.")
            print(f"Erreur inattendue : {e}")

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
            await interaction.followup.send(f"Erreur : {str(e)}")
        except Exception as e:
            await interaction.followup.send("Une erreur inattendue est survenue.")
            print(f"Erreur inattendue : {e}")

    @tree.command(name='addsummoner', description='Ajouter un invocateur à la liste pour être notifié quand celui-ci est en game')
    @app_commands.describe(pseudo='Nom invocateur', tag='EUW')
    async def addsummoner(interaction: discord.Interaction, pseudo: str, tag: str):
        try:
            print(f"Requesting summoner with pseudo: {pseudo}, tag: {tag}")
            summoner = await requestSummoner(pseudo, tag)
            print(f"Summoner information: {summoner}")
            if summoner:
                # Vérifie si l'invocateur est déjà dans la liste
                if any(s['puuid'] == summoner[6] for s in data_manager.summoners):
                    await interaction.response.send_message(f"L'invocateur {summoner[1]} est déjà suivi.")
                    return
                
                summoner_id = len(data_manager.summoners) + 1
                (summonerTagline, summonerGamename, summonerLevel, profileIcon, summonerId, totalMastery_data, puuid) = summoner
                new_summoner = {
                    'id': summoner_id, 
                    'name': summonerGamename, 
                    'tag': summonerTagline, 
                    'puuid': puuid
                }
                data_manager.summoners.append(new_summoner)
                data_manager.save_summoners_to_watch(data_manager.summoners)
                await interaction.response.send_message(f"Summoner {summonerGamename}#{tag} a été ajouté à la liste avec l'ID {summoner_id}.")
            else:
                await interaction.response.send_message("Erreur : L'invocateur n'a pas pu être trouvé.")
        except ValueError as e:
            print(f"Erreur de valeur : {e}")
            await interaction.response.send_message(f"Erreur : {str(e)}")
        except Exception as e:
            print(f"Erreur inattendue : {e}")
            await interaction.response.send_message("Une erreur inattendue est survenue.")

    @tree.command(name='removesummoner', description='Supprimer un invocateur de la liste des suivis par ID')
    @app_commands.describe(summoner_id='ID de l\'invocateur')
    async def removesummoner(interaction: discord.Interaction, summoner_id: int):
        initial_count = len(data_manager.summoners)
        data_manager.summoners = [s for s in data_manager.summoners if s['id'] != summoner_id]
        if len(data_manager.summoners) < initial_count:
            data_manager.save_summoners_to_watch(data_manager.summoners)
            await interaction.response.send_message(f"Invocateur avec l'ID {summoner_id} a été supprimé de la liste.")
        else:
            await interaction.response.send_message(f"Aucun invocateur trouvé avec l'ID {summoner_id}.")

    @tree.command(name='listsummoners', description='Afficher la liste des invocateurs suivis')
    async def listsummoners(interaction: discord.Interaction):
        try:
            if not data_manager.summoners:
                await interaction.response.send_message("Aucun invocateur n'est suivi pour le moment.")
            else:
                summoner_list = "\n".join([f"ID: **{summoner['id']}** - {summoner['name']}#{summoner['tag']}" for summoner in data_manager.summoners])
                embed = discord.Embed(description=f"Liste des invocateurs suivis :\n{summoner_list}")
                await interaction.response.send_message(embed=embed)
        except Exception as e:
            await interaction.response.send_message("Une erreur inattendue est survenue.")
            print(f"Erreur inattendue : {e}")
            
    @tree.command(name='ingame', description='Savoir si un joueur est en jeu')
    @app_commands.describe(pseudo='Nom invocateur', tag='EUW')
    async def ingame(interaction: discord.Interaction, pseudo: str, tag: str):
        try:
            summoner = await requestSummoner(pseudo, tag)
            riot_id, champion_name, game_mode, game_id, champion_icon = fetchGameOngoing(puuid=summoner[6])

            if riot_id and game_mode:
                encoded_name = urllib.parse.quote(summoner[1])
                encoded_tag = urllib.parse.quote(summoner[0])
                url = f"https://porofessor.gg/fr/live/euw/{encoded_name}%20-{encoded_tag}"
                link_text = f"**[En jeu]({url})**"

                embed = discord.Embed(
                    description=f"{link_text}\n\n{summoner[1]} est en **{game_mode}**. Il joue **{champion_name}**",
                    color=discord.Colour.blue()
                )
                embed.set_thumbnail(url=champion_icon)
                await interaction.response.send_message(embed=embed)
            else:
                await interaction.response.send_message(f"{summoner[1]} n'est actuellement pas en jeu.", ephemeral=True)
        except ValueError as e:
            await interaction.response.send_message(f"Erreur : {str(e)}", ephemeral=True)
        except Exception as e:
            await interaction.response.send_message("Une erreur inattendue est survenue.", ephemeral=True)
            print(f"Erreur inattendue : {e}")

    @tree.command(name='sync', description='Owner Only')
    async def sync(interaction: discord.Interaction):
        idumi = os.getenv('ID_IDUMI')
        if idumi is None:
            await interaction.response.send_message("Erreur : l'identifiant de l'owner n'est pas défini dans les variables d'environnement.")
            return
        owner_id = int(idumi)
        if interaction.user.id == owner_id:
            await interaction.response.send_message('Synchronisation en cours...')
            try:
                await tree.sync()
                await interaction.followup.send('Arbre de commandes synchronisé.')
                print('Arbre de commandes synchronisé')
            except Exception as e:
                await interaction.followup.send(f'Échec de la synchronisation des commandes : {e}')
                print(f'Échec de la synchronisation des commandes : {e}')
        else:
            id = interaction.user.id
            await interaction.response.send_message(f'Seul le développeur peut utiliser cette commande -> {id} / {owner_id}')