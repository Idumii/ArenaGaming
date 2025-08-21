# Arena Gaming Bot

Bot Discord moderne pour League of Legends et Teamfight Tactics avec détection automatique des parties et suivi des performances.

## 🚀 Fonctionnalités

- 🎮 **Détection automatique des parties** - Surveillance en temps réel
- 📊 **Affichage des résultats** - Statistiques détaillées de fin de partie
- 👤 **Profils utilisateurs** - Rangs, statistiques et historique
- 🏆 **Système de LP** - Suivi des gains/pertes (en développement)
- ⚔️ **Support complet** - LoL et TFT
- 🎯 **Commandes slash** - Interface Discord moderne
- 📈 **Rate limiting intelligent** - Respect des limites API Riot

## 📁 Structure du projet

```
src/
├── commands/          # Commandes Discord slash
│   ├── profile_commands.py    # /profile, /me
│   ├── match_commands.py      # /lastgame, /ingame
│   └── admin_commands.py      # /watch, /unwatch, /watchlist
├── api/              # Endpoints API Riot Games
│   ├── summoner_api.py        # Gestion des invocateurs
│   ├── match_api.py          # Parties LoL
│   └── tft_api.py            # Parties TFT
├── services/         # Logique métier
│   └── game_detection.py     # Détection automatique
├── models/           # Modèles de données
│   ├── game_models.py        # Summoner, Match, TFT...
│   └── config_models.py      # Configuration, surveillance
├── utils/            # Utilitaires
│   ├── discord_embeds.py     # Création d'embeds
│   └── rate_limiter.py       # Limitation des requêtes
└── config/           # Configuration
    └── settings.py           # Paramètres centralisés

config/               # Configuration serveur
data/                 # Données statiques (champions, items, etc.)
```

## ⚡ Installation

### Prérequis
- Python 3.11+
- UV (gestionnaire de paquets Python)
- Token Discord Bot
- Clé API Riot Games

### Installation rapide

1. **Cloner le projet**
```bash
git clone <votre-repo>
cd NewArenaGaming
```

2. **Installer avec UV**
```bash
uv sync
```

3. **Configuration**
```bash
cp .env.example .env
# Éditer .env avec vos tokens
```

4. **Tester la structure**
```bash
uv run python test_structure.py
```

5. **Lancer le bot**
```bash
uv run python main.py
```

## 🔧 Configuration

Créer un fichier `.env` avec :
```env
# Configuration du bot Discord
TOKEN_DISCORD=votre_token_discord_ici

# Clé API Riot Games
API_RIOT_KEY=votre_clé_api_riot_ici

# Configuration optionnelle
DEFAULT_REGION=europe
DEFAULT_PLATFORM=euw1
MAX_REQUESTS_PER_MINUTE=100
DEBUG_MODE=false
```

## 🎮 Commandes disponibles

### Profils
- `/profile <nom> [tag]` - Afficher le profil d'un joueur
- `/me` - Afficher votre profil lié (à venir)

### Parties
- `/lastgame <nom> [tag] [type]` - Dernière partie (LoL/TFT)
- `/ingame <nom> [tag]` - Vérifier si en partie

### Administration
- `/watch <nom> [tag] [user]` - Surveiller un joueur
- `/unwatch <nom> [tag]` - Arrêter la surveillance
- `/watchlist` - Liste des joueurs surveillés

## 🔄 Améliorations apportées

### Architecture
- **Séparation des responsabilités** - Modules dédiés pour chaque fonction
- **API clients spécialisés** - LoL, TFT et Summoner séparés
- **Modèles de données structurés** - Types définis pour toutes les entités
- **Gestion centralisée de la configuration** - Paramètres unifiés

### Performances
- **Rate limiting intelligent** - Respect automatique des limites API
- **Requêtes asynchrones** - Performance optimisée
- **Cache en mémoire** - Réduction des appels API redondants

### Fonctionnalités
- **Détection automatique** - Surveillance continue des nouvelles parties
- **Notifications Discord** - Alertes automatiques de fin de partie
- **Commandes slash modernes** - Interface Discord intuitive
- **Gestion d'erreurs robuste** - Logging détaillé pour le debugging

## 🛠️ Développement

### Tests
```bash
uv run python test_structure.py
```

### Ajout de nouvelles commandes
1. Créer dans `src/commands/`
2. Ajouter le cog dans `main.py`
3. Synchroniser avec `/sync` (commande admin)

### Contribution
1. Fork le projet
2. Créer une branche feature
3. Commit et push
4. Créer une Pull Request

## 📝 TODO

- [ ] Système de liaison des comptes Discord-LoL
- [ ] Base de données persistante
- [ ] Dashboard web
- [ ] Statistiques avancées
- [ ] Support multi-serveurs
- [ ] Commandes de configuration par serveur

## 🐛 Debugging

Activer le mode debug dans `.env` :
```env
DEBUG_MODE=true
```

Logs détaillés disponibles dans la console.
