"""
Utilitaires pour la gestion des embeds Discord
"""
import discord
from typing import List, Optional, Dict, TYPE_CHECKING, Tuple, Any
from datetime import datetime
from ..models.game_models import GameResult, TFTGameResult, Summoner, RankedInfo
from .item_image_generator import ItemImageGenerator

def _get_tft_queue_name(queue_id: int) -> str:
    """Convertir l'ID de queue TFT en nom lisible"""
    queue_names = {
        1090: "Normal",  # TFT Normal
        1100: "Classé",  # TFT Ranked
        1130: "Double UP",  # TFT Double Up
        1160: "Épreuves de Pic Toc",  # TFT Pic Toc (ou autres épreuves)
        # Autres IDs possibles selon les mises à jour
        1091: "Normal (Turbo)",
        1101: "Classé (Hyper Roll)",
    }
    return queue_names.get(queue_id, f"Mode inconnu ({queue_id})")

def _get_placement_emoji(placement: int) -> str:
    """Obtenir l'emoji correspondant au placement"""
    emojis = {
        1: "🥇",  # Or
        2: "🥈",  # Argent
        3: "🥉",  # Bronze
        4: "🎖️",  # Top 4
        5: "🎯",  # Top 5
        6: "⚽",  # Top 6
        7: "💀",  # Bottom 2
        8: "☠️",  # Dernier
    }
    return emojis.get(placement, "🎮")

def _get_companion_info(companion: Optional[Dict[str, Any]]) -> Optional[str]:
    """Extraire les informations de la petite légende"""
    if not companion:
        return None
    
    # Exemple de structure companion (peut varier selon l'API)
    content_id = companion.get('content_ID', '')
    item_id = companion.get('item_ID', 0)
    skin_id = companion.get('skin_ID', 0)
    species = companion.get('species', '')
    
    # Vous pouvez créer un mapping des IDs vers les noms si nécessaire
    return f"Petite légende: {species}" if species else None

if TYPE_CHECKING:
    from ..models.game_models import Participant

def _get_item_icon_url(item_id: int) -> str:
    """Récupérer l'URL de l'icône d'un item"""
    if item_id == 0:
        return ""
    return f"https://ddragon.leagueoflegends.com/cdn/14.24.1/img/item/{item_id}.png"

def _format_items_display(participant: "Participant") -> List[int]:
    """Récupérer la liste des IDs d'items du participant"""
    items = []
    for i in range(7):  # 6 items + trinket
        item_id = getattr(participant, f'item{i}', 0)
        if item_id > 0:
            items.append(item_id)
    return items

def create_basic_profile_embed(summoner: Summoner, mastery_score: int = 0, top_masteries: Optional[List[dict]] = None) -> discord.Embed:
    """Créer l'embed basique du profil avec niveau, icône et maîtrises"""
    embed = discord.Embed(
        title=f"{summoner.name}#{summoner.tag_line}",
        description=f"Niveau {summoner.summoner_level}",
        color=discord.Color.blue(),
        timestamp=datetime.now()
    )
    
    # Icône de profil
    icon_url = f"https://cdn.communitydragon.org/14.10.1/profile-icon/{summoner.profile_icon_id}"
    embed.set_thumbnail(url=icon_url)
    
    # Score de maîtrise total
    if mastery_score > 0:
        embed.add_field(
            name="🏆 Score de Maîtrise Total",
            value=f"{mastery_score:,} points",
            inline=True
        )
    
    # Top maîtrises si disponibles
    if top_masteries and len(top_masteries) > 0:
        # Créer les champs pour les maîtrises
        champions_info = []
        masteries_info = []
        points_info = []
        
        for i, mastery in enumerate(top_masteries[:3], 1):  # Top 3 seulement
            champions_info.append(f"#{i} - {mastery['championName']}")
            masteries_info.append(f"Niveau {mastery['championLevel']}")
            points_info.append(f"{mastery['championPoints']:,} pts")
        
        if champions_info:
            embed.add_field(
                name="🏅 Top Champions",
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
    
    return embed

def create_lol_ranked_embed(summoner: Summoner, ranked_info: dict) -> discord.Embed:
    """Créer l'embed des rangs League of Legends"""
    embed = discord.Embed(
        title=f"🎮 Rangs League of Legends - {summoner.name}",
        color=discord.Color.gold(),
        timestamp=datetime.now()
    )
    
    print(f"DEBUG: Rangs LoL disponibles: {list(ranked_info.keys()) if ranked_info else 'Aucun'}")
    
    if not ranked_info:
        embed.add_field(
            name="📋 Statut",
            value="Aucun rang classé cette saison",
            inline=False
        )
        return embed
    
    # Informations de rang League of Legends
    if "RANKED_SOLO_5x5" in ranked_info:
        solo_rank = ranked_info["RANKED_SOLO_5x5"]
        embed.add_field(
            name="🎯 Solo/Duo",
            value=f"{solo_rank.tier} {solo_rank.rank} ({solo_rank.league_points} LP)\n"
                  f"{solo_rank.wins}W/{solo_rank.losses}L ({solo_rank.winrate:.1f}% WR)",
            inline=True
        )
    
    if "RANKED_FLEX_SR" in ranked_info:
        flex_rank = ranked_info["RANKED_FLEX_SR"]
        embed.add_field(
            name="⚡ Flex 5v5",
            value=f"{flex_rank.tier} {flex_rank.rank} ({flex_rank.league_points} LP)\n"
                  f"{flex_rank.wins}W/{flex_rank.losses}L ({flex_rank.winrate:.1f}% WR)",
            inline=True
        )
    
    if "CHERRY" in ranked_info:
        arena_rank = ranked_info["CHERRY"]
        embed.add_field(
            name="🏟️ Arena",
            value=f"{arena_rank.tier} {arena_rank.rank} ({arena_rank.league_points} LP)\n"
                  f"{arena_rank.wins}W/{arena_rank.losses}L ({arena_rank.winrate:.1f}% WR)",
            inline=True
        )
    
    return embed

def create_tft_ranked_embed(summoner: Summoner, tft_ranked_info: Optional[Dict[str, RankedInfo]] = None) -> discord.Embed:
    """Créer l'embed des rangs TFT"""
    embed = discord.Embed(
        title=f"♛ Rangs Teamfight Tactics - {summoner.name}",
        color=discord.Color.purple(),
        timestamp=datetime.now()
    )
    
    print(f"DEBUG: Rangs TFT disponibles: {list(tft_ranked_info.keys()) if tft_ranked_info else 'Aucun'}")
    
    if not tft_ranked_info or len(tft_ranked_info) == 0:
        embed.add_field(
            name="📋 Statut",
            value="Aucun rang TFT cette saison",
            inline=False
        )
        return embed
    
    # Informations de rang TFT
    for queue_type, tft_rank in tft_ranked_info.items():
        total_games = tft_rank.wins + tft_rank.losses
        winrate = (tft_rank.wins / total_games * 100) if total_games > 0 else 0
        
        if queue_type == 'RANKED_TFT':
            embed.add_field(
                name="♛ TFT Classé",
                value=f"{tft_rank.tier} {tft_rank.rank} ({tft_rank.league_points} LP)\n"
                      f"{tft_rank.wins}W/{tft_rank.losses}L ({winrate:.1f}% WR)",
                inline=True
            )
        elif queue_type == 'RANKED_TFT_DOUBLE_UP':
            embed.add_field(
                name="👥 TFT Double Up",
                value=f"{tft_rank.tier} {tft_rank.rank} ({tft_rank.league_points} LP)\n"
                      f"{tft_rank.wins}W/{tft_rank.losses}L ({winrate:.1f}% WR)",
                inline=True
            )
        elif queue_type == 'RANKED_TFT_TURBO':
            embed.add_field(
                name="⚡ TFT Hyper Roll",
                value=f"{tft_rank.tier} {tft_rank.rank} ({tft_rank.league_points} LP)\n"
                      f"{tft_rank.wins}W/{tft_rank.losses}L ({winrate:.1f}% WR)",
                inline=True
            )
        elif queue_type == 'RANKED_TFT_TURBO':
            embed.add_field(
                name="⚡ TFT Hyper Roll",
                value=f"{tft_rank.tier} {tft_rank.rank} ({tft_rank.league_points} LP)\n"
                      f"{tft_rank.wins}W/{tft_rank.losses}L ({winrate:.1f}% WR)",
                inline=True
            )
    
    return embed

async def create_game_result_embed(game_result: GameResult, target_puuid: str) -> Tuple[discord.Embed, Optional[discord.File]]:
    """Créer un embed enrichi pour afficher le résultat d'une partie LoL avec image des items"""
    # Trouver le joueur cible
    target_participant = None
    for participant in game_result.participants:
        if participant.puuid == target_puuid:
            target_participant = participant
            break
    
    if not target_participant:
        error_embed = discord.Embed(title="Erreur", description="Joueur non trouvé dans cette partie")
        return error_embed, None
    
    # Couleur selon victoire/défaite
    color = discord.Color.green() if target_participant.win else discord.Color.red()
    result_text = "🎉 Victoire" if target_participant.win else "💔 Défaite"
    
    # Formatage de la durée
    duration_minutes = game_result.match_info.game_duration // 60
    duration_seconds = game_result.match_info.game_duration % 60
    
    # Mode de jeu formaté
    game_mode = game_result.match_info.game_mode
    queue_info = "Classé" if game_result.is_ranked else game_mode
    
    embed = discord.Embed(
        title=f"{target_participant.riot_id_game_name} - {result_text}",
        description=f"**{target_participant.champion_name}** • {queue_info} • {duration_minutes}:{duration_seconds:02d}",
        color=color,
        timestamp=game_result.match_info.game_creation
    )
    
    # Performance principale
    kda_ratio = target_participant.kda_ratio if target_participant.kda_ratio != float('inf') else target_participant.kills + target_participant.assists
    embed.add_field(
        name="🎯 Performance",
        value=f"**{target_participant.kills}/{target_participant.deaths}/{target_participant.assists}**\n"
              f"KDA: **{kda_ratio:.2f}**\n"
              f"Level: **{target_participant.champ_level}**",
        inline=True
    )
    
    # Farm et économie
    cs_total = target_participant.total_minions_killed + target_participant.neutral_minions_killed
    cs_per_min = round((cs_total / (game_result.match_info.game_duration / 60)), 1) if game_result.match_info.game_duration > 0 else 0
    embed.add_field(
        name="💰 Farm & Gold",
        value=f"CS: **{cs_total}** ({cs_per_min}/min)\n"
              f"Gold: **{target_participant.gold_earned:,}**\n"
              f"Vision: **{target_participant.vision_score}**",
        inline=True
    )
    
    # Dégâts
    embed.add_field(
        name="⚔️ Dégâts",
        value=f"Total: **{target_participant.total_damage_dealt_to_champions:,}**\n"
              f"Magiques: **{target_participant.magic_damage_dealt_to_champions:,}**\n"
              f"Pris: **{target_participant.total_damage_taken:,}**",
        inline=True
    )
    
    # Objectifs et structures
    objectives_text = []
    if target_participant.dragon_kills > 0:
        objectives_text.append(f"🐲 Dragons: {target_participant.dragon_kills}")
    if target_participant.baron_kills > 0:
        objectives_text.append(f"👑 Baron: {target_participant.baron_kills}")
    if target_participant.turret_kills > 0:
        objectives_text.append(f":tokyo_tower: Tours: {target_participant.turret_kills}")
    if target_participant.inhibitor_kills > 0:
        objectives_text.append(f"🛡️ Inhibs: {target_participant.inhibitor_kills}")
    
    if objectives_text:
        embed.add_field(
            name="🎯 Objectifs",
            value="\n".join(objectives_text),
            inline=True
        )
    
    # Multikills et faits marquants
    multikills_text = []
    if target_participant.penta_kills > 0:
        multikills_text.append(f"🔥 **Penta Kill** x{target_participant.penta_kills}")
    elif target_participant.quadra_kills > 0:
        multikills_text.append(f"💥 **Quadra Kill** x{target_participant.quadra_kills}")
    elif target_participant.triple_kills > 0:
        multikills_text.append(f"⚡ **Triple Kill** x{target_participant.triple_kills}")
    elif target_participant.double_kills > 0:
        multikills_text.append(f"✨ **Double Kill** x{target_participant.double_kills}")
    
    if target_participant.first_blood_kill:
        multikills_text.append("🩸 **First Blood**")
    if target_participant.largest_killing_spree > 3:
        multikills_text.append(f"🔥 **Killing Spree**: {target_participant.largest_killing_spree}")
    
    if multikills_text:
        embed.add_field(
            name="🏆 Faits marquants",
            value="\n".join(multikills_text),
            inline=True
        )
    
    # Items avec image composite (comme dans votre ancienne version)
    item_ids = _format_items_display(target_participant)
    items_file = None
    
    if item_ids:
        # Créer l'image composite des items
        item_generator = ItemImageGenerator()
        items_image_bytes = await item_generator.create_items_image(item_ids)
        
        if items_image_bytes:
            # Créer un fichier Discord avec l'image
            items_file = discord.File(items_image_bytes, filename="items.png")
            # Utiliser l'attachment dans l'embed
            embed.set_image(url="attachment://items.png")
        else:
            # Fallback vers l'affichage textuel si l'image échoue
            item_urls = [f"https://ddragon.leagueoflegends.com/cdn/14.24.1/img/item/{item_id}.png" for item_id in item_ids]
            items_text = " ".join([f"[🎒]({url})" for url in item_urls])
            embed.add_field(
                name="🎒 Items",
                value=items_text,
                inline=False
            )

    # Footer avec informations supplémentaires
    embed.set_footer(
        text=f"Match ID: {game_result.match_info.match_id} • Queue: {game_result.match_info.queue_id}"
    )
    
    # Image du champion en thumbnail
    champion_icon_url = f"https://cdn.communitydragon.org/latest/champion/{target_participant.champion_id}/tile"
    embed.set_thumbnail(url=champion_icon_url)
    
    return embed, items_file

def create_tft_result_embed(tft_result: TFTGameResult, target_puuid: str, summoner_info: Optional[Dict[str, str]] = None) -> discord.Embed:
    """Créer un embed pour afficher le résultat d'une partie TFT avec mode de jeu et pseudo"""
    # Trouver le joueur cible
    target_participant = None
    for participant in tft_result.participants:
        if participant.puuid == target_puuid:
            target_participant = participant
            break
    
    if not target_participant:
        return discord.Embed(title="Erreur", description="Joueur non trouvé dans cette partie TFT")
    
    # Couleur selon le placement
    if target_participant.placement <= 4:
        color = discord.Color.green()
    elif target_participant.placement <= 6:
        color = discord.Color.orange()
    else:
        color = discord.Color.red()
    
    # Emoji selon le placement
    placement_emoji = _get_placement_emoji(target_participant.placement)
    
    # Nom du joueur - utiliser les infos surveillées si disponibles
    player_name = target_participant.summoner_name
    if summoner_info:
        summoner_name = summoner_info.get('summoner_name', target_participant.summoner_name)
        tag_line = summoner_info.get('tag_line', '')
        if tag_line:
            player_name = f"{summoner_name}#{tag_line}"
        else:
            player_name = summoner_name
    
    # Mode de jeu
    game_mode = _get_tft_queue_name(tft_result.queue_id)
    
    # Titre avec pseudo, mode et placement
    title = f"🎯 TFT {game_mode} - {placement_emoji} {target_participant.placement}e place"
    
    embed = discord.Embed(
        title=title,
        description=f"**{player_name}** a terminé {target_participant.placement}e sur 8 joueurs",
        color=color,
        timestamp=tft_result.match_info.game_creation
    )
    
    # Informations principales
    embed.add_field(
        name="🔼 Niveau",
        value=f"{target_participant.level}",
        inline=True
    )
    
    embed.add_field(
        name="🎯 Dernier round",
        value=f"Round {target_participant.last_round}",
        inline=True
    )
    
    embed.add_field(
        name="⚔️ Dégâts totaux",
        value=f"{target_participant.total_damage_to_players:,}",
        inline=True
    )
    
    # Joueurs éliminés
    if hasattr(target_participant, 'players_eliminated') and target_participant.players_eliminated > 0:
        embed.add_field(
            name="💀 Éliminations",
            value=f"{target_participant.players_eliminated} joueur(s)",
            inline=True
        )
    
    # Petite légende si disponible
    companion_info = _get_companion_info(target_participant.companion)
    if companion_info:
        embed.add_field(
            name="🐣 Petite légende",
            value=companion_info,
            inline=True
        )
    
    # Set TFT si disponible
    if hasattr(tft_result, 'set_number') and tft_result.set_number:
        embed.add_field(
            name="📦 Set TFT",
            value=f"Set {tft_result.set_number}",
            inline=True
        )
    
    # Augments (limité à 3 principaux)
    if target_participant.augments:
        augments_text = "\n".join([f"• {augment}" for augment in target_participant.augments[:3]])
        embed.add_field(
            name="⚡ Augments",
            value=augments_text or "Aucun",
            inline=False
        )
    
    # Traits principaux (limité à 4-5 plus importants)
    if target_participant.traits:
        active_traits = [trait for trait in target_participant.traits if trait.get('tier_current', 0) > 0]
        active_traits.sort(key=lambda x: x.get('tier_current', 0), reverse=True)
        
        if active_traits:
            traits_text = ""
            for trait in active_traits[:5]:  # Max 5 traits
                name = trait.get('name', 'Inconnu')
                tier = trait.get('tier_current', 0)
                units = trait.get('num_units', 0)
                
                # Emojis selon le tier
                tier_emoji = {1: "🔹", 2: "🔸", 3: "⭐", 4: "🌟", 5: "✨"}.get(tier, "•")
                traits_text += f"{tier_emoji} {name} ({units})\n"
            
            embed.add_field(
                name="🎨 Traits actifs",
                value=traits_text.strip() or "Aucun trait actif",
                inline=False
            )
    
    # Durée de la partie
    if hasattr(tft_result.match_info, 'game_duration'):
        duration_minutes = tft_result.match_info.game_duration // 60
        duration_seconds = tft_result.match_info.game_duration % 60
        embed.add_field(
            name="⏱️ Durée",
            value=f"{duration_minutes}m {duration_seconds}s",
            inline=True
        )
    
    # Footer avec informations additionnelles
    embed.set_footer(text=f"Match ID: {tft_result.match_info.match_id}")
    
    return embed

def create_error_embed(title: str, description: str) -> discord.Embed:
    """Créer un embed d'erreur"""
    return discord.Embed(
        title=f"❌ {title}",
        description=description,
        color=discord.Color.red()
    )

def create_daily_recap_embed(day_recap) -> discord.Embed:
    """Créer un embed pour le récapitulatif quotidien"""
    from ..models.daily_stats_models import DayRecap
    
    recap: DayRecap = day_recap
    
    embed = discord.Embed(
        title="📊 Récapitulatif Quotidien",
        description=f"**{recap.date.strftime('%d/%m/%Y')}** - Statistiques des joueurs surveillés",
        color=discord.Color.gold(),
        timestamp=datetime.now()
    )
    
    # Statistiques globales
    total_hours = recap.total_guild_playtime // 3600
    total_minutes = (recap.total_guild_playtime % 3600) // 60
    
    embed.add_field(
        name="🎮 Activité Globale",
        value=f"**{recap.total_guild_games}** parties jouées\n"
              f"**{total_hours}h{total_minutes:02d}** de jeu total\n"
              f"**{len(recap.players_stats)}** joueurs actifs",
        inline=True
    )
    
    # Joueur le plus actif
    most_active = recap.most_active_player
    if most_active:
        embed.add_field(
            name="🔥 Joueur le plus actif",
            value=f"**{most_active.summoner_name}**\n"
                  f"{most_active.total_games} parties\n"
                  f"{most_active.win_rate:.1f}% de victoires",
            inline=True
        )
    
    # Meilleur taux de victoire
    best_wr = recap.best_win_rate_player
    if best_wr:
        embed.add_field(
            name="🏆 Meilleur taux de victoire",
            value=f"**{best_wr.summoner_name}**\n"
                  f"{best_wr.total_games} parties\n"
                  f"**{best_wr.win_rate:.1f}%** de victoires",
            inline=True
        )
    
    # Détails par joueur (top 5 par activité)
    top_players = sorted(recap.players_stats, key=lambda p: p.total_games, reverse=True)[:5]
    
    if top_players:
        players_text = []
        for i, player in enumerate(top_players, 1):
            # Modes principaux
            modes = []
            if player.ranked_solo_games > 0:
                wr = (player.ranked_solo_wins / player.ranked_solo_games * 100) if player.ranked_solo_games > 0 else 0
                modes.append(f"Solo: {player.ranked_solo_games}G ({wr:.0f}%)")
            if player.ranked_flex_games > 0:
                wr = (player.ranked_flex_wins / player.ranked_flex_games * 100) if player.ranked_flex_games > 0 else 0
                modes.append(f"Flex: {player.ranked_flex_games}G ({wr:.0f}%)")
            if player.aram_games > 0:
                wr = (player.aram_wins / player.aram_games * 100) if player.aram_games > 0 else 0
                modes.append(f"ARAM: {player.aram_games}G ({wr:.0f}%)")
            if player.tft_ranked_games > 0:
                wr = (player.tft_ranked_wins / player.tft_ranked_games * 100) if player.tft_ranked_games > 0 else 0
                modes.append(f"TFT: {player.tft_ranked_games}G ({wr:.0f}%)")
            
            modes_text = " • ".join(modes) if modes else "Autres modes"
            
            players_text.append(
                f"**{i}. {player.summoner_name}**\n"
                f"Total: {player.total_games}G ({player.win_rate:.1f}%)\n"
                f"{modes_text}\n"
            )
        
        embed.add_field(
            name="📈 Top Joueurs",
            value="\n".join(players_text),
            inline=False
        )
    
    embed.set_footer(text="Récapitulatif automatique • Arena Gaming Bot")
    
    return embed
