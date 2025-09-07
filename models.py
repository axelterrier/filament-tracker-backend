import os, json
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from sqlalchemy import event

db = SQLAlchemy()

# --------- Chargement du mapping matériau + hex -> nom marketing ---------
def _normalize_hex(h: str | None) -> str | None:
    if not h:
        return None
    s = h.strip().upper()
    if not s.startswith("#"):
        s = "#" + s
    # #RGB -> #RRGGBB
    if len(s) == 4 and all(c in "0123456789ABCDEF" for c in s[1:]):
        s = "#" + "".join([c * 2 for c in s[1:]])
    # force #RRGGBB
    if len(s) == 7:
        return s
    # RRGGBB -> #RRGGBB
    if len(s) == 6:
        return "#" + s
    return None

def _normalize_material(m: str | None) -> str:
    return (m or "").strip().upper()

def _load_color_map() -> dict[tuple[str, str], str]:
    # 1) prend la var d'env si dispo
    path = os.environ.get("FILAMENT_COLOR_JSON")
    # 2) sinon fallback vers ./data/filaments_min.json
    if not path:
        base_dir = os.path.abspath(os.path.dirname(__file__))
        path = os.path.join(base_dir, "data", "filaments_min.json")

    cmap: dict[tuple[str, str], str] = {}
    try:
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            for row in data:
                mat = _normalize_material(row.get("material"))
                hx = _normalize_hex(row.get("hex"))
                name = (row.get("name") or "").strip()
                if mat and hx and name:
                    cmap[(mat, hx)] = name
    except Exception:
        cmap = {}
    return cmap


COLOR_MAP = _load_color_map()

def resolve_color_name(material: str | None, hex_code: str | None) -> str | None:
    if not hex_code:
        return None
    mat = _normalize_material(material)
    hx = _normalize_hex(hex_code)
    if not hx:
        return None
    return COLOR_MAP.get((mat, hx))


class Filament(db.Model):
    __tablename__ = 'filaments'

    id = db.Column(db.Integer, primary_key=True)
    uid = db.Column(db.String, unique=True, nullable=False)           # Block 0
    tray_uid = db.Column(db.String)                                   # Block 9
    tag_manufacturer = db.Column(db.String)                           # Block 0

    filament_type = db.Column(db.String)                              # Block 2
    filament_detailed_type = db.Column(db.String)                     # Block 4

    color_code = db.Column(db.String)                                 # Block 5 (#RRGGBB)
    color_name = db.Column(db.String)                                 # ← Nouveau champ
    extra_color_info = db.Column(db.String)                           # Block 16
    filament_diameter = db.Column(db.Float)                           # Block 5

    spool_width = db.Column(db.Float)                                 # Block 10
    spool_weight = db.Column(db.Integer)                              # Block 5
    filament_length = db.Column(db.Integer)                           # Block 14

    print_temp_min = db.Column(db.Integer)                            # Block 6
    print_temp_max = db.Column(db.Integer)                            # Block 6
    dry_temp = db.Column(db.Integer)                                  # Block 6
    dry_time_hour = db.Column(db.Integer)                             # Block 6
    dry_bed_temp = db.Column(db.Integer)                              # Block 6

    nozzle_diameter = db.Column(db.Integer)                           # Block 8
    xcam_info = db.Column(db.String)                                  # Block 8

    manufacture_datetime_utc = db.Column(db.DateTime)                 # Block 12
    short_date = db.Column(db.String)                                 # Block 13

    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # ——— Champs utiles pour la synchro AMS ———
    remaining_percent = db.Column(db.Integer)         # JSON: remain
    remaining_grams = db.Column(db.Integer)           # calculé: spool_weight * remain / 100
    remaining_length_mm = db.Column(db.Integer)       # calculé: total_len * remain / 100
    last_sync_source = db.Column(db.String)           # "ams"
    last_sync_at = db.Column(db.DateTime)

    def to_dict(self):
        result = {}
        for column in self.__table__.columns:
            value = getattr(self, column.name)
            if isinstance(value, datetime):
                result[column.name] = value.strftime("%Y-%m-%d %H:%M:%S")
            else:
                result[column.name] = value
        return result


# --------- Events: assignation auto du color_name ---------
def _apply_color_name(target: Filament):
    material = target.filament_detailed_type or target.filament_type
    target.color_name = resolve_color_name(material, target.color_code)

@event.listens_for(Filament, "before_insert")
def filament_before_insert(mapper, connection, target: Filament):
    _apply_color_name(target)

@event.listens_for(Filament, "before_update")
def filament_before_update(mapper, connection, target: Filament):
    _apply_color_name(target)
