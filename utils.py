from data_manager import DataManager

# Initialiser DataManager
data_manager = DataManager()

# Fonction pour générer un identifiant simple
def generate_simple_id():
    if data_manager.summoners:
        return max([s['id'] for s in data_manager.summoners], default=0) + 1
    else:
        return 1

# Ajoutez d'autres fonctions utilitaires ici
def clearGamename(gamenameWithspaces):
    return gamenameWithspaces.replace(" ", "")