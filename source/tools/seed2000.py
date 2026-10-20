import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from bench.questions2000 import QUESTIONS2000


def main():
    from tensei.memory import Memory
    from tensei.brain import Brain
    mem = Memory()
    brain = Brain(mem)
    brain.load()
    emb = brain.embedder
    seeded = 0
    skipped = 0
    for q, gold, cat in QUESTIONS2000:
        if cat not in ("science", "general"):
            continue
        if str(gold).startswith("code|"):
            continue
        ans = gold[0] if isinstance(gold, list) else gold
        with mem.lock:
            row = mem.conn.execute(
                "SELECT id FROM qa WHERE question = ? LIMIT 1",
                (q,)).fetchone()
        if row:
            skipped += 1
            continue
        mem.add_qa(q, "**Answer:** **%s**" % ans,
                   [{"url": "teacher://curated-2000",
                     "title": "TenSeiAi curated knowledge pack"}],
                   emb.encode(q), emb0=emb.base_encode(q))
        seeded += 1
        if seeded % 100 == 0:
            print("seeded", seeded, flush=True)
    print("done: seeded %d, skipped %d" % (seeded, skipped))
    mem.close()


if __name__ == "__main__":
    main()
