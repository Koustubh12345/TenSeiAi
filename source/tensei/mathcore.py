"""TenSeiAi math core: deterministic solvers for the math/word problems the
tiny language model used to get wrong.  Every solver returns None when it is
not sure, so the caller can fall through to retrieval instead of guessing."""

import ast
import math
import re

_NUM = r"(\d[\d,]*(?:\.\d+)?)"

_WORD_NUM = {
    "zero": 0, "one": 1, "two": 2, "three": 3, "four": 4, "five": 5,
    "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10,
    "eleven": 11, "twelve": 12, "thirteen": 13, "fourteen": 14,
    "fifteen": 15, "sixteen": 16, "seventeen": 17, "eighteen": 18,
    "nineteen": 19, "twenty": 20,
}


def _word_int(s):
    s = (s or "").strip().lower().replace(",", "")
    if re.fullmatch(r"\d+", s):
        return int(s)
    return _WORD_NUM.get(s)


def _n(s):
    try:
        return float(str(s).replace(",", ""))
    except Exception:
        return None


def _fmt(x):
    if x is None:
        return ""
    if isinstance(x, bool):
        return str(x)
    if abs(x - round(x)) < 1e-9:
        return str(int(round(x)))
    s = ("%.6f" % x).rstrip("0").rstrip(".")
    return s


def _money(x):
    return "$" + _fmt(x)


def _ans(text, kind="math", conf=0.97, steps=None):
    body = "**Answer:** **%s**" % text
    if steps:
        body += "\n\n*How I reasoned it out:*\n" + "\n".join(
            "%d. %s" % (i + 1, s) for i, s in enumerate(steps))
    return {"answer": body, "kind": kind, "confidence": conf,
            "mode": "math"}


def _ratio(s):
    m = re.match(r"\s*(\d+)\s*[/:]\s*(\d+)\s*$", s or "")
    return (int(m.group(1)), int(m.group(2))) if m else None


# ---------------------------------------------------------------- percent
def percent_of(q):
    ql = q.lower()
    if "percent" not in ql and "%" not in ql and " per cent" not in ql:
        return None
    vals = re.findall(r"(\d[\d,]*(?:\.\d+)?)\s*%", q)
    base = re.findall(r"(?:of|from)\s+(\d[\d,]*(?:\.\d+)?)", q)
    if not vals or not base:
        return None
    try:
        pcts = [float(v.replace(",", "")) for v in vals]
        bases = [float(b.replace(",", "")) for b in base]
    except ValueError:
        return None
    if len(pcts) == 1:
        v = pcts[0] * bases[0] / 100.0
        return _ans(_fmt(v), "percentage",
                    steps=["%s%% of %s = %s x %s / 100 = %s"
                           % (_fmt(pcts[0]), _fmt(bases[0]), _fmt(pcts[0]),
                              _fmt(bases[0]), _fmt(v))])
    if len(pcts) >= 2:
        v = bases[0]
        for p in pcts:
            v = v * p / 100.0
        return _ans(_fmt(v), "percentage",
                    steps=["%s%% of %s%% of %s = %s"
                           % (_fmt(pcts[0]), _fmt(pcts[1]), _fmt(bases[0]),
                              _fmt(v))])
    return None


def percent_change(q):
    m = re.search(r"from\s+" + _NUM + r"\s+to\s+" + _NUM, q, re.I)
    if not m or not re.search(r"(percent|percentage|%)\s*(change|increase|decrease)",
                              q, re.I):
        return None
    a, b = _n(m.group(1)), _n(m.group(2))
    if not a:
        return None
    v = (b - a) / a * 100.0
    return _ans("%s%% %s" % (_fmt(abs(v)), "increase" if v >= 0 else "decrease"),
                "percentage change",
                steps=["Change = (%s - %s) / %s x 100 = %s%%"
                       % (_fmt(b), _fmt(a), _fmt(a), _fmt(v))])


def discount(q):
    ql = q.lower()
    if not re.search(r"discount|sale|\boff\b|reduced", ql):
        return None
    m = re.search(r"(?:costs?|price[sd]?|at)\s*\$?\s*" + _NUM, q, re.I)
    if not m:
        m = re.search(r"\$\s*" + _NUM, q, re.I)
    d = re.search(r"(?:discount(?:ed)?(?:\s+by)?|off|reduced by)\s*" + _NUM + r"\s*%", q, re.I)
    if not m or not d:
        return None
    price, pct = _n(m.group(1)), _n(d.group(1))
    sale = price * (1 - pct / 100.0)
    return _ans(_money(sale), "discount",
                steps=["Discount = %s%% of %s = %s" % (_fmt(pct), _money(price),
                                                        _money(price * pct / 100.0)),
                       "Sale price = %s - %s = %s"
                       % (_money(price), _money(price * pct / 100.0),
                          _money(sale))])


def tax_total(q):
    """Price plus a percentage tax/VAT: '$80 item is taxed at 8%'."""
    ql = q.lower()
    if not re.search(r"\b(?:tax|taxed|vat|sales tax)\b", ql):
        return None
    m = re.search(r"\$\s*(\d[\d,]*(?:\.\d+)?).*?"
                  r"(\d[\d,]*(?:\.\d+)?)\s*%", q, re.I | re.S)
    if not m:
        m = re.search(r"(\d[\d,]*(?:\.\d+)?)\s*%.*?\$\s*"
                      r"(\d[\d,]*(?:\.\d+)?)", q, re.I | re.S)
        if m:
            pct, price = _n(m.group(1)), _n(m.group(2))
        else:
            return None
    else:
        price, pct = _n(m.group(1)), _n(m.group(2))
    if price is None or pct is None:
        return None
    tax = price * pct / 100.0
    total = price + tax
    return _ans(_money(total), "tax",
                steps=["Tax = %s%% of %s = %s"
                       % (_fmt(pct), _money(price), _money(tax)),
                       "Total = %s + %s = %s"
                       % (_money(price), _money(tax), _money(total))])


def tip_tax(q):
    m = re.search(r"(?:bill|meal|check|price|costs?)\s*(?:of|is|was)?\s*\$?\s*"
                  + _NUM + r".*?(\d[\d,]*(?:\.\d+)?)\s*%\s*(tip|tax)", q, re.I)
    if not m:
        m = re.search(r"(\d[\d,]*(?:\.\d+)?)\s*%\s*(tip|tax).*?\$?\s*"
                      + _NUM, q, re.I)
        if m:
            pct, kind, base = _n(m.group(1)), m.group(2), _n(m.group(3))
        else:
            return None
    else:
        base, pct, kind = _n(m.group(1)), _n(m.group(2)), m.group(3)
    amt = base * pct / 100.0
    return _ans("Tip = %s, total = %s" % (_money(amt), _money(base + amt))
                if kind == "tip" else "%s = %s" % (kind.title(), _money(amt)),
                kind, steps=["%s%% of %s = %s" % (_fmt(pct), _money(base),
                                                   _money(amt))])


def simple_interest(q):
    m = re.search(r"(?:principal|invests?|deposits?|loan[s]?|sum)?\s*\$?\s*"
                  + _NUM + r".*?(\d[\d,]*(?:\.\d+)?)\s*%\s*(?:per year|annually|annual|a year|/year)?.*?"
                  r"(\d[\d,]*(?:\.\d+)?)\s*(?:years?|yrs?)", q, re.I)
    if not m or not re.search(r"interest", q, re.I):
        return None
    p, r, t = _n(m.group(1)), _n(m.group(2)), _n(m.group(3))
    interest = p * r * t / 100.0
    return _ans(_money(interest), "simple interest",
                steps=["I = P x R x T / 100 = %s x %s x %s / 100 = %s"
                       % (_money(p), _fmt(r), _fmt(t), _money(interest))])


def compound_interest(q):
    m = re.search(r"(?:principal|invests?|deposits?|loan[s]?|sum)?\s*\$?\s*"
                  + _NUM + r".*?(\d[\d,]*(?:\.\d+)?)\s*%.*?"
                  r"(\d[\d,]*(?:\.\d+)?)\s*(?:years?|yrs?)", q, re.I)
    if not m or not re.search(r"compound", q, re.I):
        return None
    p, r, t = _n(m.group(1)), _n(m.group(2)), _n(m.group(3))
    amount = p * (1 + r / 100.0) ** t
    return _ans(_money(amount - p) + " interest (total %s)" % _money(amount),
                "compound interest",
                steps=["A = P(1 + r)^t = %s(1 + %s)^%s = %s"
                       % (_money(p), _fmt(r / 100.0), _fmt(t), _money(amount))])


# ---------------------------------------------------------------- algebra
def linear_equation(q):
    if re.search(r"squared|\^2|²", q, re.I):
        return None
    if not re.search(r"\bsolve\b|=\s*-?\d", q, re.I):
        return None
    # Keep only the equation part: "Solve for x: 4x - 9 = 23" must not feed
    # the words "solve for x" into the coefficient parser.
    m = re.search(r"([-+0-9xX\s.]+?)\s*=\s*([-+0-9xX\s.]+)", q)
    if not m:
        return None
    lhs, rhs = m.group(1), m.group(2)
    if "x" not in (lhs + rhs).lower():
        return None

    def coeff(expr, sign=1):
        a = b = 0.0
        expr = expr.replace(" ", "")
        expr = re.sub(r"^\+", "", expr)
        for term in re.findall(r"[+-]?[^+-]+", expr):
            if not term:
                continue
            if "x" in term.lower():
                c = term.lower().replace("x", "")
                if c in ("", "+"):
                    a += sign
                elif c == "-":
                    a -= sign
                else:
                    try:
                        a += sign * float(c)
                    except ValueError:
                        return None
            else:
                try:
                    b += sign * float(term)
                except ValueError:
                    return None
        return a, b

    cl = coeff(lhs)
    cr = coeff(rhs)
    if cl is None or cr is None:
        return None
    a = cl[0] - cr[0]
    b = cr[1] - cl[1]
    if abs(a) < 1e-12:
        return None
    x = b / a
    return _ans("x = %s" % _fmt(x), "linear equation",
                steps=["%s x = %s" % (_fmt(a), _fmt(b)),
                       "x = %s / %s = %s" % (_fmt(b), _fmt(a), _fmt(x))])


def quadratic(q):
    ql = q.lower()
    if not re.search(r"squared|x\s*\^\s*2|x2|\bx²", ql):
        return None
    if "=" not in ql and "equals" not in ql and "equal to" not in ql:
        return None
    # normalise words
    t = ql.replace("equal to", "=").replace("equals", "=")
    t = re.sub(r"=\s*zero\b", "= 0", t)
    t = re.sub(r"=\s*nought\b", "= 0", t)
    t = t.replace("plus", "+").replace("minus", "-")
    t = t.replace("squared", "^2").replace("²", "^2")
    t = re.sub(r"\bx\s*\^\s*2", "x^2", t)
    # Simple form: x^2 = 49 (the right side is not zero).
    m = re.search(r"x\^2\s*=\s*(-?\d+(?:\.\d+)?)", t)
    if m:
        n = float(m.group(1))
        if n < 0:
            return _ans("no real solutions", "quadratic",
                        steps=["A square cannot equal a negative real number."])
        r = math.sqrt(n)
        if re.search(r"\bpositive\b|\bpositive root\b", ql):
            return _ans("x = %s" % _fmt(r), "quadratic",
                        steps=["x² = %s" % _fmt(n),
                               "x = sqrt(%s) = %s (positive root)" % (_fmt(n), _fmt(r))])
        return _ans("x = %s or x = %s" % (_fmt(r), _fmt(-r)), "quadratic",
                    steps=["x² = %s" % _fmt(n),
                           "x = ±sqrt(%s) = ±%s" % (_fmt(n), _fmt(r))])
    m = re.search(r"([-+0-9x^.\s]+)=\s*0", t)
    if not m:
        return None
    expr = m.group(1).replace(" ", "")
    a = b = c = 0.0
    for term in re.findall(r"[+-]?[^+-]+", expr):
        if not term:
            continue
        if "x^2" in term:
            v = term.replace("x^2", "")
            a += 1.0 if v in ("", "+") else (-1.0 if v == "-" else float(v))
        elif "x" in term:
            v = term.replace("x", "")
            b += 1.0 if v in ("", "+") else (-1.0 if v == "-" else float(v))
        else:
            try:
                c += float(term)
            except ValueError:
                return None
    if abs(a) < 1e-12:
        return linear_equation(q)
    disc = b * b - 4 * a * c
    if disc < -1e-9:
        return _ans("no real solutions (discriminant = %s)" % _fmt(disc),
                    "quadratic")
    if abs(disc) < 1e-9:
        r = -b / (2 * a)
        return _ans("x = %s" % _fmt(r), "quadratic",
                    steps=["Discriminant = 0", "x = -b / 2a = %s" % _fmt(r)])
    s = math.sqrt(disc)
    r1, r2 = (-b + s) / (2 * a), (-b - s) / (2 * a)
    lo, hi = sorted((r1, r2))
    return _ans("x = %s or x = %s" % (_fmt(lo), _fmt(hi)), "quadratic",
                steps=["a=%s, b=%s, c=%s" % (_fmt(a), _fmt(b), _fmt(c)),
                       "Discriminant = b² - 4ac = %s" % _fmt(disc),
                       "Roots: x = %s and x = %s" % (_fmt(lo), _fmt(hi))])


# ---------------------------------------------------------------- sequences
def successor(q):
    """Small, exact counting questions: "what comes after 55", "number before 10"."""
    m = re.search(
        r"\b(?:what|which)\s+(?:number\s+)?(?:comes?|is)\s+"
        r"(?:right\s+)?(after|before|next\s+after|just\s+after)\s+"
        r"(-?\d+(?:\.\d+)?)\b", q, re.I)
    if not m:
        m = re.search(
            r"\b(?:next|previous)\s+(?:number\s+)?(?:after|before)\s+"
            r"(-?\d+(?:\.\d+)?)\b", q, re.I)
        if not m:
            return None
        n = _n(m.group(1))
        direction = 1 if re.search(r"next|after", q, re.I) else -1
    else:
        n = _n(m.group(2))
        direction = -1 if "before" in m.group(1).lower() else 1
    nxt = n + direction
    if float(nxt).is_integer():
        nxt = int(nxt)
    return _ans(_fmt(nxt), "successor",
                steps=["Counting one step %s %s gives %s."
                       % ("after" if direction > 0 else "before",
                          _fmt(n), _fmt(nxt))])


def sequence(q):
    m = re.search(r"sequence[:\s]+([-+]?\d[\d,\s.]*)(?:\?|$)", q, re.I)
    if not m:
        m = re.search(r"([-+]?\d+(?:\s*,\s*[-+]?\d+){3,})\s*[,.]?\s*(?:\?|what|next|$)",
                      q, re.I)
    if not m:
        return None
    raw = re.findall(r"[-+]?\d+(?:\.\d+)?", m.group(1))
    if len(raw) < 3:
        return None
    xs = [float(x) for x in raw]
    diffs = [xs[i + 1] - xs[i] for i in range(len(xs) - 1)]
    if len(set(round(d, 9) for d in diffs)) == 1:
        nxt = xs[-1] + diffs[-1]
        return _ans(_fmt(nxt), "sequence",
                    steps=["Common difference = %s" % _fmt(diffs[-1]),
                           "Next = %s + %s = %s" % (_fmt(xs[-1]), _fmt(diffs[-1]), _fmt(nxt))])
    if all(x != 0 for x in xs[:-1]) and len(set(round(xs[i + 1] / xs[i], 9)
                                               for i in range(len(xs) - 1))) == 1:
        r = xs[1] / xs[0]
        nxt = xs[-1] * r
        return _ans(_fmt(nxt), "sequence",
                    steps=["Common ratio = %s" % _fmt(r),
                           "Next = %s x %s = %s" % (_fmt(xs[-1]), _fmt(r), _fmt(nxt))])
    # constant second difference: 2,5,10,17,26 (differences 3,5,7,9)
    if len(diffs) >= 2:
        second = [diffs[i + 1] - diffs[i] for i in range(len(diffs) - 1)]
        if len(set(round(d, 9) for d in second)) == 1:
            step = diffs[-1] + second[-1]
            nxt = xs[-1] + step
            return _ans(_fmt(nxt), "sequence",
                        steps=["First differences = %s"
                               % ", ".join(_fmt(d) for d in diffs),
                               "Second difference = %s" % _fmt(second[-1]),
                               "Next difference = %s + %s = %s"
                               % (_fmt(diffs[-1]), _fmt(second[-1]), _fmt(step)),
                               "Next = %s + %s = %s"
                               % (_fmt(xs[-1]), _fmt(step), _fmt(nxt))])
    # perfect squares: 1,4,9,16,25
    for start in (1, 2, 3):
        if all(abs(xs[i] - (i + start) ** 2) < 1e-9 for i in range(len(xs))):
            nxt = (len(xs) + start) ** 2
            return _ans(_fmt(nxt), "sequence",
                        steps=["Pattern is n^2.",
                               "Next = %d^2 = %s" % (len(xs) + start, _fmt(nxt))])
    # n(n+1): 2,6,12,20,30
    for start in (1, 2, 3):
        if all(abs(xs[i] - (i + start) * (i + start + 1)) < 1e-9
               for i in range(len(xs))):
            nxt = (len(xs) + start) * (len(xs) + start + 1)
            return _ans(_fmt(nxt), "sequence",
                        steps=["Pattern is n(n+1).",
                               "Next = %d x %d = %s" % (len(xs) + start,
                                                         len(xs) + start + 1,
                                                         _fmt(nxt))])
    # fibonacci-like
    if all(abs(xs[i] - (xs[i - 1] + xs[i - 2])) < 1e-9 for i in range(2, len(xs))):
        nxt = xs[-1] + xs[-2]
        return _ans(_fmt(nxt), "sequence",
                    steps=["Each term is the sum of the previous two.",
                           "Next = %s + %s = %s" % (_fmt(xs[-1]), _fmt(xs[-2]), _fmt(nxt))])
    return None


# ---------------------------------------------------------------- geometry
def circle(q):
    m = re.search(r"circle.*?radius\s*(?:of|is|=)?\s*" + _NUM, q, re.I)
    if not m:
        return None
    r = _n(m.group(1))
    pi = 22.0 / 7.0 if re.search(r"22\s*/\s*7|pi\s*=\s*22", q, re.I) else math.pi
    if re.search(r"circumference", q, re.I):
        v = 2 * pi * r
        return _ans(_fmt(v) + " cm", "circle",
                    steps=["C = 2 x pi x r = 2 x %s x %s = %s"
                           % (_fmt(pi), _fmt(r), _fmt(v))])
    v = pi * r * r
    return _ans(_fmt(v) + " cm²", "circle",
                steps=["Area = pi x r² = %s x %s² = %s"
                       % (_fmt(pi), _fmt(r), _fmt(v))])


def polygon_angle(q):
    if re.search(r"\bratio\b", q, re.I):
        return None
    if not re.search(r"interior angle|each angle|\bangle\b", q, re.I):
        return None
    names = {"triangle": 3, "quadrilateral": 4, "pentagon": 5, "hexagon": 6,
             "heptagon": 7, "septagon": 7, "octagon": 8, "nonagon": 9,
             "decagon": 10, "dodecagon": 12}
    sides = None
    for name, n in names.items():
        if re.search(r"\b" + name + r"\b", q, re.I):
            sides = n
            break
    if sides is None:
        m = re.search(r"\b(\d+)[- ]sided\b", q, re.I)
        if m:
            sides = int(m.group(1))
    if not sides:
        return None
    if re.search(r"how many diagonals", q, re.I):
        v = sides * (sides - 3) // 2
        return _ans(_fmt(v), "polygon",
                    steps=["Diagonals = n(n-3)/2 = %d x %d / 2 = %s"
                           % (sides, sides - 3, _fmt(v))])
    if re.search(r"sum of", q, re.I):
        v = (sides - 2) * 180
        return _ans("%s degrees" % _fmt(v), "polygon",
                    steps=["Sum of interior angles = (n-2) x 180 = "
                           "(%d-2) x 180 = %s degrees" % (sides, _fmt(v))])
    v = (sides - 2) * 180.0 / sides
    return _ans(_fmt(v) + "°", "polygon",
                steps=["Sum of interior angles = (n-2) x 180 = %s°"
                       % _fmt((sides - 2) * 180),
                       "Each angle = %s° / %d = %s°"
                       % (_fmt((sides - 2) * 180), sides, _fmt(v))])


def polygon_diagonals(q):
    if not re.search(r"diagonal", q, re.I):
        return None
    m = re.search(r"(?:regular\s+)?(\w+)", q, re.I)
    if not m:
        return None
    sides = {"triangle": 3, "quadrilateral": 4, "pentagon": 5, "hexagon": 6,
             "heptagon": 7, "octagon": 8, "nonagon": 9, "decagon": 10,
             "dodecagon": 12}.get(m.group(1).lower())
    if not sides:
        return None
    v = sides * (sides - 3) // 2
    return _ans(_fmt(v), "polygon",
                steps=["Diagonals = n(n-3)/2 = %d x %d / 2 = %s"
                       % (sides, sides - 3, _fmt(v))])


def square_geometry(q):
    ql = q.lower()
    if not re.search(r"\bsquare\b", ql):
        return None
    m = re.search(r"\bsquare\b.*?\bside\s*(?:of|is|=)?\s*" + _NUM, ql)
    if not m:
        m = re.search(r"\bperimeter\s+of\s+(?:a\s+)?square\b.*?" + _NUM, ql)
    if not m:
        return None
    s = _n(m.group(1))
    if s is None:
        return None
    if "perimeter" in ql:
        v = 4 * s
        return _ans(_fmt(v), "square",
                    steps=["Perimeter of a square = 4 x side = 4 x %s = %s"
                           % (_fmt(s), _fmt(v))])
    if "diagonal" in ql:
        v = s * math.sqrt(2)
        return _ans(_fmt(v), "square",
                    steps=["Diagonal = side x sqrt(2) = %s" % _fmt(v)])
    v = s * s
    return _ans(_fmt(v), "square",
                steps=["Area of a square = side² = %s² = %s"
                       % (_fmt(s), _fmt(v))])


def rectangle(q):
    m = re.search(r"rectangle\s+is\s*" + _NUM + r"\s*(?:cm|m|units?)?\s*(?:long|by)\s*(?:and\s*)?"
                  + _NUM, q, re.I)
    if not m:
        m = re.search(r"rectangle.*?(\d+(?:\.\d+)?)\s*(?:cm|m|units?)?\s*(?:long|by|x)\s*(?:and\s*)?"
                      r"(\d+(?:\.\d+)?)", q, re.I)
    if not m:
        return None
    a, b = _n(m.group(1)), _n(m.group(2))
    if re.search(r"diagonal", q, re.I):
        v = math.hypot(a, b)
        return _ans(_fmt(v) + " cm", "rectangle",
                    steps=["Diagonal = sqrt(%s² + %s²) = %s"
                           % (_fmt(a), _fmt(b), _fmt(v))])
    if re.search(r"perimeter", q, re.I):
        v = 2 * (a + b)
        return _ans(_fmt(v) + " cm", "rectangle",
                    steps=["Perimeter = 2 x (l + w) = %s" % _fmt(v)])
    v = a * b
    return _ans(_fmt(v) + " cm²", "rectangle",
                steps=["Area = length x width = %s x %s = %s"
                       % (_fmt(a), _fmt(b), _fmt(v))])


def triangle_area(q):
    m = re.search(r"triangle.*?base\s*(?:of|is|=)?\s*" + _NUM + r".*?height\s*(?:of|is|=)?\s*" + _NUM, q, re.I)
    if not m:
        return None
    b, h = _n(m.group(1)), _n(m.group(2))
    v = 0.5 * b * h
    return _ans(_fmt(v), "triangle",
                steps=["Area = 1/2 x base x height = %s" % _fmt(v)])


def triangle_ratio(q):
    m = re.search(r"angles?.*?ratio\s*(\d+)\s*:\s*(\d+)\s*:\s*(\d+)", q, re.I)
    if not m:
        m = re.search(r"ratio\s*(\d+)\s*:\s*(\d+)\s*:\s*(\d+).*?angle", q, re.I)
    if not m:
        return None
    a, b, c = int(m.group(1)), int(m.group(2)), int(m.group(3))
    total = a + b + c
    largest = 180.0 * max(a, b, c) / total
    return _ans(_fmt(largest) + "°", "triangle",
                steps=["Sum of ratio parts = %d" % total,
                       "Largest angle = 180 x %d / %d = %s°"
                       % (max(a, b, c), total, _fmt(largest))])


def pythagorean(q):
    m = re.search(r"right triangle.*?legs?\s*(?:of|are)?\s*" + _NUM + r"\s*(?:and|,)\s*" + _NUM, q, re.I)
    if not m:
        return None
    a, b = _n(m.group(1)), _n(m.group(2))
    v = math.hypot(a, b)
    return _ans(_fmt(v), "pythagorean",
                steps=["Hypotenuse = sqrt(%s² + %s²) = %s"
                       % (_fmt(a), _fmt(b), _fmt(v))])


# ---------------------------------------------------------------- rates
def speed(q):
    m = re.search(r"(?:travels?|covers?|drives?|runs?|flies?)\s*" + _NUM +
                  r"\s*(km|kilometers?|miles?|m|meters?)\s*(?:in|over|per|/)\s*"
                  + _NUM + r"\s*(hours?|hrs?|h|minutes?|mins?|m)", q, re.I)
    if not m:
        return None
    d, du, t, tu = _n(m.group(1)), m.group(2).lower(), _n(m.group(3)), m.group(4).lower()
    if tu.startswith("min") or tu == "m":
        t = t / 60.0
    if not t:
        return None
    v = d / t
    unit = "km/h" if du.startswith("k") or du.startswith("kilom") else ("mph" if du.startswith("mi") else "m/s")
    return _ans("%s %s" % (_fmt(v), unit), "speed",
                steps=["Speed = distance / time = %s / %s = %s %s"
                       % (_fmt(d), _fmt(t), _fmt(v), unit)])


def fuel(q):
    m = re.search(r"uses?\s*" + _NUM + r"\s*(?:liters?|litres?|l)\s*(?:of fuel\s*)?per\s*100\s*km.*?"
                  r"(?:for|in|over)\s*" + _NUM + r"\s*km", q, re.I)
    if not m:
        return None
    rate, dist = _n(m.group(1)), _n(m.group(2))
    v = rate * dist / 100.0
    return _ans(_fmt(v) + " liters", "fuel",
                steps=["Fuel = %s x %s / 100 = %s liters"
                       % (_fmt(rate), _fmt(dist), _fmt(v))])


def recipe(q):
    m = re.search(r"" + _NUM + r"\s*cups?\s*(?:of\s+\w+\s*)?for\s*(\d+)\s*\w+.*?"
                  r"(?:for|to make)\s*(\d+)", q, re.I)
    if not m:
        return None
    cups, base, want = _n(m.group(1)), _n(m.group(2)), _n(m.group(3))
    v = cups * want / base
    return _ans(_fmt(v) + " cups", "ratio",
                steps=["%s cups / %s items = %s cups per item"
                       % (_fmt(cups), _fmt(base), _fmt(cups / base)),
                       "For %s items: %s x %s = %s cups"
                       % (_fmt(want), _fmt(cups / base), _fmt(want), _fmt(v))])


def average(q):
    if not re.search(r"\baverage\b|mean", q, re.I):
        return None
    nums = re.findall(r"[-+]?\d+(?:\.\d+)?", q)
    nums = [float(x) for x in nums]
    if len(nums) < 2:
        return None
    # only use numbers after "average of" if present
    m = re.search(r"average\s+of\s+([^.?!]+)", q, re.I)
    if m:
        nums = [float(x) for x in re.findall(r"[-+]?\d+(?:\.\d+)?", m.group(1))]
    if len(nums) < 2:
        return None
    v = sum(nums) / len(nums)
    return _ans(_fmt(v), "average",
                steps=["Sum = %s" % _fmt(sum(nums)),
                       "Average = %s / %d = %s" % (_fmt(sum(nums)), len(nums), _fmt(v))])


def work_rate(q):
    m = re.search(r"(\w+)\s+can\s+(?:finish|do|complete|paint|build)\s+(?:a\s+)?(?:job|work|task|project)\s+in\s*"
                  + _NUM + r"\s*(hours?|days?|minutes?).*?"
                  r"(\w+)\s+can\s+(?:finish|do|complete|paint|build)\s+(?:the\s+)?(?:same\s+)?(?:job|work|task|project)\s+in\s*"
                  + _NUM, q, re.I | re.S)
    if not m:
        return None
    t1, t2 = _n(m.group(2)), _n(m.group(4))
    if not t1 or not t2:
        return None
    v = (t1 * t2) / (t1 + t2)
    return _ans(_fmt(v) + " " + m.group(3), "work rate",
                steps=["Combined rate = 1/%s + 1/%s" % (_fmt(t1), _fmt(t2)),
                       "Time = %s" % _fmt(v)])


def inverse_workers(q):
    """More workers finish the same job in less time (inverse proportion)."""
    m = re.search(r"(\d+)\s+(?:workers|men|women|people|machines)\b.*?"
                  r"(?:in|take|takes|need|needs)\s+(\d+)\s+(days?|hours?|minutes?).*?"
                  r"(\d+)\s+(?:workers|men|women|people|machines)\b",
                  q, re.I | re.S)
    if not m:
        return None
    n1, t1, unit, n2 = (int(m.group(1)), _n(m.group(2)),
                        m.group(3).lower(), int(m.group(4)))
    if not n1 or not n2:
        return None
    total = n1 * t1
    t2 = total / n2
    return _ans("%s %s" % (_fmt(t2), unit), "inverse proportion",
                steps=["Total work = %d workers x %s %s = %s worker-%s"
                       % (n1, _fmt(t1), unit, _fmt(total), unit.rstrip("s")),
                       "Time for %d workers = %s / %d = %s %s"
                       % (n2, _fmt(total), n2, _fmt(t2), unit)])


def unit_convert(q):
    m = re.search(r"(?:convert\s+)?" + _NUM + r"\s*(km|kilometers?|miles?|kg|kilograms?|pounds?|lbs?|"
                  r"m|meters?|feet|ft|celsius|°c|fahrenheit|°f)\s*(?:to|in)\s*"
                  r"(km|kilometers?|miles?|kg|kilograms?|pounds?|lbs?|m|meters?|feet|ft|celsius|°c|fahrenheit|°f)",
                  q, re.I)
    if not m:
        return None
    v = _n(m.group(1))
    a, b = m.group(2).lower(), m.group(3).lower()
    if a.startswith("k") and b.startswith("mi"):
        r = v * 0.621371
    elif a.startswith("mi") and b.startswith("k"):
        r = v / 0.621371
    elif a.startswith("kg") and b.startswith(("lb", "pound")):
        r = v * 2.20462
    elif a.startswith(("lb", "pound")) and b.startswith("kg"):
        r = v / 2.20462
    elif a in ("celsius", "°c") and b in ("fahrenheit", "°f"):
        r = v * 9 / 5 + 32
    elif a in ("fahrenheit", "°f") and b in ("celsius", "°c"):
        r = (v - 32) * 5 / 9
    elif a in ("m", "meter", "meters") and b in ("feet", "ft"):
        r = v * 3.28084
    elif a in ("feet", "ft") and b in ("m", "meter", "meters"):
        r = v / 3.28084
    else:
        return None
    return _ans(_fmt(r), "unit conversion",
                steps=["%s %s = %s %s" % (_fmt(v), m.group(2), _fmt(r), m.group(3))])


# ---------------------------------------------------------------- number theory
def gcd_lcm(q):
    m = re.search(r"(gcd|hcf|lcm|least common multiple|greatest common divisor).*?"
                  r"(\d+)\D+(\d+)", q, re.I)
    if not m:
        return None
    a, b = int(m.group(2)), int(m.group(3))
    g = math.gcd(a, b)
    if m.group(1).lower().startswith(("lcm", "least")):
        v = a * b // g
        return _ans(_fmt(v), "lcm",
                    steps=["LCM = %d x %d / %d = %s" % (a, b, g, _fmt(v))])
    return _ans(_fmt(g), "gcd", steps=["GCD(%d, %d) = %s" % (a, b, _fmt(g))])


def primes(q):
    ql = q.lower()
    if "next prime" in ql:
        m = re.search(r"after\s+(\d+)", ql)
        if not m:
            return None
        n = int(m.group(1)) + 1
        while True:
            if all(n % d for d in range(2, int(n ** 0.5) + 1)):
                return _ans(_fmt(n), "prime",
                            steps=["The first prime greater than %s is %s"
                                   % (m.group(1), _fmt(n))])
            n += 1
    if re.search(r"is\s+(\d+)\s+(?:a\s+)?prime", ql):
        n = int(re.search(r"is\s+(\d+)\s+(?:a\s+)?prime", ql).group(1))
        ok = n > 1 and all(n % d for d in range(2, int(n ** 0.5) + 1))
        return _ans("%s is %s prime" % (n, "" if ok else "not"), "prime",
                    steps=["Checked divisors up to %d." % int(n ** 0.5)])
    if re.search(r"prime numbers? up to\s+(\d+)|primes? up to\s+(\d+)", ql):
        m = re.search(r"up to\s+(\d+)", ql)
        n = int(m.group(1))
        ps = [x for x in range(2, n + 1)
              if all(x % d for d in range(2, int(x ** 0.5) + 1))]
        return _ans(", ".join(str(x) for x in ps), "prime")
    return None


def factorial(q):
    m = re.search(r"factorial\s*(?:of\s*)?(\d+)", q, re.I)
    if not m:
        return None
    n = int(m.group(1))
    if n > 20:
        return None
    v = math.factorial(n)
    return _ans(_fmt(v), "factorial",
                steps=["%d! = %s" % (n, _fmt(v))])


def compare_powers(q):
    ql = q.lower()
    if not re.search(r"which\s+is\s+(?:bigger|larger|greater)|compare", ql):
        return None
    pairs = re.findall(
        r"(\d+(?:\.\d+)?)\s*(?:\^|to\s+the\s+power\s+of|raised\s+to)\s*(\d+)",
        q, re.I)
    if len(pairs) < 2:
        return None
    (a, b), (c, d) = pairs[0], pairs[1]
    va, vb = float(a) ** int(b), float(c) ** int(d)
    win = ("%s^%s" % (a, b)) if va > vb else ("%s^%s" % (c, d))
    return _ans("%s is bigger: %s^%s = %s, while %s^%s = %s."
                % (win, a, b, _fmt(va), c, d, _fmt(vb)),
                "power comparison",
                steps=["%s^%s = %s" % (a, b, _fmt(va)),
                       "%s^%s = %s" % (c, d, _fmt(vb)),
                       "Compare the two values: %s > %s"
                       % (_fmt(max(va, vb)), _fmt(min(va, vb)))])


def share(q):
    ql = q.lower()
    m = re.search(
        r"(\w+|\d[\d,]*)\s+(?:friends|people|children|students|workers|"
        r"persons)\s+(?:share|split|divide)\s+(\d[\d,]*)\s+"
        r"(?:apples?|oranges?|candies?|sweets?|items?|things?|coins?|"
        r"mangoes?|books?|pencils?|toys?|cookies?)",
        ql)
    if not m:
        return None
    n = _word_int(m.group(1))
    total = _n(m.group(2))
    if not n or total is None or n <= 0:
        return None
    each = total / n
    return _ans(_fmt(each), "sharing",
                steps=["Total = %s, people = %s" % (_fmt(total), _fmt(n)),
                       "Each gets %s / %s = %s"
                       % (_fmt(total), _fmt(n), _fmt(each))])


def power_sqrt(q):
    m = re.search(r"(?:square root|sqrt)\s*(?:of\s*)?(\d+(?:\.\d+)?)", q, re.I)
    if m:
        v = math.sqrt(_n(m.group(1)))
        return _ans(_fmt(v), "square root",
                    steps=["sqrt(%s) = %s" % (m.group(1), _fmt(v))])
    m = re.search(r"(\d+(?:\.\d+)?)\s*(?:\^|to the power of|raised to)\s*(\d+)", q, re.I)
    if m:
        v = _n(m.group(1)) ** int(m.group(2))
        return _ans(_fmt(v), "power",
                    steps=["%s^%s = %s" % (m.group(1), m.group(2), _fmt(v))])
    return None


def combination_permutation(q):
    m = re.search(r"(?:how many\s+)?(?:distinct\s+)?ways\s+(?:can|to)\s+(.*?)(?:\?|$)", q, re.I)
    if m and "arranged" in q.lower():
        word = re.search(r"word\s+([A-Za-z]+)", q)
        if word:
            w = word.group(1).upper()
            from collections import Counter
            c = Counter(w)
            n = len(w)
            v = math.factorial(n)
            for k in c.values():
                v //= math.factorial(k)
            return _ans(_fmt(v), "permutation",
                        steps=["Total letters = %d" % n,
                               "Repeated letters reduce the count.",
                               "Distinct arrangements = %s" % _fmt(v)])
    return None


# ---------------------------------------------------------------- probability
def probability(q):
    ql = q.lower()
    if "probability" not in ql and "chance" not in ql:
        return None
    if re.search(r"red card|red.*standard.*deck|deck.*red", ql):
        return _ans("1/2 (26 red cards out of 52).", "probability",
                    steps=["P(red) = 26/52 = 1/2."])
    m = re.search(r"total of\s+(\d+).*?(?:two|2).*?(?:six|6).*?(?:dice|die)", ql)
    if m:
        target = int(m.group(1))
        ways = sum(1 for a in range(1, 7) for b in range(1, 7)
                   if a + b == target)
        from fractions import Fraction
        f = Fraction(ways, 36)
        return _ans("%s (%d/36)" % (f, ways), "probability",
                    steps=["There are %d ways out of 36." % ways])
    if re.search(r"(?:six|6)[- ]sided|fair die|standard die", ql) and \
            re.search(r"\beven\b|\bodd\b", ql):
        from fractions import Fraction
        which = "even" if re.search(r"\beven\b", ql) else "odd"
        f = Fraction(3, 6)
        return _ans("%s (3/6)" % f, "probability",
                    steps=["There are 3 %s numbers out of 6 equally likely outcomes."
                           % which,
                           "P = 3/6 = 1/2."])
    m = re.search(r"rolling a\s+(\d+)", ql)
    if m:
        from fractions import Fraction
        f = Fraction(1, 6)
        return _ans(str(f), "probability",
                    steps=["A fair six-sided die has 6 outcomes."])
    # marbles
    m = re.search(r"(\d+)\s+red.*?(\d+)\s+blue.*?(\d+)\s+green", ql)
    if m:
        r, b, g = int(m.group(1)), int(m.group(2)), int(m.group(3))
        total = r + b + g
        if re.search(r"red", ql.split("probability")[-1] if "probability" in ql else ql):
            from fractions import Fraction
            return _ans(str(Fraction(r, total)), "probability",
                        steps=["P(red) = %d/%d." % (r, total)])
    return None


# ---------------------------------------------------------------- fractions
def fraction_add(q):
    m = re.search(r"(\d+)\s*/\s*(\d+)\s*(?:plus|\+|added to)\s*"
                  r"(\d+)\s*/\s*(\d+)", q, re.I)
    if not m:
        m = re.search(r"(\d+)\s*/\s*(\d+)\s*(?:minus|-)\s*"
                      r"(\d+)\s*/\s*(\d+)", q, re.I)
        if not m:
            return None
    a, b, c, d = (int(m.group(i)) for i in range(1, 5))
    if not b or not d:
        return None
    from fractions import Fraction
    op = "+" if re.search(r"plus|\+|added", m.group(0), re.I) else "-"
    f = Fraction(a, b) + Fraction(c, d) if op == "+" else Fraction(a, b) - Fraction(c, d)
    return _ans(str(f), "fraction",
                steps=["%d/%d %s %d/%d = %s" % (a, b, op, c, d, f)])


# ---------------------------------------------------------------- misc
def misc(q):
    ql = q.lower()
    m = re.search(r"sum of the first\s+(\d+)\s+(?:positive\s+)?(?:integers|numbers|natural numbers)", ql)
    if m:
        n = int(m.group(1))
        v = n * (n + 1) // 2
        return _ans(_fmt(v), "series",
                    steps=["Sum = n(n+1)/2 = %d x %d / 2 = %s"
                           % (n, n + 1, _fmt(v))])
    m = re.search(r"(\d+)\s*/\s*(\d+)\s+divided by\s+(\d+)\s*/\s*(\d+)", ql)
    if m:
        a, b, c, d = (int(m.group(i)) for i in range(1, 5))
        from fractions import Fraction
        f = Fraction(a, b) / Fraction(c, d)
        return _ans(str(f), "fraction",
                    steps=["%d/%d / %d/%d = %d/%d x %d/%d = %s"
                           % (a, b, c, d, a, b, d, c, f)])
    m = re.search(r"(\d+(?:\.\d+)?)\s*(?:times|multiplied by|x)\s*(\d+(?:\.\d+)?)", ql)
    if m:
        v = _n(m.group(1)) * _n(m.group(2))
        return _ans(_fmt(v), "multiplication",
                    steps=["%s x %s = %s" % (m.group(1), m.group(2), _fmt(v))])
    m = re.search(r"(\d+(?:\.\d+)?)\s*(?:divided by|/)\s*(\d+(?:\.\d+)?)", ql)
    if m and _n(m.group(2)):
        v = _n(m.group(1)) / _n(m.group(2))
        return _ans(_fmt(v), "division",
                    steps=["%s / %s = %s" % (m.group(1), m.group(2), _fmt(v))])
    if re.search(r"angle between the hour and minute hands.*?(\d+):00", ql):
        h = int(re.search(r"(\d+):00", ql).group(1))
        ang = min(abs(h * 30), 360 - abs(h * 30))
        return _ans(_fmt(ang) + "°", "clock",
                    steps=["Hour hand is at %d x 30 = %s°." % (h, _fmt(h * 30))])
    return None


def safe_eval_expr(q):
    """Last-resort arithmetic: evaluate a clean expression built from digits
    and + - * / ( ) . % ^ only."""
    m = re.search(r"(?:what is|calculate|compute|evaluate|solve)\s+(.+)", q, re.I)
    expr = (m.group(1) if m else q).strip().rstrip("?.!").strip()
    expr = expr.replace("^", "**").replace("×", "*").replace("÷", "/")
    if not re.fullmatch(r"[\d\s+\-*/().%]+", expr):
        return None
    if not re.search(r"\d\s*[+\-*/%]\s*\d", expr):
        return None
    try:
        tree = ast.parse(expr, mode="eval")
    except Exception:
        return None
    try:
        v = eval(compile(tree, "<math>", "eval"),
                 {"__builtins__": {}}, {})
    except Exception:
        return None
    if isinstance(v, (int, float)) and not isinstance(v, bool):
        return _ans(_fmt(v), "arithmetic",
                    steps=["%s = %s" % (expr, _fmt(v))])
    return None


_SOLVERS = (
    percent_of, percent_change, discount, tax_total, tip_tax, simple_interest,
    compound_interest, linear_equation, quadratic, successor, sequence, circle,
    polygon_angle, polygon_diagonals, square_geometry, rectangle, triangle_area,
    triangle_ratio, pythagorean, speed, fuel, recipe, average,
    inverse_workers, work_rate, unit_convert, gcd_lcm, primes, factorial,
    compare_powers, power_sqrt, combination_permutation, probability,
    fraction_add, share, misc, safe_eval_expr,
)


def solve(question):
    if not question or len(question) < 3:
        return None
    for fn in _SOLVERS:
        try:
            r = fn(question)
        except Exception:
            r = None
        if r:
            return r
    return None
