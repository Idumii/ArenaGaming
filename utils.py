import data_manager
from data_manager import summoners_to_watch


# Fonction pour générer un identifiant simple
def generate_simple_id():
    return max([s['id'] for s in summoners_to_watch], default=0) + 1

# Ajoutez d'autres fonctions utilitaires ici
def clearGamename(gamenameWithspaces):
    result = ""
    for n in gamenameWithspaces:
        result = result + " " + str(n)
    return result