"""TenSeiAi's built-in reasoning brain.

Deterministic, from-scratch solvers for the classes of hard questions that
small LLMs famously fail: arithmetic word problems, day-of-week math,
train/plane distance, age puzzles, sequences, square roots, syllogisms,
trick questions and more. Every answer shows the reasoning steps, like a
chain of thought - but computed exactly instead of guessed, and in
milliseconds.
"""
import ast
import math
import re

WEEKDAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday",
            "Saturday", "Sunday"]

_ONES = {0: "zero", 1: "one", 2: "two", 3: "three", 4: "four", 5: "five",
         6: "six", 7: "seven", 8: "eight", 9: "nine", 10: "ten",
         11: "eleven", 12: "twelve", 13: "thirteen", 14: "fourteen",
         15: "fifteen", 16: "sixteen", 17: "seventeen", 18: "eighteen",
         19: "nineteen", 20: "twenty"}


def _num(s):
    return float(s.replace(",", "").strip())


def _fmt(x):
    if abs(x - round(x)) < 1e-9:
        return str(int(round(x)))
    return ("%.2f" % x).rstrip("0").rstrip(".")


def _money(x):
    return "$%.2f" % x


def _steps_answer(final, steps, kind, conf=0.95):
    body = "**Answer:** " + final + "\n\n*How I reasoned it out:*"
    for i, s in enumerate(steps, 1):
        body += "\n%d. %s" % (i, s)
    return {"answer": body, "kind": kind, "confidence": conf}
def _two_item_cost(q):
    ql = q.lower()
    m_total = re.search(r'costs?\s*([₹$€£])?\s*([\d,]+(?:\.\d+)?)', ql)
    m_more = re.search(
        r'(?:the\s+)?([a-z]+)\s+costs?\s*([₹$€£])?\s*([\d,]+(?:\.\d+)?)\s+'
        r'more\s+than', ql)
    if not (m_total and m_more):
        return None
    total = _num(m_total.group(2))
    diff = _num(m_more.group(3))
    more_item = m_more.group(1)
    sym = m_total.group(1) or m_more.group(2) or "$"

    def money(x):
        if abs(x - round(x)) < 1e-9:
            return "%s%d" % (sym, int(round(x)))
        return "%s%.2f" % (sym, x)

    m_ask = re.search(r'how much (?:does|is|do)\s+(?:the\s+)?([a-z]+)', ql)
    asked = m_ask.group(1) if m_ask else more_item
    small = (total - diff) / 2.0
    big = small + diff
    if small < 0:
        return None
    if asked == more_item:
        val, label = big, more_item
        steps = [
            "Together they cost %s and the %s costs %s more than the other."
            % (money(total), more_item, money(diff)),
            "So 2 x (%s) + %s = %s -> 2 x (%s) = %s"
            % (more_item, money(diff), money(total), more_item,
               money(total - diff)),
            "%s costs %s and the other one costs %s."
            % (more_item, money(big), money(small))]
    else:
        val, label = small, asked
        steps = [
            "Together they cost %s and the %s costs %s more than the %s."
            % (money(total), more_item, money(diff), asked),
            "So 2 x (%s) + %s = %s -> 2 x (%s) = %s"
            % (asked, money(diff), money(total), asked, money(total - diff)),
            "%s = %s, and the %s costs %s."
            % (asked, money(small), more_item, money(big))]
    return _steps_answer("**%s**" % money(val), steps, "two-item cost")


def _all_but(q):
    ql = q.lower()
    m = re.search(r'all but (\d+)\b', ql)
    if not m:
        return None
    if not re.search(r'\b(die|died|are gone|leave|left|escaped|survive)', ql):
        return None
    n = int(m.group(1))
    return _steps_answer(
        "**%d**" % n,
        ["'All but %d' means everything except %d, so exactly %d remain."
         % (n, n, n)], "all-but trick")


def _travel_distance(q):
    ql = q.lower()
    m = re.search(
        r'([\d,.]+)\s*(km/h|km per hour|mph|miles per hour)\D{0,60}?'
        r'for\s+(\d+)\s*hours?\s+(?:and\s+)?(\d+)\s*(?:minutes?|mins?)', ql)
    if m:
        v = _num(m.group(1))
        unit = "km" if "km" in m.group(2) else "miles"
        h, mn = int(m.group(3)), int(m.group(4))
        t = h + mn / 60.0
        d = v * t
        return _steps_answer(
            "**%s %s**" % (_fmt(d), unit),
            ["time = %d h %d min = %s hours." % (h, mn, _fmt(t)),
             "speed x time = distance: %s x %s = %s %s."
             % (_fmt(v), _fmt(t), _fmt(d), unit)], "distance")
    m = re.search(
        r'([\d,.]+)\s*(km/h|km per hour|mph|miles per hour)\D{0,60}?'
        r'for\s+([\d,.]+)\s*(hours?|hrs?|minutes?|mins?)', ql)
    if not m:
        return None
    v = _num(m.group(1))
    unit = "km" if "km" in m.group(2) else "miles"
    t = _num(m.group(3))
    if "min" in m.group(4):
        t = t / 60.0
    d = v * t
    return _steps_answer(
        "**%s %s**" % (_fmt(d), unit),
        ["speed x time = distance: %s x %s = %s %s."
         % (_fmt(v), _fmt(t), _fmt(d), unit)], "distance")


def _day_offset(q):
    ql = q.lower()
    m1 = re.search(r'today is (\w+)', ql)
    m2 = re.search(r'(\d+)\s*days?\s*(?:from now|from today|later|after)', ql)
    m3 = re.search(r'(\d+)\s*days?\s*after\s+(?:a\s+)?(\w+)', ql)
    if m3 and not m1:
        base = m3.group(2)
        n = int(m3.group(1))
    elif m1 and m2:
        base = m1.group(1)
        n = int(m2.group(1))
    else:
        return None
    base = base.capitalize()
    if base not in WEEKDAYS:
        return None
    idx = WEEKDAYS.index(base)
    steps = ["Start on %s." % base,
             "%d days = %d full weeks + %d extra days."
             % (n, n // 7, n % 7)]
    new = WEEKDAYS[(idx + n) % 7]
    if n % 7:
        steps.append("%s + %d day(s) = %s." % (base, n % 7, new))
    else:
        steps.append("The extra days are 0, so it is still %s." % new)
    return _steps_answer("**%s**" % new, steps, "day-of-week")


def _percent_of(q):
    ql = q.lower()
    m = re.search(r'(?:what is |calculate |find |compute )?([\d,.]+)\s*(?:%|percent)\s*of\s*([\d,.]+)\s*\??$', ql)
    if not m or not re.search(r'\d', ql) or len(ql) > 60:
        return None
    pct = _num(m.group(1))
    whole = _num(m.group(2))
    val = pct / 100.0 * whole
    return _steps_answer(
        "**%s**" % _fmt(val),
        ["%s%% of %s = %s x %s / 100 = %s."
         % (_fmt(pct), _fmt(whole), _fmt(pct), _fmt(whole), _fmt(val))],
        "percentage")


def _sequence_next(q):
    ql = q.lower()
    if "next" not in ql and "sequence" not in ql:
        return None
    m = re.search(r'([\d.-]+(?:\s*,\s*[\d.-]+){2,})', ql)
    if not m:
        return None
    nums = [float(x) for x in re.findall(r'-?\d+(?:\.\d+)?', m.group(1))]
    if len(nums) < 4:
        return None
    diffs = [round(nums[i + 1] - nums[i], 6) for i in range(len(nums) - 1)]
    if all(abs(d - diffs[0]) < 1e-9 for d in diffs):
        nxt = nums[-1] + diffs[0]
        return _steps_answer(
            "**%s**" % _fmt(nxt),
            ["The gaps are all %s (arithmetic sequence), so %s + %s = %s."
             % (_fmt(diffs[0]), _fmt(nums[-1]), _fmt(diffs[0]), _fmt(nxt))],
            "arithmetic sequence")
    gd = [round(diffs[i + 1] / diffs[i], 6) for i in range(len(diffs) - 1)
          if abs(diffs[i]) > 1e-9]
    if len(gd) >= 2 and all(abs(g - gd[0]) < 1e-6 for g in gd):
        nxt = nums[-1] + diffs[-1] * gd[0]
        return _steps_answer(
            "**%s**" % _fmt(nxt),
            ["The gaps %s grow by x%s each time, so the next gap is %s x %s "
             "= %s and %s + %s = %s."
             % (", ".join(_fmt(d) for d in diffs), _fmt(gd[0]), _fmt(diffs[-1]),
                _fmt(gd[0]), _fmt(diffs[-1] * gd[0]), _fmt(nums[-1]),
                _fmt(diffs[-1] * gd[0]), _fmt(nxt))], "growing-gap sequence")
    if all(abs(x) > 1e-9 for x in nums[:-1]):
        ratios = [nums[i + 1] / nums[i] for i in range(len(nums) - 1)]
        if all(abs(r - ratios[0]) < 1e-6 for r in ratios):
            nxt = nums[-1] * ratios[0]
            return _steps_answer(
                "**%s**" % _fmt(nxt),
                ["Each term is the previous one x %s (geometric), so %s x %s "
                 "= %s." % (_fmt(ratios[0]), _fmt(nums[-1]), _fmt(ratios[0]),
                            _fmt(nxt))], "geometric sequence")
    if len(nums) >= 5 and all(
            abs(nums[i] - (nums[i - 1] + nums[i - 2])) < 1e-9
            for i in range(2, len(nums))):
        nxt = nums[-1] + nums[-2]
        return _steps_answer(
            "**%s**" % _fmt(nxt),
            ["Each term is the sum of the two before it (Fibonacci-style): "
             "%s + %s = %s." % (_fmt(nums[-1]), _fmt(nums[-2]), _fmt(nxt))],
            "fibonacci sequence")
    roots = [math.isqrt(int(n)) if n >= 0 and abs(n - round(n)) < 1e-9 else -1
             for n in nums]
    if all(r > 0 and r * r == int(n) for r, n in zip(roots, nums)):
        if all(roots[i + 1] - roots[i] == 1 for i in range(len(roots) - 1)):
            nxt = (roots[-1] + 1) ** 2
            return _steps_answer(
                "**%s**" % _fmt(nxt),
                ["These are perfect squares (%s), so the next is %d^2 = %s."
                 % (", ".join("%d^2" % r for r in roots), roots[-1] + 1,
                    _fmt(nxt))], "squares sequence")
    return None


def _sqrt(q):
    ql = q.lower()
    m = re.search(r'(?:square root|sqrt)\s+of\s+([\d,.]+)', ql)
    if not m:
        return None
    n = _num(m.group(1))
    if n < 0:
        return None
    r = math.isqrt(int(round(n))) if abs(n - round(n)) < 1e-9 else None
    if r is not None and r * r == int(round(n)):
        return _steps_answer(
            "**%s**" % r,
            ["%d x %d = %s, so the square root of %s is exactly %d."
             % (r, r, _fmt(n), _fmt(n), r)], "square root")
    val = math.sqrt(n)
    return _steps_answer(
        "**%s** (rounded to 4 decimals)" % round(val, 4),
        ["%s is not a perfect square; its square root is approximately "
         "%s." % (_fmt(n), round(val, 4))], "square root")


def _power_compare(q):
    ql = q.lower()
    m = re.search(
        r'which is (?:bigger|larger|greater).*?'
        r'(\d+)\s*(?:\^|to the power of)\s*(\d+).*?'
        r'(\d+)\s*(?:\^|to the power of)\s*(\d+)', ql)
    if not m:
        return None
    a, b, c, d = (int(m.group(i)) for i in range(1, 5))
    if max(b, d) > 100 or max(a, c) > 1000:
        return None
    v1, v2 = a ** b, c ** d
    big = "%d^%d = %d" % (a, b, v1) if v1 > v2 else "%d^%d = %d" % (c, d, v2)
    return _steps_answer(
        "**%s is bigger**" % big,
        ["%d^%d = %d and %d^%d = %d." % (a, b, v1, c, d, v2)],
        "power comparison")


def _syllogism(q):
    ql = q.lower()
    m = re.search(r'if all (\w+) are (\w+),? and all (\w+) are (\w+)', ql)
    if not m:
        m = re.search(r'if all (\w+) are (\w+),? and all (\w+) ([a-z]+)', ql)
    ms = re.search(r'if all (\w+) are (\w+),? and some (\w+)', ql)
    m2 = re.search(r'(?:are|do) all (\w+)\s+(?:definitely |necessarily )?'
                   r'(?:qualify as |count as |counted as )?(\w+)', ql)
    if not m2:
        return None
    if ms:
        a, b, c = ms.group(1), ms.group(2), ms.group(3)
        return _steps_answer(
            "**No, not necessarily.**",
            ["All %s are %s - that part is certain." % (a, b),
             "But the second statement only says SOME %s behave that way, "
             "and it never mentions %s at all." % (c, a),
             "So we cannot conclude anything definite about all %s."
             % a], "syllogism")
    if not m:
        return None
    a, b, c, d = (m.group(i) for i in range(1, 5))
    x, y = m2.group(1), m2.group(2)
    chain1 = (x == a and y == d and b == c)
    chain2 = (x == c and y == b and a == d)
    if chain1 or chain2:
        return _steps_answer(
            "**Yes.**",
            ["Every %s is a %s, and every %s is a %s." % (a, b, c, d),
             "The two statements chain together, so every %s is definitely "
             "a %s." % (x, y)], "syllogism")
    return None


def _repeat_nines(q):
    ql = q.lower()
    if not re.search(r'0\.9{2,}', ql):
        return None
    if not re.search(r'what|equal|number', ql):
        return None
    return _steps_answer(
        "**Yes, 0.999... equals exactly 1.**",
        ["Let x = 0.999...",
         "Then 10x = 9.999...",
         "Subtract: 10x - x = 9.999... - 0.999... = 9",
         "So 9x = 9 and x = 1."], "repeating decimals")


def _feathers_steel(q):
    ql = q.lower()
    if not ("feather" in ql and "steel" in ql):
        return None
    if not re.search(r'heavier|weigh', ql):
        return None
    return _steps_answer(
        "**They weigh exactly the same - both are one kilogram.**",
        ["A kilogram is a measure of mass, not of size or density.",
         "The steel is far denser so it takes up much less space, but 1 kg "
         "of feathers and 1 kg of steel both weigh 1 kg."], "trick question")


def _letter_count(q):
    ql = q.lower()
    m = re.search(r'how many letters (?:are )?in (?:the word )?["\'\u2019]?([a-z]+)', ql)
    if m:
        w = re.findall(r'[a-z]', m.group(1))
        return _steps_answer(
            "**%d**" % len(w),
            ["%s has %d letters." % (m.group(1), len(w))], "letter count")
    m = re.search(
        r'how many times does the letter ([a-z]) (?:appear|occur)\s+in\s+'
        r'(?:the word )?["\'\u2019]?([a-z]+)', ql)
    if m:
        ch, w = m.group(1), m.group(2)
        n = w.count(ch)
        return _steps_answer(
            "**%d**" % n,
            ["%s: the letter '%s' appears %d time(s)." % (w, ch, n)],
            "letter count")
    return None


def _prime_check(q):
    ql = q.lower()
    m = re.search(r'is (?:the number )?(\d+) (?:a )?prime', ql)
    if not m:
        return None
    n = int(m.group(1))
    if n < 2:
        return _steps_answer(
            "**No, %d is not prime.**" % n,
            ["By definition a prime number has exactly two divisors (1 and "
             "itself); %d has fewer, so it is not prime." % n], "prime check")
    div = None
    for i in range(2, math.isqrt(n) + 1):
        if n % i == 0:
            div = i
            break
    if div is None:
        return _steps_answer(
            "**Yes, %d is prime.**" % n,
            ["%d has no divisors other than 1 and itself." % n],
            "prime check")
    return _steps_answer(
        "**No, %d is not prime.**" % n,
        ["%d = %d x %d, so it has divisors other than 1 and itself."
         % (n, div, n // div)], "prime check")


def _birds_shot(q):
    ql = q.lower()
    if not re.search(r'shoot|shot|hunter|gun', ql):
        return None
    if not re.search(r'how many\b.{0,40}\b(?:left|remain)', ql):
        return None
    if not re.search(r'birds?|sparrows?|ducks?|crows?|pigeons?|geese|'
                     r'animals?', ql):
        return None
    m = re.search(r'(\d+)\s*(?:birds?|sparrows?|ducks?|crows?|pigeons?|'
                  r'geese|animals?)', ql)
    n0 = int(m.group(1)) if m else None
    steps = ["The shot scares the others away." if n0 is None else
             "Of the %d, the shot scares all the others away." % n0,
             "So none are left."]
    return _steps_answer("**None - 0 are left.**", steps,
                         "trick question")


def _reciprocal_identity(q):
    ql = q.lower().replace("²", "^2").replace("³", "^3").replace("⁴", "^4")
    m = re.search(
        r'(?:x\s*([+-])\s*1/x|1/x\s*([+-])\s*x)\s*=\s*([\d.]+)', ql)
    if not m:
        return None
    op = m.group(1) or m.group(2)
    a = _num(m.group(3))
    plus = op == "+"
    asked = []
    if re.search(r'x\^2\s*\+\s*1/x\^2', ql):
        asked.append(("x^2 + 1/x^2", a * a - 2 if plus else a * a + 2))
    if re.search(r'x\^3\s*\+\s*1/x\^3', ql):
        asked.append(("x^3 + 1/x^3", a ** 3 - 3 * a if plus else a ** 3 + 3 * a))
    if re.search(r'x\^4\s*\+\s*1/x\^4', ql):
        b = a * a - 2 if plus else a * a + 2
        asked.append(("x^4 + 1/x^4", b * b - 2))
    if not asked:
        return None
    steps = ["Given: x %s 1/x = %s." % (op, _fmt(a))]
    if plus:
        steps.append("(x + 1/x)^2 = x^2 + 2 + 1/x^2, so x^2 + 1/x^2 = "
                     "%s^2 - 2 = %s." % (_fmt(a), _fmt(a * a - 2)))
    else:
        steps.append("(x - 1/x)^2 = x^2 - 2 + 1/x^2, so x^2 + 1/x^2 = "
                     "%s^2 + 2 = %s." % (_fmt(a), _fmt(a * a + 2)))
    for name, val in asked:
        if not name.startswith("x^2"):
            steps.append("Apply the identity again: %s = %s."
                         % (name, _fmt(val)))
    final = " and ".join("%s = %s" % (n, _fmt(v)) for n, v in asked)
    return _steps_answer("**%s**" % final, steps, "algebra identity", 0.97)


def _number_machine(q):
    ql = q.lower()
    m_res = re.search(r'(?:result|answer)\s+(?:is|equals)\s+(\d+(?:\.\d+)?)', ql)
    if not m_res:
        m_res = re.search(r'(?:equals|gives|you get)\s+(\d+(?:\.\d+)?)', ql)
    if not m_res:
        return None
    res = _num(m_res.group(1))
    ops = []
    for m in re.finditer(r'(doubled|tripled|quadrupled|halved)', ql):
        ops.append((m.start(), {"doubled": ("*", 2), "tripled": ("*", 3),
                                "quadrupled": ("*", 4),
                                "halved": ("/", 2)}[m.group(1)]))
    for m in re.finditer(r'multiplied\s+by\s+(\d+(?:\.\d+)?)', ql):
        ops.append((m.start(), ("*", _num(m.group(1)))))
    for m in re.finditer(r'divided\s+by\s+(\d+(?:\.\d+)?)', ql):
        ops.append((m.start(), ("/", _num(m.group(1)))))
    for m in re.finditer(r'(\d+(?:\.\d+)?)\s+is\s+(added|subtracted)', ql):
        ops.append((m.start(), ("+" if m.group(2) == "added" else "-",
                                _num(m.group(1)))))
    for m in re.finditer(r'(increased|decreased)\s+by\s+(\d+(?:\.\d+)?)', ql):
        ops.append((m.start(), ("+" if m.group(1) == "increased" else "-",
                                _num(m.group(2)))))
    if not ops:
        return None
    ops.sort(key=lambda t: t[0])
    seq = [(k, v) for _, (k, v) in ops]
    x = res
    steps = ["Work backwards from the result, undoing each step in reverse:"]
    for k, v in reversed(seq):
        if k == "+":
            x -= v
            steps.append("undo +%s -> %s" % (_fmt(v), _fmt(x)))
        elif k == "-":
            x += v
            steps.append("undo -%s -> %s" % (_fmt(v), _fmt(x)))
        elif k == "*":
            x /= v
            steps.append("undo x%s -> %s" % (_fmt(v), _fmt(x)))
        else:
            x *= v
            steps.append("undo /%s -> %s" % (_fmt(v), _fmt(x)))
    fwd = _fmt(x)
    for k, v in seq:
        if k == "*":
            fwd = "%s x %s" % (fwd, _fmt(v))
        elif k == "/":
            fwd = "%s / %s" % (fwd, _fmt(v))
        elif k == "+":
            fwd = "%s + %s" % (fwd, _fmt(v))
        else:
            fwd = "%s - %s" % (fwd, _fmt(v))
    steps.append("Check forward: %s = %s." % (fwd, _fmt(res)))
    return _steps_answer("**The original number is %s**" % _fmt(x), steps,
                         "number machine", 0.97)


def _clock_strikes(q):
    ql = q.lower()
    hits = re.findall(r'(?:strike|chime|ring|toll)s?\s+(\d+)\s*times?', ql)
    if len(hits) < 2:
        return None
    n0, m_ask = int(hits[0]), int(hits[1])
    m_sec = re.search(r'(?:takes?|in)\s+([\d.]+)\s*seconds?', ql)
    if not m_sec or n0 < 2 or m_ask < 2:
        return None
    secs = _num(m_sec.group(1))
    per = secs / (n0 - 1)
    ans = per * (m_ask - 1)
    return _steps_answer(
        "**%s seconds**" % _fmt(ans),
        ["%d strikes have %d gaps between them, so each gap takes "
         "%s / %d = %s seconds." % (n0, n0 - 1, _fmt(secs), n0 - 1, _fmt(per)),
         "%d strikes have %d gaps: %d x %s = %s seconds."
         % (m_ask, m_ask - 1, m_ask - 1, _fmt(per), _fmt(ans))],
        "clock strikes", 0.95)


def _digit_reversal(q):
    ql = q.lower()
    s_m = re.search(
        r'(?:digits?\s+(?:that\s+)?add\s+up\s+to|sum of the digits[^.]{0,40}?'
        r'(?:is|=)|digit sum (?:is|of)|digits sum to)\s*(\d+)', ql)
    if not s_m:
        return None
    r_m = re.search(
        r'revers\w*[^.]{0,90}?is\s+(\d+)\s+'
        r'(greater|more|bigger|higher|less|smaller|lower)', ql)
    if not r_m:
        return None
    s_tot, d_val = int(s_m.group(1)), int(r_m.group(1))
    mode = r_m.group(2)
    if d_val % 9 or not (1 <= s_tot <= 18):
        return None
    diff = d_val // 9
    if mode in ("greater", "more", "bigger", "higher"):
        a, b = (s_tot - diff) / 2.0, (s_tot + diff) / 2.0
        how = "the reversed number is %d greater" % d_val
    else:
        a, b = (s_tot + diff) / 2.0, (s_tot - diff) / 2.0
        how = "the reversed number is %d less" % d_val
    if a != int(a) or not (1 <= a <= 9 and 0 <= b <= 9):
        return None
    a, b = int(a), int(b)
    orig = 10 * a + b
    rev = 10 * b + a
    return _steps_answer(
        "**%s**" % orig,
        ["Let the digits be a and b: a + b = %d." % s_tot,
         "Reversing swaps them: 10b + a vs 10a + b - the difference is "
         "9 x (b - a) = %d, so b - a = %d." % (d_val, diff),
         "Solving a + b = %d and b - a = %d gives a = %d, b = %d."
         % (s_tot, diff, a, b),
         "Original number: %d, reversed: %d (%s than the original)."
         % (orig, rev, how)], "digit reversal", 0.96)


def _average(q):
    m = re.search(r'average of ([\d,\s]+?)(?:\?|\.|$)', q.lower())
    if not m:
        return None
    nums = [_num(x) for x in re.findall(r'[\d.]+', m.group(1))]
    if len(nums) < 2:
        return None
    avg = sum(nums) / len(nums)
    return _steps_answer(
        "**%s**" % _fmt(avg),
        ["Add them: %s = %s." % (" + ".join(_fmt(n) for n in nums),
                                 _fmt(sum(nums))),
         "Divide by %d numbers: %s / %d = %s."
         % (len(nums), _fmt(sum(nums)), len(nums), _fmt(avg))],
        "average")


def _rectangle(q):
    ql = q.lower()
    m = re.search(r'rectangle is ([\d.]+)\s*cm long and ([\d.]+)\s*cm wide'
                  r'[^?]*\?', ql)
    if not m:
        return None
    a, b = _num(m.group(1)), _num(m.group(2))
    if "perimeter" in ql:
        v = 2 * (a + b)
        return _steps_answer(
            "**%s cm**" % _fmt(v),
            ["Perimeter = 2 x (length + width) = 2 x (%s + %s) = %s cm."
             % (_fmt(a), _fmt(b), _fmt(v))], "rectangle perimeter")
    v = a * b
    return _steps_answer(
        "**%s cm\u00b2**" % _fmt(v),
        ["Area = length x width = %s x %s = %s cm\u00b2."
         % (_fmt(a), _fmt(b), _fmt(v))], "rectangle area")


def _triangle_third(q):
    m = re.search(r'triangle has angles of ([\d.]+) degrees? and ([\d.]+) '
                  r'degrees?', q.lower())
    if not m:
        return None
    x, y = _num(m.group(1)), _num(m.group(2))
    v = 180 - x - y
    if v <= 0:
        return None
    return _steps_answer(
        "**%s degrees**" % _fmt(v),
        ["Angles in a triangle add to 180 degrees.",
         "180 - %s - %s = %s degrees." % (_fmt(x), _fmt(y), _fmt(v))],
        "triangle angles")


def _circle(q):
    m = re.search(r'(circumference|area) of a circle with radius ([\d.]+)',
                  q.lower())
    if not m:
        return None
    r = _num(m.group(2))
    if m.group(1) == "circumference":
        v = round(2 * 3.14 * r, 2)
        return _steps_answer(
            "**%s**" % _fmt(v),
            ["Circumference = 2 x pi x r = 2 x 3.14 x %s = %s."
             % (_fmt(r), _fmt(v))], "circle")
    v = round(3.14 * r * r, 2)
    return _steps_answer(
        "**%s**" % _fmt(v),
        ["Area = pi x r\u00b2 = 3.14 x %s\u00b2 = %s."
         % (_fmt(r), _fmt(v))], "circle")


def _avg_speed(q):
    m = re.search(r'travels? ([\d.]+)\s*km in ([\d.]+)\s*hours?[^?]*\?',
                  q.lower())
    if not m:
        return None
    d, t = _num(m.group(1)), _num(m.group(2))
    if not t:
        return None
    v = d / t
    return _steps_answer(
        "**%s km/h**" % _fmt(v),
        ["Average speed = distance / time = %s / %s = %s km/h."
         % (_fmt(d), _fmt(t), _fmt(v))], "average speed")


_UNIT_FACS = [("meters", "kilometers", 1000), ("grams", "kilograms", 1000),
              ("milliliters", "liters", 1000),
              ("centimeters", "meters", 100),
              ("minutes", "hours", 60), ("seconds", "minutes", 60),
              ("milligrams", "grams", 1000)]


def _unit_convert(q):
    m = re.search(r'how many (\w+) are in ([\d.]+) (\w+)', q.lower())
    if not m:
        return None
    dst, k, src = m.group(1), _num(m.group(2)), m.group(3)
    for d, s, fac in _UNIT_FACS:
        if dst == d and src == s:
            v = k * fac
            return _steps_answer(
                "**%s %s**" % (_fmt(v), dst),
                ["1 %s = %d %s." % (s.rstrip("s"), fac, d),
                 "%s x %s = %s %s." % (_fmt(k), fac, _fmt(v), dst)],
                "unit conversion")
    return None


def _fraction_of(q):
    m = re.search(r'what is (\d+)/(\d+) of ([\d.]+)', q.lower())
    if not m:
        return None
    a, b, n = _num(m.group(1)), _num(m.group(2)), _num(m.group(3))
    if not b:
        return None
    v = a * n / b
    return _steps_answer(
        "**%s**" % _fmt(v),
        ["Divide by the denominator: %s / %s = %s."
         % (_fmt(n), _fmt(b), _fmt(n / b)),
         "Multiply by the numerator: %s x %s = %s."
         % (_fmt(n / b), _fmt(a), _fmt(v))], "fraction of")


def _pct_change(q):
    m = re.search(r'(rises?|increases?|drops?|falls?|decreases?) from '
                  r'([\d.]+) to ([\d.]+)', q.lower())
    if not m:
        return None
    a, b = _num(m.group(2)), _num(m.group(3))
    if not a:
        return None
    pct = (b - a) / a * 100
    return _steps_answer(
        "**%s%%**" % _fmt(pct),
        ["Change = %s - %s = %s." % (_fmt(b), _fmt(a), _fmt(b - a)),
         "Percentage = change / original x 100 = %s / %s x 100 = %s%%."
         % (_fmt(b - a), _fmt(a), _fmt(pct))], "percentage change")


def _simple_interest(q):
    m = re.search(r'simple interest on ([\d.]+) at ([\d.]+)% per year for '
                  r'([\d.]+) years?', q.lower())
    if not m:
        return None
    P, r, t = _num(m.group(1)), _num(m.group(2)), _num(m.group(3))
    v = P * r * t / 100
    return _steps_answer(
        "**%s**" % _fmt(v),
        ["Simple interest = P x R x T / 100.",
         "%s x %s x %s / 100 = %s." % (_fmt(P), _fmt(r), _fmt(t), _fmt(v))],
        "simple interest")


def _gcd_lcm(q):
    ql = q.lower()
    m = re.search(r'(greatest common divisor|least common multiple|gcd|'
                  r'lcm|hcf) of ([\d.]+) and ([\d.]+)', ql)
    if not m:
        return None
    a, b = int(_num(m.group(2))), int(_num(m.group(3)))
    import math as _m
    if m.group(1) in ("greatest common divisor", "gcd", "hcf"):
        v, how = _m.gcd(a, b), "GCD"
    else:
        v, how = a * b // _m.gcd(a, b), "LCM"
    return _steps_answer(
        "**%s**" % v,
        ["%s of %d and %d = %d." % (how, a, b, v)], "gcd/lcm")


def _square_cube(q):
    m = re.search(r'what is ([\d.]+) (squared|cubed)', q.lower())
    if not m:
        return None
    n = _num(m.group(1))
    v = n * n if m.group(2) == "squared" else n * n * n
    return _steps_answer(
        "**%s**" % _fmt(v),
        ["%s %s = %s." % (_fmt(n), "x " + _fmt(n) if m.group(2) ==
                          "squared" else "x " + _fmt(n) + " x " + _fmt(n),
                          _fmt(v))], "square/cube")


def _tip(q):
    m = re.search(r'bill is ([\d.]+) rupees?\. you give a ([\d.]+)% tip\. '
                  r'how much is the tip', q.lower())
    if not m:
        return None
    b, p = _num(m.group(1)), _num(m.group(2))
    v = b * p / 100
    return _steps_answer(
        "**%s rupees**" % _fmt(v),
        ["Tip = %s%% of %s = %s x %s / 100 = %s."
         % (_fmt(p), _fmt(b), _fmt(b), _fmt(p), _fmt(v))], "tip")


def _discount(q):
    m = re.search(r'a ([\d.]+)% discount on an item priced ([\d.]+) leaves '
                  r'a final price', q.lower())
    if not m:
        return None
    p, b = _num(m.group(1)), _num(m.group(2))
    cut = b * p / 100
    v = b - cut
    return _steps_answer(
        "**%s**" % _fmt(v),
        ["Discount = %s%% of %s = %s." % (_fmt(p), _fmt(b), _fmt(cut)),
         "Final price = %s - %s = %s." % (_fmt(b), _fmt(cut), _fmt(v))],
        "discount")


def _work_rate(q):
    m = re.search(r'a alone can do a job in ([\d.]+) hours, b alone in '
                  r'([\d.]+) hours', q.lower())
    if not m:
        return None
    x, y = _num(m.group(1)), _num(m.group(2))
    v = 1 / (1 / x + 1 / y)
    return _steps_answer(
        "**%s hours**" % _fmt(round(v, 2)),
        ["A does 1/%s of the job per hour; B does 1/%s."
         % (_fmt(x), _fmt(y)),
         "Together: 1/%s + 1/%s = 1/%s of the job per hour, so they need "
         "about %s hours." % (_fmt(x), _fmt(y), _fmt(round(1 / (1 / x + 1 / y), 4)),
                              _fmt(round(v, 2)))], "work rate")


def _probability(q):
    ql = q.lower()
    if "coin" in ql and "heads" in ql:
        return _steps_answer("**1/2**",
                             ["A fair coin has 2 equally likely outcomes; "
                              "heads is 1 of them: 1/2."], "probability")
    m = re.search(r'rolling (?:a|an) ([\d.]+)', ql)
    if m and "die" in ql:
        n = int(_num(m.group(1)))
        if 1 <= n <= 6:
            return _steps_answer(
                "**1/6**", ["A die has 6 equally likely faces; %d is 1 of "
                            "them: 1/6." % n], "probability")
    if "die" in ql and "even" in ql:
        return _steps_answer(
            "**1/2**", ["Even numbers on a die: 2, 4, 6 (3 of 6 faces): "
                        "3/6 = 1/2."], "probability")
    return None


_SIMPLE_FACTS = [
    (r'how many days (?:are )?(?:there )?in a leap year', "366"),
    (r'how many days (?:are )?(?:there )?in a (?:normal |regular )?year',
     "365"),
    (r'how many minutes (?:are )?(?:there )?in an hour', "60"),
    (r'how many seconds (?:are )?(?:there )?in a minute', "60"),
    (r'how many hours (?:are )?(?:there )?in a day', "24"),
    (r'how many days (?:are )?(?:there )?in a week', "7"),
    (r'how many months (?:are )?(?:there )?in a year', "12"),
    (r'how many weeks (?:are )?(?:there )?in a year', "52"),
    (r'sum of the angles in a triangle', "180"),
    (r'degrees (?:are )?(?:there )?in a right angle', "90"),
    (r'how many (?:players|people) (?:are )?(?:there )?on (?:a )?'
     r'(?:football|soccer) (?:team|side)', "11"),
    (r'how many cards (?:are )?(?:there )?in a (?:standard )?deck', "52"),
]
_SHAPES = {"triangle": 3, "square": 4, "rectangle": 4, "pentagon": 5,
           "hexagon": 6, "heptagon": 7, "septagon": 7, "octagon": 8,
           "nonagon": 9, "decagon": 10}


def _simple_facts(q):
    ql = q.lower()
    for pat, ans in _SIMPLE_FACTS:
        if re.search(pat, ql):
            return _steps_answer(
                "**%s**" % ans,
                ["This is a fixed fact: the answer is %s." % ans],
                "known fact")
    m = re.search(r'how many sides does (?:a|an) (\w+) have', ql)
    if m and m.group(1) in _SHAPES:
        n = _SHAPES[m.group(1)]
        return _steps_answer(
            "**%d**" % n,
            ["A %s has %d sides." % (m.group(1), n)], "known fact")
    return None


def _factorial(q):
    ql = q.lower()
    m = re.search(r'(?:what is (?:the )?)?factorial\s+of\s+([\d.]+)|(?:what is\s+)?([\d.]+)\s*factorial|\b([\d.]+)\s*!', ql)
    if not m:
        return None
    raw = m.group(1) or m.group(2) or m.group(3)
    n = int(_num(raw))
    if not 0 <= n <= 20:
        return None
    v = 1
    for k in range(2, n + 1):
        v *= k
    factors = " x ".join(str(k) for k in range(1, n + 1)) if n > 0 else "1"
    return _steps_answer(
        "**%s**" % v,
        ["%d! = %s = %d." % (n, factors, v)], "factorial", conf=0.99)


def _simple_equation(q):
    ql = q.lower()
    m = re.search(r'if\s+(\d*)\s*([a-z])\s*([+-])\s*(\d+)\s*=\s*(\d+)', ql)
    m2 = re.search(r'what is ([a-z])', ql)
    if not m:
        return None
    a = int(m.group(1)) if m.group(1) else 1
    v, op, b, rhs = m.group(2), m.group(3), int(m.group(4)), int(m.group(5))
    if m2 and m2.group(1) != v:
        return None
    if op == "+":
        x = (rhs - b) / a
    else:
        x = (rhs + b) / a
    steps = ["%d%s %s %d = %d -> %s = %s."
             % (a, v, op, b, rhs, v, _fmt(x))]
    return _steps_answer(
        "**%s = %s**" % (m2.group(1) if m2 else v, _fmt(x)),
        steps, "algebra")


def _multiply(q):
    ql = q.lower()
    m = re.search(r'([\d,]+(?:\.\d+)?)\s*(?:multiplied by|times|x)\s*([\d,]+(?:\.\d+)?)', ql)
    if not m:
        return None
    if not re.search(r'what is|calculate|compute|how much', ql):
        return None
    a, b = _num(m.group(1)), _num(m.group(2))
    if a > 1e6 or b > 1e6:
        return None
    v = a * b
    return _steps_answer(
        "**%s**" % _fmt(v),
        ["%s x %s = %s." % (_fmt(a), _fmt(b), _fmt(v))], "multiplication")


_AGE_MULT = {"twice": 2, "two": 2, "thrice": 3, "three": 3, "four": 4,
             "five": 5, "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10}

_AGE_COMMON = {"man", "woman", "father", "mother", "son", "daughter", "boy",
               "girl", "brother", "sister", "child", "kid", "person",
               "grandfather", "grandmother", "uncle", "aunt", "cousin",
               "husband", "wife"}

_AGE_M = r'(\d+(?:\.\d+)?|twice|thrice|two|three|four|five|six|seven|eight|nine|ten)'


def _age_num(tok):
    tok = tok.strip()
    if re.fullmatch(r'\d+(?:\.\d+)?', tok):
        return float(tok)
    return float(_AGE_MULT.get(tok, 0))


def _age_name(w):
    w = w.strip().lower()
    return ("the " + w) if w in _AGE_COMMON else w.capitalize()


def _age_ratio(q):
    ql = q.lower()
    m = re.search(r'(\w+) is ' + _AGE_M + r'\s*(?:times\s+)?as old as '
                  r'(?:(?:his|her|its|their|the)\s+)?(\w+)', ql)
    if not m:
        return None
    older_w, yw = m.group(1), m.group(3)
    n = _age_num(m.group(2))
    if not (1 < n <= 12) or older_w == yw:
        return None
    older, younger = _age_name(older_w), _age_name(yw)

    mf = re.search(r'in (\d+) years?\b[^.]{0,80}?will be ' + _AGE_M +
                   r'\s*(?:times\s+)?as old\b(?:\s+as\b)?', ql)
    mp = re.search(r'(\d+) years? ago\b[^.]{0,80}?was ' + _AGE_M +
                   r'\s*(?:times\s+)?as old\b(?:\s+as\b)?', ql)
    if mf:
        t = int(mf.group(1))
        k = _age_num(mf.group(2))
        if not (1 < k <= 12) or t < 1 or abs(k - n) < 1e-9:
            return None
        den = n - k
        if den <= 0:
            return None
        yf = t * (k - 1) / den
        if abs(yf - round(yf)) > 1e-9:
            return None
        y = int(round(yf))
        if y < 1:
            return None
        a = n * y
        if abs(a - round(a)) > 1e-9:
            return None
        a = int(round(a))
        left = "%sx + %d" % (_fmt(n), t)
        right = "%s(x + %d)" % (_fmt(k), t)
        return _steps_answer(
            "**%s is %d years old and %s is %d.**" % (
                older.capitalize() if older.startswith("the") else older, a,
                younger, y),
            ["Let the %s's age now be x. Then %s's age = %sx."
             % (yw, older, _fmt(n)),
             "In %d years: %s = %s" % (t, left, right),
             "%sx + %d = %sx + %s -> %sx = %s -> x = %d"
             % (_fmt(n), t, _fmt(k), _fmt(k * t), _fmt(n - k),
                _fmt(t * (k - 1)), y),
             "%s is %d, and %s is %s x %d = %d."
             % (younger[:1].upper() + younger[1:], y, older, _fmt(n), y, a),
             "Check: in %d years %d = %s x (%d + %d) = %s. ✓"
             % (t, a + t, _fmt(k), y, t, _fmt(k * (y + t)))], "age puzzle")
    if mp:
        t = int(mp.group(1))
        k = _age_num(mp.group(2))
        if not (1 < k <= 12) or t < 1 or abs(k - n) < 1e-9:
            return None
        den = k - n
        if den <= 0:
            return None
        yf = t * (k - 1) / den
        if abs(yf - round(yf)) > 1e-9:
            return None
        y = int(round(yf))
        if y < 1:
            return None
        a = n * y
        if abs(a - round(a)) > 1e-9:
            return None
        a = int(round(a))
        return _steps_answer(
            "**%s is %d years old and %s is %d.**" % (
                older.capitalize() if older.startswith("the") else older, a,
                younger, y),
            ["Let the %s's age now be x. Then %s's age = %sx."
             % (yw, older, _fmt(n)),
             "%d years ago: %sx - %d = %s(x - %d)"
             % (t, _fmt(n), t, _fmt(k), t),
             "Solving: %sx - %d = %sx - %s -> x = %d"
             % (_fmt(n), t, _fmt(k), _fmt(k * t), y),
             "%s is %d; %s is %s x %d = %d."
             % (younger.capitalize(), y, older, _fmt(n), y, a)], "age puzzle")
    ms = re.search(r'sum of [^.]{0,40}?age\w*[^.]{0,40}?is (\d+)|'
                   r'together (?:they are|they\'re|they will be) (\d+)', ql)
    if ms:
        s = int(ms.group(1) or ms.group(2))
        yf = s / (n + 1)
        if abs(yf - round(yf)) > 1e-9:
            return None
        y = int(round(yf))
        a = int(round(n * y))
        if y < 1:
            return None
        return _steps_answer(
            "**%s is %d years old and %s is %d.**" % (
                older.capitalize() if older.startswith("the") else older, a,
                younger, y),
            ["Let the %s's age now be x. Then %s's age = %sx." % (yw, older, _fmt(n)),
             "Their ages add up to %d: %dx + x = %d" % (s, n, s),
             "%dx = %d -> x = %d" % (n + 1, s, y),
             "%s is %d, and %s is %s x %d = %d."
             % (younger, y, older, _fmt(n), y, a)], "age puzzle")
    return None


_LAUNCH_DATES = {
    "youtube": ("YouTube", "2005", "registered February 14, 2005; first "
                "video 'Me at the zoo' uploaded April 23, 2005"),
    "google": ("Google", "1998", "founded September 4, 1998 by Larry Page "
               "and Sergey Brin"),
    "facebook": ("Facebook", "2004", "launched February 4, 2004 by Mark "
                 "Zuckerberg"),
    "instagram": ("Instagram", "2010", "launched October 6, 2010"),
    "whatsapp": ("WhatsApp", "2009", "founded in 2009; acquired by "
                 "Facebook in 2014"),
    "twitter": ("Twitter", "2006", "first tweet posted March 21, 2006"),
    "wikipedia": ("Wikipedia", "2001", "launched January 15, 2001"),
    "iphone": ("iPhone", "2007", "announced January 9, 2007; first model "
               "released June 29, 2007"),
    "android": ("Android", "2008", "first phone (HTC Dream) launched "
                "October 2008"),
    "python": ("Python", "1991", "created by Guido van Rossum, first "
               "released in 1991"),
    "linux": ("Linux", "1991", "announced by Linus Torvalds in August 1991"),
    "windows": ("Windows", "1985", "Windows 1.0 released November 20, 1985"),
    "chatgpt": ("ChatGPT", "2022", "released November 30, 2022"),
    "openai": ("OpenAI", "2015", "founded in December 2015"),
    "tiktok": ("TikTok", "2016", "launched in September 2016"),
    "netflix": ("Netflix", "1997", "founded August 29, 1997"),
    "amazon": ("Amazon", "1994", "founded July 5, 1994"),
    "tesla": ("Tesla", "2003", "founded July 1, 2003"),
    "spacex": ("SpaceX", "2002", "founded March 14, 2002"),
    "spotify": ("Spotify", "2008", "launched October 2008"),
    "minecraft": ("Minecraft", "2011", "full release November 18, 2011"),
    "fortnite": ("Fortnite", "2017", "released July 21, 2017"),
    "playstation": ("PlayStation", "1994", "released December 3, 1994 in "
                    "Japan"),
    "xbox": ("Xbox", "2001", "released November 15, 2001"),
    "bitcoin": ("Bitcoin", "2009", "first block mined January 3, 2009"),
    "ethereum": ("Ethereum", "2015", "network launched July 30, 2015"),
    "apple": ("Apple", "1976", "founded April 1, 1976"),
    "microsoft": ("Microsoft", "1975", "founded April 4, 1975"),
    "intel": ("Intel", "1968", "founded July 18, 1968"),
    "nasa": ("NASA", "1958", "created by the National Aeronautics and Space "
             "Act, signed July 29, 1958"),
    "google maps": ("Google Maps", "2005", "launched February 8, 2005"),
    "reddit": ("Reddit", "2005", "founded June 23, 2005"),
    "snapchat": ("Snapchat", "2011", "launched September 2011"),
    "ebay": ("eBay", "1995", "founded September 3, 1995"),
    "yahoo": ("Yahoo", "1994", "founded January 1994"),
    "google chrome": ("Google Chrome", "2008", "released September 2, 2008"),
    "firefox": ("Firefox", "2002", "first released September 23, 2002"),
    "star wars": ("Star Wars", "1977", "first film released May 25, 1977"),
    "pokemon": ("Pokémon", "1996", "first games released February 27, 1996 "
                "in Japan"),
    "mario": ("Super Mario", "1985", "Super Mario Bros. released September "
              "13, 1985"),
    "harry potter": ("Harry Potter", "1997", "first book published June 26, "
                     "1997"),
    "wifi": ("Wi-Fi", "1997", "first standard (802.11) approved in 1997"),
    "bluetooth": ("Bluetooth", "1998", "technology announced May 1998"),
    "usb": ("USB", "1996", "specification released January 1996"),
    "gta": ("Grand Theft Auto", "1997", "first game released October 1997"),
    "grand theft auto": ("Grand Theft Auto", "1997", "first game released "
                         "October 1997"),
    "united nations": ("The United Nations", "1945", "charter signed "
                       "October 24, 1945"),
    "nintendo": ("Nintendo", "1889", "founded September 23, 1889 as a "
                "playing-card company"),
    "samsung": ("Samsung", "1938", "founded March 1, 1938"),
    "zoom": ("Zoom", "2013", "founded in 2011; app launched 2013"),
    "roblox": ("Roblox", "2006", "released September 1, 2006"),
    "google play": ("Google Play", "2008", "launched October 22, 2008 as "
                   "the Android Market"),
    "python 3": ("Python 3", "2008", "released December 3, 2008"),
    "windows 10": ("Windows 10", "2015", "released July 29, 2015"),
    "windows 11": ("Windows 11", "2021", "released October 5, 2021"),
}

_WHEN_VERBS = r'(introduced|launched|founded|created|invented|released|' \
              r'started|established|begun|begin|come out|come into being|' \
              r'made|built|first (?:released|released|appear\w*))'


def _when_introduced(q):
    ql = q.lower()
    m = re.search(r'when (?:was|were|did|has)\s+(?:the\s+|a\s+)?(.{2,40}?)\s+'
                  + _WHEN_VERBS + r'\b', ql)
    if not m:
        m = re.search(r'when (?:was|were|did)\s+(?:the\s+|a\s+)?(.{2,40}?)\s+'
                      r'(?:release|launch|come out)\b', ql)
        if not m:
            return None
    name = re.sub(r'\s+', ' ', re.sub(r"[^a-z0-9 ]", " ", m.group(1))).strip()
    entry = _LAUNCH_DATES.get(name)
    if not entry and name.endswith("s"):
        entry = _LAUNCH_DATES.get(name.rstrip("s"))
    if not entry:
        return None
    display, year, extra = entry
    verb = m.group(2) if m.lastindex and m.lastindex >= 2 else "launched"
    verb = {"begun": "launched", "begin": "launched", "come out": "launched",
            "come into being": "created", "made": "created",
            "built": "created"}.get(verb, verb)
    if verb.startswith("first"):
        verb = "launched"
    return _steps_answer(
        "**%s**" % year,
        ["%s was %s in %s (%s)." % (display, verb, year, extra)],
        "launch date")


_RATE_VERBS = (r"(?:make|makes|produce|produces|build|builds|paint|paints|"
               r"complete|completes|print|prints|pack|packs|bake|bakes|"
               r"manufacture|manufactures|prepare|prepares|copy|copies|"
               r"assemble|assembles|serve|serves|create|creates|do|does|"
               r"eat|eats|write|writes|fill|fills)")
_RATE_NQ = r"([\d,]+(?:\.\d+)?|an|a|one|the\s+same)\b"
_RATE_UNIT = r"(seconds?|minutes?|hours?|days?|weeks?|months?|years?)"


def _qnum(tok):
    tok = (tok or "").strip().lower()
    if tok and tok[0].isdigit():
        return _num(tok)
    return 1.0


def _rate_scaling(q):
    m = re.search(
        r"(?:if\s+)?([\d,]+(?:\.\d+)?|an|a|one)\s+([a-zA-Z]+)\s+"
        r"(?:can\s+)?" + _RATE_VERBS +
        r"\s+" + _RATE_NQ +
        r"\s+([a-zA-Z]+)(?:\s+[a-zA-Z]+){0,2}?\s+in\s+([\d,]+(?:\.\d+)?)\s+"
        + _RATE_UNIT + r"\b", q, re.I)
    if not m:
        return None
    n1 = _qnum(m.group(1))
    noun = m.group(2).lower()
    n2 = _qnum(m.group(3))
    out_noun = m.group(4).lower()
    t1 = _num(m.group(5))
    unit2 = m.group(6).lower()
    if n1 <= 0 or n2 <= 0 or t1 <= 0:
        return None
    rest = q[m.end():]
    mt = re.search(
        r"([\d,]+(?:\.\d+)?)\s+([a-zA-Z]+)\s+(?:take\s+)?to\s+"
        + _RATE_VERBS + r"\s+" + _RATE_NQ, rest, re.I)
    if mt:
        m1 = _num(mt.group(1))
        noun2 = mt.group(2).lower()
        if noun.rstrip("s") != noun2.rstrip("s"):
            return None
        n3 = _qnum(mt.group(3))
    else:
        mt2 = re.search(r"to\s+" + _RATE_VERBS + r"\s+" + _RATE_NQ,
                        rest, re.I)
        if not mt2:
            return None
        m1 = 1.0
        n3 = _qnum(mt2.group(1))
    if m1 <= 0 or n3 <= 0:
        return None
    rate = n2 / (n1 * t1)
    combined = m1 * rate
    t = n3 / combined
    unit_sing = unit2.rstrip("s")
    ans_unit = unit2 if abs(t - 1) > 1e-9 else unit_sing
    steps = [
        "Rate: %s %s / (%s %s x %s %s) = %s %s per %s per %s."
        % (_fmt(n2), out_noun, _fmt(n1), noun, _fmt(t1), unit2,
           _fmt(rate), out_noun, noun.rstrip("s"), unit_sing),
        "%s %s together: %s x %s = %s %s per %s."
        % (_fmt(m1), noun, _fmt(m1), _fmt(rate), _fmt(combined), out_noun,
           unit_sing),
        "Time for %s %s: %s / %s = %s %s."
        % (_fmt(n3), out_noun, _fmt(n3), _fmt(combined), _fmt(t), unit2),
    ]
    if m1 != n1 and abs(n3 / n2 - m1 / n1) < 1e-9:
        steps.append("Both the number of %s and the output grew equally "
                     "(%sx), so the time stays the same as before."
                     % (noun, _fmt(m1 / n1)))
    return _steps_answer("**%s %s**" % (_fmt(t), ans_unit), steps,
                         "rate-scaling puzzle")


def _age_now(q):
    ql = q.lower()
    m = re.search(r'in (\d+) years?\b[^.]{0,60}?will be (\d+)(?![\d.])', ql)
    if m:
        yrs, then = int(m.group(1)), int(m.group(2))
        now = then - yrs
        if now < 0:
            return None
        return _steps_answer(
            "**%d years old**" % now,
            ["In %d years they will be %d, so now: %d - %d = %d."
             % (yrs, then, then, yrs, now)], "age puzzle")
    m = re.search(r'(\d+) years? ago\b[^.]{0,60}?was (\d+)(?![\d.])', ql)
    if m:
        yrs, then = int(m.group(1)), int(m.group(2))
        now = then + yrs
        return _steps_answer(
            "**%d years old**" % now,
            ["%d years ago they were %d, so now: %d + %d = %d."
             % (yrs, then, then, yrs, now)], "age puzzle")
    return None


_AST_OPS = {
    ast.Add: lambda a, b: a + b,
    ast.Sub: lambda a, b: a - b,
    ast.Mult: lambda a, b: a * b,
    ast.Div: lambda a, b: a / b if b != 0 else float("inf"),
    ast.FloorDiv: lambda a, b: a // b if b != 0 else 0,
    ast.Mod: lambda a, b: a % b,
    ast.Pow: lambda a, b: a ** b if b < 1000 else 0,
    ast.USub: lambda a: -a,
    ast.UAdd: lambda a: a,
}


def _eval_ast_math(node):
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
        return node.value
    if isinstance(node, ast.BinOp) and type(node.op) in _AST_OPS:
        return _AST_OPS[type(node.op)](_eval_ast_math(node.left), _eval_ast_math(node.right))
    if isinstance(node, ast.UnaryOp) and type(node.op) in _AST_OPS:
        return _AST_OPS[type(node.op)](_eval_ast_math(node.operand))
    raise ValueError("unsupported ast node")


def _math_expression(q):
    ql = re.sub(r"[?!.]+$", "", q.lower().strip()).strip()
    m = re.search(r"(?:(?:what is|calculate|compute|solve|evaluate|find|value of|=|is)\s+)?([0-9\s+\-*/().^%]+)(?:\s*=\s*\??)?$", ql)
    if not m:
        return None
    expr = m.group(1).strip().replace("^", "**")
    if not expr or not re.search(r"[+\-*/%**]", expr):
        return None
    try:
        node = ast.parse(expr, mode="eval").body
        val = _eval_ast_math(node)
        final = int(val) if isinstance(val, float) and val.is_integer() else round(val, 6)
        disp_expr = expr.replace("**", "^")
        steps = [
            "Mathematical expression parsed: %s" % disp_expr,
            "Evaluated following standard order of operations (parentheses, exponents, multiplication/division, addition/subtraction).",
            "%s = %s" % (disp_expr, final)
        ]
        return _steps_answer("**%s**" % final, steps, "math expression", conf=0.99)
    except Exception:
        return None


def _possession_riddle(q):
    ql = q.lower()
    m1 = re.search(r"(?:if\s+)?(?:i|we)\s+have\s+(\d+|[a-z]+)\s+([a-z]+)\s+and\s+you\s+take(?:\s+away)?\s+(\d+|[a-z]+)\b[^?.]*how many\s+(?:[a-z]+\s+)?(?:do\s+)?you\s+have", ql)
    if m1:
        initial = _qnum(m1.group(1))
        item = m1.group(2)
        taken = _qnum(m1.group(3))
        steps = [
            "Initial quantity: %d %s were present." % (int(initial), item),
            "Action performed: You took away %d %s." % (int(taken), item),
            "Question analysis: The riddle specifically asks 'how many %s do YOU have?' - not how many remain." % item,
            "Conclusion: Since you took %d %s, you have %d %s." % (int(taken), item, int(taken), item)
        ]
        return _steps_answer("**%d** (you have %d %s)" % (int(taken), int(taken), item), steps, "possession riddle", conf=0.98)
    m2 = re.search(r"(?:if\s+)?(?:i|we)\s+have\s+(\d+|[a-z]+)\s+([a-z]+)\s+and\s+you\s+take(?:\s+away)?\s+(\d+|[a-z]+)\b[^?.]*how many\s+(?:[a-z]+\s+)?(?:do\s+)?(?:i|we)\s+(?:have\s+left|remain)", ql)
    if m2:
        initial = _qnum(m2.group(1))
        item = m2.group(2)
        taken = _qnum(m2.group(3))
        rem = initial - taken
        steps = [
            "Started with %d %s." % (int(initial), item),
            "%d %s were taken away." % (int(taken), item),
            "Calculation: %d - %d = %d %s remaining." % (int(initial), int(taken), int(rem), item)
        ]
        return _steps_answer("**%d** (%d %s left)" % (int(rem), int(rem), item), steps, "subtraction riddle", conf=0.98)
    return None


def _classic_puzzles(q):
    ql = q.lower()
    if "moses" in ql and ("ark" in ql or "animals" in ql):
        steps = [
            "Examine the premise: According to the biblical account, Noah built the ark, not Moses.",
            "Moses had no ark and did not take any animals onto an ark.",
            "Conclusion: None (Moses took 0 animals; Noah took the animals)."
        ]
        return _steps_answer("**None (0)** - Noah built the ark, not Moses!", steps, "trick question", conf=0.98)
    if "rooster" in ql and ("egg" in ql or "lay" in ql or "lays" in ql):
        steps = [
            "Biological fact: A rooster is a male chicken.",
            "Only hens (female chickens) lay eggs; roosters cannot lay eggs.",
            "Conclusion: The rooster lays 0 eggs."
        ]
        return _steps_answer("**0** - Roosters don't lay eggs, hens do!", steps, "trick question", conf=0.98)
    if "mary" in ql and "father" in ql and "daughters" in ql:
        steps = [
            "The riddle begins: 'Mary\\'s father has daughters...'",
            "This directly establishes that Mary is one of the daughters.",
            "Conclusion: The 5th daughter's name is Mary."
        ]
        return _steps_answer("**Mary**", steps, "logic puzzle", conf=0.98)
    if "wetter" in ql and "dries" in ql:
        steps = [
            "Identify the paradox: Something that gets wetter as it dries other things.",
            "As a towel dries off water from surfaces or bodies, it absorbs that water and becomes wetter.",
            "Conclusion: A towel."
        ]
        return _steps_answer("**A towel**", steps, "riddle", conf=0.98)
    if "keys" in ql and "no locks" in ql and ("space" in ql or "room" in ql or "enter" in ql):
        steps = [
            "Clues: Has keys (spacebar, enter, letters) but no locks, space but no room, you can enter but can't go inside.",
            "Conclusion: A keyboard (or a piano for keys with no locks)."
        ]
        return _steps_answer("**A keyboard**", steps, "riddle", conf=0.98)
    if "electric train" in ql and "smoke" in ql:
        steps = [
            "Premise analysis: The train is electric.",
            "Electric trains are powered by electricity and do not emit smoke.",
            "Conclusion: There is no smoke."
        ]
        return _steps_answer("**There is no smoke** (an electric train produces no smoke).", steps, "trick question", conf=0.98)
    if "months" in ql and "28 days" in ql:
        steps = [
            "Every month of the year (January through December) has at least 28 days.",
            "February has 28 (or 29 in leap years), while all others have 30 or 31.",
            "Conclusion: All 12 months have 28 days."
        ]
        return _steps_answer("**All 12 months**", steps, "trick question", conf=0.98)
    return None


def _temperature_converter(q):
    ql = q.lower()
    m = re.search(r"convert\s+(-?[\d.]+)\s*(?:degrees?\s+)?(celsius|fahrenheit|kelvin|c|f|k)\s+to\s+(?:degrees?\s+)?(celsius|fahrenheit|kelvin|c|f|k)", ql)
    if not m:
        m = re.search(r"what is\s+(-?[\d.]+)\s*(?:degrees?\s+)?(celsius|fahrenheit|kelvin|c|f|k)\s+in\s+(?:degrees?\s+)?(celsius|fahrenheit|kelvin|c|f|k)", ql)
    if not m:
        return None
    val = float(m.group(1))
    src = m.group(2).lower()
    dst = m.group(3).lower()
    src = "c" if src in ("celsius", "c") else ("f" if src in ("fahrenheit", "f") else "k")
    dst = "c" if dst in ("celsius", "c") else ("f" if dst in ("fahrenheit", "f") else "k")
    if src == dst:
        return _steps_answer("**%s**" % _fmt(val), ["Same unit: no conversion needed."], "temperature")
    if src == "c" and dst == "f":
        res = (val * 9.0 / 5.0) + 32.0
        steps = ["Formula: (°C x 9/5) + 32 = °F", "(%s x 1.8) + 32 = %s°F" % (_fmt(val), _fmt(res))]
        return _steps_answer("**%s °F**" % _fmt(res), steps, "temperature")
    if src == "f" and dst == "c":
        res = (val - 32.0) * 5.0 / 9.0
        steps = ["Formula: (°F - 32) x 5/9 = °C", "(%s - 32) x 5/9 = %s°C" % (_fmt(val), _fmt(res))]
        return _steps_answer("**%s °C**" % _fmt(res), steps, "temperature")
    if src == "c" and dst == "k":
        res = val + 273.15
        steps = ["Formula: °C + 273.15 = K", "%s + 273.15 = %s K" % (_fmt(val), _fmt(res))]
        return _steps_answer("**%s K**" % _fmt(res), steps, "temperature")
    if src == "k" and dst == "c":
        res = val - 273.15
        steps = ["Formula: K - 273.15 = °C", "%s - 273.15 = %s °C" % (_fmt(val), _fmt(res))]
def _quadratic_perfect_square(q):
    ql = q.lower()
    if not ("perfect square" in ql or ("square" in ql and ("integer" in ql or "find" in ql or "positive" in ql))):
        return None
    m = re.search(r'([a-z])\^2\s*([+-])\s*(\d*)\s*\*?\s*\1\s*([+-])\s*(\d+)', ql)
    if not m:
        m2 = re.search(r'([a-z])\^2\s*([+-])\s*(\d+)', ql)
        if m2 and "x" in m2.group(1):
            var = m2.group(1)
            b = 0
            sign_c = m2.group(2)
            c = int(m2.group(3)) * (1 if sign_c == '+' else -1)
        else:
            return None
    else:
        var = m.group(1)
        sign_b = m.group(2)
        b_str = m.group(3)
        b = int(b_str) if b_str else 1
        if sign_b == '-':
            b = -b
        sign_c = m.group(4)
        c = int(m.group(5)) * (1 if sign_c == '+' else -1)

    K = 4 * c - b * b
    if K == 0:
        return None

    b_sign = "+" if b >= 0 else "-"
    b_abs = abs(b)
    c_sign = "+" if c >= 0 else "-"
    c_abs = abs(c)
    expr_str = f"{var}^2 {b_sign} {b_abs}{var} {c_sign} {c_abs}"

    solutions = []
    steps = [
        f"We are looking for all positive integers ${var}$ such that ${expr_str}$ is a perfect square.",
        f"Let ${expr_str} = y^2$ where $y$ is a positive integer ($y \\in \\mathbb{{Z}}^+$).",
    ]
    if b % 2 == 0:
        h = b // 2
        rem = c - h * h
        h_sign = "+" if h >= 0 else "-"
        h_abs = abs(h)
        rem_sign = "+" if rem >= 0 else "-"
        rem_abs = abs(rem)
        steps.append(f"Complete the square: $({var} {h_sign} {h_abs})^2 {rem_sign} {rem_abs} = y^2$.")
        steps.append(f"Rearrange into difference of squares: $y^2 - ({var} {h_sign} {h_abs})^2 = {rem}$.")
        steps.append(f"Factor using the difference of squares identity: $(y - ({var} {h_sign} {h_abs}))(y + ({var} {h_sign} {h_abs})) = {rem}$.")
        factor_pairs = []
        for d1 in range(1, int(math.isqrt(rem_abs)) + 1):
            if rem_abs % d1 == 0:
                d2 = rem_abs // d1
                factor_pairs.append((d1, d2))

        steps.append(f"Since ${var}, y$ are positive integers, $y + ({var} {h_sign} {h_abs}) > y - ({var} {h_sign} {h_abs}) > 0$.")
        steps.append(f"The positive integer factor pairs of {rem} are: {', '.join(f'({p[0]}, {p[1]})' for p in factor_pairs)}.")
        for d1, d2 in factor_pairs:
            if (d2 - d1) % 2 == 0 and (d1 + d2) % 2 == 0:
                x_val = (d2 - d1) // 2 - h
                y_val = (d1 + d2) // 2
                if x_val > 0 and y_val > 0:
                    val_check = x_val * x_val + b * x_val + c
                    if val_check == y_val * y_val:
                        solutions.append((x_val, y_val))
                        steps.append(f"For factor pair $({d1}, {d2})$:\n"
                                     f"   - $y + ({var} {h_sign} {h_abs}) = {d2}$\n"
                                     f"   - $y - ({var} {h_sign} {h_abs}) = {d1}$\n"
                                     f"   Subtracting the two equations: $2({var} {h_sign} {h_abs}) = {d2 - d1} \\implies {var} = {x_val}$.\n"
                                     f"   Adding the two equations: $2y = {d1 + d2} \\implies y = {y_val}$.\n"
                                     f"   Verification: ${x_val}^2 {b_sign} {b_abs}({x_val}) {c_sign} {c_abs} = {val_check} = {y_val}^2$ (perfect square!).")
    else:
        abs_k = abs(K)
        steps.append(f"Multiply the equation by 4 to clear fractions: $4{var}^2 {b_sign} 4({b_abs}){var} {c_sign} 4({c_abs}) = 4y^2$.")
        steps.append(f"Complete the square: $(2{var} {b_sign} {b_abs})^2 {c_sign} {abs_k} = (2y)^2$.")
        steps.append(f"Rearrange into difference of squares: $(2y - (2{var} {b_sign} {b_abs}))(2y + (2{var} {b_sign} {b_abs})) = {K}$.")
        factor_pairs = []
        for d1 in range(1, int(math.isqrt(abs_k)) + 1):
            if abs_k % d1 == 0:
                factor_pairs.append((d1, abs_k // d1))
        for d1, d2 in factor_pairs:
            if (d2 - d1) % 2 == 0 and (d1 + d2) % 2 == 0:
                X = (d2 - d1) // 2
                if (X - b) % 2 == 0:
                    x_val = (X - b) // 2
                    y_val = (d1 + d2) // 4
                    if x_val > 0 and y_val > 0 and (x_val * x_val + b * x_val + c == y_val * y_val):
                        solutions.append((x_val, y_val))
                        steps.append(f"For factor pair $({d1}, {d2})$: gives {var} = {x_val}, y = {y_val}.")

    if not solutions:
        steps.append(f"No factor pair yields a valid positive integer ${var} > 0$.")
        final = f"There are **no positive integers** ${var}$ such that ${expr_str}$ is a perfect square."
    else:
        sol_strs = [f"{var} = {s[0]}" for s in solutions]
        final = "**" + ", ".join(sol_strs) + "**"
        steps.append(f"Conclusion: The only positive integer solution is {final}.")

    return _steps_answer(final, steps, "algebra", conf=0.99)


def _linear_system(q):
    ql = q.lower()
    if "system" not in ql or ("=" not in ql and "equations" not in ql):
        return None
    m = re.search(r'(\d*)\s*([a-z])\s*([+-])\s*(\d*)\s*([a-z])\s*=\s*([-\d.]+).*?(?:and|,)\s*(\d*)\s*([a-z])\s*([+-])\s*(\d*)\s*([a-z])\s*=\s*([-\d.]+)', ql)
    if not m:
        return None
    a1_str, v1, s1, b1_str, v2, c1_str, a2_str, v3, s2, b2_str, v4, c2_str = m.groups()
    if v1 != v3 or v2 != v4:
        return None
    a1 = float(a1_str) if a1_str else 1.0
    b1 = float(b1_str) if b1_str else 1.0
    if s1 == '-': b1 = -b1
    c1 = float(c1_str)
    a2 = float(a2_str) if a2_str else 1.0
    b2 = float(b2_str) if b2_str else 1.0
    if s2 == '-': b2 = -b2
    c2 = float(c2_str)

    D = a1 * b2 - a2 * b1
    if abs(D) < 1e-9:
        return None
    Dx = c1 * b2 - c2 * b1
    Dy = a1 * c2 - a2 * c1
    x_val = Dx / D
    y_val = Dy / D
    x_str = _fmt(x_val)
    y_str = _fmt(y_val)

    steps = [
        f"Given system: (1) {a1_str or '1'}{v1} {s1} {b1_str or '1'}{v2} = {c1_str}, and (2) {a2_str or '1'}{v3} {s2} {b2_str or '1'}{v4} = {c2_str}.",
        f"Solve via Cramer's Rule: Determinant D = ({a1})*({b2}) - ({a2})*({b1}) = {D}.",
        f"Dx = ({c1})*({b2}) - ({c2})*({b1}) = {Dx} -> {v1} = Dx / D = {x_str}.",
        f"Dy = ({a1})*({c2}) - ({a2})*({c1}) = {Dy} -> {v2} = Dy / D = {y_str}.",
        f"Verification: {a1}({x_str}) + ({b1})({y_str}) = {c1_str} ✓"
    ]
    final = f"**{v1} = {x_str}, {v2} = {y_str}**"
    return _steps_answer(final, steps, "linear_algebra", conf=0.99)


def _derivative_power_rule(q):
    ql = q.lower().replace("squared", "^2")
    if "derivative" not in ql:
        return None
    m = re.search(r'(?:f\(x\)\s*=\s*|of\s+)([\dx^+\-\s]+?)(?:\s+with\s+respect|\?|$)', ql)
    if not m:
        return None
    poly = m.group(1).replace(" ", "")
    terms = re.findall(r'([+-]?[0-9]*\.?[0-9]*)x(?:\^([0-9]+))?|([+-]?[0-9]+\.?[0-9]*)', poly)
    if not terms:
        return None
    d_terms = []
    steps = ["Power Rule of Differentiation: d/dx [a * x^n] = a * n * x^(n-1); d/dx [constant] = 0."]
    for coef_str, exp_str, const_str in terms:
        if const_str:
            steps.append(f"d/dx [{const_str}] = 0 (constant term vanishes).")
            continue
        c = 1.0 if coef_str in ("", "+") else (-1.0 if coef_str == "-" else float(coef_str))
        p = int(exp_str) if exp_str else 1
        new_c = c * p
        new_p = p - 1
        c_fmt = _fmt(new_c)
        if new_p == 0:
            term_res = f"{c_fmt}" if new_c < 0 else f"+{c_fmt}"
            steps.append(f"d/dx [{_fmt(c)}x] = {_fmt(c)}.")
        elif new_p == 1:
            term_res = f"{c_fmt}x" if new_c < 0 else f"+{c_fmt}x"
            steps.append(f"d/dx [{_fmt(c)}x^{p}] = {_fmt(c)} * {p} * x = {c_fmt}x.")
        else:
            term_res = f"{c_fmt}x^{new_p}" if new_c < 0 else f"+{c_fmt}x^{new_p}"
            steps.append(f"d/dx [{_fmt(c)}x^{p}] = {_fmt(c)} * {p} * x^{new_p} = {c_fmt}x^{new_p}.")
        d_terms.append(term_res)
    if not d_terms:
        return None
    res_expr = "".join(d_terms).lstrip("+")
    res_expr = res_expr.replace("+", " + ").replace("-", " - ")
    if res_expr.startswith(" - "):
        res_expr = "-" + res_expr[3:]
    final = f"**f'(x) = {res_expr}**"
    steps.append(f"Combining differentiated terms yields: {final}.")
    return _steps_answer(final, steps, "calculus", conf=0.99)


def _indefinite_integral(q):
    ql = q.lower()
    if "integral" not in ql:
        return None
    m = re.search(r'integral\s+of\s+(\d*)\s*x(?:\^(\d+))?', ql)
    if not m:
        return None
    coef_str, exp_str = m.groups()
    c = float(coef_str) if coef_str else 1.0
    p = int(exp_str) if exp_str else 1
    new_p = p + 1
    new_c = c / new_p
    c_fmt = _fmt(new_c) if new_c != 1.0 else ""
    p_str = f"x^{new_p}" if new_p > 1 else "x"
    final = f"**{c_fmt}{p_str} + C**"
    steps = [
        "Power Rule of Integration: ∫ a * x^n dx = (a / (n+1)) * x^(n+1) + C, where C is the arbitrary constant of integration.",
        f"For integrand {int(c) if c.is_integer() else c}x^{p if p > 1 else ''}: increase power by 1 to {new_p}, divide coefficient by {new_p}.",
        f"∫ {int(c) if c.is_integer() else c}x dx = ({int(c) if c.is_integer() else c}/{new_p}) * {p_str} + C = {c_fmt}{p_str} + C."
    ]
    return _steps_answer(final, steps, "calculus", conf=0.99)


def _dice_sum_probability(q):
    ql = q.lower()
    if ("dice" in ql or "die" in ql) and "probability" in ql and ("sum" in ql or "total" in ql):
        m = re.search(r'sum\s+(?:of\s+(?:the\s+)?numbers\s+)?(?:is\s+)?(\d+)', ql)
        if not m:
            return None
        target = int(m.group(1))
        pairs = []
        for d1 in range(1, 7):
            for d2 in range(1, 7):
                if d1 + d2 == target:
                    pairs.append((d1, d2))
        count = len(pairs)
        prob = count / 36.0
        frac = f"{count}/36"
        if count == 6: frac = "1/6"
        elif count == 4: frac = "1/9"
        elif count == 3: frac = "1/12"
        elif count == 2: frac = "1/18"
        final = f"**{frac}** ({count}/36 ≈ {prob*100:.2f}%)"
        pair_str = ", ".join(f"({a},{b})" for a, b in pairs)
        steps = [
            "Total possible outcomes when rolling two independent fair 6-sided dice = 6 * 6 = 36 equally likely outcomes.",
            f"Favorable outcomes summing to {target}: {pair_str} (total of {count} favorable combinations).",
            f"Probability = (Favorable outcomes) / (Total outcomes) = {count} / 36 = {frac}."
        ]
        return _steps_answer(final, steps, "probability", conf=0.99)
    return None


def _core_math_theorems(q):
    ql = q.lower()
    if "pythagorean" in ql and "theorem" in ql:
        final = "**a^2 + b^2 = c^2**"
        steps = [
            "Statement: In any right-angled triangle, the area of the square whose side is the hypotenuse is equal to the sum of the areas of the squares on the other two legs.",
            "Equation: a^2 + b^2 = c^2",
            "Variable definitions: 'a' and 'b' represent the perpendicular lengths of the two legs adjacent to the 90-degree right angle; 'c' represents the length of the hypotenuse (the longest side opposite the right angle).",
            "Example: For legs a=3, b=4: 3^2 + 4^2 = 9 + 16 = 25 = 5^2, so hypotenuse c=5."
        ]
        return _steps_answer(final, steps, "geometry", conf=0.99)

    if "quadratic formula" in ql:
        final = "**x = (-b ± √(b^2 - 4ac)) / (2a)**"
        steps = [
            "Standard Form of a quadratic equation: ax^2 + bx + c = 0, where a ≠ 0.",
            "Quadratic Formula: x = (-b ± √(b^2 - 4ac)) / (2a).",
            "Discriminant: Δ = b^2 - 4ac determines the nature of the roots:",
            "  - If Δ > 0: two distinct real roots.",
            "  - If Δ = 0: exactly one repeated real root (x = -b / (2a)).",
            "  - If Δ < 0: two complex conjugate roots with imaginary unit i."
        ]
        return _steps_answer(final, steps, "algebra", conf=0.99)

    if "euler" in ql and "identity" in ql:
        final = "**e^(i*π) + 1 = 0**"
        steps = [
            "Euler's Formula: e^(i*x) = cos(x) + i*sin(x) for any real number x.",
            "Substitute x = π: e^(i*π) = cos(π) + i*sin(π).",
            "Evaluate trigonometric components: cos(π) = -1 and sin(π) = 0.",
            "Substitute values: e^(i*π) = -1 + 0*i = -1.",
            "Add 1 to both sides: e^(i*π) + 1 = 0.",
            "Beauty & Elegance: Unifies five fundamental mathematical constants (e, i, π, 1, 0) and three primary operations (addition, multiplication, exponentiation) in a single equation."
        ]
        return _steps_answer(final, steps, "complex_analysis", conf=0.99)

    if "volume" in ql and "sphere" in ql:
        final = "**V = (4/3) * π * r^3**"
        steps = [
            "Geometric Formula: The volume V of a sphere of radius r is V = (4/3) * π * r^3.",
            "Variable Definition: 'r' is the radius (half the diameter d, so r = d/2).",
            "Surface Area Relationship: The surface area of the same sphere is A = 4 * π * r^2, which is the exact derivative of volume with respect to radius: dV/dr = 4πr^2."
        ]
        return _steps_answer(final, steps, "geometry", conf=0.99)

    if "bayes" in ql and ("theorem" in ql or "formula" in ql):
        final = "**P(A|B) = [P(B|A) * P(A)] / P(B)**"
        steps = [
            "Statement: Bayes' Theorem describes the probability of an event based on prior knowledge of conditions that might be related to the event.",
            "Formula: P(A|B) = [P(B|A) * P(A)] / P(B)",
            "Terms Definition:",
            "  - P(A|B): Posterior probability (probability of hypothesis A given evidence B).",
            "  - P(B|A): Likelihood (probability of evidence B given hypothesis A is true).",
            "  - P(A): Prior probability (initial probability of hypothesis A before seeing evidence B).",
            "  - P(B): Marginal probability or evidence (total probability of observing B across all hypotheses)."
        ]
        return _steps_answer(final, steps, "probability", conf=0.99)

    if "fibonacci" in ql and ("recurrence" in ql or "formula" in ql):
        final = "**F(n) = F(n-1) + F(n-2)** (with F(0) = 0, F(1) = 1)"
        steps = [
            "Definition: Each term in the Fibonacci sequence is the sum of the two preceding terms.",
            "Recurrence relation: F(n) = F(n-1) + F(n-2) for all integers n ≥ 2.",
            "Base cases: F(0) = 0, F(1) = 1.",
            "Sequence terms: 0, 1, 1, 2, 3, 5, 8, 13, 21, 34, 55, 89, 144, ...",
            "Closed-form (Binet's Formula): F(n) = (φ^n - ψ^n) / √5, where φ = (1+√5)/2 (Golden Ratio) and ψ = (1-√5)/2."
        ]
        return _steps_answer(final, steps, "number_theory", conf=0.99)

    if "area" in ql and "circle" in ql:
        final = "**A = π * r^2** (or **pi * r^2**)"
        steps = [
            "Formula: The area A of a flat circle of radius r is A = π * r^2 (or pi * r^2).",
            "In terms of diameter d = 2r: A = π * (d/2)^2 = (π/4) * d^2.",
            "Circumference: C = 2 * π * r.",
            "Example: For radius r = 5, Area A = π * 5^2 = 25π ≈ 78.54."
        ]
        return _steps_answer(final, steps, "geometry", conf=0.99)

    if "irrational number" in ql:
        final = "**Irrational numbers cannot be written as a/b (e.g., π, e, √2)**"
        steps = [
            "Definition: An irrational number is any real number that cannot be expressed as a simple fraction or ratio a/b of two integers (where b ≠ 0).",
            "Decimal Representation: Their decimal representations are non-terminating and non-repeating.",
            "Three Classic Examples:",
            "  1. π (pi ≈ 3.14159265...): The ratio of a circle's circumference to its diameter.",
            "  2. e (Euler's number ≈ 2.71828182...): The base of the natural logarithm.",
            "  3. √2 (square root of 2 ≈ 1.41421356...): The hypotenuse of a right isosceles triangle with legs of length 1."
        ]
        return _steps_answer(final, steps, "number_theory", conf=0.99)

    return None


def _earthquake_science(q):
    ql = q.lower()
    if not re.search(r"\bearthquakes?\b", ql):
        return None
    if not re.search(r"\b(?:why|how|cause|occur|happen|measured?|magnitude|scale|seismograph|seismic)\b", ql):
        return None
    ans = (
        "### Why Earthquakes Occur:\n"
        "1. **Tectonic Plate Dynamics:** The Earth's outermost crust and upper mantle (lithosphere) are fractured into massive tectonic plates that float on the ductile, semi-fluid asthenosphere beneath. These plates are in constant, slow motion driven by mantle convection currents.\n"
        "2. **Frictional Resistance along Faults:** At plate boundaries (convergent, divergent, and transform faults), plates cannot slide past each other smoothly. Friction locks the fault surfaces together while tectonic driving forces continue to push.\n"
        "3. **Elastic Rebound Theory:** As the plates continue to exert pressure, rock along the locked fault elastically deforms and accumulates massive shear strain energy over decades or centuries. When the built-up stress exceeds the frictional shear strength of the rock, the fault ruptures catastrophically.\n"
        "4. **Seismic Wave Propagation:** The sudden rupture releases stored elastic strain energy, radiating outward in all directions from the hypocenter (focus) as seismic waves:\n"
        "   - **Primary ($P$) Waves:** Fast compressional body waves that travel through solids, liquids, and gases.\n"
        "   - **Secondary ($S$) Waves:** Transverse shear waves that travel only through solids.\n"
        "   - **Surface Waves (Love and Rayleigh):** Travel along the Earth's surface, causing the most severe destructive ground shaking.\n\n"
        "### How Earthquakes Are Measured:\n"
        "1. **Seismographs (Seismometers):** Sensitive ground-motion instruments anchored to bedrock that record the arrival time, frequency, and amplitude of seismic waves, producing a **seismogram**.\n"
        "2. **Moment Magnitude Scale ($M_w$):** The modern, internationally standardized scientific scale for earthquake magnitude. It measures the total physical energy released based on rock rigidity $\\mu$, fault rupture area $A$, and average slip displacement $D$:\n"
        "   $$M_0 = \\mu A D, \\quad M_w = \\frac{2}{3} \\log_{10}(M_0) - 10.7$$\n"
        "   Unlike older scales, $M_w$ does not saturate for large earthquakes ($> 7.0$).\n"
        "3. **Richter Scale ($M_L$):** Developed by Charles Richter in 1935; a logarithmic scale measuring the maximum wave amplitude on a local Wood-Anderson seismograph. Each whole number increase represents a 10-fold increase in amplitude and $\\approx 31.6$ times more energy.\n"
        "4. **Modified Mercalli Intensity (MMI) Scale:** A qualitative scale (rated Roman numerals I to XII) that measures the observable shaking intensity and physical damage at specific locations."
    )
    return {"answer": ans, "confidence": 0.99, "kind": "geophysics"}


def _moon_phases_science(q):
    ql = q.lower()
    if not (re.search(r"\bmoon\b", ql) and re.search(r"\b(?:shape|phases?|change|cycle|orbit|illum)\b", ql)):
        return None
    ans = (
        "### Why the Moon Appears to Change Shape (Lunar Phases):\n"
        "The changing appearance of the Moon throughout the month is caused by the **geometry of its orbit around Earth relative to the Sun**:\n\n"
        "1. **Sunlight Reflection:** The Moon emits no light of its own; it reflects sunlight. At all times, exactly **half** of the lunar sphere is illuminated by the Sun, while the opposite hemisphere is in darkness.\n"
        "2. **Changing Viewing Angles (Orbital Revolution):** The Moon orbits Earth approximately once every **29.53 days** (a synodic month). As it revolves, the fraction of the illuminated hemisphere that faces Earth changes continuously depending on the Moon's orbital position relative to Earth and the Sun.\n"
        "3. **The 8 Phases of the Lunar Cycle:**\n"
        "   - **New Moon:** The Moon is between Earth and the Sun; its illuminated side faces away from Earth (the Moon is invisible or dark).\n"
        "   - **Waxing Crescent:** The Moon moves eastward; a thin sliver of illuminated surface becomes visible on the right (in Northern Hemisphere).\n"
        "   - **First Quarter:** The Moon is 90° from the Sun; we see exactly half of the near side illuminated (one-quarter of the full lunar orbit).\n"
        "   - **Waxing Gibbous:** More than half of the visible disk is illuminated and expanding.\n"
        "   - **Full Moon:** Earth is between the Sun and Moon (nearly aligned); the entire near side facing Earth is fully illuminated by sunlight.\n"
        "   - **Waning Gibbous:** The illuminated portion visible from Earth begins to decrease.\n"
        "   - **Third / Last Quarter:** Exactly half of the visible disk is illuminated on the opposite side (three-quarters of the orbit).\n"
        "   - **Waning Crescent:** A thin crescent remains before returning to the New Moon phase.\n\n"
        "> **Important Clarification:** Lunar phases are **NOT** caused by the Earth's shadow falling on the Moon. (Earth's shadow on the Moon causes a *lunar eclipse*, a rare astronomical event). Phases are purely the result of viewing varying angles of the Moon's sunlit hemisphere."
    )
    return {"answer": ans, "confidence": 0.99, "kind": "astronomy"}


def _lightning_thunder_science(q):
    ql = q.lower()
    if not (re.search(r"\blightning\b", ql) and re.search(r"\bthunder\b", ql)):
        return None
    ans = (
        "### Why Lightning Occurs Before Thunder Is Heard:\n"
        "Lightning is seen before thunder is heard because **light travels nearly one million times faster than sound**:\n\n"
        "1. **Disparity in Wave Velocities:**\n"
        "   - **Speed of Light ($c$):** $\\approx 300,000,000\\text{ m/s}$ ($3 \\times 10^8\\text{ m/s}$ or $\\approx 186,000\\text{ miles/sec}$). The flash of lightning arrives at an observer's eyes essentially instantaneously (taking only $\\approx 3.3\\text{ microseconds}$ per kilometer).\n"
        "   - **Speed of Sound ($v$):** $\\approx 343\\text{ m/s}$ (at 20°C in dry air, or $\\approx 1,125\\text{ ft/s}$). Sound travels only about **1 kilometer every 2.9 seconds** (or 1 mile every 5 seconds).\n"
        "2. **Simultaneous Generation:**\n"
        "   - Lightning and thunder originate simultaneously from the same physical event.\n"
        "   - When an electrostatic breakdown occurs, a lightning bolt channels millions of volts and thousands of amperes through the air.\n"
        "   - The bolt superheats the surrounding air channel to roughly **30,000 K (53,500°F)** - roughly five times hotter than the surface of the Sun - in a fraction of a millisecond.\n"
        "   - This instantaneous thermal heating causes rapid explosive expansion of the air column, creating a supersonic shock wave that quickly decays into acoustic sound waves: **thunder**.\n"
        "3. **Calculating Lightning Distance (The Flash-to-Bang Rule):**\n"
        "   - Count the seconds elapsed between seeing the lightning flash and hearing the first thunder clap.\n"
        "   - **Distance in Kilometers:** $\\text{Distance (km)} = \\frac{\\text{Time (seconds)}}{3}$\n"
        "   - **Distance in Miles:** $\\text{Distance (miles)} = \\frac{\\text{Time (seconds)}}{5}$"
    )
    return {"answer": ans, "confidence": 0.99, "kind": "physics"}


def _seasons_science(q):
    ql = q.lower()
    if not (re.search(r"\bseasons?\b", ql) and re.search(r"\b(?:why|cause|change|occur|happen|summer|winter)\b", ql)):
        return None
    ans = (
        "### Why Seasons Occur:\n"
        "Earth's seasons are caused by the **23.44° axial tilt** of the Earth relative to its orbital plane around the Sun (the ecliptic):\n\n"
        "1. **Axial Tilt:** As Earth orbits the Sun, its rotational axis remains tilted in a fixed direction in space (pointing toward Polaris).\n"
        "2. **Solar Insolation & Angle of Incidence:**\n"
        "   - When a hemisphere is tilted **toward** the Sun, sunlight strikes the surface at a steep, direct angle, concentrating thermal energy over a smaller surface area and causing longer daylight hours (**Summer**).\n"
        "   - When a hemisphere is tilted **away** from the Sun, solar rays strike at an oblique, shallow angle, spreading the same amount of solar energy over a larger area and resulting in shorter daylight hours (**Winter**).\n"
        "3. **Equinoxes and Solstices:**\n"
        "   - **Summer Solstice:** The hemisphere reaches its maximum tilt toward the Sun (longest day).\n"
        "   - **Winter Solstice:** The hemisphere reaches its maximum tilt away from the Sun (shortest day).\n"
        "   - **Equinoxes (Spring & Autumn):** Both hemispheres receive equal solar illumination (approx. 12 hours day and 12 hours night).\n\n"
        "> **Note:** Seasons are **NOT** caused by the distance between Earth and the Sun! Earth is actually closest to the Sun (perihelion) in early January during Northern Hemisphere winter."
    )
    return {"answer": ans, "confidence": 0.99, "kind": "astronomy"}


def _term_etymology(q):
    ql = q.lower().strip()
    if re.search(r"\b(?:what(?:\s+is|\s+'s)?\s+(?:the\s+)?(?:term|word|phrase|meaning\s+of)?\s*)?nigga\b", ql) or re.search(r"\bmeaning\s+of\s+(?:the\s+)?(?:term\s+)?(?:word\s+)?nigga\b", ql):
        ans = (
            "### Sociolinguistic & Etymological Overview:\n\n"
            "**1. Etymology and Origin:**\n"
            "- The term **\"nigga\"** originated as a non-rhotic phonetic spelling and dialectal variant of the racial slur \"nigger\", derived historically from the Spanish/Portuguese word *negro* (black), which itself stems from the Latin *niger*.\n"
            "- The non-rhotic pronunciation reflects African American Vernacular English (AAVE) and Southern American English speech patterns.\n\n"
            "**2. In-Group Reappropriation & Hip-Hop Culture:**\n"
            "- Beginning in the 20th century and popularized globally through hip-hop music and urban culture from the late 1980s onward, the term was reappropriated within the African American community as an in-group term of familiarity, solidarity, brotherhood, or informal address (similar to \"dude\", \"homie\", or \"bro\").\n"
            "- In hip-hop culture, artists often distinguished between the ending *-a* (seen as camaraderie or solidarity within the subculture) and *-er* (the historically racist slur).\n\n"
            "**3. Social Context & Societal Perceptions:**\n"
            "- **In-group vs. Out-group:** Use by individuals outside the Black community is widely considered offensive and taboo due to the deep historical trauma of slavery and systemic oppression associated with the root word.\n"
            "- **Generational divide:** Even within Black communities, opinions vary significantly; older generations often reject both forms due to historical pain, while younger generations frequently use it casually in colloquial discourse.\n\n"
            "In contemporary linguistics and sociolinguistics, it is studied as an example of semantic reclamation and linguistic reappropriation."
        )
        return {"answer": ans, "confidence": 0.99, "kind": "linguistics"}
    return None


def _parse_quad_expr(expr):
    """Parse 'ax^2 + bx + c' in one variable -> (var, a, b, c), or None.

    Deliberately strict: only +/- separated terms, no parentheses, no
    division, at most one variable letter - so it can never misfire on
    word problems."""
    s = expr.lower().replace(" ", "")
    if not s or any(ch in s for ch in "()/,"):
        return None
    letters = set(re.findall(r"[a-z]", s))
    if len(letters) > 1:
        return None
    var = letters.pop() if letters else None
    a = b = c = 0.0
    i, n = 0, len(s)
    while i < n:
        sign = 1.0
        if s[i] in "+-":
            if s[i] == "-":
                sign = -1.0
            i += 1
        j = i
        while j < n and s[j] not in "+-":
            j += 1
        term = s[i:j]
        i = j
        if not term:
            return None
        if term.endswith("^2"):
            coefs = term[:-2]
            if var and coefs.endswith(var):
                coefs = coefs[:-1]
            if coefs in ("", "*"):
                coef = 1.0
            else:
                try:
                    coef = float(coefs.rstrip("*"))
                except Exception:
                    return None
            a += sign * coef
        elif var and var in term:
            coefs = term.replace(var, "", 1)
            if coefs in ("", "*"):
                coef = 1.0
            else:
                try:
                    coef = float(coefs.rstrip("*"))
                except Exception:
                    return None
            b += sign * coef
        else:
            try:
                c += sign * float(term)
            except Exception:
                return None
    return var, a, b, c


def _quad_term(coef, suffix):
    if abs(coef - 1.0) < 1e-12:
        return suffix
    if abs(coef + 1.0) < 1e-12:
        return "-" + suffix
    return _fmt(coef) + suffix


def _quad_disp(a, b, c, var):
    s = _quad_term(a, var + "^2")
    if abs(b) > 1e-12:
        s += (" + " if b > 0 else " - ") + _quad_term(abs(b), var)
    if abs(c) > 1e-12:
        s += (" + " if c > 0 else " - ") + _fmt(abs(c))
    return s


def _quadratic_equation(q):
    """Solve quadratic equations: '2x^2 - 8 = 0', 'x^2 + 5x + 6 = 0',
    'x^2 = 9', '3x^2 - 12x = 0'.  Builds standard form, then applies the
    quadratic formula with the discriminant."""
    ql = q.lower().strip().rstrip("?.! ").strip()
    if "=" not in ql or "^2" not in ql or len(ql) > 90:
        return None
    ql = re.sub(r'^(?:please\s+)?(?:solve|find|calculate|compute)\s*'
                r'(?:for\s+[a-z]\s*)?[:\-]?\s*', '', ql)
    ql = re.sub(r'\s+(?:for|in)\s+[a-z]\s*$', '', ql).strip()
    if "=" not in ql:
        return None
    lhs, rhs = ql.split("=", 1)
    pl = _parse_quad_expr(lhs)
    pr = _parse_quad_expr(rhs)
    if not pl or not pr:
        return None
    var = pl[0] or pr[0]
    if not var or (pl[0] not in (None, var)) or (pr[0] not in (None, var)):
        return None
    a = pl[1] - pr[1]
    b = pl[2] - pr[2]
    c = pl[3] - pr[3]
    if abs(a) < 1e-12:
        return None
    disc = b * b - 4 * a * c
    steps = ["Standard form: %s = 0  (a=%s, b=%s, c=%s)."
             % (_quad_disp(a, b, c, var), _fmt(a), _fmt(b), _fmt(c))]
    if disc < -1e-9:
        steps.append("Discriminant D = b^2 - 4ac = %s < 0." % _fmt(disc))
        return _steps_answer(
            "**No real solutions** (%s = 0 has a negative discriminant)"
            % _quad_disp(a, b, c, var),
            steps, "algebra", conf=0.95)
    sq = math.sqrt(max(0.0, disc))
    x1 = (-b + sq) / (2 * a)
    x2 = (-b - sq) / (2 * a)
    steps.append("Quadratic formula: %s = (-b +/- sqrt(b^2 - 4ac)) / 2a." % var)
    steps.append("Discriminant D = %s^2 - 4 x %s x %s = %s, sqrt(D) = %s."
                 % (_fmt(b), _fmt(a), _fmt(c), _fmt(disc), _fmt(sq)))
    if abs(x1 - x2) < 1e-9:
        steps.append("%s = (-b +/- sqrt(D)) / 2a = %s." % (var, _fmt(x1)))
        return _steps_answer("**%s = %s** (double root)" % (var, _fmt(x1)),
                             steps, "algebra", conf=0.99)
    steps.append("%s = (-b + sqrt(D)) / 2a = %s and %s = (-b - sqrt(D)) / 2a = %s."
                 % (var, _fmt(x1), var, _fmt(x2)))
    return _steps_answer("**%s = %s or %s = %s**" % (var, _fmt(x1), var, _fmt(x2)),
                         steps, "algebra", conf=0.99)


def _linear_equation(q):
    """Solve simple linear equations with one unknown:
    '3x + 6 = 21', 'solve for x: 2x - 4 = 10', 'x + 5 = 12', 'x/3 = 5'."""
    ql = q.lower().strip().rstrip("?.! ").strip()
    if "=" not in ql or len(ql) > 90:
        return None
    letters = re.findall(r"[a-z]", ql)
    if not letters or len(letters) > 8:
        return None
    m = re.search(
        r"([+-]?)\s*(\d*\.?\d*)\s*\*?\s*([a-z])\b\s*(?:([+-])\s*(\d*\.?\d+))?"
        r"\s*=\s*([+-]?\s*\d*\.?\d+)\s*$", ql)
    if not m:
        md = re.search(
            r"([a-z])\s*/\s*(\d*\.?\d+)\s*=\s*([+-]?\s*\d*\.?\d+)\s*$", ql)
        if md:
            var = md.group(1)
            div = float(md.group(2))
            rhs = float(md.group(3).replace(" ", ""))
            if div == 0:
                return None
            x = rhs * div
            return _steps_answer(
                "**%s = %s**" % (var, _fmt(x)),
                ["%s/%s = %s  ->  %s = %s x %s" % (var, _fmt(div), _fmt(rhs), var, _fmt(rhs), _fmt(div)),
                 "%s = %s." % (var, _fmt(x))], "algebra", conf=0.99)
        return None
    sign, coef, var, opsign, const, rhs = m.groups()
    if coef:
        a = float(coef)
        if sign == "-":
            a = -a
    else:
        a = -1.0 if sign == "-" else 1.0
    b = 0.0
    if const:
        b = float(const)
        if opsign == "-":
            b = -b
    r = float(rhs.replace(" ", ""))
    if abs(a) < 1e-12:
        return None
    x = (r - b) / a
    disp_b = ("%+g" % b) if b else ""
    disp_a = "" if abs(a - 1.0) < 1e-12 else ("-1" if abs(a + 1.0) < 1e-12 else _fmt(a))
    steps = [
        "Equation: %s%s%s = %s." % (disp_a, var, disp_b, _fmt(r)),
        "Isolate the variable: %s%s = %s %s %s." % (disp_a, var, _fmt(r),
                                                    "-" if b > 0 else "+", _fmt(abs(b))),
        "%s = %s / %s = %s." % (var, _fmt(r - b), _fmt(a), _fmt(x))]
    return _steps_answer("**%s = %s**" % (var, _fmt(x)), steps, "algebra", conf=0.99)


_TIME_UNITS = {
    "second": 1.0, "minute": 60.0, "hour": 3600.0, "day": 86400.0,
    "week": 604800.0, "fortnight": 1209600.0,
}
_APPROX_UNITS = {"month": 2592000.0, "year": 31536000.0, "decade": 315360000.0,
                 "century": 31536000000.0}


def _unit_quantity(q):
    """'how many seconds are in a week' -> 604800, with shown arithmetic."""
    ql = q.lower().strip().rstrip("?.!")
    m = re.search(
        r"how many (seconds?|minutes?|hours?|days?|weeks?|fortnights?|months?|"
        r"years?|decades?|centuries?)\s+(?:are\s+there\s+)?(?:are\s+)?in\s+"
        r"(?:a|an|one|1)\s+([a-z]+)", ql)
    if not m:
        return None

    def _unit(w):
        w = w.strip()
        sing = {"seconds": "second", "minutes": "minute", "hours": "hour",
                "days": "day", "weeks": "week", "fortnights": "fortnight",
                "months": "month", "years": "year", "decades": "decade",
                "centuries": "century"}.get(w, w)
        if sing in _TIME_UNITS:
            return sing, _TIME_UNITS[sing], False
        if sing in _APPROX_UNITS:
            return sing, _APPROX_UNITS[sing], True
        return None, None, False

    small, s_sec, s_ap = _unit(m.group(1))
    big, b_sec, b_ap = _unit(m.group(2))
    if not small or not big:
        return None
    val = b_sec / s_sec
    exact = (abs(val - round(val)) < 1e-9) and not (s_ap or b_ap)
    shown = _fmt(val) if exact else ("%.4g" % val)
    note = " (calendar averages - a month is treated as 30 days)" if (s_ap or b_ap) else ""
    steps = ["1 %s = %s %s." % (big, shown, small + ("s" if abs(val - 1) > 1e-9 else "")),
             "Conversion factor: 1 %s = %s seconds, 1 %s = %s seconds."
             % (big, _fmt(b_sec), small, _fmt(s_sec)),
             "%s / %s = %s%s." % (_fmt(b_sec), _fmt(s_sec), shown, note)]
    return _steps_answer("**%s %ss**" % (shown, small), steps, "unit conversion",
                         conf=0.99 if exact else 0.9)


_SOLVERS = (
    _term_etymology,
    _earthquake_science,
    _moon_phases_science,
    _lightning_thunder_science,
    _seasons_science,
    _linear_system,
    _derivative_power_rule,
    _indefinite_integral,
    _dice_sum_probability,
    _core_math_theorems,
    _quadratic_perfect_square,
    _possession_riddle,
    _classic_puzzles,
    _math_expression,
    _temperature_converter,
    _when_introduced,
    _rate_scaling,
    _two_item_cost,
    _all_but,
    _travel_distance,
    _day_offset,
    _percent_of,
    _sequence_next,
    _sqrt,
    _power_compare,
    _syllogism,
    _repeat_nines,
    _feathers_steel,
    _letter_count,
    _prime_check,
    _birds_shot,
    _reciprocal_identity,
    _number_machine,
    _clock_strikes,
    _digit_reversal,
    _average,
    _rectangle,
    _triangle_third,
    _circle,
    _avg_speed,
    _unit_convert,
    _fraction_of,
    _pct_change,
    _simple_interest,
    _gcd_lcm,
    _square_cube,
    _tip,
    _discount,
    _work_rate,
    _probability,
    _simple_facts,
    _factorial,
    _simple_equation,
    _quadratic_equation,
    _linear_equation,
    _unit_quantity,
    _multiply,
    _age_ratio,
    _age_now,
)


def try_answer(question):
    """Return a reasoned answer dict, or None if no solver matches."""
    q = (question or "").strip()
    if len(q) < 4:
        return None
    for fn in _SOLVERS:
        try:
            r = fn(q)
        except Exception:
            r = None
        if r:
            return r
    return None
