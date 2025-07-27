from flask import Blueprint, request, jsonify
from models import db, Filament

api = Blueprint('api', __name__)

# Get all filaments
@api.route('/api/filaments', methods=['GET'])
def get_filaments():
    filaments = Filament.query.all()
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
            "dry_time_minutes": f.dry_time_minutes,
            "dry_bed_temp": f.dry_bed_temp,
            "nozzle_diameter": f.nozzle_diameter,
            "xcam_info": f.xcam_info,
            "manufacture_datetime_utc": f.manufacture_datetime_utc.strftime("%Y-%m-%d %H:%M:%S") if f.manufacture_datetime_utc else None,
            "short_date": f.short_date
        } for f in filaments
    ]
    return jsonify(data)

#Get one specific filaments
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
    # Validez au moins la présence de l’UID
    if not data.get("uid"):
        return jsonify({"error": "Le champ uid est requis"}), 400

    # Instanciez votre modèle
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
        dry_time_minutes=data.get("dry_time_minutes"),
        dry_bed_temp=data.get("dry_bed_temp"),
        nozzle_diameter=data.get("nozzle_diameter"),
        xcam_info=data.get("xcam_info"),
        # manufacture_datetime_utc attend un datetime Python : parsez-le si besoin
    )

    # Enregistrez en base
    db.session.add(filament)
    try:
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500

    # Renvoie l’objet créé (assurez-vous d’avoir une méthode to_dict())
    return jsonify(filament.to_dict()), 201

#Delete a specific filament
@api.route('/api/filaments/<int:filament_id>', methods=['DELETE'])
def delete_filament(filament_id):
    """
    Supprime un filament par son ID.
    Retourne 204 No Content si supprimé, 404 si non trouvé, 500 si erreur.
    """
    # Recherche du filament
    filament = Filament.query.get(filament_id)
    if filament is None:
        return jsonify({"error": "Filament non trouvé."}), 404

    try:
        # Suppression et commit
        db.session.delete(filament)
        db.session.commit()
        # Pas de contenu à renvoyer
        return ('', 204)

    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500

#Update a specific filament
@api.route('/api/filaments/<int:id>', methods=['PUT', 'PATCH'])
def update_filament(id):
    filament = Filament.query.get(id)
    if not filament:
        return jsonify({'error': 'Not found'}), 404

    data = request.get_json() or {}

    # Mets à jour les champs que tu veux autoriser à éditer
    for field in [
        "uid", "tray_uid", "tag_manufacturer",
        "filament_type", "filament_detailed_type",
        "color_code", "extra_color_info", "filament_diameter",
        "spool_width", "spool_weight", "filament_length",
        "print_temp_min", "print_temp_max", "dry_temp", "dry_time_minutes", "dry_bed_temp",
        "nozzle_diameter", "xcam_info", "manufacture_datetime_utc", "short_date"
    ]:
        if field in data:
            setattr(filament, field, data[field])

    db.session.commit()
    return jsonify(filament.to_dict())