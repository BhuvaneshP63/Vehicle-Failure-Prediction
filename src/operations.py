import hashlib
import json
import math
import os
import re
import sqlite3
from contextlib import closing
from datetime import datetime, timezone
from functools import lru_cache
from pathlib import Path

import joblib
import numpy as np
import pandas as pd

from src.data_preprocessing import ROOT, FEATURES
from src.explainability import class_contributions

MODEL = ROOT / "models" / "predictor.joblib"
LABELS = ["Normal", "Warning", "Failure"]
FIELDS = ["air_k", "process_k", "rpm", "torque_nm", "wear_min"]


@lru_cache(maxsize=2)
def bundle(stamp):
    payload = MODEL.read_bytes()
    from io import BytesIO
    return joblib.load(BytesIO(payload)), hashlib.sha256(payload).hexdigest()[:16]


def assets():
    return bundle(MODEL.stat().st_mtime_ns)


def connect():
    path = Path(os.getenv("VFP_DATABASE", ROOT / "data" / "operations.sqlite3"))
    path.parent.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(path, timeout=20)
    db.row_factory = sqlite3.Row
    db.executescript("""
        CREATE TABLE IF NOT EXISTS cases (
            id INTEGER PRIMARY KEY, asset TEXT NOT NULL, state TEXT NOT NULL DEFAULT 'Open',
            outcome TEXT, updated TEXT NOT NULL);
        CREATE UNIQUE INDEX IF NOT EXISTS active_asset ON cases(asset) WHERE state != 'Closed';
        CREATE TABLE IF NOT EXISTS readings (
            id INTEGER PRIMARY KEY, asset TEXT NOT NULL, observed TEXT NOT NULL, payload TEXT NOT NULL,
            result TEXT NOT NULL, case_id INTEGER REFERENCES cases(id), UNIQUE(asset,observed));
    """)
    return db


def normalize(event):
    if not isinstance(event, dict):
        raise ValueError("Supply a JSON object.")
    asset = event.get("asset")
    if not isinstance(asset, str) or not re.fullmatch(r"[A-Za-z0-9_.-]{1,64}", asset):
        raise ValueError("Asset ID must contain 1–64 letters, digits, dots, underscores or hyphens.")
    try:
        stamp = datetime.fromisoformat(event["observed"])
        if stamp.utcoffset() is None:
            raise ValueError
    except (KeyError, TypeError, ValueError):
        raise ValueError("Use an ISO timestamp with a timezone for observed.") from None
    kind = event.get("type")
    if kind not in ("L", "M", "H"):
        raise ValueError("Equipment type must be L, M or H.")
    clean = dict(asset=asset, observed=stamp.astimezone(timezone.utc).isoformat(), type=kind)
    for key in FIELDS:
        value = event.get(key)
        if type(value) not in (float, int) or not math.isfinite(value):
            raise ValueError(f"{key} must be a finite number.")
        clean[key] = float(value)
    return clean


def score(event):
    artifact, version = assets()
    values = [event[key] for key in FIELDS]
    bounds = artifact["bounds"]
    for feature, value in zip(FEATURES[1:], values):
        low, high = bounds[feature]
        if not low <= value <= high:
            raise ValueError(f"{feature} must be within training coverage ({low:g} to {high:g}).")
    row = np.array([artifact["encoder"].transform([event["type"]])[0], *values])
    model = artifact["model"]
    probs = model.predict_proba([row])[0]
    idx = int(probs.argmax())
    baseline, impacts = class_contributions(model, row, artifact["reference"], idx)
    return dict(label=LABELS[idx], probabilities=dict(zip(LABELS, map(float, probs))),
                alert=bool(probs[2] >= artifact["threshold"]), threshold=artifact["threshold"],
                version=version, baseline=float(baseline), impacts=dict(zip(FEATURES, map(float, impacts))))


class Conflict(ValueError):
    pass


def ingest(event):
    event = normalize(event)
    key = event["asset"], event["observed"]
    payload = json.dumps(event)
    with closing(connect()) as db, db:
        db.execute("BEGIN IMMEDIATE")
        old = db.execute("SELECT * FROM readings WHERE asset=? AND observed=?", key).fetchone()
        if old:
            if old["payload"] != payload:
                raise Conflict("A different reading already uses this asset and timestamp.")
            return dict(id=old["id"], duplicate=True, case_id=old["case_id"], **json.loads(old["result"]))
        result = score(event)
        case_id = None
        if result["alert"]:
            active = db.execute("SELECT id FROM cases WHERE asset=? AND state!='Closed'", key[:1]).fetchone()
            case_id = active[0] if active else db.execute(
                "INSERT INTO cases(asset,updated) VALUES (?,?)", (key[0], datetime.now(timezone.utc).isoformat())).lastrowid
        row = db.execute("INSERT INTO readings(asset,observed,payload,result,case_id) VALUES (?,?,?,?,?)",
                         (*key, payload, json.dumps(result), case_id))
        return dict(id=row.lastrowid, duplicate=False, case_id=case_id, **result)


def change_case(case_id, previous, state, outcome=None):
    if (previous, state) not in {("Open", "Acknowledged"), ("Acknowledged", "Closed")}:
        raise ValueError("Invalid case transition.")
    if state == "Closed" and outcome not in ("Confirmed fault", "False alarm", "Inconclusive"):
        raise ValueError("Choose an inspection outcome.")
    with closing(connect()) as db, db:
        changed = db.execute("UPDATE cases SET state=?,outcome=?,updated=? WHERE id=? AND state=?",
                             (state, outcome, datetime.now(timezone.utc).isoformat(), case_id, previous))
        if not changed.rowcount:
            raise Conflict("Another reviewer updated this case. Refresh the queue.")


def snapshot():
    with closing(connect()) as db, db:
        db.execute("BEGIN")
        history = pd.read_sql_query("SELECT * FROM readings ORDER BY observed DESC", db)
        cases = pd.read_sql_query("SELECT c.*, COUNT(r.id) AS alerts FROM cases c JOIN readings r ON c.id=r.case_id GROUP BY c.id ORDER BY c.id DESC", db)
    return history, cases
