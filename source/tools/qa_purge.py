"""Purge known-broken rows from older knowledge packs.

The first distillation pack (teacher://smollm2-135m) contains a few scraped
page fragments, apologies and meta-answers that were stored as if they were
facts. They are trusted during recall, so they win against good answers -
delete them and let the curated facts pack refill those questions.

Usage:
    python tools/qa_purge.py            # dry run
    python tools/qa_purge.py --apply
"""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from tensei.memory import Memory  # noqa: E402

BAD_IDS = [
    277,    # "What is quantum computing?" -> scraped page fragment
    294,    # "When was ww2?" -> apology, no answer
    299,    # WhatsApp -> wrong content
    300,    # Google founded -> no date
    307,    # telephone invented -> vague "late 1800s"
    312,    # cold war -> confused
    314,    # India PM -> non-answer
    320,    # founded Microsoft -> off topic
    323,    # created Pokemon -> off topic
    328,    # invented the internet -> off topic
    329,    # how does a computer work -> scraped fragment
    337,    # car engine -> scraped fragment
    339,    # 5g -> scraped fragment
    341,    # GPS -> "Photo credit" fragment
    352,    # calculator -> wrong code
    354,    # 2+2 -> rambling
    357,    # 89-45 -> nonsense
    358,    # 12*12 -> rambling
    359,    # "hi" stored as knowledge
    360,    # "Tell me a joke" -> not a joke
    368,    # "Tell me something interesting" -> scraped fragment
    370, 371, 372, 374,   # meta answers "From my trained memory..."
    399,    # Hamlet -> fragment
    409,    # OpenAI CEO -> fragment
    410,    # train distance -> no answer
    412,    # 17*23 -> rambling
    414,    # x+5=12 -> wrong (talks about 144)
    416,    # strawberry letters -> wrong
    19008,  # Two Sum -> wrong answer
]

BAD_PATTERNS = [
    "%From my trained memory%",
    "%I'm sorry for any confusion%",
    "%as a chatbot, I don't have%",
    "%Photo credit%",
]


def main():
    apply = "--apply" in sys.argv
    mem = Memory()
    kill = []
    for rid in BAD_IDS:
        row = mem.conn.execute(
            "SELECT id,question FROM qa WHERE id=?", (rid,)).fetchone()
        if row:
            kill.append((row[0], row[1], "listed as broken"))
    for pat in BAD_PATTERNS:
        for rid, q in mem.conn.execute(
                "SELECT id,question FROM qa WHERE answer LIKE ?", (pat,)):
            if rid not in [k[0] for k in kill]:
                kill.append((rid, q, "matches broken pattern " + pat))
    print("rows to purge:", len(kill))
    for rid, q, why in kill[:40]:
        print("   #%-6s %-50s | %s" % (rid, (q or "")[:50], why))
    if not apply:
        print("(dry run - rerun with --apply to delete)")
        return 0
    with mem.lock:
        for rid, _, _ in kill:
            mem.conn.execute("DELETE FROM qa WHERE id=?", (rid,))
        mem.conn.commit()
        mem._qa_base_cache = None
    print("removed", len(kill), "rows")
    print("memory now:", mem.stats())
    return 0


if __name__ == "__main__":
    sys.exit(main())
