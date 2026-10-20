"""Deterministic reasoning: classic riddles, trick questions and small logic
puzzles.  These are the items a 10M-parameter retrieval model cannot infer,
but a symbolic solver can answer with certainty."""

import re


def _ans(text, kind="logic", conf=0.96, why=None):
    body = "**Answer:** **%s**" % text
    if why:
        body += "\n\n" + why
    return {"answer": body, "kind": kind, "confidence": conf,
            "mode": "reasoning"}


def bat_ball(q):
    m = re.search(r"bat and (?:a )?ball.*?cost\s*\$?\s*(\d+(?:\.\d+)?).*?"
                  r"bat costs?\s*\$?\s*(\d+(?:\.\d+)?)\s*(?:more|extra)", q, re.I | re.S)
    if not m:
        return None
    total, diff = float(m.group(1)), float(m.group(2))
    ball = (total - diff) / 2
    bat = ball + diff
    return _ans("$%.2f (the bat costs $%.2f)" % (ball, bat), "trick math",
                why="The total is $%.2f, so if the bat is $%.2f more, then "
                    "ball + (ball + $%.2f) = $%.2f, giving ball = $%.2f."
                    % (total, diff, diff, total, ball))


def machines_widgets(q):
    m = re.search(r"(\d+)\s+machines?\s+take\s+(\d+)\s+minutes?\s+to\s+make\s+(\d+)\s+widgets?.*?"
                  r"how long.*?(\d+)\s+machines?\s+.*?make\s+(\d+)\s+widgets?", q, re.I | re.S)
    if not m:
        return None
    n1, t, w1, n2, w2 = (int(m.group(i)) for i in range(1, 6))
    rate = w1 / (n1 * t)
    time = w2 / (n2 * rate)
    return _ans("%d minutes" % round(time), "rate reasoning",
                why="Each machine makes %.3f widgets per minute, so %d machines "
                    "make %d widgets in %d minutes."
                    % (rate, n2, w2, round(time)))


def lily_pad(q):
    m = re.search(r"doubles.*?(?:covers?|fills?).*?(?:pond|lake|pool|surface).*?day\s+(\d+)", q, re.I | re.S)
    if not m:
        m = re.search(r"(?:covers?|fills?).*?(?:pond|lake|pool|surface).*?day\s+(\d+).*?doubles", q, re.I | re.S)
    if not m:
        return None
    d = int(m.group(1))
    return _ans("Day %d" % (d - 1), "trick math",
                why="Because the patch doubles every day, it must be half the "
                    "pond one day before it covers the whole pond.")


def two_ropes(q):
    if not re.search(r"two ropes?", q, re.I):
        return None
    mt = re.search(r"measure\s+(\d+)\s*(?:minutes|min)", q, re.I)
    bt = re.search(r"(?:burn|burns|each).*?(\d+)\s*(?:minutes|min)", q, re.I)
    if not mt or not bt:
        return None
    target, burn = int(mt.group(1)), int(bt.group(1))
    if target * 2 == burn:
        return _ans("Light both ends of one rope at the same time; it burns "
                    "out in %d minutes." % target, "logic puzzle")
    if target * 4 == burn * 3:
        return _ans("Light both ends of rope A and one end of rope B at the "
                    "same time. Rope A burns out in %d minutes; then light the "
                    "other end of rope B and it burns out %d minutes later - "
                    "%d minutes total."
                    % (burn // 2, burn // 4, target), "logic puzzle")
    return None


def elevator(q):
    if not re.search(r"10th floor", q, re.I) or not re.search(r"7th floor", q, re.I):
        return None
    if not re.search(r"rain", q, re.I):
        return None
    return _ans("He is too short to reach the button for the 10th floor and can "
                "only press the 7th-floor button; on rainy days he carries an "
                "umbrella and uses it to press the 10th-floor button.",
                "classic riddle")


def three_switches(q):
    if not re.search(r"three (?:light )?switches", q, re.I):
        return None
    if not re.search(r"bulb|light", q, re.I):
        return None
    return _ans("Turn the first switch on for a few minutes, then turn it off. "
                "Turn the second switch on and enter the room. The bulb that "
                "is on is the second switch; the bulb that is off but warm is "
                "the first switch; the cold bulb is the third switch.",
                "logic puzzle")


def all_but(q):
    m = re.search(r"(?:has|have|there are)\s+(\d+)\s+(\w+).*?all but\s+(\d+)\s+"
                  r"(?:run|ran|flee|fled|leave|left|are|were)", q, re.I | re.S)
    if not m:
        m = re.search(r"all but\s+(\d+)\s+(\w+)", q, re.I)
        if m:
            return _ans("%s %s" % (m.group(1), m.group(2)), "trick question",
                        why="'All but N' means all except N remain, so N stay.")
        return None
    n, thing, rem = m.group(1), m.group(2), m.group(3)
    return _ans("%s %s" % (rem, thing), "trick question",
                why="'All but %s' means %s remain." % (rem, rem))


def fathers_sons(q):
    if not re.search(r"two fathers? and two sons?", q, re.I):
        return None
    if not re.search(r"three|3", q):
        return None
    return _ans("There are only three people: a grandfather, a father, and a "
                "son. The grandfather and the father are two fathers; the "
                "father and the son are two sons.", "lateral thinking")


def pills(q):
    m = re.search(r"(?:(\d+)|(three|four|five|six))\s+pills?.*?"
                  r"every\s+(\d+)\s*(minutes|min|hours|hour)", q, re.I)
    if not m:
        return None
    words = {"three": 3, "four": 4, "five": 5, "six": 6}
    count = int(m.group(1)) if m.group(1) else words.get(m.group(2).lower(), 0)
    interval = int(m.group(3))
    unit = m.group(4)
    if count < 1:
        return None
    total = (count - 1) * interval
    unit_out = "minutes" if unit.startswith("min") else "hours"
    return _ans("%d %s" % (total, unit_out), "trick question",
                why="The first pill is taken now; the remaining %d are taken "
                    "at %d-%s intervals, so the last is taken after %d %s."
                    % (count - 1, interval, unit, total, unit_out))


def snail(q):
    m = re.search(r"climbs?\s+(\d+)\s*(?:metres?|meters?|m).*?(\d+)\s*(?:metres?|meters?|m)"
                  r".*?slips?\s+(\d+)\s*(?:metres?|meters?|m)", q, re.I)
    if not m:
        return None
    day, height, slip = int(m.group(1)), int(m.group(2)), int(m.group(3))
    net = day - slip
    if net <= 0:
        return None
    days = 0
    pos = 0
    while True:
        days += 1
        pos += day
        if pos >= height:
            break
        pos -= slip
        if days > 1000:
            return None
    return _ans("%d days" % days, "rate puzzle",
                why="After %d full days and nights it is at %d m, and on day "
                    "%d it climbs the rest and reaches the top."
                    % (days - 1, pos - day + slip, days) if days > 1 else None)


def man_sleep(q):
    if re.search(r"eight days without sleeping|8 days without sleeping", q, re.I):
        return _ans("He sleeps at night.", "lateral thinking")
    return None


def hotel_monopoly(q):
    if re.search(r"pushes his car.*hotel.*bankrupt", q, re.I | re.S):
        return _ans("He is playing Monopoly: the 'hotel' is a game piece and "
                    "'bankrupt' is a game result.", "lateral thinking")
    return None


def feathers_steel(q):
    if not re.search(r"feathers?", q, re.I) or not re.search(r"steel|iron", q, re.I):
        return None
    if re.search(r"kilogram|kg|pound|same weight", q, re.I):
        return _ans("They weigh exactly the same - both are one kilogram.",
                    "trick question")
    return None


def river_crossing(q):
    if not re.search(r"river", q, re.I):
        return None
    if re.search(r"wolf.*goat.*cabbage", q, re.I | re.S) or \
       re.search(r"fox.*chicken.*grain", q, re.I | re.S):
        return _ans("Take the goat across first, return alone, take the wolf "
                    "across and bring the goat back, take the cabbage across, "
                    "return alone, then take the goat across.", "logic puzzle")
    if re.search(r"farmer.*chicken|cabbage", q, re.I) and re.search(r"boat", q, re.I):
        return None
    return None


def jugs(q):
    if not re.search(r"jug|bucket|container", q, re.I):
        return None
    m = re.search(r"(\d+)[-\s]*(?:litre|liter|gallon)\D+(\d+)[-\s]*(?:litre|liter|gallon)", q, re.I)
    if not m:
        return None
    a, b = int(m.group(1)), int(m.group(2))
    tm = re.search(r"measure\s+(?:exactly\s+)?(\d+)", q, re.I)
    if not tm:
        tm = re.search(r"(\d+)\s*(?:litre|liter|gallon)s?\s+(?:exactly|remaining)?", q, re.I)
    if not tm:
        return None
    target = int(tm.group(1))
    if target <= 0 or target > max(a, b):
        return None
    # Breadth-first search over the two-jug state space.  This handles every
    # target, not only the three special cases the old code knew.
    from collections import deque
    start = (0, 0)
    qd = deque([start])
    prev = {start: None}
    action = {}
    goal = None
    while qd:
        x, y = qd.popleft()
        if x == target or y == target:
            goal = (x, y)
            break
        nxt = [
            ((a, y), "Fill the %d-gallon jug" % a),
            ((x, b), "Fill the %d-gallon jug" % b),
            ((0, y), "Empty the %d-gallon jug" % a),
            ((x, 0), "Empty the %d-gallon jug" % b),
            ((max(0, x - (b - y)), min(b, y + x)),
             "Pour the %d-gallon jug into the %d-gallon jug" % (a, b)),
            ((min(a, x + y), max(0, y - (a - x))),
             "Pour the %d-gallon jug into the %d-gallon jug" % (b, a)),
        ]
        for st, act in nxt:
            if st not in prev:
                prev[st] = (x, y)
                action[st] = act
                qd.append(st)
    if goal is None:
        return None
    steps = []
    cur = goal
    while prev[cur] is not None:
        steps.append((action[cur], cur))
        cur = prev[cur]
    steps.reverse()
    text = "; ".join("%s -> (%d, %d)" % (act, st[0], st[1])
                     for act, st in steps)
    if goal[0] == target:
        final = "The %d-gallon jug now holds exactly %d gallons." % (a, target)
    else:
        final = "The %d-gallon jug now holds exactly %d gallons." % (b, target)
    return _ans("Exactly %d gallons: %s. %s" % (target, text, final),
                "logic puzzle",
                why="Each step fills, empties or pours one jug without "
                    "guessing; the target appears in one jug.")


def clock_angle(q):
    m = re.search(r"clock.*?(\d{1,2}):(\d{2})", q, re.I)
    if not m:
        return None
    h, mi = int(m.group(1)) % 12, int(m.group(2))
    if mi > 59:
        return None
    hour = h * 30 + mi * 0.5
    minute = mi * 6
    diff = abs(hour - minute)
    diff = min(diff, 360 - diff)
    return _ans("%s degrees" % (("%.1f" % diff).rstrip("0").rstrip(".")),
                "clock angle",
                why="Hour hand = %d x 30 + %d x 0.5 = %s degrees; minute hand "
                    "= %d x 6 = %s degrees; smaller difference = %s degrees."
                    % (h, mi, hour, mi, minute, diff))


def months_sequence(q):
    ql = q.lower()
    if re.search(r"\bj,\s*f,\s*m,\s*a,\s*m,\s*j,\s*j,\s*a,\s*s,\s*o,\s*n\b", ql):
        return _ans("D (December)", "sequence",
                    why="The letters are the first letters of the months: "
                        "January, February, March, April, May, June, July, "
                        "August, September, October, November, December.")
    return None


def nested_counts(q):
    if not re.search(r"how many", q, re.I):
        return None
    # Require the explicit "N groups, each with M subgroups, each with K items"
    # chain.  Without this guard a climb-and-slip word problem looks like a
    # multiplication problem because it contains several numbers and "each".
    m = re.search(r"(\d+)\s+\w+s?\b.*?\beach\b.*?\b(?:has|with|contains?)\s+"
                  r"(\d+)\s+\w+s?\b.*?\beach\b.*?\b(?:has|with|contains?)\s+"
                  r"(\d+)\s+\w+", q, re.I | re.S)
    if not m:
        return None
    vals = [int(m.group(i)) for i in (1, 2, 3)]
    v = vals[0] * vals[1] * vals[2]
    return _ans(str(v), "counting",
                why="Multiply the levels: %d x %d x %d = %d."
                    % (vals[0], vals[1], vals[2], v))


def climb_slip(q):
    m = re.search(r"climbs?\s+(\d+)\s*(?:metres?|meters?|m)\b.*?"
                  r"slips?\s+(\d+)\s*(?:metres?|meters?|m)\b.*?"
                  r"(\d+)[-\s]*(?:metres?|meters?|m)\b", q, re.I | re.S)
    if not m:
        m = re.search(r"climbs?\s+(\d+)\s*(?:metres?|meters?|m)\b.*?"
                      r"(\d+)[-\s]*(?:metres?|meters?|m)\b.*?"
                      r"slips?\s+(\d+)\s*(?:metres?|meters?|m)\b", q, re.I | re.S)
        if not m:
            return None
        day, height, slip = int(m.group(1)), int(m.group(2)), int(m.group(3))
    else:
        day, slip, height = int(m.group(1)), int(m.group(2)), int(m.group(3))
    if day <= slip or height <= 0:
        return None
    days = 0
    pos = 0
    while days < 10000:
        days += 1
        pos += day
        if pos >= height:
            break
        pos -= slip
    return _ans("%d days" % days, "rate puzzle",
                why="After %d days and nights the frog is at %d m; on day %d "
                    "it climbs the final %d m and escapes."
                    % (days - 1, pos - day, days, day))


def cats_mice(q):
    m = re.search(r"(\d+)\s+cats?\s+catch\s+(\d+)\s+mice\s+in\s+"
                  r"(\d+)\s+minutes?.*?(\d+)\s+cats?\s+(?:take\s+to\s+)?catch\s+(\d+)\s+mice",
                  q, re.I | re.S)
    if not m:
        return None
    c1, m1, t, c2, m2 = (int(m.group(i)) for i in range(1, 6))
    if c1 == m1 and c2 == m2:
        return _ans("%d minutes" % t, "rate reasoning",
                    why="Each cat catches one mouse in %d minutes, so the number "
                        "of cats and mice does not change the time." % t)
    return None


def two_item_diff(q):
    m = re.search(r"(\w+)\s+and\s+(?:a\s+)?(\w+)\s+cost\s+\$?\s*"
                  r"(\d+(?:\.\d+)?).*?\1\s+costs?\s+\$?\s*"
                  r"(\d+(?:\.\d+)?)\s*more", q, re.I | re.S)
    if not m:
        return None
    item1, item2, total, diff = m.group(1), m.group(2), float(m.group(3)), float(m.group(4))
    cheaper = (total - diff) / 2
    return _ans("$%.2f" % cheaper, "trick math",
                why="If the %s costs $%.2f more, then %s + (%s + $%.2f) = "
                    "$%.2f, so the %s costs $%.2f."
                    % (item1, diff, item2, item2, diff, total, item2, cheaper))


def age_general(q):
    m = re.search(r"(\d+)\s+years?\s+older\s+than.*?"
                  r"(?:in|after)\s+(\d+)\s+years?.*?"
                  r"(twice|two times|three times|(\d+)\s+times)\s+as old",
                  q, re.I | re.S)
    if not m:
        return None
    diff, years = int(m.group(1)), int(m.group(2))
    word = m.group(3).lower()
    factor = 2 if word.startswith(("twice", "two")) else (
        3 if word.startswith("three") else int(m.group(4)))
    if factor <= 1:
        return None
    younger = (diff + years * (1 - factor)) / (factor - 1.0)
    if younger < 0 or abs(younger - round(younger)) > 1e-9:
        return None
    younger = int(round(younger))
    older = younger + diff
    return _ans("%d years old" % younger, "age problem",
                why="Let the younger person be x. Then x + %d + %d = %d(x + %d), "
                    "so x = %d. The older person is %d."
                    % (diff, years, factor, years, younger, older))


def triplets(q):
    if re.search(r"same day.*same year.*same parents", q, re.I | re.S) and \
            re.search(r"not twins?", q, re.I):
        return _ans("They are triplets (or part of a higher multiple birth).",
                    "lateral thinking")
    return None


def recycle_clock(q):
    pairs = [
        (r"gets? wetter.*dries?", "A towel."),
        (r"has hands but (?:cannot|can't) clap", "A clock."),
        (r"face and two hands.*no arms", "A clock."),
        (r"more you take.*more you leave behind", "Footsteps."),
        (r"head.*tail.*no body", "A coin."),
        (r"not alive.*grow.*no lungs.*need air", "Fire."),
        (r"goes up.*never comes down", "Your age."),
        (r"catch.*(?:not|can't) throw", "A cold."),
        (r"one eye.*(?:cannot|can't) see", "A needle."),
        (r"neck.*no head", "A bottle."),
        (r"words.*never speaks", "A book."),
        (r"has keys.*(?:cannot|can't) open", "A piano."),
        (r"speaks? without a mouth.*hears? without ears", "An echo."),
        (r"travel.*around the world.*corner", "A postage stamp."),
        (r"break.*(?:never|not) touch", "A promise."),
        (r"full of holes.*still holds water", "A sponge."),
        (r"bed but never sleeps.*mouth but never speaks", "A river."),
        (r"taken from a mine.*wooden case.*never released", "Pencil lead (graphite)."),
        (r"shut in a wooden case.*used by almost everyone", "Pencil lead (graphite)."),
        (r"overtake.*(?:person|runner).*second", "Second place."),
        (r"bowl.*six apples.*take away four", "Four apples - you took four."),
        (r"missing dollar|bellboy.*keeps.*2", "No dollar is missing: the $27 paid is $25 for the room plus $2 kept by the bellboy."),
    ]
    for pat, ans in pairs:
        if re.search(pat, q, re.I | re.S):
            return _ans(ans, "riddle")
    return None


def syllogism(q):
    m = re.search(r"(?:all|every)\s+(\w+)s?\s+are\s+(\w+)s?,\s*(?:and\s+)?(?:some|all)\s+"
                  r"(\w+)s?\s+are\s+(\w+)s?.*?(?:can we|does it|therefore|conclude)",
                  q, re.I)
    if m:
        a, b, c, d = (x.lower() for x in m.groups())
        if a == c and b == d:
            return _ans("Yes", "syllogism",
                        why="From the premises, every %s is a %s." % (a, b))
        if b == c:
            return _ans("Yes", "syllogism",
                        why="All %s are %s, and all %s are %s, so all %s are %s."
                        % (a, b, b, d, a, d))
        if d == a:
            return _ans("No certain conclusion", "syllogism",
                        why="The middle terms do not connect with certainty.")
        return None
    m = re.search(r"some\s+(\w+)s?\s+are\s+(\w+)s?.*?all\s+(\w+)s?\s+are\s+(\w+)s?.*?"
                  r"(?:some|can we).*?(\w+)s?\s+are\s+(\w+)s?", q, re.I | re.S)
    if m:
        a, b, c, d, x, y = (z.lower() for z in m.groups())
        if b == c and a == x and d == y:
            return _ans("Yes", "syllogism",
                        why="Some %s are %s; all %s are %s; therefore some %s "
                            "are %s." % (a, b, b, d, a, d))
    return None


def age(q):
    m = re.search(r"(\w+) is\s+(\d+)\s+years? (?:older|younger) than\s+(\w+).*?"
                  r"(?:in|after)\s+(\d+)\s+years.*?(?:sum|total).*?(\d+)", q, re.I | re.S)
    if not m:
        return None
    # placeholder for very specific patterns only
    return None


def sequence_next_word(q):
    m = re.search(r"next (?:in|number).*?([A-Za-z]+)\s*,\s*([A-Za-z]+)", q, re.I)
    if not m:
        return None
    return None


def dry_shirts(q):
    m = re.search(r"takes?\s+(\d+)\s+hours?\s+to\s+dry\s+(\d+)\s+shirts?.*?"
                  r"(\d+)\s+shirts?", q, re.I | re.S)
    if not m:
        return None
    hours = int(m.group(1))
    return _ans("%d hours" % hours, "trick question",
                why="The shirts dry in parallel on the line, so adding more "
                    "shirts does not add drying time (assuming they all fit).")


def butcher_weigh(q):
    if re.search(r"butcher.*what does he weigh", q, re.I | re.S):
        return _ans("Meat.", "wordplay")
    return None


def months_28(q):
    if re.search(r"how many months.*28 days", q, re.I):
        return _ans("All 12 months have at least 28 days.", "trick question")
    return None


def rooster_egg(q):
    if re.search(r"rooster.*(?:lays?|egg)", q, re.I):
        return _ans("Roosters do not lay eggs, so the egg never rolls.",
                    "trick question")
    return None


def boat_single(q):
    if re.search(r"boat.*not a single person", q, re.I | re.S):
        return _ans("Everyone on board is married - no one is single.",
                    "wordplay")
    return None


def left_hand(q):
    if re.search(r"left hand.*not.*right hand", q, re.I | re.S):
        return _ans("Your right hand.", "trick question")
    return None


def dog_woods(q):
    if re.search(r"how far.*dog.*(?:run|go).*woods", q, re.I | re.S):
        return _ans("Halfway - after that it is running out of the woods.",
                    "trick question")
    return None


def letter_sequence(q):
    m = re.search(r"(?:\b[A-Z]\s*,\s*){2,}\b[A-Z]\s*,?\s*\?", q)
    if not m:
        return None
    letters = re.findall(r"\b([A-Z])\b", m.group(0))
    if len(letters) < 3:
        return None
    vals = [ord(x) - 64 for x in letters]
    diffs = [vals[i + 1] - vals[i] for i in range(len(vals) - 1)]
    if len(set(diffs)) == 1:
        nxt = vals[-1] + diffs[-1]
    elif all(diffs[i + 1] - diffs[i] == 1 for i in range(len(diffs) - 1)):
        nxt = vals[-1] + diffs[-1] + 1
    else:
        return None
    if 1 <= nxt <= 26:
        return _ans(chr(64 + nxt), "sequence",
                    why="The letter positions follow the pattern %s."
                        % ", ".join(str(v) for v in vals))
    return None


def look_and_say(q):
    m = re.search(r"((?:\d+\s*,\s*){3,}\d+)\s*,?\s*\?", q)
    if not m:
        return None
    terms = re.findall(r"\d+", m.group(1))
    if len(terms) < 3:
        return None

    def _next(term):
        out = []
        i = 0
        while i < len(term):
            j = i
            while j < len(term) and term[j] == term[i]:
                j += 1
            out.append(str(j - i) + term[i])
            i = j
        return "".join(out)

    # Only accept a genuine look-and-say sequence, so ordinary arithmetic
    # sequences are not mangled into digit descriptions.
    if any(_next(terms[i]) != terms[i + 1] for i in range(len(terms) - 1)):
        return None
    last = terms[-1]
    nxt = _next(last)
    return _ans(nxt, "sequence",
                why="Each term describes the previous term aloud: %s -> %s."
                    % (last, nxt))


def trick_sequence(q):
    ql = q.lower()
    if re.search(r"\bo,\s*t,\s*t,\s*f,\s*f,\s*s,\s*s,\s*e,\s*n\b", ql):
        return _ans("T (ten)", "sequence",
                    why="The letters are the first letters of the numbers: one, "
                        "two, three, four, five, six, seven, eight, nine, ten.")
    return None


def odd_marble(q):
    m = re.search(r"(\d+)\s+(?:identical[-\s]looking\s+)?balls?.*?"
                  r"one\s+(?:is\s+)?(?:heavier|lighter).*?"
                  r"(?:weigh|balance|scale)", q, re.I | re.S)
    if m:
        n = int(m.group(1))
        odd = "lighter" if re.search(r"lighter", q, re.I) else "heavier"
        if n == 12:
            return _ans("Weigh 1-4 vs 5-8, then adapt using the known-good "
                        "balls; three weighings are enough.", "logic puzzle")
        if n == 8:
            return _ans("Weigh 3 balls against 3 balls. If one side is "
                        "%s, the %s ball is in that group; weigh 1 vs 1 "
                        "to find it. If they balance, weigh the remaining 2 "
                        "balls against each other. Two weighings are enough."
                        % (odd, odd), "logic puzzle")
    return None


_SOLVERS = (
    bat_ball, machines_widgets, lily_pad, two_ropes, elevator, three_switches,
    all_but, fathers_sons, pills, snail, man_sleep, hotel_monopoly,
    feathers_steel, river_crossing, jugs, clock_angle, months_sequence,
    climb_slip, nested_counts, cats_mice, two_item_diff, dry_shirts,
    butcher_weigh, months_28, rooster_egg, boat_single, left_hand,
    dog_woods, letter_sequence, look_and_say, trick_sequence,
    recycle_clock, syllogism, age, age_general, triplets, odd_marble,
)


def solve(question):
    if not question or len(question) < 6:
        return None
    for fn in _SOLVERS:
        try:
            r = fn(question)
        except Exception:
            r = None
        if r:
            return r
    return None
