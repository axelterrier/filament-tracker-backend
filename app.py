import os
from flask import Flask
from flask_cors import CORS
from flask_migrate import Migrate
from sqlalchemy import inspect
from models import db
from routes import api
from mqtt_listener import MqttManager
from helper import load_config

app = Flask(__name__)

# — DB: chemin absolu + création du dossier si besoin —
base_dir = os.path.abspath(os.path.dirname(__file__))
db_dir = os.path.join(base_dir, "database")
os.makedirs(db_dir, exist_ok=True)
db_path = os.path.join(db_dir, "filaments.db")

app.config["SQLALCHEMY_DATABASE_URI"] = f"sqlite:///{db_path}"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

# — CORS : autoriser Ionic + Vite —
CORS(app, origins=["http://localhost:8100", "http://localhost:5173"])

# — SQLAlchemy + Migrations —
db.init_app(app)
migrate = Migrate(app, db)

# — Création auto des tables si absentes —
with app.app_context():
    insp = inspect(db.engine)
    if "filaments" not in insp.get_table_names():
        print("[DB] Base vide détectée → création des tables...")
        db.create_all()

# — MQTT Manager global sur l'app —
app.mqtt_manager = MqttManager()

# — Routes (utilisent current_app.mqtt_manager) —
app.register_blueprint(api)

# — Démarrage auto du MQTT si config déjà présente —
cfg = load_config()
if cfg:
    try:
        app.mqtt_manager.start(cfg)
    except Exception as e:
        print(f"[MQTT] Startup error: {e}")

# — Ping route pour vérification —
@app.get("/health")
def health():
    return {"status": "ok"}

if __name__ == "__main__":
    app.run(debug=True)
