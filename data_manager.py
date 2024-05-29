import json

# Déclarations globales
summoners_to_watch = []
notified_summoners = {}
notified_games = {}

# Chargement des invocateurs à surveiller depuis un fichier JSON
def load_summoners_to_watch(file_path='summoners_to_watch.json'):
    global summoners_to_watch
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            summoners_to_watch = json.load(f)
        print(f"Summoners to watch loaded successfully. Current list: {summoners_to_watch}")
    except FileNotFoundError:
        print("Summoners to watch file not found. Starting with an empty list.")
    except json.JSONDecodeError as e:
        print(f"Failed to load summoners to watch (JSON Decode Error): {e}")
    except Exception as e:
        print(f"Failed to load summoners to watch: {e}")

# Sauvegarde des invocateurs suivis dans un fichier JSON
def save_summoners_to_watch(file_path='summoners_to_watch.json'):
    global summoners_to_watch
    try:
        print(f"About to save to file {file_path}. Data: {summoners_to_watch}")
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(summoners_to_watch, f, ensure_ascii=False, indent=4)
        print(f"Summoners to watch saved successfully.")
        # Relire le fichier pour vérifier la sauvegarde
        with open(file_path, 'r', encoding='utf-8') as f:
            saved_data = json.load(f)
        print(f"Verified saved data: {saved_data}")
    except Exception as e:
        print(f"Failed to save summoners to watch: {e}")

# Affichage de la liste des invocateurs suivis pour le débogage
def print_summoners_to_watch(prefix=''):
    print(f"{prefix} Summoners to watch: {summoners_to_watch}")

def load_champion():
    with open('champion.json', 'r', encoding='utf-8') as f:
        champion_data = json.load(f)
     
    # Créer un dictionnaire pour accéder rapidement aux informations des champions par leur ID
    champion_name_dict = {int(info['key']): info['name'] for info in champion_data['data'].values()}  
    
    return champion_name_dict        

class DataManager:
    def __init__(self, summoners_file_path='summoners_to_watch.json'):
        self.summoners_file_path = summoners_file_path
        self.summoners = self.load_summoners_to_watch()
        self.champion_name_dict = self.load_champion_data()

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
            print(f"About to save to file {self.summoners_file_path}. Data: {summoners}")
            with open(self.summoners_file_path, 'w', encoding='utf-8') as f:
                json.dump(summoners, f, ensure_ascii=False, indent=4)
            print(f"Summoners to watch saved successfully.")
            # Relire le fichier pour vérifier la sauvegarde
            with open(self.summoners_file_path, 'r', encoding='utf-8') as f:
                saved_data = json.load(f)
            print(f"Verified saved data: {saved_data}")
        except Exception as e:
            print(f"Failed to save summoners to watch: {e}")

    def load_champion_data(self):
        with open('champion.json', 'r', encoding='utf-8') as f:
            champion_data = json.load(f)
        return {int(info['key']): info['name'] for info in champion_data['data'].values()}

    def get_champion_name(self, champion_id):
        return self.champion_name_dict.get(champion_id, "Unknown Champion")