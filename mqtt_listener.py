#!/usr/bin/env python3
import ssl
import json
import time
import threading
import os
from typing import Optional, Dict, Any
from paho.mqtt import client as mqtt
import requests

# Permet de configurer l’URL de sync via une variable d’environnement
API_PREFIX = os.getenv("API_PREFIX", "/api")
SYNC_URL = os.getenv("SYNC_URL", f"http://localhost:5000{API_PREFIX}/ams/sync")


class MqttManager:
    def __init__(self):
        self.client: Optional[mqtt.Client] = None
        self.cfg: Optional[Dict[str, Any]] = None
        self.lock = threading.Lock()
        self.connected: bool = False
        self.last_error: Optional[str] = None

    # ---------- Callbacks ----------
    def _on_connect(self, client, userdata, flags, rc):
        self.connected = (rc == 0)
        if not self.connected:
            self.last_error = f"rc={rc}"
            return

        serial = (self.cfg or {}).get("serial") or "bambu"
        rep_topic = f"device/{serial}/report"
        req_topic = f"device/{serial}/request"
        client.subscribe(rep_topic)

        # Force un push complet
        payload = {
            "pushing": {
                "sequence_id": str(int(time.time())),
                "command": "pushall",
            },
            "user_id": (self.cfg or {}).get("password", ""),
        }
        client.publish(req_topic, json.dumps(payload), qos=1)

    def _on_disconnect(self, client, userdata, rc):
        self.connected = False
        self.last_error = f"disconnect rc={rc}"

    def _on_message(self, client, userdata, msg):
        try:
            data = json.loads(msg.payload.decode(errors="replace"))
        except Exception:
            return

        # Filtre: si pas d'info AMS, on ignore
        ams_list = data.get("print", {}).get("ams", {}).get("ams", [])
        if not ams_list:
            return

        # → Forward au backend interne (endpoint Flask /api/ams/sync)
        try:
            requests.post(SYNC_URL, json=data, timeout=5)
        except Exception as e:
            self.last_error = f"/ams/sync: {e}"

    # ---------- Construction client ----------
    def _build_client(self, cfg: Dict[str, Any]) -> mqtt.Client:
        serial = cfg.get("serial") or "bambu-client"
        c = mqtt.Client(client_id=serial, protocol=mqtt.MQTTv311)
        # En LAN Bambu : username "bblp", password = LAN code
        c.username_pw_set("bblp", cfg["password"])

        if cfg.get("useTLS", True):
            c.tls_set(cert_reqs=ssl.CERT_NONE, tls_version=ssl.PROTOCOL_TLSv1_2)
            c.tls_insecure_set(True)

        c.on_connect = self._on_connect
        c.on_disconnect = self._on_disconnect
        c.on_message = self._on_message
        return c

    # ---------- API publique ----------
    def start(self, cfg: Dict[str, Any]) -> None:
        with self.lock:
            # Stop ancien client
            if self.client is not None:
                try:
                    self.client.loop_stop()
                    self.client.disconnect()
                except Exception:
                    pass
                self.client = None

            self.cfg = cfg
            self.client = self._build_client(cfg)

            host = cfg["ip"]
            port = cfg["portTLS"] if cfg.get("useTLS", True) else cfg.get("portPlain", 1883)
            self.client.connect(host, port, keepalive=60)
            self.client.loop_start()  # non bloquant

    def stop(self) -> None:
        with self.lock:
            if self.client is not None:
                try:
                    self.client.loop_stop()
                    self.client.disconnect()
                except Exception:
                    pass
                self.client = None
                self.connected = False

    def quick_test(self, cfg: Dict[str, Any], timeout: float = 4.0) -> Dict[str, Any]:
        """Connexion éphémère pour valider les paramètres sans lancer le loop permanent."""
        test_client = self._build_client(cfg)
        host = cfg["ip"]
        port = cfg["portTLS"] if cfg.get("useTLS", True) else cfg.get("portPlain", 1883)
        res = {"ok": False, "details": ""}

        done = threading.Event()

        def on_connect(c, u, f, rc):
            if rc == 0:
                res["ok"] = True
                res["details"] = f"Connecté à {host}:{port} (TLS={cfg.get('useTLS', True)})"
            else:
                res["details"] = f"Échec rc={rc}"
            done.set()

        # Remplace temporairement le callback
        orig = test_client.on_connect
        test_client.on_connect = on_connect

        try:
            test_client.connect(host, port, keepalive=30)
            test_client.loop_start()
            done.wait(timeout)
        except Exception as e:
            res["details"] = f"Exception: {e}"
        finally:
            try:
                test_client.loop_stop()
                test_client.disconnect()
            except Exception:
                pass
            test_client.on_connect = orig

        return res
