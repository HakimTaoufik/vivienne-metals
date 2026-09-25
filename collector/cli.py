import argparse
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
from urllib.parse import urlsplit
from .adapters import parse, ParseError
from .http import Client
from .store import connect, previous, save, export, merge_snapshot

ROOT = Path(__file__).resolve().parents[1]


def now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def validate(quotes, spots, old):
    for q in quotes:
        prior = old.get(q["product"], {})
        for side in ("bid", "ask"):
            a, b = q[side], prior.get(side)
            if a and b and abs(a / b - 1) > .25:
                raise ParseError(f"Quarantined >25% jump: {q['product']} {side}")
    for s in spots:
        low, high = (10, 1000) if s["metal"] == "gold" else (.1, 100)
        if not low <= s["eurPerGram"] <= high:
            raise ParseError("Spot outside sanity bounds")


def collect(db_path, destination, sources=None, fetcher=None):
    sources = sources or json.loads((ROOT / "config/sources.json").read_text())
    db = connect(db_path)
    seed = ROOT / 'data/market.json'
    if seed.exists() and fetcher is None:
        merge_snapshot(db, json.loads(seed.read_text()))
    # Parallel across dealers, sequential within each host; requests remain modest.
    groups = {}
    for source in sources:
        groups.setdefault(urlsplit(source.get("fetchUrl", source["url"])).netloc, []).append(source)

    def fetch_group(group):
        client, results = Client(), []
        for source in group:
            try:
                body = fetcher(source) if fetcher else client.get(source.get("fetchUrl", source["url"]))
                observed = now()
                quotes, spots = parse(body, source, observed)
                results.append((source, quotes, spots, dict(id=source["id"], dealer=source["dealer"], url=source["url"],
                    status="ok", checkedAt=observed, count=len(quotes), sha256=hashlib.sha256(body.encode()).hexdigest())))
            except Exception as e:
                results.append((source, [], [], dict(id=source["id"], dealer=source["dealer"], url=source["url"], status="error",
                    checkedAt=now(), count=0, error=f"{type(e).__name__}: {str(e)[:180]}")))
        return results

    success = 0
    with ThreadPoolExecutor(max_workers=min(3, len(groups))) as pool:
        for results in pool.map(fetch_group, groups.values()):
            for source, quotes, spots, health in results:
                try:
                    if health["status"] == "ok":
                        old = previous(db, source["id"])
                        validate(quotes, spots, old)
                        if old and len(quotes) < max(1, len(old) * .6):
                            raise ParseError("Quarantined sudden loss of product coverage")
                        success += 1
                    save(db, quotes, spots, health)
                except ParseError as e:
                    health.update(status="error", count=0, error=str(e))
                    save(db, [], [], health)
                print(f"{source['id']}: {health['status']} ({health['count']} products)", flush=True)
    payload = export(db, destination, now())
    db.close()
    return payload, success


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=["collect"])
    parser.add_argument("--db", default="private/market.sqlite")
    parser.add_argument("--output", default="data/market.json")
    args = parser.parse_args()
    _, success = collect(args.db, args.output)
    if not success:
        raise SystemExit("All sources failed; no fresh observations")


if __name__ == "__main__":
    main()
