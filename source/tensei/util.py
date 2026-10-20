import hashlib
import math
import re
import struct

MASK64 = (1 << 64) - 1
_SPLIT_A = 0x9E3779B97F4A7C15
_SPLIT_B = 0xBF58476D1CE4E5B9
_SPLIT_C = 0x94D049BB133111EB

def splitmix64(x):
    x = (x + _SPLIT_A) & MASK64
    x = ((x ^ (x >> 30)) * _SPLIT_B) & MASK64
    x = ((x ^ (x >> 27)) * _SPLIT_C) & MASK64
    return x ^ (x >> 31)

def h64(s, seed=0):
    d = hashlib.blake2b(s.encode("utf-8", "ignore"), digest_size=8).digest()
    return splitmix64(int.from_bytes(d, "little") ^ seed)

WORD_RE = re.compile(r"[a-z0-9][a-z0-9'\-]*")

STOP = set((
    "a an the is are was were be been being am do does did doing have has had having "
    "i you he she it we they me him her us them my your his its our their this that these those "
    "of in on at to for with by from as into about between over after before under again further "
    "then once here there when where why how all any both each few more most other some such "
    "no nor not only own same so than too very can will just should now "
    "what which who whom whose if or and but because while during "
    "also may might must shall would could get got make made makes use used using "
    "one two three many much lot new "
    "invented discovered created called said says according happens happened "
    "mean means know tell explain define really actually works worked better best "
    "good bad thing things stuff stuffs please thanks thank"
).split())

def words(text):
    return WORD_RE.findall(text.lower())

def content_words(text):
    return [w for w in words(text) if w not in STOP and len(w) > 1]

def bigrams(tokens):
    return [tokens[i] + " " + tokens[i + 1] for i in range(len(tokens) - 1)]

_SENT_SPLIT = re.compile(r"(?<=[.!?])\s+")

def sentences(text):
    text = re.sub(r"\s+", " ", text or "").strip()
    if not text:
        return []
    parts = _SENT_SPLIT.split(text)
    out = []
    for p in parts:
        p = p.strip()
        if not p:
            continue
        if out and len(p) < 30:
            out[-1] = out[-1] + " " + p
        else:
            out.append(p)
    return [s for s in out if len(s) >= 15]

def clamp_text(text, limit):
    text = text or ""
    if len(text) <= limit:
        return text
    cut = text[:limit]
    sp = cut.rfind(" ")
    if sp > limit * 0.6:
        cut = cut[:sp]
    return cut + " (...)"

def digest_key(text):
    norm = re.sub(r"\s+", " ", (text or "").lower()).strip()
    return hashlib.blake2b(norm.encode("utf-8", "ignore"), digest_size=16).hexdigest()

def nrm(v):
    n = math.sqrt(sum(x * x for x in v))
    if n == 0.0:
        return list(v)
    inv = 1.0 / n
    return [x * inv for x in v]

def dot(a, b):
    return sum(x * y for x, y in zip(a, b))

def pack_f32(v):
    return struct.pack("<%df" % len(v), *v)

def unpack_f32(b):
    if not b:
        return []
    return list(struct.unpack("<%df" % (len(b) // 4), b))

BLOCKED_TERMS = frozenset([
    "childporn", "csam", "pedophilia", "pedophile"
])

def is_blocked(text):
    if not text:
        return False
    ws = set(words(text))
    return bool(ws & BLOCKED_TERMS)

_FENCE_OPEN_RE = re.compile(
    r"^([ \t]*)(`{2,})([A-Za-z0-9_+\-.#]*)[ \t]*(.*)$")
_FENCE_CLOSE_RE = re.compile(r"^[ \t]*(`{2,})[ \t]*$")
_LONE_FENCE_RE = re.compile(r"^[ \t]*`[ \t]*$")

def canonical_code_fences(text):
    """Turn 2+-backtick or malformed answer fences into standard ``` fences.

    Scraped answers sometimes contain ``python ... ` or only two opening
    backticks.  The web renderer and terminal both understand triple fences,
    so normalise every answer at the boundary instead of hoping the source was
    tidy.  Code content is preserved line-for-line.
    """
    if not text or "`" not in text:
        return text
    lines = text.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    out = []
    in_code = False
    fence_len = 3
    for line in lines:
        if not in_code:
            m = _FENCE_OPEN_RE.match(line)
            if not m:
                im = re.search(
                    r"(?<!\S)(`{2,})([A-Za-z][A-Za-z0-9_+\-.#]*)[ \t]*(.*)$",
                    line)
                if im:
                    prefix = line[:im.start()].rstrip()
                    if prefix:
                        out.append(prefix)
                    out.append("```" + im.group(2).lower())
                    rest = (im.group(3) or "").rstrip()
                    if rest:
                        rest = rest.rstrip("`").rstrip()
                        if rest:
                            out.append(rest)
                    in_code = True
                    fence_len = max(2, len(im.group(1)))
                    continue
            if m:
                lang = (m.group(3) or "").lower()
                rest = (m.group(4) or "").rstrip()
                out.append(m.group(1) + "```" + lang)
                if rest:
                    if rest.endswith("`"):
                        rest = rest.rstrip("`").rstrip()
                    if rest:
                        out.append(rest)
                in_code = True
                fence_len = max(2, len(m.group(2)))
                continue
            out.append(line)
            continue

        m = _FENCE_CLOSE_RE.match(line)
        if (m and len(m.group(1)) >= fence_len) or _LONE_FENCE_RE.match(line):
            out.append("```")
            in_code = False
            continue
        out.append(line)
    if in_code:
        out.append("```")
    return "\n".join(out)

def clean_answer(text):
    """Remove obvious scraped promotion tails and normalise code fences."""
    if not text:
        return text
    t = text.replace("\r\n", "\n").replace("\r", "\n")
    t = re.sub(r"(?is)\bIn our Ethical Hacking with Python Ebook[^.\n]*\.?", "", t)
    t = re.sub(r"(?is)\bIf Yes,?\s*please give[^\n]*", "", t)
    t = re.sub(r"(?is)\bTags?\s*:[^\n]*(?:calculator|python project)[^\n]*", "", t)
    t = re.sub(r"(?is)\bAt PythonGeeks,[^\n]*", "", t)
    t = canonical_code_fences(t)
    t = re.sub(r"\n{3,}", "\n\n", t).strip()
    return t

def top_ngrams(text, limit=8):
    ws = content_words(text)
    counts = {}
    for w in ws:
        counts[w] = counts.get(w, 0) + 1
    for bg in bigrams(ws):
        if " " in bg:
            counts[bg] = counts.get(bg, 0) + 1
    ranked = sorted(counts.items(), key=lambda kv: (-kv[1], len(kv[0])))
    return [k for k, c in ranked[:limit] if c >= 1]
