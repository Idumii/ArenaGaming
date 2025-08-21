#!/usr/bin/env python3
"""
Récupérer les PUUID LoL et TFT pour un compte
"""
import asyncio
import json
from dotenv import load_dotenv
from src.api.summoner_api import SummonerAPI

load_dotenv()

async def get_both_puuids():
    game_name = "FroFrotte"
    tag_line = "IMLVP"
    
    summoner_api = SummonerAPI()
    
    try:
        print(f"🔍 Recherche de {game_name}#{tag_line}...")
        
        # Récupérer les infos LoL
        lol_summoner = await summoner_api.get_summoner_by_riot_id(game_name, tag_line)
        
        if lol_summoner:
            print(f"✅ Compte LoL trouvé:")
            print(f"   Nom: {lol_summoner.name}")
            print(f"   Tag: {lol_summoner.tag_line}")
            print(f"   Level: {lol_summoner.summoner_level}")
            print(f"   PUUID LoL: {lol_summoner.puuid}")
            
            # Récupérer les infos TFT
            tft_summoner = await summoner_api.get_summoner_by_riot_id_tft(game_name, tag_line)
            
            if tft_summoner:
                print(f"✅ Compte TFT trouvé:")
                print(f"   PUUID TFT: {tft_summoner.puuid}")
                
                # Créer l'entrée de surveillance avec les 2 PUUID
                watch_entry = {
                    "puuid_lol": lol_summoner.puuid,
                    "puuid_tft": tft_summoner.puuid,
                    "summoner_name": lol_summoner.name,
                    "tag_line": lol_summoner.tag_line,
                    "discord_user_id": 177510632000716800,
                    "watch_lol": True,
                    "watch_tft": True,
                    "notify_game_start": True,
                    "notify_game_end": True,
                    "guild_id": 1220706693294325790
                }
                
                print(f"\n🎯 Entrée de surveillance avec double PUUID:")
                print(json.dumps(watch_entry, indent=2))
                
                # Comparaison avec le PUUID que tu avais donné
                your_puuid = "Wo21ORrlPkwiB59yodCZt3ToORVpOKqQtstKftdxF7GO0SkvB2AIGQH-_Mu13zpt5kHKAwmmeHAAyQ"
                print(f"\n🔍 Comparaison avec ton PUUID:")
                print(f"   Ton PUUID: {your_puuid}")
                print(f"   PUUID LoL: {lol_summoner.puuid}")
                print(f"   PUUID TFT: {tft_summoner.puuid}")
                print(f"   Match LoL: {your_puuid == lol_summoner.puuid}")
                print(f"   Match TFT: {your_puuid == tft_summoner.puuid}")
                
            else:
                print("❌ Compte TFT non trouvé")
        else:
            print("❌ Compte LoL non trouvé")
            
    except Exception as e:
        print(f"❌ Erreur: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(get_both_puuids())
