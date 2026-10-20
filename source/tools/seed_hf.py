"""Digest the downloaded HuggingFace slices (data/hf/*.jsonl) into TenSeiAi's
memory as learned Q&A pairs (evidence=teacher://hf-*), then optionally
retrain the brain. Run tools/fetch_hf.py first.

Usage: python3 tools/seed_hf.py [--no-train] [max_total_qa]
"""
import json
import os
import re
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
HF = os.path.join(ROOT, "data", "hf")

MAX_TOTAL_QA = 19800


def _steps_md(text):
    lines = [l.strip() for l in text.split("\n") if l.strip()]
    out = []
    for l in lines:
        l = re.sub(r"<<[^>]*>>", "", l).strip()
        l = re.sub(r"\s{2,}", " ", l)
        if l:
            out.append(l)
    if len(out) <= 1:
        return ""
    body = "\n".join("%d. %s" % (i + 1, s) for i, s in enumerate(out[:-1]))
    return "\n\n*How I reasoned it out:*\n" + body


def _gsm8k(row):
    a = row["a"]
    m = re.search(r"####\s*([\-\d,\.]+)\s*$", a)
    if not m:
        return None
    final = m.group(1).replace(",", "")
    steps = _steps_md(a[:m.start()])
    return "**Answer:** **%s**%s" % (final, steps)


def _sciq(row):
    sup = (row.get("support") or "").strip()
    sup = re.sub(r"\s{2,}", " ", sup)
    if len(sup) > 280:
        sup = sup[:280].rsplit(" ", 1)[0] + "..."
    body = "\n\n*Context:* %s" % sup if sup else ""
    return "**Answer:** **%s**%s" % ((row.get("a") or "").strip(), body)


def _codealpaca(row):
    code = row["a"].strip()
    return "**Answer:**\n\n```\n%s\n```" % code[:3000]


LOADERS = (("gsm8k.jsonl", _gsm8k, "gsm8k"), ("sciq.jsonl", _sciq, "sciq"),
           ("codealpaca.jsonl", _codealpaca, "codealpaca"))


def main():
    from tensei.memory import Memory
    from tensei.brain import Brain
    no_train = "--no-train" in sys.argv
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    max_total = int(args[0]) if args else MAX_TOTAL_QA

    mem = Memory()
    brain = Brain(mem)
    brain.load()
    emb = brain.embedder
    with mem.lock:
        n0 = mem.conn.execute("SELECT COUNT(*) FROM qa").fetchone()[0]
    have = set()
    with mem.lock:
        for (q,) in mem.conn.execute("SELECT question FROM qa"):
            have.add(q)
    budget = max_total - n0
    print("qa: %d, budget: %d" % (n0, budget), flush=True)
    total = 0
    for fname, fmt, src in LOADERS:
        path = os.path.join(HF, fname)
        if not os.path.exists(path):
            print("skip %s (missing)" % fname)
            continue
        n = 0
        t0 = time.time()
        with open(path) as f:
            for line in f:
                if total >= budget:
                    break
                try:
                    row = json.loads(line)
                except Exception:
                    continue
                try:
                    ans = fmt(row)
                except Exception:
                    ans = None
                if not ans:
                    continue
                q = row["q"].strip()
                if q in have:
                    continue
                have.add(q)
                mem.add_qa(q, ans,
                           [{"url": "teacher://hf-%s" % src,
                             "title": "HuggingFace %s (public training data)" % src}],
                           emb.encode(q), emb0=emb.base_encode(q))
                n += 1
                total += 1
                if total % 500 == 0:
                    print("  %s: +%d (%.0fs)" % (src, n, time.time() - t0),
                          flush=True)
        print("%s: ingested %d in %.0fs" % (src, n, time.time() - t0), flush=True)
    with mem.lock:
        n1 = mem.conn.execute("SELECT COUNT(*) FROM qa").fetchone()[0]
    print("qa rows: %d -> %d" % (n0, n1))
    if not no_train:
        t0 = time.time()
        print("retraining brain...", flush=True)
        brain.train_all(log=lambda s: print(s, flush=True))
        print("train_all done in %.0fs" % (time.time() - t0))
    mem.close()
    print("DONE")


if __name__ == "__main__":
    main()
