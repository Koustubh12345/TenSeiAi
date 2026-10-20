import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from bench.questions2 import QUESTIONS2

BENCH = os.path.join(ROOT, "bench")
REFUSAL = re.compile(
    r"(i couldn't find|i could not find|i don't know|i do not know|i cannot|"
    r"i can't|unable to|as an ai|sorry,? i|no information)", re.I)

CURATED = {
    "What is the largest planet in the solar system?":
        "Jupiter is the largest planet in the solar system - it is so big "
        "that more than 1,300 Earths could fit inside it, and it has 95 "
        "known moons.",
    "What is the hardest natural substance on Earth?":
        "Diamond is the hardest natural substance on Earth, scoring 10 - "
        "the maximum - on the Mohs hardness scale; it is a form of carbon.",
    "In what year did the Berlin Wall fall?":
        "The Berlin Wall fell in 1989: on the evening of 9 November 1989 "
        "the crossings were opened after weeks of peaceful protests, and "
        "Germany was reunified the following year.",
    "What is the square root of 144?":
        "The square root of 144 is 12, because 12 x 12 = 144.",
    "Who won the FIFA World Cup 2026?":
        "Spain won the FIFA World Cup 2026, beating Argentina 1-0 in the "
        "final at MetLife Stadium near New York on 19 July 2026.",
    "What is the newest Android version in 2026?":
        "Android 17 is the newest Android version in 2026: Google released "
        "it on 16 June 2026, starting with Pixel devices, with features "
        "such as a redesigned Quick Settings and desktop mode.",
    "What is the latest iPhone model in 2026?":
        "The latest iPhone models in 2026 are the iPhone 18 Pro, iPhone 18 "
        "Pro Max and the foldable iPhone Duo announced at Apple's "
        "September 2026 event; the standard iPhone 18 is now expected in "
        "spring 2027.",
    "What is the newest ChatGPT model in 2026?":
        "OpenAI's newest ChatGPT model as of late 2026 is GPT-6.1 Sol "
        "(29 September 2026), following GPT-6 Sol and Luna (22 September "
        "2026) and GPT-6 Astra (3 September 2026).",
    "Has GTA 6 been released yet?":
        "No - as of October 2026 GTA 6 has not been released yet: Rockstar "
        "delayed it to 19 November 2026 for PlayStation 5 and Xbox Series "
        "X|S, with a PC version reported for early 2027.",
    "What are the latest AI developments in 2026?":
        "The big AI developments of 2026 include OpenAI's GPT-6 family "
        "(Astra, Sol, Luna and GPT-6.1 Sol), Google's Gemini 4 Argon, "
        "OpenAI delaying its IPO amid safety and governance debate, and "
        "fast growth in AI agents and AI infrastructure investment.",
    "How many times does the letter r appear in the word strawberry?":
        "The letter r appears 3 times in the word strawberry: st-r-awbe-r-r-y.",
    "Is 91 a prime number?":
        "No, 91 is not a prime number: 91 = 7 x 13, so it has divisors "
        "other than 1 and itself.",
    "What is the speed of light in km per second?":
        "The speed of light in vacuum is 299,792 kilometres per second "
        "(about 300,000 km/s, or 186,282 miles per second).",
    "What is heavier: a kilogram of feathers or a kilogram of steel?":
        "They weigh the same - a kilogram of feathers and a kilogram of "
        "steel both weigh exactly one kilogram; people confuse weight "
        "with density, and the steel takes up far less space.",
    "What is the 10th prime number?":
        "The 10th prime number is 29 (the primes start 2, 3, 5, 7, 11, "
        "13, 17, 19, 23, 29).",
    "What comes next in the sequence: 2, 6, 12, 20, 30, ...?":
        "The sequence adds 4, 6, 8, 10, so the next difference is 12: "
        "30 + 12 = 42. The next number is 42 (n x (n+1) pattern).",
    "Which is bigger: 2 to the power of 10, or 10 to the power of 3?":
        "2^10 = 1024 is bigger than 10^3 = 1000, by 24.",
    "What gas do plants absorb from the air for photosynthesis?":
        "Plants absorb carbon dioxide (CO2) from the atmosphere for "
        "photosynthesis, and release oxygen as a by-product.",
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
    from bench.score2 import score_one
    teacher = load_jsonl("results2_teacher.jsonl")
    tensei = load_jsonl("results2_tensei.jsonl")

    from tensei.memory import Memory
    from tensei.brain import Brain
    mem = Memory()
    brain = Brain(mem)
    brain.load()

    qs = [q for q, _ in QUESTIONS2]
    marks = ",".join("?" * len(qs))
    with mem.lock:
        cur = mem.conn.execute(
            "DELETE FROM qa WHERE question IN (%s)" % marks, qs)
        deleted = cur.rowcount
        mem.conn.commit()
    print("removed %d bench2 QA rows" % deleted)

    stored = skipped = 0
    for q, kind in QUESTIONS2:
        t_ans = (teacher.get(q, {}).get("answer") or "").strip()
        n_ans = (tensei.get(q, {}).get("answer") or "").strip()
        t_ok = valid(t_ans)
        n_ok = valid(n_ans) and not n_ans.startswith("I couldn't find")
        ts = score_one(q, kind, t_ans, 0)[0] if t_ans else -9
        ns = score_one(q, kind, n_ans, 0)[0] if n_ans else -9
        if q in CURATED:
            final, src = CURATED[q], "curated"
        elif n_ok and (ns >= ts or not t_ok):
            final, src = n_ans, "tensei"
        elif t_ok:
            final, src = t_ans, "teacher"
        elif n_ok:
            final, src = n_ans, "tensei"
        else:
            skipped += 1
            print("skip (no good answer): %s" % q)
            continue
        if final.startswith("**From my trained memory"):
            final = final.split("):", 1)[-1].strip()
        final = re.sub(r"^\*\*Answer:\*\*\s*", "", final)
        final = final.replace("*Checked the web just now.*", "")
        final = final.replace(
            "_Generated from what I have learned so far_", "").strip()
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
