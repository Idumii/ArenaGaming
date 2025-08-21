#!/usr/bin/env python3
"""
Test direct API Account pour récupérer le nom
"""
import asyncio
import aiohttp
from dotenv import load_dotenv
import os

load_dotenv()

async def get_account_info():
    puuid = "Wo21ORrlPkwiB59yodCZt3ToORVpOKqQtstKftdxF7GO0SkvB2AIGQH-_Mu13zpt5kHKAwmmeHAAyQ"
    api_key = os.getenv("API_RIOT_KEY")
    
    url = f"https://europe.api.riotgames.com/riot/account/v1/accounts/by-puuid/{puuid}?api_key={api_key}"
    
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            print(f"Status: {response.status}")
            if response.status == 200:
                data = await response.json()
                print(f"Nom: {data.get('gameName', 'Unknown')}")
                print(f"Tag: {data.get('tagLine', 'Unknown')}")
                print(f"PUUID: {data.get('puuid', 'Unknown')}")
                return data
            else:
                text = await response.text()
                print(f"Erreur: {text}")

if __name__ == "__main__":
    asyncio.run(get_account_info())
