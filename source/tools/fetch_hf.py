"""Download high-value slices of public datasets (GSM8K, SciQ, CodeAlpaca)
into data/hf/*.jsonl so tools/seed_hf.py can digest them into TenSeiAi.

FineWeb / Dolma / The Stack are terabyte-scale (they need GPU clusters and
weeks of compute); they cannot be trained on a phone. These smaller datasets
fit the model's learning system and target the same skills: math reasoning,
science facts, coding instructions.
"""
import json
import os
import random
import sys
import time
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "data", "hf")

ROWS_API = ("https://datasets-server.huggingface.co/rows?dataset=%s"
            "&config=%s&split=%s&offset=%d&length=%d")


def _get(url, tries=8):
    import urllib.error
    for i in range(tries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "TenSeiAi/1.0"})
            with urllib.request.urlopen(req, timeout=60) as r:
                return r.read()
        except urllib.error.HTTPError as e:
            if i == tries - 1:
                raise
            wait = 30 if e.code == 429 else 4
            time.sleep(wait * (1 + i // 2))
        except Exception:
            if i == tries - 1:
                raise
            time.sleep(3 * (i + 1))


def _rows(dataset, config, split, count, cap=None):
    out = []
    offset = 0
    while len(out) < count:
        want = min(100, count - len(out))
        url = ROWS_API % (dataset, config, split, offset, want)
        data = json.loads(_get(url).decode("utf-8"))
        rows = data.get("rows", [])
        if not rows:
            break
        for r in rows:
            out.append(r["row"])
        offset += len(rows)
        time.sleep(0.3)
        print("  %s/%s %d/%d" % (dataset, split, len(out), count), flush=True)
        if cap and len(out) >= cap:
            break
    return out[:count]


def fetch_gsm8k():
    path = os.path.join(OUT, "gsm8k.jsonl")
    count = 0
    with open(path, "w", buffering=1) as f:
        for split, n in (("train", 7473), ("test", 1319)):
            for row in _rows("openai/gsm8k", "main", split, n):
                q = (row.get("question") or "").strip()
                a = (row.get("answer") or "").strip()
                if not q or not a:
                    continue
                f.write(json.dumps({"q": q, "a": a, "src": "gsm8k"}) + "\n")
                f.flush()
                count += 1
    print("gsm8k: %d rows -> %s" % (count, path))


def fetch_sciq():
    path = os.path.join(OUT, "sciq.jsonl")
    count = 0
    with open(path, "w", buffering=1) as f:
        for row in _rows("allenai/sciq", "default", "train", 4000):
            q = (row.get("question") or "").strip()
            a = (row.get("correct_answer") or "").strip()
            sup = (row.get("support") or "").strip()
            if not q or not a:
                continue
            f.write(json.dumps({"q": q, "a": a, "support": sup,
                                "src": "sciq"}) + "\n")
            f.flush()
            count += 1
    print("sciq: %d rows -> %s" % (count, path))


def fetch_codealpaca():
    path = os.path.join(OUT, "codealpaca.jsonl")
    url = ("https://huggingface.co/datasets/sahil2801/CodeAlpaca-20k"
           "/resolve/main/code_alpaca_20k.json")
    raw = _get(url)
    data = json.loads(raw.decode("utf-8"))
    rng = random.Random(41)
    rng.shuffle(data)
    count = 0
    with open(path, "w", buffering=1) as f:
        for row in data[:5000]:
            instr = (row.get("instruction") or "").strip()
            inp = (row.get("input") or "").strip()
            out = (row.get("output") or "").strip()
            if not instr or not out:
                continue
            q = instr if not inp else instr + "\n" + inp
            f.write(json.dumps({"q": q, "a": out, "src": "codealpaca"}) + "\n")
            count += 1
    print("codealpaca: %d rows -> %s" % (count, path))


def main():
    os.makedirs(OUT, exist_ok=True)
    which = sys.argv[1:] or ["gsm8k", "sciq", "codealpaca"]
    for name in which:
        print("fetching %s..." % name, flush=True)
        {"gsm8k": fetch_gsm8k, "sciq": fetch_sciq,
         "codealpaca": fetch_codealpaca}[name]()


if __name__ == "__main__":
    main()
