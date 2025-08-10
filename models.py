from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()

class Filament(db.Model):
    __tablename__ = 'filaments'

    id = db.Column(db.Integer, primary_key=True)
    uid = db.Column(db.String, unique=True, nullable=False)           # Block 0
    tray_uid = db.Column(db.String)                                   # Block 9
    tag_manufacturer = db.Column(db.String)                           # Block 0

    filament_type = db.Column(db.String)                              # Block 2
    filament_detailed_type = db.Column(db.String)                     # Block 4

    color_code = db.Column(db.String)                                 # Block 5
    extra_color_info = db.Column(db.String)                           # Block 16
    filament_diameter = db.Column(db.Float)                           # Block 5

    spool_width = db.Column(db.Float)                                 # Block 10
    spool_weight = db.Column(db.Integer)                              # Block 5
    filament_length = db.Column(db.Integer)                           # Block 14

    print_temp_min = db.Column(db.Integer)                            # Block 6
    print_temp_max = db.Column(db.Integer)                            # Block 6
    dry_temp = db.Column(db.Integer)                                  # Block 6
    dry_time_minutes = db.Column(db.Integer)                          # Block 6
    dry_bed_temp = db.Column(db.Integer)                              # Block 6

    nozzle_diameter = db.Column(db.Integer)                           # Block 8
    xcam_info = db.Column(db.String)                                  # Block 8

    manufacture_datetime_utc = db.Column(db.DateTime)                 # Block 12
    short_date = db.Column(db.String)                                 # Block 13

    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    tag_manufacturer = db.Column(db.String)

        # ——— NOUVEAUX CHAMPS utiles pour la synchro AMS ———
    remaining_percent = db.Column(db.Integer)   # JSON: remain
    remaining_grams = db.Column(db.Integer)     # calculé: spool_weight * remain / 100
    remaining_length_mm = db.Column(db.Integer) # calculé: total_len * remain / 100
    last_sync_source = db.Column(db.String)     # "ams"
    last_sync_at = db.Column(db.DateTime)

    def to_dict(self):
        return {
            "id": self.id,
            "uid": self.uid,
            "tray_uid": self.tray_uid,
            "tag_manufacturer": self.tag_manufacturer,
            "filament_type": self.filament_type,
            "filament_detailed_type": self.filament_detailed_type,
            "color_code": self.color_code,
            "extra_color_info": self.extra_color_info,
            "filament_diameter": self.filament_diameter,
            "spool_width": self.spool_width,
            "spool_weight": self.spool_weight,
            "filament_length": self.filament_length,
            "print_temp_min": self.print_temp_min,
            "print_temp_max": self.print_temp_max,
            "dry_temp": self.dry_temp,
            "dry_time_minutes": self.dry_time_minutes,
            "dry_bed_temp": self.dry_bed_temp,
            "nozzle_diameter": self.nozzle_diameter,
            "xcam_info": self.xcam_info,
            "manufacture_datetime_utc": self.manufacture_datetime_utc.strftime("%Y-%m-%d %H:%M:%S") if self.manufacture_datetime_utc else None,
            "short_date": self.short_date
        }