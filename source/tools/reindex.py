"""Re-embed the whole memory with the current brain weights.

Retraining updates the learned projection `W`, so vectors stored earlier live
in an older space - ranking then compares a fresh query against stale passage
vectors and quality drops. This recomputes `docs.emb` (and `qa.emb`) from the
text with the live embedder. `qa.emb0` (the stable hash space) is untouched.

Usage:
    python tools/reindex.py            # reindex documents + questions
    python tools/reindex.py docs       # documents only
"""
import os
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from tensei import util  # noqa: E402
from tensei.memory import Memory  # noqa: E402
from tensei.brain import Brain  # noqa: E402


def main():
    which = sys.argv[1] if len(sys.argv) > 1 else "all"
    mem = Memory()
    brain = Brain(mem)
    t0 = time.time()
    if which in ("all", "docs"):
        rows = mem.conn.execute("SELECT id,passage FROM docs").fetchall()
        n = 0
        with mem.lock:
            for rid, passage in rows:
                emb = brain.embedder.encode(passage or "")
                if emb:
                    mem.conn.execute("UPDATE docs SET emb=? WHERE id=?",
                                     (util.pack_f32(emb), rid))
                    n += 1
            mem.conn.commit()
        mem._dm_cache = None
        print("reindexed %d/%d passages in %.1fs" % (n, len(rows), time.time() - t0))
    if which in ("all", "qa"):
        rows = mem.conn.execute("SELECT id,question FROM qa").fetchall()
        n = 0
        with mem.lock:
            for rid, q in rows:
                emb = brain.embedder.encode(q or "")
                if emb:
                    mem.conn.execute("UPDATE qa SET emb=? WHERE id=?",
                                     (util.pack_f32(emb), rid))
                    n += 1
            mem.conn.commit()
        mem._qa_base_cache = None
        print("reindexed %d/%d questions in %.1fs" % (n, len(rows), time.time() - t0))
    print("done in %.1fs" % (time.time() - t0))
    return 0


if __name__ == "__main__":
    sys.exit(main())
