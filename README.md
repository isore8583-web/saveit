# SaveIt

Site + PWA de téléchargement de vidéos (FastAPI + yt-dlp + ffmpeg).

## Lancer en local
    pip install -r requirements.txt      # ffmpeg doit être installé sur la machine
    uvicorn main:app --reload
    # ouvre http://localhost:8000

## Déployer (gratuit pour démarrer)
Le Dockerfile est prêt : Render, Railway, Fly.io ou Oracle Cloud Free Tier.
Une fois en ligne (HTTPS), le site est installable comme app depuis le navigateur
(Android : « Installer l’application », iPhone : Partager > « Sur l’écran d’accueil »).

## Réglages (variables d’environnement)
- MAX_MB : taille max par fichier (défaut 500)
- RATE_LIMIT : requêtes/minute/IP (défaut 20)

## Maintenance
Les plateformes changent souvent : mets à jour yt-dlp régulièrement
(`pip install -U yt-dlp`, ou rebuild de l’image Docker).
