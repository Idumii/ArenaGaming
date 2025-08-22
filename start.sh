#!/bin/bash

echo "🚀 Arena Gaming Bot - Script de démarrage"

# Vérifier si le dossier .git existe
if [ ! -d ".git" ]; then
    echo "📥 Clonage initial du repository..."
    git clone https://github.com/Idumii/ArenaGaming.git .
    echo "✅ Repository cloné"
else
    echo "🔄 Mise à jour du repository..."
    git pull origin main
    echo "✅ Repository mis à jour"
fi

# Installer les dépendances si le fichier requirements.txt existe
if [ -f "requirements.txt" ]; then
    echo "📦 Installation des dépendances..."
    pip install --disable-pip-version-check -U --prefix .local -r requirements.txt
    echo "✅ Dépendances installées"
fi

# Démarrer le bot
echo "🤖 Démarrage du bot Arena Gaming..."
python main.py
