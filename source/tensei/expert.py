"""Expert layer: deterministic answers before the small neural model.

The old pipeline is a retrieval/composition system with a 10M-parameter
character model.  It is good at prose, but it loses to a 0.8B model on
math, code, puzzles and exact facts.  This layer gives TenSeiAi a fast,
auditable symbolic core for exactly those domains, then falls back to the
old memory/web pipeline for everything else.
"""


def try_answer(question, mem=None, debug=False):
    if not question or not question.strip():
        return None
    q = question.strip()

    # 1. Code: concept cards and short verified generators.
    try:
        from . import codecore
        r = codecore.solve(q)
        if r:
            return r
    except Exception as e:
        if debug:
            print("codecore error:", e)

    # 2. Writing: haiku, tips, emails, descriptions, summaries, rewrites.
    try:
        from . import writecore
        r = writecore.solve(q)
        if r:
            return r
    except Exception as e:
        if debug:
            print("writecore error:", e)

    # 3. Math: arithmetic, algebra, geometry, rates, percentages.
    try:
        from . import mathcore
        r = mathcore.solve(q)
        if r:
            return r
    except Exception as e:
        if debug:
            print("mathcore error:", e)

    # 4. Reasoning: classic puzzles and trick questions.
    try:
        from . import reasoncore
        r = reasoncore.solve(q)
        if r:
            return r
    except Exception as e:
        if debug:
            print("reasoncore error:", e)

    # 5. Facts: structured table, then BM25 memory + answer extraction.
    try:
        from . import factcore
        r = factcore.solve(q, mem, debug=debug)
        if r and r.get("confidence", 0) >= 0.62:
            return r
    except Exception as e:
        if debug:
            print("factcore error:", e)

    return None
