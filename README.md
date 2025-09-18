# Déploiement « tout-en-un » — Filament Tracker (Frontend + Backend)

Cette doc propose un **seul** `docker-compose.yml` pour lancer le backend (API) et le frontend (UI) ensemble, avec Nginx en reverse proxy pour `/api`.

---

## 🗂️ Arborescence conseillée

```
filament-tracker/
├── backend-data/
│   └── app.db              # créé automatiquement (SQLite)
├── nginx.conf              # config Nginx pour le frontend
└── docker-compose.yml      # stack complète
```

Crée le dossier, copie les fichiers, puis lance `docker compose up -d` à la racine du dossier.

---

## ⚙️ Fichiers

### 1) `docker-compose.yml` (stack complète)

```yaml
version: "3.8"

networks:
  filament_net:
    driver: bridge

services:
  backend:
    image: ghcr.io/axelterrier/filament-tracker-backend:latest
    container_name: filament-backend
    restart: unless-stopped
    networks: [filament_net]
    ports:
      - "9100:5000"                    # API exposée sur http://<host>:9100
    volumes:
      - ./backend-data:/app/data       # persistance DB/exports/logs
    environment:
      - DATABASE_URL=sqlite:////app/data/app.db
    command: gunicorn -w 2 -k gthread --threads 1 -b 0.0.0.0:5000 app:app
    healthcheck:
      test: ["CMD", "wget", "-qO-", "http://localhost:5000/health"]
      interval: 15s
      timeout: 3s
      retries: 10
      start_period: 15s

  frontend:
    image: ghcr.io/axelterrier/filament-tracker-frontend:latest
    container_name: filament-frontend
    restart: unless-stopped
    networks: [filament_net]
    depends_on:
      backend:
        condition: service_healthy
    ports:
      - "9200:80"                      # UI sur http://<host>:9200
    volumes:
      - ./nginx.conf:/etc/nginx/conf.d/default.conf:ro
```

### 2) `nginx.conf`

```nginx
server {
  listen 80;
  server_name _;

  root   /usr/share/nginx/html;
  index  index.html;

  # Proxy des appels API vers le backend
  location /api/ {
    proxy_pass http://backend:5000;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_http_version 1.1;
  }

  # SPA routing (Vue/React)
  location / {
    try_files $uri $uri/ /index.html;
  }
}
```

---

## 🚀 Lancement

```bash
# 1) Préparer l'arborescence
mkdir -p filament-tracker/backend-data
cd filament-tracker

# 2) Copier nginx.conf et docker-compose.yml (contenu ci-dessus)

# 3) Démarrer la stack
docker compose up -d

# 4) Ouvrir
# UI  : http://<host>:9200
# API : http://<host>:9100
```

> Le fichier `app.db` (SQLite) sera créé automatiquement dans `backend-data/` au premier démarrage.

---

## 🔄 Mise à jour

```bash
docker compose pull
docker compose up -d
docker image prune -f
```

---

## 🧪 Dépannage rapide

- **UI fonctionne mais API KO depuis l’UI**  
  - Vérifie que `frontend` et `backend` partagent bien `filament_net`.  
  - Vérifie `proxy_pass http://backend:5000;` dans `nginx.conf`.  
  - Teste directement l’API : `curl http://<host>:9100/health`.

- **Permissions SQLite**  
  ```bash
  sudo chown -R 1000:1000 backend-data || true
  sudo chmod -R 775 backend-data
  ```

- **Santé backend KO**  
  ```bash
  docker logs filament-backend
  docker exec -it filament-backend sh -lc "wget -qO- http://localhost:5000/health"
  ```

- **404/blank sur navigation frontend**  
  - Assure-toi d’avoir `try_files $uri $uri/ /index.html;` (SPA).
