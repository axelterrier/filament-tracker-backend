# backend/helper.py
from datetime import datetime
from models import Filament 
import json
from pathlib import Path
from typing import Optional, Dict, Any

def _hex_rgba_to_hex(rgb_or_rgba: str) -> str | None:
    if not rgb_or_rgba:
        return None
    s = rgb_or_rgba.strip()
    if len(s) == 8:  # RRGGBBAA -> on ignore l'alpha
        s = s[:6]
    if len(s) == 6:
        return "#" + s.upper()
    return None

def tray_to_filament_dict(sensor_id: str, tray: dict) -> dict:
    try:
        spool_weight_g = int(float(tray.get("tray_weight"))) if tray.get("tray_weight") else None
    except (ValueError, TypeError):
        spool_weight_g = None

    try:
        filament_diam = float(tray.get("tray_diameter")) if tray.get("tray_diameter") else None
    except (ValueError, TypeError):
        filament_diam = None

    try:
        total_len_mm = int(tray.get("total_len")) if tray.get("total_len") else None
    except (ValueError, TypeError):
        total_len_mm = None

    try:
        remain_pct = int(tray.get("remain")) if tray.get("remain") else None
    except (ValueError, TypeError):
        remain_pct = None

    remaining_grams = (
        int(round(spool_weight_g * (remain_pct / 100.0)))
        if spool_weight_g is not None and remain_pct is not None else None
    )
    remaining_length_mm = (
        int(round(total_len_mm * (remain_pct / 100.0)))
        if total_len_mm is not None and remain_pct is not None else None
    )

    def to_int_or_none(v):
        try:
            return int(float(v))
        except (TypeError, ValueError):
            return None

    return {
        "uid": tray.get("tag_uid"),
        "tray_uid": tray.get("tray_uuid"),
        "ams_id": sensor_id,
        "ams_slot": tray.get("tray_id_name"),

        "filament_type": tray.get("tray_type"),
        "filament_detailed_type": tray.get("tray_sub_brands"),
        "color_code": _hex_rgba_to_hex(tray.get("tray_color")),
        "filament_diameter": filament_diam,
        "spool_weight": spool_weight_g,
        "filament_length": total_len_mm,

        "print_temp_min": to_int_or_none(tray.get("nozzle_temp_min")),
        "print_temp_max": to_int_or_none(tray.get("nozzle_temp_max")),
        "dry_temp": to_int_or_none(tray.get("tray_temp")),
        "dry_time_minutes": to_int_or_none(tray.get("tray_time")),
        "dry_bed_temp": to_int_or_none(tray.get("bed_temp")),
        "xcam_info": tray.get("xcam_info"),

        "remaining_percent": remain_pct,
        "remaining_grams": remaining_grams,
        "remaining_length_mm": remaining_length_mm,

        "last_sync_source": "ams",
        "last_sync_at": datetime.utcnow(),
    }

def upsert_filament(session, payload: dict):
    """
    Identifie par payload['uid'] (tag_uid). Fallback sur payload['tray_uid'].
    Met à jour uniquement les champs non-nuls.
    """
    key_uid = payload.get("uid")
    alt_key = payload.get("tray_uid")
    if not key_uid and not alt_key:
        return

    q = None
    if key_uid:
        q = Filament.query.filter_by(uid=key_uid).first()
    if not q and alt_key:
        q = Filament.query.filter_by(tray_uid=alt_key).first()

    if not q:
        q = Filament(uid=key_uid or alt_key)
        session.add(q)

    for k, v in payload.items():
        if v is not None and hasattr(q, k):
            setattr(q, k, v)

    session.commit()

CONFIG_FILE = Path("./config/mqtt.json")
CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)

def load_config() -> Optional[Dict[str, Any]]:
    if CONFIG_FILE.exists():
        return json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
    return None

def save_config(cfg: Dict[str, Any]) -> None:
    CONFIG_FILE.write_text(json.dumps(cfg, indent=2), encoding="utf-8")

def validate_cfg(payload: Dict[str, Any]) -> Optional[str]:
    required = ["ip", "password"]
    for k in required:
        if not payload.get(k):
            return f"Champ manquant: {k}"
    # Valeurs par défaut
    payload.setdefault("useTLS", True)
    payload.setdefault("portTLS", 8883)
    payload.setdefault("portPlain", 1883)
    # Serial utile (sinon client_id par défaut)
    payload.setdefault("serial", "")
    return None