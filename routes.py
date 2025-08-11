from flask import Blueprint, request, jsonify, current_app
from models import db, Filament
from datetime import datetime
from sqlalchemy import func, cast, Float
from helper import tray_to_filament_dict, upsert_filament, validate_cfg, save_config, _parse_dt, _NUMERIC_FIELDS, _DATETIME_FIELDS, _ALLOWED
import tempfile
import os
import zipfile
import json
import xml.etree.ElementTree as ET

api = Blueprint('api', __name__)

# ------------------- MQTT endpoints -------------------

@api.post("/api/mqtt/test")
def api_mqtt_test():
    payload = request.get_json(force=True) or {}
    err = validate_cfg(payload)
    if err:
        return jsonify({"error": err}), 400
    res = current_app.mqtt_manager.quick_test(payload)
    return (jsonify(res), 200) if res.get("ok") else (jsonify(res), 400)

@api.post("/api/mqtt/config")
def api_mqtt_config():
    payload = request.get_json(force=True) or {}
    err = validate_cfg(payload)
    if err:
        return jsonify({"error": err}), 400

    save_config(payload)
    try:
        current_app.mqtt_manager.start(payload)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

    return jsonify({"ok": True, "message": "Client MQTT démarré"})

@api.get("/api/mqtt/status")
def api_mqtt_status():
    m = current_app.mqtt_manager
    cfg = m.cfg or {}
    broker = None
    if cfg:
        port = cfg["portTLS"] if cfg.get("useTLS", True) else cfg.get("portPlain", 1883)
        broker = f"{cfg.get('ip')}:{port}"

    return jsonify({
        "connected": m.connected,
        "last_error": m.last_error,
        "broker": broker,
        "useTLS": cfg.get("useTLS", True) if cfg else None,
        "serial": cfg.get("serial") if cfg else None,
    })

# ------------------- Filaments API (inchangé) -------------------

# Get all filaments
@api.route('/api/filaments', methods=['GET'])
def get_filaments():
    # Clé de tri poids: poids réel si dispo, sinon poids bobine; cast au cas où la colonne est TEXT
    weight_key = func.coalesce(
        cast(Filament.remaining_grams, Float),
        cast(Filament.spool_weight, Float),
        1e12  # met les inconnus tout à la fin
    )

    # Tri SQL: matériau → sous-type → couleur → poids (desc)
    filaments = (
        db.session.query(Filament)
        .order_by(
            func.lower(func.coalesce(Filament.filament_type, 'zzzz')),
            func.lower(func.coalesce(Filament.filament_detailed_type, 'zzzz')),
            func.lower(func.coalesce(Filament.color_code, 'zzzz')),
            weight_key.desc()
        )
        .all()
    )

    data = [
        {
            "id": f.id,
            "uid": f.uid,
            "tray_uid": f.tray_uid,
            "tag_manufacturer": f.tag_manufacturer,
            "filament_type": f.filament_type,
            "filament_detailed_type": f.filament_detailed_type,
            "color_code": f.color_code,
            "extra_color_info": f.extra_color_info,
            "filament_diameter": f.filament_diameter,
            "spool_width": f.spool_width,
            "spool_weight": f.spool_weight,
            "filament_length": f.filament_length,
            "print_temp_min": f.print_temp_min,
            "print_temp_max": f.print_temp_max,
            "dry_temp": f.dry_temp,
            "dry_time_hour": f.dry_time_hour,
            "dry_bed_temp": f.dry_bed_temp,
            "nozzle_diameter": f.nozzle_diameter,
            "xcam_info": f.xcam_info,
            "manufacture_datetime_utc": f.manufacture_datetime_utc.strftime("%Y-%m-%d %H:%M:%S") if f.manufacture_datetime_utc else None,
            "short_date": f.short_date,
            "remaining_percent": f.remaining_percent,
            "remaining_weight": f.remaining_grams,
            "remaining_length": f.remaining_length_mm,
            "last_sync_source": f.last_sync_source,
            "last_sync_at": f.last_sync_at.strftime("%Y-%m-%d %H:%M:%S") if f.last_sync_at else None,
        }
        for f in filaments
    ]

    return jsonify(data)

#Get one specific filament
@api.route('/api/filaments/<int:id>', methods=['GET'])
def get_filament(id):
    filament = Filament.query.get(id)
    if not filament:
        return jsonify({'error': 'Not found'}), 404
    return jsonify(filament.to_dict())

#Create a new filament
@api.route("/api/filaments", methods=['POST'])
def create_filament():
    data = request.get_json() or {}
    if not data.get("uid"):
        return jsonify({"error": "Le champ uid est requis"}), 400

    filament = Filament(
        uid=data["uid"],
        tag_manufacturer=data.get("tag_manufacturer"),
        filament_type=data.get("filament_type"),
        filament_detailed_type=data.get("filament_detailed_type"),
        color_code=data.get("color_code"),
        extra_color_info=data.get("extra_color_info"),
        filament_diameter=data.get("filament_diameter"),
        spool_width=data.get("spool_width"),
        spool_weight=data.get("spool_weight"),
        filament_length=data.get("filament_length"),
        print_temp_min=data.get("print_temp_min"),
        print_temp_max=data.get("print_temp_max"),
        dry_temp=data.get("dry_temp"),
        dry_time_hour=data.get("dry_time_hour"),
        dry_bed_temp=data.get("dry_bed_temp"),
        nozzle_diameter=data.get("nozzle_diameter"),
        xcam_info=data.get("xcam_info"),
    )

    db.session.add(filament)
    try:
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500

    return jsonify(filament.to_dict()), 201

#Delete a specific filament
@api.route('/api/filaments/<int:filament_id>', methods=['DELETE'])
def delete_filament(filament_id):
    filament = Filament.query.get(filament_id)
    if filament is None:
        return jsonify({"error": "Filament non trouvé."}), 404

    try:
        db.session.delete(filament)
        db.session.commit()
        return ('', 204)
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500

#Update a specific filament
@api.route('/api/filaments/<int:id>', methods=['PUT', 'PATCH'])
def update_filament(id):
    # Flask ajoute déjà OPTIONS automatiquement, mais on l’annonce pour clarté
    filament = Filament.query.get(id)
    if not filament:
        return jsonify({'error': 'Not found'}), 404

    data = request.get_json(silent=True) or {}

    # Appliquer champs connus avec conversion
    for field, value in data.items():
        if field not in _ALLOWED:
            continue
        if field in _NUMERIC_FIELDS:
            try:
                value = _NUMERIC_FIELDS[field](value) if value is not None else None
            except (TypeError, ValueError):
                return jsonify({'error': f'Invalid number for {field}'}), 400
        elif field in _DATETIME_FIELDS:
            value = _parse_dt(value)
        else:
            # stringy
            value = None if value is None else str(value)
        setattr(filament, field, value)

    # Petites règles de cohérence AMS
    g = filament.remaining_grams
    sw = filament.spool_weight or 0
    pct = filament.remaining_percent

    if g is not None and sw > 0:
        filament.remaining_percent = max(0, min(100, round(g / sw * 100)))
    elif pct is not None and sw > 0 and g is None:
        filament.remaining_grams = max(0, round(sw * (pct / 100)))

    # Dates nulles si parsing KO (optionnel)
    # if 'manufacture_datetime_utc' in data and filament.manufacture_datetime_utc is None: ...
    # if 'last_sync_at' in data and filament.last_sync_at is None: ...

    db.session.commit()
    return jsonify(filament.to_dict())

# Import one or multiple JSON
@api.route('/api/filaments/import', methods=['POST'])
def import_filaments():
    if 'files' not in request.files:
        return jsonify({"error": "No files part in request"}), 400

    files = request.files.getlist('files')
    imported = 0
    skipped = 0
    errors = []

    for file in files:
        if not file.filename.endswith('.json'):
            skipped += 1
            continue

        try:
            raw = file.read().decode('utf-8')
            content = json.loads(raw)

            uid = content.get('tag_uid')
            if not uid:
                skipped += 1
                continue

            existing = Filament.query.filter_by(uid=uid).first()
            if existing:
                skipped += 1
                continue

            filament = Filament(
                uid=uid,
                tray_uid=uid,
                tag_manufacturer=content.get('material_code'),
                filament_type=content.get('type'),
                filament_detailed_type=content.get('subtype'),
                color_code=content.get('color_hex'),
                filament_diameter=content.get('diameter_mm'),
                spool_weight=content.get('spool_weight_g'),
                filament_length=content.get('length_m'),
                nozzle_diameter=int(round(content.get('nozzle_diameter_mm', 0) * 1000)),
                print_temp_min=content.get('temp_hotend_min'),
                print_temp_max=content.get('temp_hotend_max'),
                dry_temp=content.get('temp_drying'),
                dry_time_hour=content.get('drying_time_h', 0) * 60,
                manufacture_datetime_utc=datetime.strptime(content.get('produced_at'), "%Y-%m-%d-%H-%M"),
                short_date=content.get('produced_at').replace('-', '')[:8],
            )

            db.session.add(filament)
            imported += 1

        except Exception as e:
            skipped += 1
            errors.append({"file": file.filename, "error": str(e)})

    db.session.commit()

    return jsonify({
        "imported": imported,
        "skipped": skipped,
        "errors": errors
    }), 200

# ------------------- 3MF Analysis API ---------------------------

@api.route('/api/3mf/analyze', methods=['POST'])
def analyze_3mf():
    # Récupère le fichier 3MF envoyé
    file = request.files.get('file')
    if not file:
        return jsonify({'error': 'No file provided'}), 400

    with tempfile.TemporaryDirectory() as tmpdir:
        # Sauvegarde et extraction de l'archive 3MF
        file_path = os.path.join(tmpdir, 'model.3mf')
        file.save(file_path)
        with zipfile.ZipFile(file_path, 'r') as archive:
            archive.extractall(tmpdir)

        # Dossier contenant les métadonnées
        meta = os.path.join(tmpdir, 'metadata')

        # 1) Couleurs et matériaux depuis project_settings.config
        proj_cfg = os.path.join(meta, 'project_settings.config')
        with open(proj_cfg, 'r', encoding='utf-8') as f:
            settings = json.load(f)
        colors_raw = settings.get('filament_colour', [])
        mats_raw = settings.get('filament_settings_id', [])

        colors = colors_raw
        materials = [m.split('@')[0].replace('Bambu ', '').strip() for m in mats_raw]

        # 2) Comptage des pièces via le premier fichier XML/HTML contenant <objects>
        pieces_count = 0
        for fname in os.listdir(meta):
            if fname.lower().endswith(('.xml', '.html')):
                path = os.path.join(meta, fname)
                with open(path, 'r', encoding='utf-8') as f:
                    content = f.read().lstrip()
                if content.startswith('<objects') or '<objects' in content:
                    tree = ET.parse(path)
                    pieces_count = len(tree.getroot().findall('.//object'))
                    break

    # Réponse JSON simplifiée
    return jsonify({
        'colors': colors,
        'materials': materials,
        'pieces_count': pieces_count,
    })

#-------------------- AMS Sync API ---------------------------

@api.route("/ams/sync", methods=["POST"])
def ams_sync():
    data = request.get_json(silent=True) or {}
    report = data.get("print", {})
    ams = report.get("ams", {}).get("ams", [])

    updated = 0
    for sensor in ams:
        sid = sensor.get("id")
        for tray in sensor.get("tray", []):
            if not tray.get("tag_uid"):
                continue
            payload = tray_to_filament_dict(sid, tray)
            upsert_filament(db.session, payload)
            updated += 1

    return jsonify({"status": "ok", "updated": updated}), 200
