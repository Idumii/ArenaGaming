"""
Configuration du bot
"""
import os
from typing import Optional
from dataclasses import dataclass
from dotenv import load_dotenv

# Charger les variables d'environnement
load_dotenv()

@dataclass
class Settings:
    """Configuration principale du bot"""
    discord_token: str
    riot_api_key: str
    riot_tft_api_key: str
    default_region: str = "europe"
    default_platform: str = "euw1"
    max_requests_per_minute: int = 100
    debug_mode: bool = False
    
    def __post_init__(self):
        if not self.discord_token:
            raise ValueError("TOKEN_DISCORD doit être défini dans le fichier .env")
        if not self.riot_api_key:
            raise ValueError("API_RIOT_KEY doit être défini dans le fichier .env")
        if not self.riot_tft_api_key:
            raise ValueError("API_RIOT_TFT_KEY doit être défini dans le fichier .env")

_settings: Optional[Settings] = None

def get_settings() -> Settings:
    """Récupérer la configuration singleton"""
    global _settings
    if _settings is None:
        _settings = Settings(
            discord_token=os.getenv('TOKEN_DISCORD', ''),
            riot_api_key=os.getenv('API_RIOT_KEY', ''),
            riot_tft_api_key=os.getenv('API_RIOT_TFT_KEY', ''),
            default_region=os.getenv('DEFAULT_REGION', 'europe'),
            default_platform=os.getenv('DEFAULT_PLATFORM', 'euw1'),
            max_requests_per_minute=int(os.getenv('MAX_REQUESTS_PER_MINUTE', '100')),
            debug_mode=os.getenv('DEBUG_MODE', 'false').lower() == 'true'
        )
    return _settings
