"""One-time maintenance: stored Q&A answers that were cut mid-sentence by the
original distiller are trimmed back to end on a complete sentence/clause,
so the engine never recites a half sentence.  Run once against a home's DB:
    python tools_repair_truncated_qa.py <path/to/data/tensei.db>
"""
import re
import shutil
import sqlite3
import sys

TERM = re.compile(r"""[.!?*`"')\]}:\u2026\u00bb\u201d]\s*$""")
SENT_END = re.compile(r"[.!?][\"')\]]?(?=\s|$)")


def trim_to_sentence(a):
    a = a.strip()
    ends = [m.end() for m in SENT_END.finditer(a)]
    if ends:
        cut = ends[-1]
        if cut >= len(a) * 0.5:
            return a[:cut].rstrip()
    last_comma = a.rfind(", ")
    if last_comma >= len(a) * 0.5:
        return a[:last_comma].rstrip() + "."
    last_space = a.rfind(" ")
    if last_space > 0:
        return a[:last_space].rstrip() + "\u2026"
    return a


def main(path):
    shutil.copy(path, path + ".bak-trunc")
    c = sqlite3.connect(path)
    rows = c.execute("SELECT id, answer FROM qa WHERE answer IS NOT NULL").fetchall()
    fixed = 0
    for rid, a in rows:
        a = (a or "").strip()
        if len(a) > 120 and not TERM.search(a):
            new = trim_to_sentence(a)
            if new and new != a:
                c.execute("UPDATE qa SET answer=? WHERE id=?", (new, rid))
                fixed += 1
    c.commit()
    print("trimmed %d of %d rows (backup: %s.bak-trunc)" % (fixed, len(rows), path))
    c.close()


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "data/tensei.db")
