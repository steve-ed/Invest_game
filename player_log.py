"""Read/write player results to the HF dataset steve-e/realestgame-players."""
import base64, csv, io, json, os, ssl, urllib.request
from datetime import datetime

DATASET_REPO = "steve-e/realestgame-players"
_CSV_URL     = f"https://huggingface.co/datasets/{DATASET_REPO}/resolve/main/players.csv"
_COMMIT_URL  = f"https://huggingface.co/api/datasets/{DATASET_REPO}/commit/main"
_FIELDS      = ["name", "score", "rank", "era", "start_year", "date"]
_CTX         = ssl._create_unverified_context()


def _read_rows(token=""):
    try:
        req = urllib.request.Request(_CSV_URL)
        if token:
            req.add_header("Authorization", f"Bearer {token}")
            req.add_header("Cache-Control", "no-cache")
        with urllib.request.urlopen(req, context=_CTX) as r:
            content = r.read().decode("utf-8").strip()
        try:
            content = base64.b64decode(content).decode("utf-8")
        except Exception:
            pass
        return list(csv.DictReader(io.StringIO(content)))
    except Exception:
        return []


def append_result(name, score, rank, era, start_year):
    token = os.environ.get("HF_TOKEN", "")
    if not token:
        print("HF_TOKEN not set — skipping player log", flush=True)
        return
    try:
        rows = _read_rows(token)
        rows.append({
            "name":       name,
            "score":      int(score),
            "rank":       rank,
            "era":        era,
            "start_year": start_year,
            "date":       datetime.utcnow().strftime("%Y-%m-%d"),
        })
        buf = io.StringIO()
        writer = csv.DictWriter(buf, fieldnames=_FIELDS)
        writer.writeheader()
        writer.writerows(rows)

        payload = json.dumps({
            "summary": f"score: {name} R{rank} £{int(score):,}",
            "files":   [{"path": "players.csv",
                         "content": base64.b64encode(buf.getvalue().encode()).decode()}],
        }).encode()
        req = urllib.request.Request(_COMMIT_URL, data=payload, headers={
            "Authorization": f"Bearer {token}",
            "Content-Type":  "application/json",
        })
        with urllib.request.urlopen(req, context=_CTX) as r:
            r.read()
        print(f"Player log updated: {name} R{rank} £{int(score):,}", flush=True)
    except Exception as e:
        print(f"Player log write failed: {e}", flush=True)


def get_all():
    """Return all rows as a list of dicts, newest first."""
    rows = _read_rows()
    rows.reverse()
    return rows
