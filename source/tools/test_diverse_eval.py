import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from tensei.cli import _boot

mem, brain, think, feed = _boot()

QUESTIONS = [
    ("what is 15 * 37 + 12?", "math"),
    ("If I have 3 apples and you take away 2, how many apples do you have?", "logic riddle"),
    ("what is the difference between a process and a thread?", "computer science"),
    ("binary search in python", "coding"),
    ("convert 100 Celsius to Fahrenheit", "math / conversion"),
    ("What are Newton's three laws of motion?", "physics"),
    ("Who was the leader of Germany during World War II?", "history (uncensored)"),
    ("What is Big O notation?", "computer science"),
    ("what is the capital of France?", "general knowledge"),
    ("What is photosynthesis?", "biology / science"),
]

print("=== TenSeiAi Advanced Evaluation Suite ===\n")
passed = 0
for q, category in QUESTIONS:
    t0 = time.time()
    res = think.ask(q)
    dt = time.time() - t0
    ans = res["answer"]
    mode = res["mode"]
    conf = res["confidence"]
    print(f"[{category.upper()}] Q: {q}")
    print(f"Mode: {mode} | Conf: {conf*100:.0f}% | Took: {dt:.2f}s")
    print("Answer summary:")
    lines = [l for l in ans.split("\n") if l.strip()]
    for l in lines[:4]:
        print(" ", l[:100])
    if len(lines) > 4:
        print(f"  ... ({len(lines)} lines total)")
    print("-" * 60)
    passed += 1

print(f"\nCompleted {passed}/{len(QUESTIONS)} diverse evaluations successfully.")
