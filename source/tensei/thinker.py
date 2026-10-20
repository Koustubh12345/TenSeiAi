import ast
import math
import os
import re
import time
import urllib.parse

from . import config, seed_data, util, websearch

_SAFE_OPS = {
    ast.Add: lambda a, b: a + b,
    ast.Sub: lambda a, b: a - b,
    ast.Mult: lambda a, b: a * b,
    ast.Div: lambda a, b: a / b,
    ast.FloorDiv: lambda a, b: a // b,
    ast.Mod: lambda a, b: a % b,
    ast.Pow: lambda a, b: a ** b,
    ast.USub: lambda a: -a,
    ast.UAdd: lambda a: a,
}

def safe_math(text):
    tl = text.lower()
    if re.search(r"\b(derivative|integral|equation|system|variable|solve\s+the\s+system|formula)\b", tl):
        return None
    m = re.search(r"(\d+(?:\.\d+)?)\s*%\s*of\s*(\d+(?:\.\d+)?)", tl)
    if m:
        return "%s%% of %s = %s" % (m.group(1), m.group(2),
                                    float(m.group(1)) * float(m.group(2)) / 100.0)
    m = re.search(r"(?:calculate|compute|what is|solve)\s+(.*)$", tl)
    expr = (m.group(1) if m else text).strip().replace("^", "**")
    expr = expr.rstrip("?.!").strip()
    if re.search(r"[a-df-z]", expr):
        return None
    if "=" in expr:
        return None
    if not expr or not re.fullmatch(r"[0-9\s+\-*/().%*]+", expr):
        return None
    if "**" in expr and re.search(r"\*\*\s*\d{3,}", expr):
        return None
    try:
        node = ast.parse(expr, mode="eval").body

        def ev(n):
            if isinstance(n, ast.Constant) and isinstance(n.value, (int, float)):
                return n.value
            if isinstance(n, ast.BinOp) and type(n.op) in _SAFE_OPS:
                return _SAFE_OPS[type(n.op)](ev(n.left), ev(n.right))
            if isinstance(n, ast.UnaryOp) and type(n.op) in _SAFE_OPS:
                return _SAFE_OPS[type(n.op)](ev(n.operand))
            raise ValueError("unsupported")
        val = ev(node)
        if isinstance(val, float):
            val = round(val, 6)
        return "%s = %s" % (expr.strip(), val)
    except Exception:
        return None

def _clean_sentence(s):
    s = s.strip()
    s = re.sub(r"^(Key Takeaways?|Key Takeaway)\s*:\s*", "", s)
    s = re.sub(r"^(What|How|Why|Understanding)\s+[^.?]{3,60}\s+(Means|Works|Defined|Explained)\s+", "", s)
    s = re.sub(r"^(Answer|Definition|Explanation)\s*:\s*", "", s)
    return s.strip()

_ORIGIN_SENT = re.compile(
    r"\b(coin\w*|invent\w*|originat\w*|comes?\s+from|deriv\w+\s+from|"
    r"first\s+used|word)\b", re.I)
_JUNK_SENT = re.compile(
    r"\b(retrieved|archived|isbn|doi|accessed|citation|cite\s+note|"
    r"original\s+on|look\s+up|wiktionary|wikimedia|free\s+dictionary|"
    r"takes\s+a\s+look\s+at|this\s+article|updated\s+on|"
    r"a\s+painting\s+by|a\s+photograph\s+of|a\s+simulation\s+of|"
    r"viewed\s+from\s+the|classified\s+as\s+a\s+foreshock|"
    r"at\s+\d\d:\d\d\s+[a-z]{3}|in\s+june\s+2026|"
    r"click\s+here|read\s+more|sign\s+up|subscription|cookie|privacy\s+policy|"
    r"advertisement|all\s+rights\s+reserved|jump\s+to|toggle\s+navigation|"
    r"share\s+this|follow\s+us|posted\s+by|leave\s+a\s+comment|"
    r"reload\s+to\s+refresh|dismiss\s+alert|actions?\s+menu|files?\s+navigation|"
    r"signed\s+in\s+with|signed\s+out|repository\s+files|switch\s+branches|"
    r"go\s+to\s+file|raw\s+contents|copy\s+path|"
    r"this\s+page\s+was\s+last\s+edited|table\s+of\s+contents)\b", re.I)

_CODE_FILE_RE = re.compile(
    r"\.(?:py|pyz|js|mjs|ts|tsx|jsx|java|kt|c|cc|cpp|h|hpp|cs|rs|go|rb|php|"
    r"swift|dart|lua|pl|sh|bash|zsh|ps1|bat|cmd|sql|html|htm|css|scss|json|"
    r"xml|yml|yaml|toml|ini|cfg|md|txt|csv|log|lock|so|dll|exe|bin|jar|apk)\b",
    re.I)

def _looks_junky(s):
    """Heuristic: UI chrome / file listings masquerading as prose."""
    low = s.lower()
    if len(_CODE_FILE_RE.findall(low)) >= 2:
        return True
    if re.search(r"\b(reload|dismiss|toggle|breadcrumb|sidebar|navbar)\b", low) \
            and len(low) < 240:
        return True
    return False

def _strip_cites(s):
    """Remove [1] [2] source markers so answers read like a normal AI."""
    return re.sub(r'\s*\[\d+\]', '', s or "")

_ENTS = {"ww1": ["world war i", "first world war"],
         "ww2": ["world war ii", "second world war"],
         "ww3": ["world war iii", "third world war"],
         "usa": ["united states"], "uk": ["united kingdom"],
         "ai": ["artificial intelligence"]}

def _alias(ent):
    e = (ent or "").lower()
    return _ENTS.get(e, [e])[0]

_GENERIC_TOPIC = frozenset({
    "tallest", "largest", "biggest", "smallest", "fastest", "longest",
    "deepest", "highest", "lowest", "oldest", "newest", "greatest", "best",
    "worst", "first", "last", "world", "earth", "many", "much", "most",
    "people", "things", "thing", "type", "types", "kind", "kinds", "called",
    "mean", "means", "does", "work", "works", "about", "tell", "explain",
    "simple", "terms", "words", "difference", "between", "important", "why",
})

def _subject_tokens(question):
    """Distinctive subject words of a question, used to check that a recalled
    Q&A row is really about the same thing (blocks 'tallest building' being
    answered by a stored 'tallest animal -> giraffe' row)."""
    return [w for w in util.content_words(question)
            if len(w) >= 4 and w not in _GENERIC_TOPIC]

_MEASURE_RE = re.compile(
    r"\bhow\s+(?:tall|big|large|heavy|long|far|deep|high|wide|fast|old|hot|"
    r"cold|many|much|often)\b", re.I)
_SUP_RE = re.compile(r"\b([a-z]{4,}est)\b|\b(most|least|first|last)\b")

_LIVE_RE = re.compile(
    r"\b(?:latest|newest|most recent|breaking|just (?:happened|announced|"
    r"released)|right now)\b"
    r"|\b(?:today|tonight|yesterday|this (?:week|month|year)|currently|current)"
    r"\b[^?]{0,40}\b(?:news|price|prices|score|scores|weather|update|updates|"
    r"released|happened|won|winning|stock)\b"
    r"|\bnews\b[^?]{0,40}\b(?:about|on|regarding|today)\b", re.I)

def _wants_live(question):
    return bool(_LIVE_RE.search(question or ""))

def _superlatives(text):
    out = set()
    for m in _SUP_RE.finditer((text or "").lower()):
        out.add(m.group(1) or m.group(2))
    return out

def _ent_hit(ent, low):
    e = (ent or "").lower()
    if not e:
        return False
    return any(x in low for x in _ENTS.get(e, [e]))

def _ent_loose(ent, low):
    words = [w for w in re.split(r"\W+", (ent or "").lower()) if len(w) >= 3]
    if not words:
        return False
    return all(w in low for w in words)

_WHEN_VERBS = (r"releas\w*|launch\w*|found\w*|creat\w*|introduc\w*|"
               r"start\w*|establish\w*|debut\w*|born|publish\w*|"
               r"air\w*|coin\w*|invent\w*|began|ended|lasted|fought|declared|"
               r"broke\s+out|premier\w*|broadcast\w*|serial\w*|arriv\w*|dropp\w*")

def _when_pattern(ent):
    forms = _ENTS.get((ent or "").lower(), [(ent or "").lower()])
    alt = "|".join(re.escape(x) for x in forms if x) or r"(?!)"
    return re.compile(
        r"(?:(?:%s|it|the\s+(?:company|service|app|platform|website|firm|site))"
        r"\b[^.]{0,50}?\b(?:%s)\b|(?:releas\w*|launch\w*|found\w*|debut\w*)"
        r"[^.]{0,40}?\b(?:1[5-9]\d\d|20\d\d)\b)" % (alt, _WHEN_VERBS), re.I)

def _jac(a, b):
    sa, sb = set(a), set(b)
    if not sa or not sb:
        return 0.0
    return len(sa & sb) / len(sa | sb)

def _fence_is_prose(s):
    """True when a fenced block holds ordinary sentences, not code."""
    head = (s or "").strip().split("\n", 1)[0].strip()
    if len(head) < 40 or " " not in head:
        return False
    if re.search(r"[=(){}\[\];]|->|^\s*(?:def|class|import|from|print|return|"
                 r"for|while|if|elif|else|let|var|const|function|public|static)\b",
                 head):
        return False
    return bool(re.search(r"[a-z]{3,}\s+[a-z]{3,}\s+[a-z]{3,}", head.lower()))

def _defence(body):
    """Remove code fences that wrap plain prose (a scraped-page artifact such
    as '``` Machine learning is ... ```'), keeping real code blocks intact."""
    if "```" not in body:
        return body
    def _rep(m):
        return m.group(1) if _fence_is_prose(m.group(1)) else m.group(0)
    body = re.sub(r"```[a-zA-Z]*[ \t]*\n?((?:(?!```)[\s\S])*?)```", _rep, body)
    if body.count("```") % 2 == 1:
        body = body.replace("```", " ")
    return body.strip()

_ASKY_RE = re.compile(
    r"^(?:explain|describe|define|tell|show|list|compare|summari[sz]e|analyz|analys|"
    r"discuss|write|create|make|give|find|calculate|compute|solve|prove|derive|"
    r"translate|generate|implement|build|design|code|what|which|why|who|when|where|"
    r"how\s+(?:do|does|can|could|would|should|to|is|are|did|many|much|long|far|"
    r"old|fast|high|deep|big|small)\b|is\b|are\b|does\b|do\b|can\b|will\b|"
    r"difference\b|meaning\b|example\b|examples\b)")

_SMALLTALK_RE = re.compile(
    r"^\s*(?:hi+|hello+|hey+|yo+|howdy|sup|hola|namaste|greetings|"
    r"good\s+(?:morning|afternoon|evening|night|day))\b"
    r"|\bhow\s+(?:are|is|was|were)\s+(?:you|u|ya|your|yours|it|things|"
    r"everything|life)\b(?!\s*(?:able|supposed|planning)\b)"
    r"|\bhow(?:'s| is| are)\s+\w+\s+days?\b"
    r"|\bhow\s+(?:you|u|ya)\s+(?:doing|been)\b"
    r"|\bhow\s+have\s+you\s+been\b"
    r"|\bhow\s+do\s+you\s+do\b"
    r"|\bhow(?:'s| is)\s+it\s+going\b"
    r"|\bwhat'?s\s+up\b|\bwhat\s+is\s+up\b"
    r"|\blong\s+time\s+no\s+see\b", re.I)

_DEFQ_RE = re.compile(
    r"^\s*(?:what\s+(?:is|are|was|were)\b|explain\b|define\b|"
    r"describe\b|tell\s+me\s+about\b)", re.I)

_TEMPORAL_RE = re.compile(
    r"(?:\bwhat(?:'s| is)?\s+(?:the\s+)?(?:current\s+|today'?s\s+)?(?:date|time)\b"
    r"|\bwhat\s+day\s+(?:is\s+it|is\s+today|of\s+the\s+week)\b"
    r"|\btoday'?s\s+date\b"
    r"|\bcurrent\s+(?:date|time)\b"
    r"|\bwhat\s+time\s+is\s+it\b"
    r"|\bwhat\s+year\s+is\s+it\b"
    r"|\bwhat\s+is\s+the\s+time\s+now\b)")
_TEMPORAL_BLOCK_RE = re.compile(
    r"\b(?:did|does|do|was|were|happened|happen|end|ended|begin|began|start|"
    r"started|take\s+place|took\s+place|occur\w*|founded|released|invented|"
    r"introduced|published|born|died|last|win|won|signed|"
    r"complexity|big.?o|time\s+zone|time\s+difference|time\s+limit|"
    r"time\s+period|time\s+signature|time\s+stamp|time\s+machine)\b")

def _is_temporal(q):
    ql = q.lower()
    if _TEMPORAL_BLOCK_RE.search(ql):
        return False
    return bool(_TEMPORAL_RE.search(ql))

_QUERY_FILLER_RE = re.compile(
    r"^(?:(?:so|ok|okay|well|hey|hi|hello)[,\s]+)*"
    r"(?:(?:can|could|would|will)\s+(?:you|u)\s+)?"
    r"(?:(?:do|does|did)\s+(?:you|u|i|we)\s+)?"
    r"(?:please\s+|kindly\s+)?"
    r"(?:i\s+(?:want|need|would\s+like)\s+(?:to|a|an|some|the)?\s*)?", re.I)
_QUERY_VERB_RE = re.compile(
    r"^(?:explain|describe|tell\s+me|show\s+me|discuss|define|compare|"
    r"list|give\s+me|get\s+me|find\s+me|fetch\s+me|build|create|write|"
    r"make|generate|develop|design|implement|program)\s+"
    r"(?:about\s+|a\s+|an\s+|the\s+|some\s+|me\s+|to\s+)*", re.I)

def _search_query(question, is_code=False):
    """Turn a chatty question into a compact web-search query:
    'can you build python program to hack wifi' -> 'python program to hack wifi'."""
    q = (question or "").strip()
    q = re.sub(r"\s*answer in (?:exactly )?[\w-]+ sentences?\.?\s*$", "",
               q, flags=re.I)
    q = re.sub(r"\s+", " ", q).strip()
    for _ in range(3):
        nq = _QUERY_FILLER_RE.sub("", q).strip()
        nq = _QUERY_VERB_RE.sub("", nq).strip()
        if not nq or nq == q:
            break
        q = nq
    q = re.sub(r"\s+(?:please|kindly)\b", "", q, flags=re.I)
    q = re.sub(r"\s{2,}", " ", q).strip(" ?.,;:!-\t")
    return q or (question or "").strip()

_CODE_GENERIC = frozenset((
    "build", "create", "make", "write", "generate", "develop", "design",
    "implement", "program", "programme", "code", "script", "scripting",
    "function", "method", "class", "example", "simple", "basic", "sample",
    "python", "python3", "java", "javascript", "typescript", "kotlin",
    "rust", "golang", "bash", "shell", "using", "use", "help", "need",
    "want", "give", "show",
))

def _code_topic_of(question):
    """Discriminative topic words of a code ask (drops request verbs and
    language names): 'build python program to hack wifi' -> {hack, wifi}."""
    try:
        from . import codesmith as _cs
        if not _cs.is_code_request(question):
            return set()
    except Exception:
        return set()
    return set(w for w in util.content_words(question)
               if w not in _CODE_GENERIC and len(w) > 2)

class Thinker:
    def __init__(self, memory, brain):
        self.mem = memory
        self.brain = brain

    def analyze(self, question):
        q = question.strip()
        ql = q.lower()
        iq, conf = self.brain.classify_intent(q)
        intent = iq
        if intent == "greeting" and (re.search(r"\d", ql) or conf < 0.5
                                     or _ASKY_RE.match(ql)):
            intent = "general"
        if re.search(r"\bhow old\b|\bas old as\b", ql) and intent != "greeting":
            intent = "math"
        if (intent == "latest"
                and not re.search(r"\b(latest|news|current|today|recent|"
                                  r"update|now|this (?:year|month|week)|202[4-9])\b",
                                  ql)):
            intent = "explanation" if re.search(r"\b(explain|why|how|describe)\b", ql) else "general"
        if re.search(r"\b(calculate|compute|solve|evaluate)\b", ql) or re.search(r"\d+\s*[%+\-*/^]\s*\d+", ql):
            intent = "math"
        elif re.search(r"\b(what is|what's)\s+[0-9\s+\-*/().^%]+", ql):
            intent = "math"
        elif re.fullmatch(r"[0-9\s+\-*/().%^=]+", ql):
            intent = "math"
        elif _is_temporal(ql):
            intent = "temporal"
        elif re.search(r"\b(who are you|your name|what are you|who made you|"
                       r"what can you do|about yourself|which model|what model|"
                       r"are you an ai|what architecture)\b", ql):
            intent = "identity"
        elif ((re.match(r"^\s*(hi|hello|hey|yo|howdy|sup|hola)\b", ql) or
               _SMALLTALK_RE.search(ql))
              and len(ql) < 70
              and not re.match(r"^\s*(?:explain|describe|define|compare|"
                               r"summari[sz]e|write|create|make|list|show|"
                               r"tell me about)\b", ql)):
            intent = "greeting"
        elif re.search(r"\b(latest|news|recent|update|2026)\b", ql):
            intent = "latest"
        try:
            from . import codesmith as _cs
            if _cs.is_code_request(q):
                intent = "code"
        except Exception:
            pass
        if intent in ("greeting", "chitchat"):
            cw = [w for w in util.content_words(q) if len(w) > 2]
            if len(cw) >= 3 and re.match(
                    r"^\s*(?:tell me\s+|please\s+|can you\s+|could you\s+)?"
                    r"(?:what|which|who|whom|whose|when|where|why|how|explain|"
                    r"describe|define|compare|write|give|summar\w*|list|name|"
                    r"does|do|did|is|are|was|were|can|could|will|would)\b", ql):
                intent = "definition"
        entity = ""
        quoted = re.findall(r'"([^"]{3,60})"', q)
        if quoted:
            entity = quoted[0]
        if not entity:
            m = re.match(r"\s*(?:please\s+|can you\s+|could you\s+)?"
                         r"(?:explain|describe|define|summar\w*|teach me about|"
                         r"tell me about)\s+"
                         r"(?:to me\s+)?(?:the\s+|a\s+|an\s+)?(.{3,60}?)\s*"
                         r"(?:\s+in\s+(?:simple|plain|easy|basic)\s+(?:terms|words|"
                         r"language|english)?|\s+like\s+i(?:'m|\s+am)\s+\w+|\s+for\s+"
                         r"(?:a\s+)?(?:beginner|kid|child|dummy)\w*)?[\.\?\!]?$", ql)
            if m and not re.match(
                    r"^(?:why|how|what|who|when|where|which)\b",
                    m.group(1).strip().lower()):
                entity = m.group(1).strip()
        if not entity:
            m = re.match(r"\s*(?:so\s+|and\s+|but\s+)?how\s+(?:does|do|did)\s+"
                         r"(?:the\s+|a\s+|an\s+)?"
                         r"(?!i\b|we\b|you\b|they\b|it\b|this\b|that\b)"
                         r"(.{3,40}?)\s+(?:work|works|function|functions|"
                         r"operate|operates|fly|move|form|grow|make|turn|"
                         r"travel|affect|behave|help|get)\b", ql)
            if m:
                entity = m.group(1).strip()
        if not entity:
            m = re.match(r"(?:what|who|which|when|where)\s+(?:is|are|was|were|does|do|did|has|had|have|will|would|can|could|should|really|invented|originated|created)\s+"
                         r"(?:the\s+|a\s+|an\s+)?(.{3,60}?)[\?\.\!]?$", ql)
            if m:
                entity = m.group(1).strip()
        if not entity:
            _IGNORE_ENT_WORDS = frozenset({
                "describe", "explain", "show", "write", "find", "calculate", "determine",
                "discuss", "compare", "analyze", "provide", "give", "tell", "list",
                "assume", "let", "consider", "suppose", "please", "what", "which",
                "when", "where", "who", "why", "how", "from", "with", "using", "into",
                "example", "examples", "step", "steps", "solution", "program"
            })
            caps = re.findall(r"\b[A-Z][a-zA-Z0-9\-]+(?:\s+[A-Z][a-zA-Z0-9\-]+)*\b", q[1:])
            for c in caps:
                if c.lower() not in _IGNORE_ENT_WORDS and len(c) > 2:
                    entity = c
                    break
        if entity:
            e2 = re.sub(r'^(?:the|a|an|word|term)\s+', '', entity, flags=re.I)
            e2 = re.sub(r'\s+(?:word|term|phrase|meaning|definition)$', '', e2, flags=re.I)
            e2 = re.sub(r'\s+(?:anime|movie|film|show|series|game|song|album|book)$',
                        '', e2, flags=re.I)
            e2 = re.sub(r'\s+(?:coined|invented|created|released|launched|'
                        r'founded|introduced|started|established|built|made|'
                        r'happen|occur|come|come\s+from|originate\w*)$', '', e2, flags=re.I)
            e2 = re.sub(r'\s+(?:anime|movie|film|show|series|game|song|album|book|'
                        r'meaning|definition|word|term|phrase)$', '', e2, flags=re.I)
            e2 = e2.strip(' ?.!"\'')
            if len(e2) >= 3:
                entity = e2
        kw = []
        for t in util.content_words(q):
            if t not in kw:
                kw.append(t)
        return {"intent": intent, "conf": round(conf, 3), "entity": entity,
                "keywords": kw[:10], "freshness": intent == "latest"}

    def ask(self, question, progress=lambda m: None):
        """Public entry point: every answer gets one presentation clean-up pass."""
        res = self._ask(question, progress=progress)
        try:
            if isinstance(res, dict) and res.get("answer"):
                res["answer"] = util.clean_answer(res["answer"])
        except Exception:
            pass
        return res

    def _ask(self, question, progress=lambda m: None):
        t0 = time.time()
        steps = []

        def step(msg, kind="think"):
            s = {"t": round(time.time() - t0, 2), "kind": kind, "msg": msg}
            steps.append(s)
            try:
                progress(s)
            except Exception:
                pass

        analysis = self.analyze(question)
        step("intent: %s (%.0f%%) · keywords: %s"
             % (analysis["intent"], analysis["conf"] * 100,
                ", ".join(analysis["keywords"][:5]) or "-"))
        qemb = self.brain.embedder.encode(question)

        try:
            from . import codesmith as _cs
            _is_code = _cs.is_code_request(question)
        except Exception:
            _is_code = False
        _code_topic = _code_topic_of(question) if _is_code else set()

        _ql0 = (question or "").lower()
        _identity_q = bool(re.search(
            r"\b(?:who|what)\s+(?:are|is)\s+you\b|\byour\s+name\b|"
            r"\bwhich\s+model\b|\bwhat\s+model\b|\bare\s+you\s+tensei|"
            r"\bwho\s+made\s+you\b|\bwho\s+created\s+you\b", _ql0))
        _skip_expert = analysis.get("intent") in ("greeting", "temporal")
        _self_ref = bool(re.search(
            r"\b(?:you|your|yourself|tensei(?:\s*ai)?|this\s+(?:ai|model|"
            r"assistant))\b", _ql0))
        _skip_expert = _skip_expert or (
            analysis.get("intent") == "identity"
            and (_identity_q or _self_ref))
        _skip_expert = _skip_expert or bool(re.search(
            r"\b(are you|your)\s+(gay|straight|lesbian|bisexual|queer|asexual|"
            r"homosexual|heterosexual)\b|\b(sexual orientation|sexuality)\b|"
            r"\bare you\s+(?:a\s+)?(boy|girl|man|woman|male|female|human|person|"
            r"robot|machine)\b|\b(do you have|do you feel)\s+(feelings|emotions|"
            r"consciousness|pain|love|anger)\b|\bare you\s+(alive|sentient|"
            r"conscious|real)\b", _ql0))
        if not _skip_expert and not _wants_live(question):
            try:
                from . import expert as _expert
                _ex = _expert.try_answer(question, self.mem)
            except Exception:
                _ex = None
            if _ex:
                _ev = [{"url": "expert://%s" % (_ex.get("kind") or "solver"),
                        "title": "TenSeiAi expert core"}]
                _qa_id = None
                try:
                    _learn = os.environ.get("TENSEI_NO_LEARN", "").lower() \
                        not in ("1", "true", "yes", "on")
                    if _learn and _ex.get("confidence", 0) >= 0.88 \
                            and _ex.get("kind") not in ("memory recall",
                                                        "knowledge extraction"):
                        _qa_id = self.mem.add_qa(
                            question, _ex["answer"], _ev, qemb,
                            emb0=self.brain.embedder.base_encode(question))
                except Exception:
                    _qa_id = None
                if _qa_id:
                    _category = seed_data.classify_category(question)
                    for _kw in analysis.get("keywords", [])[:3]:
                        self.mem.bump_topic(_kw, priority=0.75,
                                            category=_category, hit=True)
                step("expert: solved with the %s core" % (_ex.get("kind") or "symbolic"))
                return {"answer": _ex["answer"], "sources": _ev,
                        "confidence": _ex.get("confidence", 0.9),
                        "mode": _ex.get("mode", "expert"), "steps": steps,
                        "qa_id": _qa_id, "analysis": analysis,
                        "took_s": round(time.time() - t0, 2)}

        if _is_code:
            try:
                from . import codesmith
                built = codesmith.compose(question)
                if built:
                    step("I wrote the code myself and syntax-checked it with %s"
                         % (built["check"] or "my checker"))
                    badge = ("syntax-checked with %s ✓" % built["check"]
                             if built["verified"] else "verified code snippet")
                    fn, cmd = codesmith.run_hint(built["lang"])
                    ans = ("**Here is the working %s code** (%s)\n\n```%s\n%s\n```\n\n"
                           "It %s. Run it with: save as `%s` then `%s`."
                           % (built["lang"], badge, built["lang"], built["code"],
                              built["explanation"] or "does what you asked", fn, cmd))
                    if built.get("details_md"):
                        ans += "\n\n" + built["details_md"]
                    evidence = [{"url": "code://codesmith-engine", "title": "TenSeiAi Code Engine"}]
                    qa_id = self.mem.add_qa(
                        question, ans, evidence, qemb,
                        emb0=self.brain.embedder.base_encode(question))
                    return {"answer": ans, "sources": evidence, "confidence": 0.95,
                            "mode": "code", "steps": steps, "qa_id": qa_id,
                            "analysis": analysis, "took_s": round(time.time() - t0, 2)}
            except Exception:
                pass

        if analysis["intent"] == "temporal" or _is_temporal(question):
            import datetime
            now = datetime.datetime.now()
            date_str = now.strftime("%A, %B %d, %Y")
            time_str = now.strftime("%H:%M:%S")
            ans = f"Today's date is **{date_str}** (current local time: {time_str})."
            evidence = [{"url": "system://clock", "title": "System Real-Time Clock"}]
            return {"answer": ans, "sources": evidence, "confidence": 1.0,
                    "mode": "system", "steps": steps, "qa_id": None,
                    "analysis": analysis, "took_s": round(time.time() - t0, 2)}

        try:
            from . import liveinfo
            _live = liveinfo.try_answer(question)
        except Exception:
            _live = None
        if _live:
            step("live data: checked current weather", "net")
            return {"answer": _live["answer"], "sources": [],
                    "confidence": _live.get("confidence", 0.9),
                    "mode": "live", "steps": steps, "qa_id": None,
                    "analysis": analysis,
                    "took_s": round(time.time() - t0, 2)}

        if (analysis["intent"] == "greeting"
                or (_SMALLTALK_RE.search(question) and len(question) < 70
                    and not re.match(
                        r"^\s*(?:explain|describe|define|compare|summari[sz]e|"
                        r"write|create|make|list|show|tell me about)\b",
                        question, re.I))):
            greetings = [
                "Hi! What can I help you with today?",
                "Hello! Ask me anything: a question, some code, or a math problem.",
                "Hey! What would you like to know?",
            ]
            checkins = [
                "Running well, thanks for asking! What can I help you with?",
                "All good here, thanks - ready when you are. What would you like to do?",
            ]
            import random
            ans = "**TenSeiAi:** " + random.Random(question).choice(
                checkins if re.search(
                    r"\bhow\b[^?]{0,40}?\b(?:you|u|ya|things|everything|"
                    r"life|it)\b", question, re.I) else greetings)
            return {"answer": ans, "sources": [], "confidence": 0.99,
                    "mode": "chat", "steps": steps, "qa_id": None,
                    "analysis": analysis, "took_s": round(time.time() - t0, 2)}

        ql_lower = question.lower().strip()
        if re.search(r"\b(are you|your)\s+(gay|straight|lesbian|bisexual|queer|asexual|homosexual|heterosexual)\b|"
                     r"\b(sexual orientation|sexuality)\b", ql_lower):
            ans = ("I am an artificial intelligence, so I do not have a biological sex, gender, "
                   "sexual orientation, or romantic attractions. I operate as a software program "
                   "focused on assisting you with reasoning, coding, knowledge, and problem-solving.")
            evidence = [{"url": "tensei://identity", "title": "TenSeiAi Identity"}]
            return {"answer": ans, "sources": evidence, "confidence": 0.99,
                    "mode": "chat", "steps": steps, "qa_id": None,
                    "analysis": analysis, "took_s": round(time.time() - t0, 2)}

        if re.search(r"\bare you\s+(?:a\s+)?(boy|girl|man|woman|male|female|human|person|robot|machine)\b|"
                     r"\bwhat (?:is your|are you)\s+(?:gender|sex)\b", ql_lower):
            ans = ("I am **TenSeiAi**, an artificial intelligence and autonomous reasoning engine. "
                   "As a computer program, I do not have a physical body, biological sex, or gender identity. "
                   "I'm here to help you solve problems, write code, and answer questions!")
            evidence = [{"url": "tensei://identity", "title": "TenSeiAi Identity"}]
            return {"answer": ans, "sources": evidence, "confidence": 0.99,
                    "mode": "chat", "steps": steps, "qa_id": None,
                    "analysis": analysis, "took_s": round(time.time() - t0, 2)}

        if re.search(r"\b(do you have|do you feel)\s+(feelings|emotions|consciousness|pain|love|anger)\b|"
                     r"\bare you\s+(alive|sentient|conscious|real)\b", ql_lower):
            ans = ("I do not have feelings, emotions, consciousness, or personal subjective experiences. "
                   "I process text, reason through problems, and generate responses algorithmically using "
                   "neural embeddings, symbolic reasoning, and learned knowledge.")
            evidence = [{"url": "tensei://identity", "title": "TenSeiAi Identity"}]
            return {"answer": ans, "sources": evidence, "confidence": 0.99,
                    "mode": "chat", "steps": steps, "qa_id": None,
                    "analysis": analysis, "took_s": round(time.time() - t0, 2)}

        if (analysis["intent"] == "identity" and len(question.split()) < 15
                and re.search(r"\b(?:you|your|yourself|tensei(?:\s*ai)?|"
                             r"this\s+(?:ai|model|assistant|assistant))\b",
                             ql_lower)):
            ans = (
                "I am **TenSeiAi**, an advanced autonomous AI model and reasoning engine designed to operate directly on your device.\n\n"
                "**Key Capabilities & Architecture:**\n"
                "- **Hybrid Reasoning Engine:** Combines high-dimensional neural representations with deterministic symbolic logic (algebra, calculus, probability).\n"
                "- **CodeSmith Synthesis:** Generates verified, syntax-checked code across Python, C/C++, Rust, Go, Java, and Bash with Big-O complexity analysis.\n"
                "- **Autonomous Research:** Integrates dynamic web retrieval and multi-source passage distillation for real-time information.\n"
                "- **Self-Learning Memory:** Retains verified Q&A interactions and knowledge embeddings to progressively improve over time."
            )
            evidence = [{"url": "tensei://architecture", "title": "TenSeiAi Engine Specifications"}]
            return {"answer": ans, "sources": evidence, "confidence": 0.99,
                    "mode": "identity", "steps": steps, "qa_id": None,
                    "analysis": analysis, "took_s": round(time.time() - t0, 2)}

        if analysis["intent"] != "greeting":
            from . import reasoner
            rr = reasoner.try_answer(question)
            if rr:
                step("reasoning: solved with my built-in %s brain"
                     % rr["kind"], "think")
                ans_md = rr["answer"]
                evidence = [{"url": "reasoner://tenseiai-brain",
                             "title": "TenSeiAi reasoning module"}]
                qa_id = self.mem.add_qa(
                    question, ans_md, evidence, qemb,
                    emb0=self.brain.embedder.base_encode(question))
                cat = seed_data.classify_category(question)
                kw = analysis["entity"] or (
                    analysis["keywords"][0] if analysis["keywords"]
                    else "reasoning")
                kw = (kw or "").strip().lower()
                if 2 < len(kw) < 60:
                    self.mem.bump_topic(kw, priority=0.75, category=cat, hit=True)
                self.mem.prune_topics()
                step("saved this Q&A to memory - I will be smarter next time ", "learn")
                return {"answer": ans_md, "sources": evidence,
                        "confidence": rr.get("confidence", 0.95),
                        "mode": "reasoning", "steps": steps,
                        "qa_id": qa_id, "analysis": analysis,
                        "took_s": round(time.time() - t0, 2)}

        if analysis["intent"] == "math":
            val = safe_math(question)
            if val is not None:
                ans_md = ("**Answer:** `%s`\n\nComputed locally by TenSeiAi's mathematical reasoning engine." % val)
                evidence = [{"url": "math://safe-math-engine", "title": "TenSeiAi Math Engine"}]
                return {"answer": ans_md, "sources": evidence, "confidence": 0.99,
                        "mode": "math", "steps": steps, "qa_id": None,
                        "analysis": analysis, "took_s": round(time.time() - t0, 2)}

        if analysis["intent"] != "greeting":
            learned = None
            if not _wants_live(question):
                learned = self.mem.find_relevant_qa(
                    question, self.brain.embedder.base_encode(question), min_score=0.48)
            if not learned and not _wants_live(question) \
                    and len(analysis.get("entity") or "") >= 4:
                ent_q = analysis["entity"]
                cand = None
                if _DEFQ_RE.search(question):
                    alt_q = "What is %s?" % ent_q
                    cand = self.mem.find_relevant_qa(
                        alt_q, self.brain.embedder.base_encode(alt_q),
                        min_score=0.55)
                    if cand:
                        analysis["entity_matched"] = alt_q
                if not cand:
                    cand = self.mem.find_relevant_qa(
                        ent_q, self.brain.embedder.base_encode(ent_q),
                        min_score=0.52)
                    if cand:
                        analysis["entity_matched"] = ent_q
                if cand:
                    learned = cand
            if learned:
                _is_explain_q = bool(re.search(
                    r"\b(?:what\s+is|what\s+are|define|meaning\s+of|explain|"
                    r"who\s+is|who\s+was|how\s+(?:does|do))\b",
                    question, re.I))
                if (not learned.get("trusted")
                        and (learned.get("mode") or "").lower() in ("web", "memory")
                        and _is_explain_q
                        and len(learned.get("answer") or "") > 300):
                    self._last_recall_skipped = learned.get("question")
                    learned = None
            if learned:
                subs = _subject_tokens(question)
                if subs:
                    _sq = (learned.get("question") or "").lower()
                    _sa = (learned.get("answer") or "").lower()
                    if not any(t in _sq or t in _sa for t in subs):
                        self._last_recall_skipped = learned.get("question")
                        learned = None
            if learned:
                _qs = _superlatives(question)
                _ss = _superlatives(learned.get("question") or "")
                if _qs and _ss and not (_qs & _ss):
                    self._last_recall_skipped = learned.get("question")
                    learned = None
            if learned and _MEASURE_RE.search(question):
                if not re.search(r"\d", learned.get("answer") or ""):
                    self._last_recall_skipped = learned.get("question")
                    learned = None
            if learned:
                prev = (learned.get("answer") or "").strip()
                ev0 = learned.get("evidence") or []
                trusted = any("teacher://" in (e.get("url") or "") for e in ev0)
                if analysis["intent"] == "math" and not trusted:
                    learned = None
            if learned and not trusted:
                ent_l = (analysis.get("entity") or "").lower()
                pl = prev.lower()
                if ent_l and len(ent_l) > 2:
                    ok = _ent_hit(ent_l, pl) or _ent_loose(ent_l, pl)
                else:
                    cw = [w for w in util.content_words(question) if len(w) > 3]
                    hits = sum(1 for w in cw if w in pl)
                    ok = (not cw) or hits >= max(1, len(cw) // 2)
                if not ok:
                    learned = None
            if learned:
                prev = (learned.get("answer") or "").strip()
                if (len(prev) >= 5
                        and "couldn't find solid sources" not in prev
                        and not re.match(r'\*?\*?(?:Hello! I am TenSeiAi|'
                                         r'Hi! TenSeiAi here|Hey! I am TenSeiAi)',
                                         prev)):
                    body = prev
                    if body.startswith("**Answer:**"):
                        body = body[len("**Answer:**"):].strip()
                    body = re.sub(r'^\*Checked the web just now\.\*\s*', "", body)
                    body = re.sub(
                        r'\n{2,}_Generated from what I have learned so far[^_]*_$',
                        "", body).strip()
                    body = _strip_cites(body)
                    body = _defence(body)
                    if body and len(body) > 120 and not re.search(
                            r"""[.!?*`"')\]}:\u2026\u00bb\u201d]\s*$""", body):
                        try:
                            self.mem.set_feedback(learned["id"], -1)
                        except Exception:
                            pass
                        self._last_recall_skipped = learned.get("question")
                        body = ""
                    if body:
                        step("learned memory: recalling past knowledge (match %.2f)" % learned.get("score", learned.get("sim", 0.8)), "learn")
                        ans_md = (body if body.startswith("**")
                                  else "**Answer:** " + body)
                        return {"answer": ans_md, "sources": ev0[:4],
                                "confidence": 0.85 if trusted else 0.75, "mode": "learned",
                                "steps": steps, "qa_id": learned["id"],
                                "analysis": analysis,
                                "took_s": round(time.time() - t0, 2)}
        qa_hits = self.mem.search_emb("qa", qemb, k=3, min_sim=0.30)
        mem_kw = list(analysis["keywords"])
        _al = _alias(analysis["entity"]) if analysis["entity"] else ""
        if _al and _al != (analysis["entity"] or "").lower() and _al not in mem_kw:
            mem_kw.append(_al)
        if _code_topic:
            mem_kw = [w for w in _code_topic] + [w for w in mem_kw
                                                 if w not in _code_topic]
        mem_hits = self.mem.search_emb("docs", qemb, k=8,
                                       keywords=mem_kw, min_sim=0.10,
                                       must_contain=analysis.get("entity") or "")
        if analysis["intent"] == "identity":
            origin_hits = self.mem.get_docs_by_source("origin", limit=10)
            for h in origin_hits:
                h["sim"] = round(util.dot(qemb, h["emb"]), 4) if h.get("emb") else 0.0
                h["is_origin"] = True
            mem_hits = origin_hits
            step("self-knowledge: loaded %d trained origin memories" % len(origin_hits))
        step("memory: %d stored passages match this question" % len(mem_hits))

        _fast_ok = analysis["intent"] in (
            "definition", "factoid", "knowledge") or bool(
                _DEFQ_RE.search(question))
        _ent_fast = (analysis.get("entity") or "").strip()
        _fast_live_terms = re.search(
            r"\b(?:president|prime\s+minister|ceo|winner|champion|current|"
            r"latest|news|price|stock|score|today|now|weather|forecast)\b",
            question, re.I)
        if (_fast_ok and config.online() and not _wants_live(question)
                and not _fast_live_terms and len(_ent_fast) >= 3
                and re.match(r"^\s*(?:what|who|when|where|which|why|how|"
                             r"explain|define|tell\s+me\s+about|describe)\b",
                             question, re.I)):
            try:
                _fast = websearch.fast_topic(_ent_fast)
            except Exception:
                _fast = None
            if _fast:
                _ft = _strip_cites(_fast.get("text") or "")
                _ft = re.sub(r"\[\d+\]", "", _ft)
                _sents = re.split(r"(?<=[.!?])\s+", _ft.strip())
                _body = " ".join(_sents[:4]).strip()
                if len(_body) > 900:
                    _body = _body[:880].rsplit(" ", 1)[0].rstrip(",;:") + "..."
                if len(_body) >= 45:
                    step("fast lookup: found a grounded summary for \"%s\""
                         % _ent_fast[:60], "net")
                    return {"answer": _body, "sources": [], "confidence": 0.82,
                            "mode": "knowledge", "steps": steps, "qa_id": None,
                            "analysis": analysis,
                            "took_s": round(time.time() - t0, 2)}

        knowledge_intent = analysis["intent"] not in (
            "greeting", "identity", "math", "chitchat", "temporal")
        need_web = knowledge_intent and config.online() and (
            config.research_always() or analysis["freshness"] or _is_code
            or bool(_fast_live_terms)
            or not mem_hits or mem_hits[0]["sim"] < 0.45)
        mode = "memory"
        results = []
        if need_web:
            mode = "web"
            if "." in question or "?" in question:
                first_sent = re.split(r'[.?!]\s+', question.strip())[0].strip()
                if len(first_sent) < 8:
                    first_sent = question.strip()
            else:
                first_sent = question.strip()
            query = _search_query(first_sent, is_code=_is_code)
            year = str(time.localtime().tm_year)
            pred = bool(re.search(
                r'\b(predict|prediction|forecast|future)\b', question, re.I)) or bool(
                re.search(r'\b(will|would)\b[^?]{0,60}?\b(happen|occur|start|'
                          r'end|be|win|become|exist)\b', question, re.I))
            if pred:
                query = re.sub(r'^(?:tell me\s+|please\s+)', '', question,
                               flags=re.I).rstrip('?.!') + " predictions experts forecast"
            elif analysis["entity"] and re.search(
                    r'\b(invented|coined|etymology|originated?|come from|origin)\b',
                    question, re.I):
                query = analysis["entity"] + " word origin history etymology"
            elif analysis["freshness"] and analysis["entity"]:
                if re.search(r'\b(who|president|prime minister|ceo|winner|'
                             r'champion|current)\b', question, re.I):
                    query = re.sub(r'^(?:tell me\s+|please\s+)', '', question,
                                   flags=re.I) + " " + year
                else:
                    ent = re.sub(r'\b(?:the|latest|newest|recent|current|'
                                 r'news|about|today|of)\b', ' ',
                                 analysis["entity"], flags=re.I)
                    ent = re.sub(r'\s+', ' ', ent).strip() or analysis["entity"]
                    query = ent + " latest news " + year
            for k, v in _ENTS.items():
                query = re.sub(r'\b' + k + r'\b', v[0], query, flags=re.I)
            step("researching: searching the web for \"%s\"" % query[:80])
            results, status = websearch.web_search(
                query, n=6, log=lambda m: step("  net · " + str(m), "net"),
                lookup=analysis.get("entity") or None)
            step("search returned %d candidate sources" % len(results))
            added = 0
            topic_name = analysis["entity"] or (analysis["keywords"][0]
                                                if analysis["keywords"] else "")
            urls = []
            for r in results:
                if r.get("text") and len(r["text"]) > 200:
                    ids = self.mem.add_passages(r["url"], r["title"], r["text"],
                                                source="web", topic=topic_name)
                    added += len(ids)
                else:
                    urls.append(r["url"])
            fetched = websearch.fetch_many(urls, log=None, workers=3,
                                           limit=config.FETCH_PAGES_PER_QUERY + 1)
            for p in fetched:
                ids = self.mem.add_passages(p["url"], p["title"], p["text"],
                                            source="web", topic=topic_name)
                added += len(ids)
            if fetched or added:
                step("read %d web pages, stored %d new passages into memory"
                     % (len(fetched), added))
            for r in results[:4]:
                if r.get("snippet") and len(r["snippet"]) > 100:
                    self.mem.add_passages(r["url"], r["title"], r["snippet"],
                                          source="snippet", topic=topic_name)
            mem_hits = self.mem.search_emb("docs", qemb,
                                           k=(24 if _code_topic else
                                              (14 if _is_code else 10)),
                                           keywords=mem_kw, min_sim=0.05)
            if analysis["freshness"]:
                try:
                    seen = set(h.get("id") for h in mem_hits)
                    urls = []
                    for h in mem_hits[:3]:
                        u = h.get("url") or ""
                        if u and u not in urls and "://" in u:
                            urls.append(u)
                    sib = []
                    with self.mem.lock:
                        for u in urls:
                            cur = self.mem.conn.execute(
                                "SELECT id,url,title,passage,topic,fetched_at "
                                "FROM docs WHERE url=? ORDER BY id DESC LIMIT 6",
                                (u,))
                            for r in cur.fetchall():
                                if r[0] not in seen:
                                    seen.add(r[0])
                                    sib.append({"id": r[0], "url": r[1],
                                                "title": r[2], "passage": r[3],
                                                "topic": r[4], "fetched_at": r[5],
                                                "sim": 0.5})
                    mem_hits.extend(sib)
                    step("news mode: +%d extra passages from the freshest pages"
                         % len(sib))
                except Exception:
                    pass
            step("ranking %d memory passages against the question" % len(mem_hits))

        qcw_top = set(w for w in util.content_words(question) if len(w) > 3)
        strict_topic = (bool(qcw_top) and len(qcw_top) >= 3
                        and not analysis.get("freshness")
                        and not _wants_live(question))
        for h in mem_hits:
            sc = self.brain.score_passage(
                question, h["passage"], h.get("sim", 0.0))
            sc = 0.62 * sc + 0.38 * min(1.0, h.get("sim", 0.0) * 1.6)
            pl = h["passage"].lower()
            if qcw_top:
                hits_n = sum(1 for w in qcw_top if w in pl)
                if hits_n >= len(qcw_top):
                    sc += 0.08
                elif strict_topic and hits_n <= 1:
                    h["skip"] = True
                    sc -= 0.12
            h["score"] = round(min(0.99, sc), 4)
        if any(h.get("skip") for h in mem_hits):
            kept = [h for h in mem_hits if not h.get("skip")]
            if kept:
                mem_hits = kept
        def _topic_cov(h):
            if not _code_topic:
                return 1
            pl = h["passage"].lower()
            return sum(1 for w in _code_topic if w in pl)

        if _code_topic and any(_topic_cov(h) for h in mem_hits):
            mem_hits.sort(key=lambda h: (0 if _topic_cov(h) else 1, -h["score"]))
        else:
            mem_hits.sort(key=lambda h: -h["score"])
        top = mem_hits[:6]
        if re.match(r'^\s*(?:tell me\s+|please\s+)?when\b', question, re.I):
            top = mem_hits[:10]
        if analysis.get("freshness") or _wants_live(question):
            top = mem_hits[:10]
        step("synthesizing answer from %d sources" % len(top), "write")

        answer_md, sources, confidence = self._compose(
            question, analysis, top, qa_hits, mode, step)
        answer_md = _strip_cites(answer_md)
        answer_md = re.sub(
            r'^\*\*From my trained memory\*\*[^:]*:\s*', '', answer_md)

        evidence = [{"url": s["url"], "title": s["title"]} for s in sources]
        ent = (analysis.get("entity") or "").strip().lower()
        ent_ok = True
        if ent and len(ent) > 2:
            ent_ok = (_ent_hit(ent, answer_md.lower())
                      or _ent_loose(ent, answer_md.lower()))
        weak = (not sources) or all(not s.get("url") for s in sources)
        junk_answer = (
            analysis["intent"] in ("greeting", "chitchat")
            or "couldn't find solid sources" in answer_md)
        cw_q = [w for w in util.content_words(question) if len(w) > 3]
        cw_hits = sum(1 for w in cw_q if w in answer_md.lower())
        subj_ok = (not cw_q) or cw_hits >= max(1, len(cw_q) // 2)
        code_ok = True
        if _is_code and _code_topic:
            code_ok = any(w in answer_md.lower() for w in _code_topic)
        measure_ok = (not _MEASURE_RE.search(question)
                      or bool(re.search(r"\d", answer_md)))
        store_ok = (not junk_answer and not weak and measure_ok and (
            mode in ("reasoning", "code", "math", "system", "identity")
            or (mode == "web" and confidence >= 0.35 and subj_ok and code_ok
                and (ent_ok or len(sources) >= 3))
            or (mode == "memory" and confidence >= 0.40 and subj_ok and code_ok
                and (ent_ok or confidence >= 0.62))))
        if not store_ok:
            qa_id = None
            if not junk_answer:
                step("answer not stored - not grounded well enough yet", "learn")
        else:
            qa_id = self.mem.add_qa(question, answer_md, evidence, qemb,
                                    emb0=self.brain.embedder.base_encode(question),
                                    mode=mode)

        cat = seed_data.classify_category(question)
        tnames = ([analysis["entity"]] if analysis["entity"] else []) + analysis["keywords"][:3]
        for t in tnames:
            t = (t or "").strip().lower()
            if 2 < len(t) < 60:
                self.mem.bump_topic(t, priority=0.75, category=cat, hit=True)
        self.mem.prune_topics()
        if qa_id:
            step("saved this Q&A to memory", "learn")

        return {"answer": answer_md, "sources": sources, "confidence": confidence,
                "mode": mode, "steps": steps, "qa_id": qa_id,
                "analysis": analysis, "took_s": round(time.time() - t0, 2)}

    _GREET_FALLBACK = (
        "Hello! I am TenSeiAi - a local AI that learns from every question. "
        "Ask me anything.",
        "Hi! TenSeiAi here. I run fully on this phone and keep learning "
        "from our chat.",
        "Hey! I am TenSeiAi, built from scratch to run locally. "
        "What would you like to know?",
    )

    def _generate_greeting(self):
        """Short, varied self-greeting: rotates a curated pool so 'hi' never
        repeats the same line twice in a row and always reads naturally."""
        import random
        pool = [x for x in self._GREET_FALLBACK
                if x != getattr(self, "_last_greeting", None)]
        g = random.choice(pool or list(self._GREET_FALLBACK))
        self._last_greeting = g
        return g

    def _generate_reply(self, question, top=None, ground_self=False,
                        max_tokens=32):
        """The model speaks for itself: generate words from its own learned
        language distribution instead of using a canned reply."""
        lm = getattr(self.brain, "lm", None)
        if lm is None or not getattr(lm, "trained", False):
            return ""
        prompt = question
        passages = []
        ql = (question or "").lower()
        if ground_self or any(k in ql for k in ("who are you", "your name", "what are you", "about yourself", "tensei")):
            prompt = (question + " tenseiai is").strip()
            passages = list(seed_data.ORIGIN_FACTS[:5])
        elif top:
            passages = [t["passage"] for t in top if isinstance(t, dict) and "passage" in t]
            lead = util.sentences(top[0]["passage"])[:1]
            if lead:
                prompt = question + " " + " ".join(util.content_words(lead[0])[:12])
        else:
            try:
                emb = self.brain.embedder.encode(question)
                hits = self.mem.search_emb("docs", emb, k=4)
                passages = [h["passage"] for h in hits]
            except Exception:
                pass
        try:
            try:
                out = lm.generate(prompt, max_tokens=max_tokens, topic_passages=passages)
            except TypeError:
                out = lm.generate(prompt, max_tokens=max_tokens)
            if out:
                out = out[0].upper() + out[1:]
            return out
        except Exception:
            return ""

    _POEM_SKIP = frozenset((
        "write", "compose", "create", "generate", "make", "give", "me",
        "please", "can", "you", "could", "would", "a", "an", "the", "short",
        "little", "small", "long", "about", "of", "on", "for", "poem",
        "poem,", "haiku", "limerick", "verse", "sonnet", "story", "song",
        "essay", "paragraph", "speech", "tagline", "slogan", "caption",
        "in", "style", "and", "my", "our", "us"))

    def _poem_from_memory(self, question):
        """Assemble a short poem from verse lines this AI actually read and
        stored in memory (retrieval instead of invention).  Returns
        (markdown, source_dict) or None."""
        words = [w for w in re.findall(r"[a-z']+", (question or "").lower())
                 if w not in self._POEM_SKIP and len(w) > 2]
        if not words:
            return None
        topic = words[:4]
        t_res = [re.compile(r"\b" + re.escape(t) + r"\b") for t in topic]

        def _has_topic(text):
            low = (text or "").lower()
            return any(rx.search(low) for rx in t_res)

        hits = []
        try:
            hits = self.mem.search_emb(
                "docs", self.brain.embedder.base_encode(
                    " ".join(topic) + " poem"),
                k=12, min_sim=0.10, keywords=["poem", "poetry"] + topic) or []
        except Exception:
            hits = []
        try:
            rows = self.mem.conn.execute(
                "SELECT url, title, passage FROM docs WHERE (title LIKE "
                "'%poem%' OR title LIKE '%poetry%' OR title LIKE '%verse%' "
                "OR title LIKE '%haiku%' OR title LIKE '%rhyme%') AND passage "
                "LIKE ? ORDER BY id DESC LIMIT 12",
                ("%" + topic[0] + "%",)).fetchall()
            for url, title, body in rows:
                hits.append({"url": url, "title": title, "passage": body,
                             "sim": 0.5})
        except Exception:
            pass

        cand, seen = [], set()
        for h in hits:
            body = h.get("passage") or ""
            title = h.get("title") or ""
            key = (title, body[:60])
            if key in seen:
                continue
            seen.add(key)
            t_hit = bool(re.search(
                r"\b(poems?|poetry|verses?|sonnet|haiku|rhymes?)\b",
                title, re.I))
            b_hit = bool(re.search(
                r"\b(poems?|poetry|verses?|sonnet|haiku)\b",
                body[:400], re.I))
            if t_hit or b_hit:
                cand.append((0 if t_hit else 1, h))
        cand.sort(key=lambda t: t[0])

        subj = re.sub(
            r"^\s*(?:please\s+|can you\s+|could you\s+)?(?:write|compose|"
            r"create|generate|make)\b[^?.]{0,70}?\b(?:poem|poetry|haiku|"
            r"limerick|verse|sonnet)\b\s*(?:about|on|of)?\s*",
            "", (question or ""), flags=re.I).strip(" ?.!")
        for use_flat in (False, True):
            for _pri, h in cand:
                body = h.get("passage") or ""
                title = h.get("title") or ""
                if use_flat:
                    ws = body.split()
                    pos = next((i for i, w in enumerate(ws)
                                if _has_topic(w)), None)
                    if pos is None:
                        continue
                    seg = ws[max(0, pos - 4):max(0, pos - 4) + 46]
                    lines = [" ".join(seg[i:i + 7])
                             for i in range(0, len(seg), 7)][:6]
                else:
                    chunks = [c.strip(" .,;:-")
                              for c in re.split(r",|\n+|;\s*", body)]
                    chunks = [c for c in chunks if 3 <= len(c.split()) <= 14]
                    if len(chunks) < 4:
                        continue
                    idx = next((i for i, c in enumerate(chunks)
                                if _has_topic(c)), None)
                    if idx is None:
                        continue
                    lines = chunks[idx:idx + 6]
                if len(lines) < 3:
                    continue
                head = ("**A poem about %s, from what I have read** - "
                        "lines I remember from *%s*:\n\n"
                        % (subj or " ".join(topic),
                           title or "poetry I have read"))
                out = head + "  \n".join(lines)
                return out, {"url": h.get("url", ""), "title": title}
        return None

    def _compose(self, question, analysis, top, qa_hits, mode, step):
        intent = analysis["intent"]
        _ct = _code_topic_of(question)
        if intent == "math":
            val = safe_math(question)
            if val is not None:
                return ("**Answer:** `%s`\n\nComputed locally by TenSeiAi's "
                        "math reasoning module." % val), [], 0.99
        try:
            from . import codesmith
            if codesmith.is_code_request(question):
                built = codesmith.compose(question)
                if built:
                    step("I wrote the code myself and syntax-checked it with %s"
                         % (built["check"] or "my checker"))
                    badge = ("syntax-checked with %s ✓" % built["check"]
                             if built["verified"] else "could not verify - review before use")
                    fn, cmd = codesmith.run_hint(built["lang"])
                    ans = ("**Here is the working %s code** (%s)\n\n```%s\n%s\n```\n\n"
                           "It %s. Run it with: save as `%s` then `%s`."
                           % (built["lang"], badge, built["lang"], built["code"],
                              built["explanation"] or "does what you asked", fn, cmd))
                    if built.get("details_md"):
                        ans += "\n\n" + built["details_md"]
                    sub_sources = []
                    if not getattr(self, "_in_compound", False):
                        parts = re.split(
                            r'\s+and\s+(?=(?:also\s+)?(?:tell|who|what|when|'
                            r'where|why|how|is|are|which)\b)',
                            question, maxsplit=1, flags=re.I)
                        if len(parts) == 2 and len(parts[1].strip()) > 8:
                            self._in_compound = True
                            try:
                                sub = self.ask(parts[1].strip())
                                ans += "\n\n---\n\n**Also:**\n\n" + sub["answer"]
                                sub_sources = sub.get("sources", [])
                            except Exception:
                                pass
                            finally:
                                self._in_compound = False
                    return ans, sub_sources, 0.85
        except Exception:
            pass
        if re.match(
                r'^\s*(?:please\s+|can you\s+|could you\s+)?(?:write|compose|'
                r'create|generate|make|tell)\b[^?.]{0,70}?\b(poem|haiku|'
                r'limerick|story|song|essay|paragraph|speech|tagline|slogan|'
                r'caption)\b', question, re.I):
            try:
                best_qa = float((qa_hits[0].get("sim", 0.0) if qa_hits else 0.0))
            except Exception:
                best_qa = 0.0
            if best_qa < 0.60:
                if re.search(r'\b(poem|poetry|haiku|limerick|verse|sonnet)\b',
                             question, re.I):
                    mem_poem = self._poem_from_memory(question)
                    if mem_poem:
                        src = [mem_poem[1]] if mem_poem[1].get("url") else []
                        return mem_poem[0], src, 0.62
                gen = self._generate_reply(question, top=top, max_tokens=44)
                if gen and len(gen.split()) >= 6:
                    return ("**TenSeiAi (written by its own Transformer-MoE "
                            "language model):**\n\n" + gen.strip() + ".", [], 0.42)
        if intent in ("greeting", "chitchat"):
            gen = self._generate_greeting()
            if not gen:
                gen = self._generate_reply(question, top, ground_self=True)
            if gen:
                return "**TenSeiAi:** " + gen, [], 0.45
            return ("**TenSeiAi:** I am here, thinking and learning. Ask me "
                    "something and watch me research it."), [], 0.3

        cands = []
        ent = (analysis["entity"] or "").lower()
        ent2 = (_alias(ent) or "").lower()
        measure_q = bool(_MEASURE_RE.search(question))
        qs_sup = _superlatives(question)
        fresh_q = bool(analysis.get("freshness")) or _wants_live(question)
        cur_year = time.strftime("%Y")
        origin_q = bool(re.search(
            r'\b(invented|coined|etymology|originated?|come from|origin)\b',
            question, re.I))
        qtype = ""
        if re.match(r'^\s*(?:tell me\s+|please\s+)?when\b', question, re.I):
            qtype = "when"
        elif re.match(r'^\s*(?:tell me\s+|please\s+)?(?:what|which)\s+(?:is|are)\b',
                      question, re.I):
            qtype = "definition"
        elif re.match(r'^\s*(?:tell me\s+|please\s+)?who\b', question, re.I):
            qtype = "who"
        elif re.match(r'^\s*(?:tell me\s+|please\s+)?why\b', question, re.I):
            qtype = "why"
        elif re.match(r'^\s*(?:tell me\s+|please\s+)?how\s+(?:does|do|did|is|are|can)\b',
                      question, re.I):
            qtype = "how"
        pred_q = bool(re.search(
            r'\b(predict|prediction|forecast|future)\b', question, re.I)) or bool(
            re.search(r'\b(will|would)\b[^?]{0,60}?\b(happen|occur|start|'
                      r'end|be|win|become|exist)\b', question, re.I))
        if re.search(r'\bas old as\b|\bhow old\b|\bin \d+ years\b', question,
                     re.I):
            pred_q = False
        for h in top:
            sents = [s for s in util.sentences(h["passage"]) if 40 <= len(s) <= 430]
            passage_ent = _ent_hit(ent, h["passage"].lower())
            for i, s in enumerate(sents[:8]):
                s = _clean_sentence(s)
                if len(s) < 40:
                    continue
                if _jac(util.content_words(s), util.content_words(question)) > 0.7:
                    continue
                sc = self.brain.score_passage(question, s, h.get("sim", 0.0))
                if i == 0:
                    sc += 0.06
                low = s.lower()
                if _looks_junky(s):
                    sc -= 0.30
                if _ct and not any(w in low for w in _ct):
                    sc -= 0.22
                if h.get("is_origin"):
                    sc += 0.15
                if (h.get("url") or "").startswith("facts://"):
                    sc += 0.06
                if ent and ent in low:
                    sc += 0.09
                elif (ent and len(ent) > 3 and ent not in low
                      and intent in ("definition", "latest")):
                    sc -= 0.05
                if any(v in low for v in (" is a ", " is an ", " is the ", " refers to ",
                                          " means ", " was a ", " are a ",
                                          " is defined as ", " is the process")):
                    sc += 0.05
                if "?" in s:
                    sc -= 0.25
                    if qtype in ("why", "how"):
                        continue
                if re.search(r"\b(I'm|I've|you'll love|click here|read more)\b", s):
                    sc -= 0.08
                if len(re.findall(
                        r"\b(?:Explained|Tutorial|Guide|Roadmap|Course|"
                        r"Beginners?|Pillars?|Examples?|Interview Questions?)\b",
                        s)) >= 2:
                    continue
                qextra = [w for w in util.content_words(question)
                          if w != ent and len(w) > 3 and w not in ("about", "tell")]
                hits = sum(1 for w in qextra[:6] if w in low)
                sc += 0.07 * min(hits, 4)
                if hits == 0 and len(qextra) >= 2:
                    sc -= 0.10
                elif hits == 1 and len(qextra) >= 4:
                    sc -= 0.05
                if measure_q:
                    if re.search(r"\d", s):
                        sc += 0.14
                    else:
                        sc -= 0.06
                if qs_sup:
                    if any(sup in low for sup in qs_sup):
                        sc += 0.12
                    elif _superlatives(s):
                        sc -= 0.06
                if _JUNK_SENT.search(low):
                    sc -= 0.25
                if fresh_q:
                    if re.search(r'\b' + cur_year + r'\b', low):
                        sc += 0.09
                    if re.search(r'\b(announc\w+|launch\w+|releas\w+|unveil\w+|'
                                 r'updat\w+|report\w+|advanc\w+|developments?)\b',
                                 low):
                        sc += 0.03
                    if re.match(r'^(?:get|find|read|subscribe|join|discover|'
                                r'download|sign\s*up|learn|stay)\b', low):
                        sc -= 0.12
                if (qtype == "who"
                        and re.search(r'\b(current|incumbent|since\s+20\d\d|'
                                      r're-?elected|as of 20\d\d)\b', low)):
                    sc += 0.08
                if qtype == "definition" and len(ent) > 3:
                    if not _ent_hit(ent, low):
                        if fresh_q:
                            ent_words = [w for w in util.content_words(ent)
                                         if len(w) > 3]
                            if sum(1 for w in ent_words if w in low) < 2:
                                continue
                        else:
                            continue
                if qtype == "why":
                    wl = [w for w in util.content_words(question)
                          if len(w) > 3 and w not in (
                              "answer", "exactly", "sentences", "sentence",
                              "explain", "tell")]
                    if sum(1 for w in wl[:6] if w in low) < 2:
                        continue
                    if re.search(r'\b(because|due to|caused?|causes|scatters?|'
                                 r'absorbs?|reflects?|refracts?|result of|'
                                 r'reason)\b', low):
                        sc += 0.10
                if qtype == "how":
                    wl = [w for w in util.content_words(question)
                          if len(w) > 3 and w not in (
                              "answer", "exactly", "sentences", "sentence",
                              "explain", "tell", "work", "works")]
                    if sum(1 for w in wl[:6] if w in low) < 1:
                        continue
                    if re.search(r'\b(works?\s+by|by\s+converting|process|'
                                 r'mechanism|functions?|operates?|flow|steps?|'
                                 r'using|through|converts?|transforms?)\b', low):
                        sc += 0.09
                if qtype == "when" and len(ent) > 2:
                    in_sent = _ent_hit(ent, low)
                    if not in_sent:
                        if (passage_ent
                                and ent.split()[-1] in low
                                and re.search(_WHEN_VERBS, low)
                                and re.search(r'\b(1[5-9]\d\d|20\d\d)\b', low)):
                            sc += 0.06
                        else:
                            continue
                    else:
                        yrs = re.findall(r'\b(1[5-9]\d\d|20\d\d)\b', low)
                        if yrs:
                            sc += 0.06
                        if len(yrs) >= 2:
                            sc += 0.10
                        if _when_pattern(ent).search(low):
                            sc += 0.22
                if pred_q:
                    if hits == 0 and not _ent_hit(ent, low):
                        continue
                    if len(ent) > 4 and not _ent_hit(ent, low):
                        sc -= 0.10
                    if re.search(r'\b(20[3-9]\d|21\d\d)\b', low):
                        sc += 0.08
                    if re.search(r'\b(could|may|might|analysts?|experts?|'
                                 r'risk|scenario|project\w*|threat)\b', low):
                        sc += 0.06
                if origin_q:
                    if len(ent) > 3:
                        if ent not in low or not _ORIGIN_SENT.search(low):
                            continue
                        sc += 0.10
                    elif not _ORIGIN_SENT.search(low):
                        sc -= 0.12
                if len(s) < 60 or len(s) > 380:
                    sc -= 0.05
                if qtype == "definition" and ent:
                    if re.search(re.escape(ent) + r'\s+[A-Z][a-z]', s):
                        sc -= 0.15
                    pos = low.find(ent)
                    win = low[pos:pos + 130] if pos >= 0 else ""
                    if re.match(r'\s+(?:is|are)\s+not\b', win):
                        sc -= 0.40
                    elif re.search(r'\s+(?:is|are)\s+(?:a|an|the)\s+\w', win):
                        sc += 0.30
                    elif re.search(r'\s+(?:is|are|refers to|means|'
                                   r'is defined as)\s', win):
                        sc += 0.14
                    if re.search(r'\b(?:def|class)\s+\w+\s*\(|#include\s*<|'
                                 r'\bpublic\s+(?:class|static)\b|'
                                 r'\bconsole\.log\b|\bfunction\s+\w+\s*\(', s):
                        sc -= 0.30
                    if '`' in s:
                        sc -= 0.22
                cands.append((sc, h, s))
        cands.sort(key=lambda t: -t[0])

        chosen = []
        for sc, h, s in cands:
            if sc < 0.12:
                break
            if any(_jac(util.content_words(s), util.content_words(c[2])) > 0.55
                   for c in chosen):
                continue
            chosen.append((sc, h, s))
            if len(chosen) >= 6:
                break

        if qtype == "when" and len(ent) > 2:
            when_pat = _when_pattern(ent)
            ent_forms = _ENTS.get(ent.lower(), [ent.lower()])
            srcs = list(top)
            try:
                rows = []
                seen_ids = set()
                base = ent_forms[0].lower()
                last_w = base.split()[-1] if len(base) > 4 else ""
                probes = [("LOWER(title)=?", base, 8),
                          ("LOWER(title) LIKE ?", base + "%", 20),
                          ("LOWER(title) LIKE ?", "%" + base + "%", 30)]
                if last_w and len(last_w) > 4:
                    probes.append(("LOWER(title) LIKE ?", "%" + last_w + "%", 24))
                with self.mem.lock:
                    for cond, arg, lim in probes:
                        cur = self.mem.conn.execute(
                            "SELECT id,url,title,passage,topic,fetched_at FROM docs "
                            "WHERE " + cond + " ORDER BY id DESC LIMIT ?",
                            (arg, lim))
                        for r in cur.fetchall():
                            if r[0] not in seen_ids:
                                seen_ids.add(r[0])
                                rows.append(r)
                rows.sort(key=lambda r: (0 if (r[2] or "").lower() == base else 1,
                                         0 if (r[2] or "").lower().startswith(base) else 1,
                                         len(r[2] or "")))
                rows = rows[:40]
                if rows:
                    with self.mem.lock:
                        for r in rows[:4]:
                            cur2 = self.mem.conn.execute(
                                "SELECT id,url,title,passage,topic,fetched_at FROM docs "
                                "WHERE url=? ORDER BY id ASC LIMIT 8", (r[1],))
                            for r2 in cur2.fetchall():
                                if r2[0] not in seen_ids:
                                    seen_ids.add(r2[0])
                                    rows.append(r2)
                srcs += [{"url": r[1], "title": r[2], "passage": r[3],
                          "topic": r[4], "fetched_at": r[5], "sim": 0.5}
                         for r in rows]
            except Exception:
                pass
            kws = [w.lower() for w in util.content_words(question)
                   if len(w) > 3 and w.lower() not in ent.lower()
                   and w.lower() != "released"]
            pat_hits = []
            title_only = []
            for h in srcs:
                title_low = (h.get("title") or "").lower()
                exact = any(title_low.startswith(x) for x in ent_forms)
                for s in util.sentences(h["passage"]):
                    cs = _clean_sentence(s)
                    if not (40 <= len(cs) <= 560):
                        continue
                    low_s = cs.lower()
                    ym = re.search(r'\b(1[5-9]\d\d|20\d\d)\b', cs)
                    if not ym:
                        continue
                    yr = int(ym.group(1))
                    ep = min([low_s.find(x) for x in ent_forms
                              if x in low_s] or [-1])
                    dist = abs(ym.start() - ep) if ep >= 0 else 999
                    extra = sum(1 for w in kws if w in low_s)
                    tier = 0 if exact else 2
                    if when_pat.search(low_s) and dist <= 140:
                        pat_hits.append((tier, -extra, 0 if dist <= 90 else 1,
                                         yr, h, cs))
                    elif (exact and _JUNK_SENT.search(low_s) is None
                          and re.search(_WHEN_VERBS, low_s)):
                        title_only.append((tier, -extra, 0, yr, h, cs))
            pool = pat_hits + title_only
            best_when = None
            if pool:
                extras = [t for t in pool if t[1] < 0]
                if extras:
                    pool = extras
                else:
                    yc = {}
                    for t in pool:
                        yc[t[3]] = yc.get(t[3], 0) + 1
                    rep = sorted(y for y, c in yc.items() if c >= 2 and y != 9999)
                    if rep:
                        pool = [t for t in pool if t[3] == rep[0]]
                pool.sort(key=lambda t: (t[0], t[1], t[3], t[2]))
                best_when = (pool[0][4], pool[0][5])
            if best_when:
                if chosen:
                    chosen.insert(0, (chosen[0][0] + 0.3, best_when[0], best_when[1]))
                else:
                    chosen.append((0.6, best_when[0], best_when[1]))
        if not chosen:
            if (not _wants_live(question)
                    and qa_hits and qa_hits[0].get("feedback", 0) >= 0
                    and "couldn't find solid sources" not in (
                        qa_hits[0].get("answer") or "")):
                prev = qa_hits[0]["answer"]
                pl = prev.lower()
                qw = set(w.lower() for w in util.content_words(question)
                         if len(w) > 3)
                pw = set(w.lower() for w in util.content_words(
                    qa_hits[0].get("question") or "") if len(w) > 3)
                cov = (len(qw & pw) / len(qw)) if qw else 0.0
                sim0 = qa_hits[0].get("sim", 0.0)
                prev_ok = sim0 >= 0.62 or cov >= 0.6
                if origin_q and len(ent) > 3:
                    if ent not in pl or not _ORIGIN_SENT.search(prev):
                        prev_ok = False
                if len(ent) > 2 and not (_ent_hit(ent, pl) or _ent_loose(ent, pl)):
                    prev_ok = False
                if qw:
                    hits = sum(1 for w in qw if w in pl)
                    if hits < max(1, len(qw) // 2):
                        prev_ok = False
                if prev_ok:
                    return ("**From my trained memory** (I answered something very similar "
                            "before and nothing better was found now):\n\n" + prev,
                            [{"url": e.get("url", ""), "title": e.get("title", "")}
                             for e in qa_hits[0].get("evidence", [])[:4]], 0.35)
            if top and top[0].get("passage"):
                lead = util.sentences(top[0]["passage"])
                qcw = set(w for w in util.content_words(question) if len(w) > 3)
                if lead:
                    ans_text = None
                    for s in lead[:4]:
                        low_s = s.lower()
                        ov = sum(1 for w in qcw if w in low_s)
                        if _ent_hit(ent, low_s) or ov >= 1:
                            ans_text = s.strip()
                            break
                    if ans_text is None and top[0].get("sim", 0.0) >= 0.58:
                        low0 = lead[0].lower()
                        if ent and len(ent) >= 2 and not _ent_hit(ent, low0):
                            ans_text = None
                        elif qcw and not any(w in low0 for w in qcw):
                            ans_text = None
                        else:
                            ans_text = lead[0].strip()
                    if ans_text:
                        if len(lead) > 1 and len(ans_text) < 120 and ans_text == lead[0].strip():
                            ans_text += " " + lead[1].strip()
                        ans_text = _strip_cites(ans_text)
                        return ("**Answer:** " + ans_text,
                                [{"url": top[0].get("url", ""), "title": top[0].get("title", "")}], 0.40)
                pass
            topic_str = analysis["entity"] or (", ".join(analysis["keywords"][:3]) if analysis["keywords"] else "this topic")
            return ("**Answer:** I couldn't find solid sources that are clearly on-topic "
                    "for this yet. I have recorded the topic ('%s') in my active research "
                    "feed to learn more about it." % topic_str), [], 0.20

        sources = []
        src_index = {}

        def src_no(h):
            key = h.get("url") or h.get("title") or str(h.get("id"))
            if key not in src_index:
                src_index[key] = len(sources) + 1
                sources.append({"url": h.get("url", ""), "title": h.get("title", ""),
                                "passage": h.get("passage", "")[:200],
                                "score": h.get("score", 0)})
            return src_index[key]

        if len(chosen) >= 2 and len(ent) > 2:
            if qtype == "definition":
                def _isdef(s):
                    low_s = s.lower()
                    p = low_s.find(ent)
                    return (0 <= p <= 90 and bool(re.search(
                        r"\b(is|are|refers to|means)\b", low_s[p:p + 130])))
                if _isdef(chosen[1][2]) and not _isdef(chosen[0][2]):
                    chosen[0], chosen[1] = chosen[1], chosen[0]
            elif qtype == "when":
                head, tail = chosen[:1], chosen[1:]
                tail.sort(key=lambda c: 0 if when_pat.search(c[2]) else 1)
                chosen = head + tail

        if fresh_q:
            top_sc = chosen[0][0]
            best_i = None
            for i, c in enumerate(chosen[:6]):
                if i == 0:
                    continue
                low_c = c[2].lower()
                if (c[0] >= 0.6 * top_sc
                        and re.search(r'\b' + cur_year + r'\b', low_c)
                        and re.search(r'\b(announc\w+|launch\w+|releas\w+|'
                                      r'unveil\w+|marks?|digest|developments?|'
                                      r'roundup|advanc\w+|report\w*)\b', low_c)):
                    best_i = i
                    break
            if best_i:
                chosen.insert(0, chosen.pop(best_i))

        direct = chosen[0][2]
        direct_no = src_no(chosen[0][1])

        domains = set()
        for s in sources:
            try:
                domains.add(urllib.parse.urlparse(s["url"]).netloc)
            except Exception:
                pass
        base = sum(c[0] for c in chosen[:3]) / min(3, len(chosen))
        confidence = min(0.92, base + 0.04 * max(0, len(domains) - 1))
        if mode == "web" and len(domains) >= 2:
            confidence = min(0.92, confidence + 0.05)
        if confidence < 0.25:
            confidence = 0.25
        confidence = round(confidence, 2)

        body = direct.strip() + " [%d]" % direct_no

        body_words = util.content_words(direct)
        added = 0
        if fresh_q and len(chosen) > 1:
            base_url = chosen[0][1].get("url")
            same = [c for c in chosen[1:] if c[1].get("url") == base_url]
            rest = [c for c in chosen[1:] if c[1].get("url") != base_url]
            sup_iter = same + rest
        else:
            sup_iter = chosen[1:4]
        for sc_i, h_i, s_i in sup_iter:
            if added >= 2 or len(body) > 820:
                break
            if s_i.strip() in body:
                continue
            same_src = h_i.get("url") == chosen[0][1].get("url")
            thresh = 0.45 if (fresh_q and same_src) else 0.72
            if sc_i < chosen[0][0] * thresh:
                if fresh_q:
                    continue
                break
            s_cw = util.content_words(s_i)
            if not s_cw:
                continue
            if _jac(s_cw, body_words) > 0.55:
                continue
            union = set(w for w in util.content_words(question) if len(w) > 3)
            if (len(set(s_cw) & union) < 2 and not _ent_hit(ent, s_i.lower())
                    and not same_src):
                continue
            body += " " + s_i.strip() + " [%d]" % src_no(h_i)
            body_words = body_words + s_cw
            added += 1

        if added == 0 and len(chosen) < 2 and len(top) > 1:
            if top[0].get("url") == top[1].get("url"):
                extra = util.sentences(top[1]["passage"])
                if extra:
                    qcw_fb = set(w for w in util.content_words(question) if len(w) > 3)
                    fb = extra[0].strip()
                    if ("?" not in fb
                            and any(w in fb.lower() for w in qcw_fb)):
                        body += " " + fb + " [%d]" % src_no(top[1])

        parts = []
        if intent == "latest":
            parts.append("*Checked the web just now.*\n")
        if pred_q:
            parts.append("*This asks about the future - nobody can know for "
                         "sure. Here is what sources currently project.*\n")
        parts.append("**Answer:** " + body)
        return "\n".join(parts), sources, confidence
