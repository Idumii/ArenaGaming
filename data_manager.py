import json

# Classe Singleton pour gérer les données
class DataManager:
    _instance = None

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super().__new__(cls, *args, **kwargs)
        return cls._instance

    def __init__(self, summoners_file_path='summoners_to_watch.json'):
        if not hasattr(self, "initialized"):  # Pour éviter initialisation multiple
            self.summoners_file_path = summoners_file_path
            self.summoners = []
            self.notified_summoners = []
            self.champion_name_dict = self.load_champion_data()
            self.load_summoners_to_watch()
            self.initialized = True
            self.notified_games = self.load_notified_games()


    def load_summoners_to_watch(self):
        try:
            with open(self.summoners_file_path, 'r', encoding='utf-8') as f:
                self.summoners = json.load(f)
            print(f"Summoners to watch loaded successfully. Current list: {self.summoners}")
        except FileNotFoundError:
            print("Summoners to watch file not found. Starting with an empty list.")
            self.summoners = []
        except json.JSONDecodeError as e:
            print(f"Failed to load summoners to watch (JSON Decode Error): {e}")
            self.summoners = []
        except Exception as e:
            print(f"Failed to load summoners to watch: {e}")
            self.summoners = []
        return self.summoners

    def save_summoners_to_watch(self, summoners):
        try:
            with open(self.summoners_file_path, 'w', encoding='utf-8') as f:
                json.dump(summoners, f, ensure_ascii=False, indent=4)
            print("Summoners to watch saved successfully.")
        except Exception as e:
            print(f"Failed to save summoners to watch: {e}")

    def print_summoners_to_watch(self, prefix=''):
        print(f"{prefix} Summoners to watch: {self.summoners}")

    def load_champion_data(self):
        try:
            with open('champion.json', 'r', encoding='utf-8') as f:
                champion_data = json.load(f)
            return {int(info['key']): info['name'] for info in champion_data['data'].values()}
        except Exception as e:
            print(f"Failed to load champion data: {e}")
            return {}

    def get_champion_name(self, champion_id):
        return self.champion_name_dict.get(champion_id, "Unknown Champion")
    
    def add_notified_summoner(self, puuid, game_id):
        # Ajouter une vérification pour éviter les doublons
        if not any(entry['puuid'] == puuid and entry['game_id'] == game_id for entry in self.notified_summoners):
            self.notified_summoners.append({"puuid": puuid, "game_id": game_id})
        print(f"Added {puuid} to notified_summoners with gameId: {game_id}")
        print(self.notified_summoners)
        return self  # Retourne l'instance pour faciliter le chaînage

    def remove_notified_summoner(self, puuid):
        # Supprimer toutes les entrées avec ce puuid
        self.notified_summoners = [entry for entry in self.notified_summoners if entry['puuid'] != puuid]
        print(f"Removed {puuid} from notified_summoners")

    def remove_specific_notified_summoner(self, puuid, game_id):
        # Supprimer l'entrée spécifique avec ce puuid et game_id
        self.notified_summoners = [entry for entry in self.notified_summoners if not (entry['puuid'] == puuid and entry['game_id'] == game_id)]
        print(f"Removed {puuid} with gameId {game_id} from notified_summoners")

    def get_notified_summoners(self):
        return self.notified_summoners
    
    def load_notified_games(self):
        try:
            with open('notified_games.json', 'r') as file:
                return json.load(file)
        except FileNotFoundError:
            return []

    def save_notified_games(self):
        with open('notified_games.json', 'w') as file:
            json.dump(self.notified_games, file)

    def add_notified_game(self, game_id):
        if game_id not in self.notified_games:
            self.notified_games.append(game_id)
            self.save_notified_games()