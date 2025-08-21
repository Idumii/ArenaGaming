#!/usr/bin/env python3
"""
Mettre à jour tous les PUUID TFT pour la surveillance
"""
import asyncio
import json
from dotenv import load_dotenv
from src.api.summoner_api import SummonerAPI
from src.utils.data_persistence import DataPersistence

load_dotenv()

async def update_all_puuids():
    # Charger les surveillances actuelles
    data_persistence = DataPersistence()
    guild_id = 1220706693294325790
    summoners = data_persistence.load_watched_summoners(guild_id)
    
    print(f"📂 {len(summoners)} invocateurs trouvés")
    
    summoner_api = SummonerAPI()
    updated_data = []
    
    for summoner in summoners:
        print(f"\n🔍 Traitement de {summoner.summoner_name}#{summoner.tag_line}")
        
        try:
            # Récupérer les infos LoL et TFT
            lol_summoner = await summoner_api.get_summoner_by_riot_id(summoner.summoner_name, summoner.tag_line)
            tft_summoner = await summoner_api.get_summoner_by_riot_id_tft(summoner.summoner_name, summoner.tag_line)
            
            # Créer l'entrée mise à jour
            entry = {
                "summoner_name": summoner.summoner_name,
                "tag_line": summoner.tag_line,
                "discord_user_id": summoner.discord_user_id,
                "guild_id": summoner.guild_id,
                "watch_lol": getattr(summoner, 'watch_lol', True),
                "watch_tft": getattr(summoner, 'watch_tft', True),
                "notify_game_start": getattr(summoner, 'notify_game_start', True),
                "notify_game_end": getattr(summoner, 'notify_game_end', True)
            }
            
            # Ajouter les PUUID
            if lol_summoner:
                entry["puuid"] = lol_summoner.puuid  # Compatibilité
                entry["puuid_lol"] = lol_summoner.puuid
                print(f"   ✅ PUUID LoL: {lol_summoner.puuid[:20]}...")
            else:
                # Utiliser l'ancien PUUID comme fallback pour LoL
                entry["puuid"] = getattr(summoner, 'puuid', '')
                entry["puuid_lol"] = getattr(summoner, 'puuid', '')
                print(f"   ⚠️ PUUID LoL non trouvé, utilisation ancien: {entry['puuid'][:20] if entry['puuid'] else 'Vide'}...")
            
            if tft_summoner:
                entry["puuid_tft"] = tft_summoner.puuid
                print(f"   ✅ PUUID TFT: {tft_summoner.puuid[:20]}...")
            else:
                entry["puuid_tft"] = ""
                print(f"   ❌ PUUID TFT non trouvé")
            
            updated_data.append(entry)
            
            # Petite pause pour éviter le rate limiting
            await asyncio.sleep(0.5)
            
        except Exception as e:
            print(f"   ❌ Erreur pour {summoner.summoner_name}: {e}")
            # Garder les données existantes en cas d'erreur
            entry = {
                "puuid": getattr(summoner, 'puuid', ''),
                "puuid_lol": getattr(summoner, 'puuid_lol', getattr(summoner, 'puuid', '')),
                "puuid_tft": getattr(summoner, 'puuid_tft', ''),
                "summoner_name": summoner.summoner_name,
                "tag_line": summoner.tag_line,
                "discord_user_id": summoner.discord_user_id,
                "guild_id": summoner.guild_id,
                "watch_lol": getattr(summoner, 'watch_lol', True),
                "watch_tft": getattr(summoner, 'watch_tft', True),
                "notify_game_start": getattr(summoner, 'notify_game_start', True),
                "notify_game_end": getattr(summoner, 'notify_game_end', True)
            }
            updated_data.append(entry)
    
    # Sauvegarder les données mises à jour
    file_path = f"data/watch_data/guild_{guild_id}_watched.json"
    
    # Backup
    backup_path = f"{file_path}.backup"
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            original_data = f.read()
        with open(backup_path, 'w', encoding='utf-8') as f:
            f.write(original_data)
        print(f"\n💾 Backup créé: {backup_path}")
    except Exception as e:
        print(f"⚠️ Erreur backup: {e}")
    
    # Écrire les nouvelles données
    try:
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(updated_data, f, indent=2, ensure_ascii=False)
        print(f"✅ Fichier mis à jour: {file_path}")
        print(f"📊 {len(updated_data)} entrées sauvegardées")
        
        # Résumé
        print(f"\n📋 RÉSUMÉ:")
        for entry in updated_data:
            lol_status = "✅" if entry.get('puuid_lol') else "❌"
            tft_status = "✅" if entry.get('puuid_tft') else "❌"
            print(f"   {entry['summoner_name']}#{entry['tag_line']}: LoL {lol_status} TFT {tft_status}")
            
    except Exception as e:
        print(f"❌ Erreur sauvegarde: {e}")

if __name__ == "__main__":
    asyncio.run(update_all_puuids())
