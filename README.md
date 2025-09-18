# Filament Tracker Backend

## 🚀 Démarrage rapide (Docker Compose)

```yaml
version: "3.8"

services:
  backend:
    image: ghcr.io/axelterrier/filament-tracker-backend:latest
    container_name: filament-backend
    restart: unless-stopped
    ports:
      - "9100:5000"              # hôte:conteneur
    volumes:
      - ./backend-data:/app/data # persistance DB/exports/logs
    environment:
      - DATABASE_URL=sqlite:////app/data/app.db
    command: gunicorn -w 2 -k gthread --threads 1 -b 0.0.0.0:5000 app:app
    healthcheck:
      test: ["CMD", "wget", "-qO-", "http://localhost:5000/health"]
      interval: 15s
      timeout: 3s
      retries: 10
      start_period: 15s
```

```bash
# 1) Créer le dossier de données
mkdir -p backend-data

# 2) Lancer
docker compose up -d

# 3) Tester la santé
curl http://localhost:9100/health
# -> "ok"
```

## 🔄 Mettre à jour

```bash
docker compose pull
docker compose up -d
docker image prune -f
```
