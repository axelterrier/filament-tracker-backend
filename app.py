import os
from flask import Flask
from flask_cors import CORS
from models import db
from routes import api

app = Flask(__name__)

# 🔧 Résout le chemin absolu vers le fichier de base de données
base_dir = os.path.abspath(os.path.dirname(__file__))
db_path = os.path.join(base_dir, 'database', 'filaments.db')
app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{db_path}'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

CORS(app, origins=["http://localhost:8100"])  # OK pour Ionic sur 8100

db.init_app(app)
app.register_blueprint(api)

if __name__ == '__main__':
    app.run(debug=True)
