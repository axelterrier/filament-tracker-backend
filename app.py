import os
from flask import Flask
from flask_cors import CORS
from flask_migrate import Migrate
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

CORS(app, origins=["http://localhost:8100"])

# — SQLAlchemy + Migrations — A dégager dans le futur —
db.init_app(app)
migrate = Migrate(app, db)

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
        # Optionnel: logger
        print(f"[MQTT] Startup error: {e}")

# (optionnel) Ping route
@app.get("/health")
def health():
    return {"status": "ok"}

if __name__ == "__main__":
    app.run(debug=True)
