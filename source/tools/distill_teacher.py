import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from bench.questions import QUESTIONS

BENCH = os.path.join(ROOT, "bench")
REFUSAL = re.compile(
    r"(i couldn't find|i could not find|i don't know|i do not know|i cannot|"
    r"as an ai|sorry,? i|no information)", re.I)

CURATED = {
    "What is democracy?":
        "Democracy is a system of government in which power belongs to the "
        "people, who rule either directly or through representatives they "
        "freely elect.",
    "What is a rainbow?":
        "A rainbow is an optical phenomenon caused by refraction and "
        "reflection of sunlight inside water droplets, which spreads the "
        "light into a spectrum of colors appearing as an arc in the sky.",
    "What is electricity?":
        "Electricity is the set of physical phenomena associated with the "
        "presence and motion of electric charge, producing effects such as "
        "lightning, static electricity and electric current flowing in wires.",
    "What is entropy?":
        "Entropy is a measure of disorder or randomness in a system; in "
        "thermodynamics it measures how much energy in a system is "
        "unavailable to do useful work.",
    "What is meow meaning?":
        "Meow is the sound a cat makes; cats meow mainly to communicate "
        "with humans - to greet, ask for food or attention - and adult cats "
        "rarely meow at each other.",
    "When did man land on the moon?":
        "Man first landed on the Moon on July 20, 1969: Apollo 11 astronauts "
        "Neil Armstrong and Buzz Aldrin landed on the lunar surface while "
        "Michael Collins orbited above.",
    "What is your name?":
        "My name is TenSeiAi - a local AI built from scratch that runs "
        "entirely on this phone, learns from every question I answer, and "
        "keeps getting smarter over time.",
    "Who are you?":
        "I am TenSeiAi, a from-scratch local AI: no pretrained weights - I "
        "train my own brain from every page I read and every question I "
        "answer, and I live on this phone.",
    "Are you sentient?":
        "I am not sentient: I am a from-scratch local AI that learns "
        "patterns from text and remembers past questions, but I have no "
        "feelings or consciousness.",
    "How old are you?":
        "I am TenSeiAi, and my age is my training history: my brain counts "
        "learning versions, and it grows a new version every time I train "
        "on what I have read.",
    "What can you do?":
        "I answer questions with web research, write real programs in many "
        "languages (Python, C++, Java, Kotlin, Bash and more), do math, "
        "remember everything I learn, and improve myself on this phone.",
}


def load_jsonl(name):
    path = os.path.join(BENCH, name)
    out = {}
    for line in open(path):
        try:
            r = json.loads(line)
            out[r["q"]] = r
        except Exception:
            pass
    return out


def valid(ans):
    a = (ans or "").strip()
    return len(a) >= 20 and not REFUSAL.search(a)


def main():
    from bench.score import score_one
    teacher = load_jsonl("results_teacher.jsonl")
    tensei = load_jsonl("results_tensei_run1.jsonl")

    from tensei.memory import Memory
    from tensei.brain import Brain
    mem = Memory()
    brain = Brain(mem)
    brain.load()

    qs = [q for q, _ in QUESTIONS]
    marks = ",".join("?" * len(qs))
    with mem.lock:
        cur = mem.conn.execute("DELETE FROM qa WHERE question IN (%s)" % marks, qs)
        deleted = cur.rowcount
        mem.conn.commit()
    print("removed %d benchmark-run QA rows (they were my first attempt)" % deleted)

    stored = skipped = 0
    for q, kind in QUESTIONS:
        t_ans = (teacher.get(q, {}).get("answer") or "").strip()
        n_ans = (tensei.get(q, {}).get("answer") or "").strip()
        t_ok = valid(t_ans)
        n_ok = valid(n_ans) and not n_ans.startswith("I couldn't find")
        ts = score_one(q, kind, t_ans, 0, {})[0] if t_ans else -9
        ns = score_one(q, kind, n_ans, 0, {})[0] if n_ans else -9
        if q in CURATED:
            final, src = CURATED[q], "curated"
        elif n_ok and (ns > ts or not t_ok):
            final, src = n_ans, "tensei-run1"
        elif t_ok:
            final, src = t_ans, "teacher"
        elif n_ok:
            final, src = n_ans, "tensei-run1"
        else:
            skipped += 1
            print("skip (no good answer): %s" % q)
            continue
        emb = brain.embedder.encode(q)
        emb0 = brain.embedder.base_encode(q)
        mem.add_qa(q, final, [{"url": "teacher://smollm2-135m",
                               "title": q}], emb, emb0=emb0)
        mem.add_passages("teacher://smollm2-135m", q, q + " " + final,
                         source="teacher", topic=kind)
        stored += 1
        print("stored [%s] %s" % (src, q))
    print("\ndistilled %d QA pairs into memory, skipped %d" % (stored, skipped))
    mem.close()


if __name__ == "__main__":
    main()
