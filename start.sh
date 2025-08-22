#!/bin/bash

echo "🚀 Arena Gaming Bot - Script de démarrage"

# Vérifier si on est dans un container vide
if [ ! -f "main.py" ]; then
    echo "📥 Clonage initial du repository (fichiers manquants)..."
    
    # Nettoyer le répertoire au cas où
    rm -rf .git 2>/dev/null || true
    rm -rf * 2>/dev/null || true
    
    # Cloner le repository
    git clone https://github.com/Idumii/ArenaGaming.git temp_repo
    
    # Déplacer le contenu dans le répertoire courant
    mv temp_repo/* .
    mv temp_repo/.[^.]* . 2>/dev/null || true
    rm -rf temp_repo
    
    echo "✅ Repository cloné avec succès"
else
    echo "📁 Fichiers déjà présents"
    
    # Mise à jour si .git existe
    if [ -d ".git" ]; then
        echo "🔄 Mise à jour du repository..."
        git pull origin main
        echo "✅ Repository mis à jour"
    fi
fi

# Installer les dépendances si le fichier requirements.txt existe
if [ -f "requirements.txt" ]; then
    echo "📦 Installation des dépendances..."
    pip install --disable-pip-version-check -U --prefix .local -r requirements.txt
    echo "✅ Dépendances installées"
fi

# Vérifier que main.py existe maintenant
if [ ! -f "main.py" ]; then
    echo "❌ Erreur: main.py toujours introuvable après clonage!"
    echo "📋 Contenu du répertoire:"
    ls -la
    exit 1
fi

# Démarrer le bot
echo "🤖 Démarrage du bot Arena Gaming..."
python main.py
