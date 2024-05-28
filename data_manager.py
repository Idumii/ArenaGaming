import json

    

# Liste des invocateurs à surveiller
summoners_to_watch = []

# Dictionnaire des invocateurs notifiés avec l'ID de leur partie en cours
notified_summoners = {}

# Dictionnaire des jeux notifiés (si nécessaire pour votre logique d'application)
notified_games = {}


# Charger les invocateurs à surveiller depuis un fichier
def load_summoners_to_watch():
    global summoners_to_watch
    try:
        with open('summoners_to_watch.json', 'r', encoding='utf-8') as f:
            summoners_to_watch = json.load(f)
        print("Summoners to watch loaded successfully.")
    except Exception as e:
        print(f"Failed to load summoners to watch: {e}")

def load_champion():
    with open('champion.json', 'r', encoding='utf-8') as f:
        champion_data = json.load(f)
     
    # Créer un dictionnaire pour accéder rapidement aux informations des champions par leur ID
    champion_name_dict = {int(info['key']): info['name'] for info in champion_data['data'].values()}  
    
    return champion_name_dict        
    

def save_summoners_to_watch(summoners_to_watch):
    # Logique pour sauvegarder les invocateurs à surveiller
    pass

class DataManager:
    def __init__(self):
        self.champion_name_dict = self.load_champion_data()

    def load_champion_data(self):
        with open('champion.json', 'r', encoding='utf-8') as f:
            champion_data = json.load(f)
        return {int(info['key']): info['name'] for info in champion_data['data'].values()}

    def get_champion_name(self, champion_id):
        return self.champion_name_dict.get(champion_id, "Unknown Champion")

# Ajoutez d'autres fonctions de gestion des données ici