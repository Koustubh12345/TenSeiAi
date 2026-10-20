"""Measure TenSeiAi's accuracy on GSM8K's test split (last 1319 rows of
data/hf/gsm8k.jsonl). Compares the bold number in the final answer with the
gold "#### N". Web search is disabled so the score reflects the model alone.

Usage: python3 tools/eval_gsm8k.py [limit] [--full]
       --full uses the think pipeline (memory + reasoning); default is the
       pure solver path.
"""
import json
import os
import re
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from tensei import websearch as ws
ws.web_search = lambda *a, **k: ([], "disabled-local-eval")

from tensei.reasoner import try_answer

NUM = re.compile(r"(-?[\d,]+(?:\.\d+)?)")


def gold_of(a):
    m = re.search(r"####\s*([\-\d,\.]+)\s*$", a)
    return m.group(1).replace(",", "") if m else None


def num_of(text):
    if not text:
        return None
    m = re.search(r"\*\*(-?[\d,]+(?:\.\d+)?)\*\*", text)
    if not m:
        m = NUM.search(text)
    return m.group(1).replace(",", "") if m else None


def close(a, b):
    try:
        fa, fb = float(a), float(b)
    except Exception:
        return a == b
    return abs(fa - fb) < 1e-6


def main():
    limit = 1319
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if args:
        limit = int(args[0])
    path = os.path.join(ROOT, "data", "hf", "gsm8k.jsonl")
    rows = []
    with open(path) as f:
        for line in f:
            rows.append(json.loads(line))
    test = rows[-1319:][:limit]
    ok = 0
    misses = []
    t0 = time.time()
    for i, row in enumerate(test):
        q = row["q"]
        res = try_answer(q)
        got = num_of(res["answer"]) if res else None
        want = gold_of(row["a"])
        if got is not None and want is not None and close(got, want):
            ok += 1
        elif len(misses) < 20:
            misses.append((i, want, got))
        if (i + 1) % 200 == 0:
            print("%d/%d acc=%.1f%% (%.0fs)" % (i + 1, len(test),
                  100.0 * ok / (i + 1), time.time() - t0), flush=True)
    print("GSM8K test: %d/%d = %.1f%% solver accuracy in %.0fs"
          % (ok, len(test), 100.0 * ok / len(test), time.time() - t0))
    for i, want, got in misses[:12]:
        print("  miss #%d gold=%s got=%s" % (i, want, got))


if __name__ == "__main__":
    main()
