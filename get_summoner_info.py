#!/usr/bin/env python3
"""
Récupérer les infos d'un PUUID pour l'ajouter à la surveillance
"""
import asyncio
import json
from dotenv import load_dotenv
from src.api.summoner_api import SummonerAPI

load_dotenv()

async def get_summoner_info():
    # Ton PUUID
    test_puuid = "Wo21ORrlPkwiB59yodCZt3ToORVpOKqQtstKftdxF7GO0SkvB2AIGQH-_Mu13zpt5kHKAwmmeHAAyQ"
    
    summoner_api = SummonerAPI()
    
    try:
        # Récupérer les infos du compte via PUUID
        summoner_info = await summoner_api.get_summoner_by_puuid(test_puuid)
        
        if summoner_info:
            print(f"✅ Informations trouvées:")
            print(f"Nom: {summoner_info.name}")
            print(f"Tag: {summoner_info.tag_line}")
            print(f"Level: {summoner_info.summoner_level}")
            print(f"PUUID: {summoner_info.puuid}")
            
            # Créer l'entrée de surveillance
            watch_entry = {
                "puuid": test_puuid,
                "summoner_name": summoner_info.name,
                "tag_line": summoner_info.tag_line,
                "discord_user_id": 177510632000716800,  # Même ID que les autres
                "watch_lol": True,
                "watch_tft": True,
                "notify_game_start": True,
                "notify_game_end": True,
                "guild_id": 1220706693294325790
            }
            
            print(f"\n🎯 Entrée de surveillance à ajouter:")
            print(json.dumps(watch_entry, indent=2))
                
        else:
            print("❌ Aucune information trouvée")
            
    except Exception as e:
        print(f"❌ Erreur: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(get_summoner_info())
