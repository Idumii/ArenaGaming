import discord
from discord.ext import tasks  # Apparemment inutilisé, donc à supprimer si non nécessaire.
from discord import app_commands
from riot_api import fetchGameOngoing, fetchGameResult, requestSummoner, fetchRanks, fetchMasteries, requestSummonerTFT, fetchRanksTFT
from data_manager import DataManager  # Assurez-vous qu'il n'y a plus d'import inutile.
import urllib.parse
import os
from PIL import Image
import io
import aiohttp
import asyncio

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
            summonerTFT = await requestSummonerTFT(pseudo, tag)
            summoner_id, puuid = summoner[4], summoner[6]
            summonerRanks = fetchRanks(summonerId=summoner_id)
            summonerRanksTFT = fetchRanksTFT(summonerTFTId=summonerTFT[4])  
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

            for queue_type, rank_info in summonerRanksTFT.items():
                if queue_type == 'RANKED_TFT':
                    embed.add_field(name='Classé', value=rank_info, inline=False)
                elif queue_type == 'RANKED_TFT_DOUBLE_UP':
                    embed.add_field(name='Double Up', value=rank_info, inline=False)
                elif queue_type == 'RANKED_TFT_TURBO':
                    embed.add_field(name='Hyper Roll', value=rank_info, inline=False)

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
            
            async def get_image(url):
                async with aiohttp.ClientSession() as session:
                    async with session.get(url) as response:
                        if response.status == 200:
                            return Image.open(io.BytesIO(await response.read()))
                        return None

            # Get all images
            images = await asyncio.gather(*[get_image(icon) for icon, _, _, _ in summonerMasteries])
            images = [img for img in images if img is not None]
            
            # Create a combined image
            total_width = sum(img.width for img in images)
            max_height = max(img.height for img in images)
            
            combined_image = Image.new('RGBA', (total_width, max_height))
            x_offset = 0
            for img in images:
                combined_image.paste(img, (x_offset, 0))
                x_offset += img.width

            # Save the combined image to bytes
            combined_bytes = io.BytesIO()
            combined_image.save(combined_bytes, format='PNG')
            combined_bytes.seek(0)
            
            # Create the embed
            embed = discord.Embed(
                title=f"Top {count} Maîtrises de {pseudo}",
                color=discord.Colour.dark_green()
            )

            # Add champion information in horizontal groups
            champions_info = []
            masteries_info = []
            points_info = []

            for i, (_, name, level, points) in enumerate(summonerMasteries, 1):
                champions_info.append(f"#{i} - {name}")
                masteries_info.append(f"Niveau {level}")
                points_info.append(f"{points:,} pts")

            embed.add_field(name="Champions", value="\n".join(champions_info), inline=True)
            embed.add_field(name="Maîtrise", value="\n".join(masteries_info), inline=True)
            embed.add_field(name="Points", value="\n".join(points_info), inline=True)

            # Add the combined image at the top
            file = discord.File(combined_bytes, filename="champions.png")
            embed.set_image(url="attachment://champions.png")

            await interaction.followup.send(file=file, embed=embed)

        except ValueError as e:
            await interaction.followup.send(f"Erreur : {str(e)}")
        except Exception as e:
            await interaction.followup.send("Une erreur inattendue est survenue.")
            print(f"Erreur inattendue : {e}")
    

    @tree.command(name='addsummoner', description='Ajouter un invocateur à la liste pour être notifié quand celui-ci est en game')
    @app_commands.describe(pseudo='Nom invocateur', tag='EUW')
    async def addsummoner(interaction: discord.Interaction, pseudo: str, tag: str):
        try:
            guild_id = str(interaction.guild_id)  # Convert to string for consistency
            print(f"Requesting summoner with pseudo: {pseudo}, tag: {tag}")
            summoner = await requestSummoner(pseudo, tag)
            print(f"Summoner information: {summoner}")
            
            if summoner:
                # Load existing summoners for this guild
                guild_summoners = data_manager.load_summoners_to_watch(guild_id)
                
                # Vérifie si l'invocateur est déjà dans la liste pour ce serveur
                if any(s['puuid'] == summoner[6] for s in guild_summoners):
                    await interaction.response.send_message(f"L'invocateur {summoner[1]} est déjà suivi sur ce serveur.")
                    return
                
                # Generate new ID based on guild's current summoner list
                summoner_id = len(guild_summoners) + 1
                (summonerTagline, summonerGamename, summonerLevel, profileIcon, summonerId, totalMastery_data, puuid) = summoner
                
                new_summoner = {
                    'id': summoner_id,
                    'name': summonerGamename,
                    'tag': summonerTagline,
                    'puuid': puuid
                }
                
                # Add to guild's summoner list and save
                guild_summoners.append(new_summoner)
                data_manager.save_summoners_to_watch(guild_summoners, guild_id)
                
                await interaction.response.send_message(
                    f"Summoner {summonerGamename}#{summonerTagline} a été ajouté à la liste avec l'ID {summoner_id}."
                )
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
            guild_id = str(interaction.guild_id)
            guild_summoners = data_manager.load_summoners_to_watch(guild_id)
            
            if not guild_summoners:
                await interaction.response.send_message("Aucun invocateur n'est suivi pour le moment.")
            else:
                summoner_list = "\n".join([f"ID: **{summoner['id']}** - {summoner['name']}#{summoner['tag']}" 
                                        for summoner in guild_summoners])
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

    @tree.command(name='setchannel', description="Définir le salon d'annonce des parties")
    async def set_notification_channel(interaction: discord.Interaction, channel: discord.TextChannel = None):
        """Set the channel for game notifications"""
        if channel is None:
            channel = interaction.channel
        
        guild_id = interaction.guild_id
        data_manager.set_notification_channel(guild_id, channel.id)
        await interaction.response.send_message(f"Canal de notification défini sur {channel.mention} pour ce serveur.")
        