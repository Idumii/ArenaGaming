"""
Script pour corriger les appels API - remplacer headers par params
"""
import os
import re

def fix_api_calls():
    """Corriger tous les appels API pour utiliser params au lieu de headers"""
    api_files = [
        "src/api/match_api.py",
        "src/api/tft_api.py"
    ]
    
    for file_path in api_files:
        if not os.path.exists(file_path):
            continue
            
        print(f"🔧 Correction de {file_path}...")
        
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Remplacer headers={"X-Riot-Token": ...} par params={"api_key": ...}
        content = re.sub(
            r'headers=\{"X-Riot-Token": self\.settings\.riot_api_key\}',
            'params={"api_key": self.settings.riot_api_key}',
            content
        )
        
        # Gérer les cas avec params existants
        content = re.sub(
            r'headers=\{"X-Riot-Token": self\.settings\.riot_api_key\},\s*params=params',
            'params={**params, "api_key": self.settings.riot_api_key}',
            content
        )
        
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        print(f"✅ {file_path} corrigé")

if __name__ == "__main__":
    fix_api_calls()
    print("🎉 Tous les fichiers API ont été corrigés !")
