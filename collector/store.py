"""Transactional, append-only observation archive; idempotent snapshot imports."""
import json
import sqlite3
from pathlib import Path


def connect(path):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(path)
    db.execute("PRAGMA journal_mode=WAL")
    db.executescript("""
    CREATE TABLE IF NOT EXISTS observations (
      source TEXT NOT NULL, product TEXT NOT NULL, observed TEXT NOT NULL,
      payload TEXT NOT NULL, PRIMARY KEY(source, product, observed));
    CREATE TABLE IF NOT EXISTS spots (
      source TEXT NOT NULL, metal TEXT NOT NULL, observed TEXT NOT NULL,
      payload TEXT NOT NULL, PRIMARY KEY(source, metal, observed));
    CREATE TABLE IF NOT EXISTS health (source TEXT PRIMARY KEY, payload TEXT NOT NULL);
    """)
    return db


def previous(db, source):
    rows = db.execute("SELECT payload FROM observations WHERE source=? ORDER BY observed", (source,))
    return {q["product"]: q for (raw,) in rows for q in [json.loads(raw)]}


def save(db, quotes, spots, health):
    with db:
        for q in quotes:
            db.execute("INSERT OR IGNORE INTO observations VALUES(?,?,?,?)", (q["source"], q["product"], q["observedAt"], json.dumps(q)))
        for s in spots:
            db.execute("INSERT OR IGNORE INTO spots VALUES(?,?,?,?)", (s["source"], s["metal"], s["observedAt"], json.dumps(s)))
        db.execute("INSERT OR REPLACE INTO health VALUES(?,?)", (health["id"], json.dumps(health)))


def merge_snapshot(db, snapshot):
    """Import audited observations without refreshing their time or source health.

    Also runs on existing databases: a newly added dealer may be temporarily
    inaccessible from the scheduled runner. INSERT OR IGNORE makes replays safe.
    """
    quotes = snapshot.get("history", []) + snapshot.get("quotes", [])
    spots = snapshot.get("spotHistory", []) + snapshot.get("spots", [])
    for health in snapshot.get("health", []):
        current = db.execute("SELECT payload FROM health WHERE source=?", (health["id"],)).fetchone()
        save(db, [q for q in quotes if q["source"] == health["id"]],
             [s for s in spots if s["source"] == health["id"]],
             json.loads(current[0]) if current else health)


def atomic_json(path, value):
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    temp = p.with_suffix(p.suffix + ".tmp")
    temp.write_text(json.dumps(value, ensure_ascii=False, separators=(",", ":")) + "\n")
    temp.replace(p)


def export(db, destination, generated):
    # Daily last observation for modeling; the latest seven days retain intraday detail.
    from datetime import datetime, timedelta
    from zoneinfo import ZoneInfo
    paris = ZoneInfo("Europe/Paris")

    def trading_day(stamp):
        return datetime.fromisoformat(stamp.replace("Z", "+00:00")).astimezone(paris).date().isoformat()

    cutoff = (datetime.fromisoformat(generated.replace("Z", "+00:00")) - timedelta(days=7)).isoformat()
    all_quotes = [json.loads(r[0]) for r in db.execute("SELECT payload FROM observations ORDER BY observed")]
    all_spots = [json.loads(r[0]) for r in db.execute("SELECT payload FROM spots ORDER BY observed")]
    from bisect import bisect_right
    products = {p['id']: p for p in json.loads((Path(__file__).resolve().parents[1] / 'config/products.json').read_text())}
    indexed = {}
    for s in all_spots:
        indexed.setdefault(s['metal'], []).append(s)
    times = {m: [datetime.fromisoformat(s['observedAt'].replace('Z', '+00:00')).timestamp() for s in ss] for m, ss in indexed.items()}
    for q in all_quotes:
        p = products[q['product']]
        ts = datetime.fromisoformat(q.get('publishedAt',q['observedAt']).replace('Z', '+00:00')).timestamp()
        i = bisect_right(times.get(p['metal'], []), ts) - 1
        if i >= 0 and ts - times[p['metal']][i] <= 21600:
            s = indexed[p['metal']][i]
            q['meltCents'] = round(s['eurPerGram'] * p['fineGrams'] * 100)
            q['spotObservedAt'] = s['observedAt']
            q['spotSource'] = s['source']
    latest, daily, recent = {}, {}, []
    for q in all_quotes:
        latest[(q["source"], q["product"])] = q
        daily[(q["source"], q["product"], trading_day(q.get("publishedAt",q["observedAt"])))] = q
        if q["observedAt"] >= cutoff:
            recent.append(q)
    spot_latest, spot_daily = {}, {}
    for s in all_spots:
        spot_latest[s["metal"]] = s
        spot_daily[(s["metal"], trading_day(s["observedAt"]))] = s
    payload = {"schemaVersion": 1, "generatedAt": generated, "currency": "EUR",
               "quotes": list(latest.values()), "spots": list(spot_latest.values()),
               "history": list(daily.values()), "spotHistory": list(spot_daily.values()),
               "intraday": recent, "health": [json.loads(r[0]) for r in db.execute("SELECT payload FROM health ORDER BY source")]}
    atomic_json(destination, payload)
    return payload
