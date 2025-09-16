import os
from flask import Flask
from flask_cors import CORS
from flask_migrate import Migrate
from sqlalchemy import inspect, text
from models import db
from routes import api
from mqtt_manager import MqttManager   # <- ajuste le nom du module si besoin
from helper import load_config

def create_app():
    app = Flask(__name__)

    # --- DB: URL depuis l'env ou défaut sur le volume /app/data ---
    db_url = os.getenv("DATABASE_URL", "sqlite:////app/data/app.db")
    app.config["SQLALCHEMY_DATABASE_URI"] = db_url
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

    # Options SQLite: accès multi-threads + timeout
    app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
        "connect_args": {
            "check_same_thread": False,  # thread MQTT
            "timeout": 30,               # secondes (sqlite busy_timeout)
        }
    }

    # --- CORS (facultatif si proxy /api en même origine) ---
    CORS(app, resources={r"/api/*": {"origins": "*"}})

    # --- Répertoire data par défaut pour fichiers statiques internes ---
    base_dir = os.path.abspath(os.path.dirname(__file__))
    data_dir = os.path.join(base_dir, "data")
    os.makedirs(data_dir, exist_ok=True)
    default_color_json = os.path.join(data_dir, "filaments_min.json")
    os.environ.setdefault("FILAMENT_COLOR_JSON", default_color_json)

    # --- SQLAlchemy + Migrations ---
    db.init_app(app)
    Migrate(app, db)

    # --- Crée les tables si base vide + force les PRAGMAs SQLite ---
    with app.app_context():
        # PRAGMAs pour SQLite (idempotent)
        try:
            eng = db.engine
            # Active WAL: readers non bloqués par les writes
            eng.execute(text("PRAGMA journal_mode=WAL;"))
            eng.execute(text("PRAGMA synchronous=NORMAL;"))
            eng.execute(text("PRAGMA busy_timeout=5000;"))
        except Exception as e:
            print(f"[DB] PRAGMA init skipped/failed: {e}")

        try:
            insp = inspect(db.engine)
            if "filaments" not in insp.get_table_names():
                print("[DB] Base vide détectée → création des tables...")
                db.create_all()
        except Exception as e:
            print(f"[DB] Init error: {e}")

    # --- MQTT Manager global ---
    app.mqtt_manager = MqttManager()

    # --- Routes ---
    app.register_blueprint(api)

    # --- Auto-start MQTT si config présente ---
    cfg = load_config()
    if cfg:
        try:
            app.mqtt_manager.start(cfg)
        except Exception as e:
            print(f"[MQTT] Startup error: {e}")

    @app.get("/health")
    def health():
        return {"status": "ok"}

    return app


# WSGI entrypoint pour Gunicorn: `gunicorn -w 2 -k gthread --threads 1 -b 0.0.0.0:5000 app:app`
app = create_app()

# Mode dev seulement (local, hors Docker)
if __name__ == "__main__":
    # En dev local: accessible sur 0.0.0.0, debug activable via FLASK_DEBUG=1
    debug = os.getenv("FLASK_DEBUG", "0") == "1"
    app.run(host="0.0.0.0", port=5000, debug=debug)
