from asyncio import tasks
import discord
from discord.ext import tasks
from discord import app_commands
from riot_api import fetchGameOngoing, fetchGameResult, requestSummoner, fetchRanks, fetchMasteries
from data_manager import summoners_to_watch, notified_summoners, notified_games
import urllib.parse
import json

def setup_commands(client, tree):
    #Commande pour récuperer le profil d'un invocateur
    @tree.command(name='invocateur', description='Profil d\'Invocateur')
    @app_commands.describe(pseudo='Nom invocateur', tag='EUW')
    async def invocateur(interaction: discord.Interaction, pseudo: str, tag: str):
        await interaction.response.defer()
        try:
            print('Invocateur trouvé')
            summoner = await requestSummoner(pseudo, tag)
            print(f"Summoner ID: {summoner[4]}, PUUID: {summoner[6]}")  # Debugging
            summonerRanks = fetchRanks(summonerId=summoner[4])
            embed = discord.Embed(
                title=f"{summoner[1]} #{tag}",
                description=f"Niveau: {summoner[2]}",
                color=discord.Colour.gold()
            )
            embed.set_thumbnail(url=summoner[3])

            print("Summoner Ranks:", summonerRanks)  # Ajouter cette ligne pour déboguer

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
    
    # Commande discord Maitrises
    @tree.command(name='maitrises', description='Meilleures Maitrises d\'un Invocateur')
    @app_commands.describe(pseudo='Nom invocateur', tag='EUW', count='Nombre de champions à afficher (1-5)')
    async def maitrises(interaction: discord.Interaction, pseudo: str, tag: str, count: int):
        await interaction.response.defer()
        try:
            if not 1 <= count <= 5:
                await interaction.followup.send("Veuillez spécifier un nombre entre 1 et 5.")
                return

            summoner = await requestSummoner(pseudo, tag)
            summonerMasteries = fetchMasteries(puuid=summoner[6], count=count)  # Utilisez l'index correct pour puuid

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
    
                
    # Commande pour ajouter un invocateur à la liste
    @tree.command(name='addsummoner', description='Ajouter un invocateur à la liste pour être notifié quand celui-ci est en game')
    @app_commands.describe(pseudo='Nom invocateur', tag='EUW')
    async def addsummoner(interaction: discord.Interaction, pseudo: str, tag: str):
        try:
            summoner = await requestSummoner(pseudo, tag)
            summoner_id = len(summoners_to_watch) + 1  # Utiliser un ID numérique simple
            summoners_to_watch.append({'id': summoner_id, 'name': summoner[1], 'tag': tag, 'puuid': summoner[6]})
            with open('summoners_to_watch.json', 'w', encoding='utf-8') as f:
                json.dump(summoners_to_watch, f, ensure_ascii=False, indent=4)
            await interaction.response.send_message(f"Summoner {summoner[1]}#{tag} a été ajouté à la liste avec l'ID {summoner_id}.")
        except ValueError as e:
            await interaction.response.send_message(f"Error: {str(e)}")
        except Exception as e:
            await interaction.response.send_message("Une erreur inattendue est survenue.")
            print(f"Unexpected error: {e}")

    # Commande pour supprimer un invocateur de la liste par ID
    @tree.command(name='removesummoner', description='Supprimer un invocateur de la liste des suivis par ID')
    @app_commands.describe(summoner_id='ID de l\'invocateur')
    async def removesummoner(interaction: discord.Interaction, summoner_id: int):
        initial_count = len(summoners_to_watch)
        summoners_to_watch[:] = [s for s in summoners_to_watch if s['id'] != summoner_id]
        if len(summoners_to_watch) < initial_count:
            with open('summoners_to_watch.json', 'w', encoding='utf-8') as f:
                json.dump(summoners_to_watch, f, ensure_ascii=False, indent=4)
            await interaction.response.send_message(f"Invocateur avec l'ID {summoner_id} a été supprimé de la liste.")
        else:
            await interaction.response.send_message(f"Aucun invocateur trouvé avec l'ID {summoner_id}.")



    # Commande pour afficher la liste des invocateurs suivis
    @tree.command(name='listsummoners', description='Afficher la liste des invocateurs suivis')
    async def listsummoners(interaction: discord.Interaction):
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

    # Commande discord Game en cours
    @tree.command(name='ingame', description='Savoir si un joueur est en jeu')
    @app_commands.describe(pseudo='Nom invocateur', tag='EUW')
    async def ingame(interaction: discord.Interaction, pseudo: str, tag: str):
        try:
            summoner = await requestSummoner(pseudo, tag)
            summonerInGame = fetchGameOngoing(puuid=summoner[6])

            encoded_name = urllib.parse.quote(summoner[1])
            encoded_tag = urllib.parse.quote(summoner[0])
            url = f"https://porofessor.gg/fr/live/euw/{encoded_name}%20-{encoded_tag}"
            link_text = f"**[En jeu]({url})**"

            embed = discord.Embed(
                description=f"{link_text}\n\n{summoner[1]} est en **{summonerInGame[2]}**. Il joue **{summonerInGame[1]}**",
                color=discord.Colour.blue()
            )
            await interaction.response.send_message(embed=embed)  # Envoyer la réponse sans différer

        except ValueError as e:
            await interaction.response.send_message(f"Error: {str(e)}", ephemeral=True)
        except Exception as e:
            await interaction.response.send_message("Une erreur inattendue est survenue.", ephemeral=True)
            # Enregistrement de l'erreur pour le débogage
            print(f"Unexpected error: {e}")

    # Ajoutez d'autres commandes ici