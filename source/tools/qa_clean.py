"""Clean TenSeiAi's memory after months of autonomous learning.

Two jobs:

1. QA hygiene - answers the engine composed for itself ("mode" memory/web)
   used to be replayed as learned facts even when they were off-topic
   (e.g. "Why do we dream?" remembered a passage about sky scattering).
   A composed answer is kept only if it actually talks about the subject
   words of its own question; verified packs (teacher://, facts) and
   reasoning/code answers are never touched.

2. Topic hygiene - the autonomous feed accumulated junk topics (single
   stop-words, spam phrases). They are removed so research focuses on
   real subjects.

Usage:
    python tools/qa_clean.py            # dry run (report only)
    python tools/qa_clean.py --apply    # actually delete
"""
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from tensei import util  # noqa: E402
from tensei.memory import Memory  # noqa: E402

JUNK_TOPIC_RE = re.compile(
    r"^(?:you|your|yours|hello|hi|hey|give|basic|nigga|fuck|sex|porn|xxx|"
    r"ass|dick|pussy|boobs|nude|cam|hot|free|download|click|here|now|"
    r"the|and|for|with|how|what|why|who|when|where|which|this|that|it|"
    r"me|my|we|us|they|them|he|she|his|her|its|or|if|but|not|no|yes|"
    r"a|an|is|are|was|were|be|been|do|does|did|can|could|will|would|"
    r"should|may|might|must|make|know|thing|stuff|stuff$|test|test1)$",
    re.I)

# Evidence prefixes that mark an answer as verified (packs, reasoners, code
# engine). Anything else was composed by an older, unreliable engine build and
# is treated as unverified.
TRUST_PREFIXES = ("teacher://", "reasoner://", "code://", "learned://",
                  "facts://", "tensei://", "system://")


def entry_ok(question, answer):
    qw = [w for w in util.content_words(question or "") if len(w) > 3]
    if not qw:
        return True
    aw = set(util.content_words(answer or ""))
    hit = sum(1 for w in qw if w in aw)
    return hit / float(len(qw)) >= 0.4


def main():
    apply = "--apply" in sys.argv
    purge = "--purge-unverified" in sys.argv
    mem = Memory()
    rows = mem.conn.execute(
        "SELECT id,question,answer,evidence,COALESCE(mode,'') FROM qa"
    ).fetchall()
    print("total qa rows:", len(rows))

    kill = []
    for rid, q, a, ev, mode in rows:
        ev_s = ev or ""
        trusted = any(t in ev_s for t in TRUST_PREFIXES)
        if trusted:
            continue
        if purge and mode in ("", "memory", "web"):
            kill.append((rid, q, a, "unverified engine-composed legacy answer"))
            continue
        if mode in ("memory", "web", ""):
            if not ev_s or ev_s == "[]":
                kill.append((rid, q, a, "no sources"))
                continue
            if not entry_ok(q, a):
                kill.append((rid, q, a, "answer off-topic for its question"))

    print("poisoned / ungrounded qa rows to remove:", len(kill))
    for rid, q, a, why in kill[:15]:
        print("   #%s %-52s | %s" % (rid, (q or "")[:52], why))

    topics = mem.conn.execute("SELECT name FROM topics").fetchall()
    killt = [t[0] for t in topics if JUNK_TOPIC_RE.match((t[0] or "").strip())]
    print("junk topics to remove:", len(killt), killt[:20])

    if not apply:
        print("\n(dry run - rerun with --apply to delete)")
        return 0

    with mem.lock:
        for rid, _, _, _ in kill:
            mem.conn.execute("DELETE FROM qa WHERE id=?", (rid,))
        for name in killt:
            mem.conn.execute("DELETE FROM topics WHERE name=?", (name,))
        mem.conn.commit()
        mem._qa_base_cache = None
    print("\nremoved %d qa rows and %d topics" % (len(kill), len(killt)))
    print("memory now:", mem.stats())
    return 0


if __name__ == "__main__":
    sys.exit(main())
