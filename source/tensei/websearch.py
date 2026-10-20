import gzip
import html as html_mod
import json
import re
import ssl
import threading
import time
import urllib.parse
import urllib.request
from html.parser import HTMLParser

from . import config

_UA_HEADERS = {
    "User-Agent": config.UA,
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}

_CTX = ssl.create_default_context()
_CTX_UNSAFE = ssl._create_unverified_context()

_lock = threading.Lock()
_last_req = [0.0]


def _throttle(min_gap=0.08):
    with _lock:
        now = time.time()
        gap = now - _last_req[0]
        if gap < min_gap:
            time.sleep(min_gap - gap)
        _last_req[0] = time.time()


def http_get(url, timeout=None, max_bytes=600000):
    timeout = timeout or config.HTTP_TIMEOUT
    _throttle()
    req = urllib.request.Request(url, headers=_UA_HEADERS)
    for ctx in (_CTX, _CTX_UNSAFE):
        try:
            with urllib.request.urlopen(req, timeout=timeout, context=ctx) as r:
                raw = r.read(max_bytes)
                enc = (r.headers.get("Content-Encoding") or "").lower()
                if "gzip" in enc:
                    try:
                        raw = gzip.decompress(raw)
                    except Exception:
                        pass
                return raw, r
        except ssl.SSLError:
            continue
        except Exception:
            raise
    raise RuntimeError("ssl failure")


class _Extractor(HTMLParser):
    SKIP = {"script", "style", "noscript", "svg", "head", "header", "footer",
            "nav", "aside", "form", "button", "select", "option", "iframe", "template"}
    BLOCK = {"p", "h1", "h2", "h3", "h4", "li", "td", "th", "blockquote", "pre",
             "div", "section", "article", "br", "main"}

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts = []
        self.title = ""
        self._skip_depth = 0
        self._in_title = False

    def handle_starttag(self, tag, attrs):
        if tag in self.SKIP:
            self._skip_depth += 1
        elif tag == "title":
            self._in_title = True
        elif tag in self.BLOCK:
            self.parts.append("\n")

    def handle_endtag(self, tag):
        if tag in self.SKIP and self._skip_depth > 0:
            self._skip_depth -= 1
        elif tag == "title":
            self._in_title = False
        elif tag in self.BLOCK:
            self.parts.append("\n")

    def handle_data(self, data):
        if self._in_title:
            self.title += data
        if self._skip_depth == 0 and data.strip():
            self.parts.append(data)

    def text(self):
        raw = "".join(self.parts)
        raw = html_mod.unescape(raw)
        raw = re.sub(r"[ \t\r\f\v]+", " ", raw)
        lines = [ln.strip() for ln in raw.split("\n")]
        out = []
        for ln in lines:
            if not ln:
                continue
            low = ln.lower()
            if any(b in low for b in ("cookie", "subscribe to", "sign up for our",
                                      "javascript is disabled", "enable javascript",
                                      "privacy policy", "terms of service",
                                      "all rights reserved", "advertisement",
                                      "reload to refresh", "dismiss alert",
                                      "files navigation", "signed in with",
                                      "signed out", "switch branches",
                                      "you must be signed", "skip to content")):
                continue
            if len(ln) < 20 and not ln.endswith((".", "!", "?")):
                continue
            if "»" in ln and len(ln.split()) < 30:
                continue
            out.append(ln)
        txt = "\n".join(out)
        txt = re.sub(r"\n{3,}", "\n\n", txt)
        return txt.strip()


def extract_text(html_str):
    p = _Extractor()
    try:
        p.feed(html_str)
    except Exception:
        pass
    title = re.sub(r"\s+", " ", p.title).strip()[:180]
    return title, p.text()


DDG_RESULT_RE = re.compile(
    r'<a[^>]+class="result__a"[^>]+href="([^"]+)"[^>]*>(.*?)</a>', re.S)
DDG_SNIPPET_RE = re.compile(r'class="result__snippet"[^>]*>(.*?)</a>', re.S)
TAG_RE = re.compile(r"<[^>]+>")


def _clean(s):
    return html_mod.unescape(TAG_RE.sub("", s or "")).strip()


def _unwrap_ddg(url):
    if "duckduckgo.com/l/" in url:
        try:
            q = urllib.parse.parse_qs(urllib.parse.urlparse(url).query)
            if "uddg" in q:
                return urllib.parse.unquote(q["uddg"][0])
        except Exception:
            pass
    if url.startswith("//"):
        return "https:" + url
    return url


def _search_ddg_html(query, n):
    url = "https://html.duckduckgo.com/html/?q=" + urllib.parse.quote_plus(query)
    raw, r = http_get(url)
    if getattr(r, "status", 200) not in (200,):
        return []
    text = raw.decode("utf-8", "ignore")
    links = DDG_RESULT_RE.findall(text)
    snippets = DDG_SNIPPET_RE.findall(text)
    out = []
    for i, (href, title) in enumerate(links[: n + 6]):
        u = _unwrap_ddg(href)
        if u.startswith("http") and "duckduckgo.com" not in u:
            snip = _clean(snippets[i]) if i < len(snippets) else ""
            out.append({"title": _clean(title), "url": u, "snippet": snip})
        if len(out) >= n:
            break
    return out


LITE_RE = re.compile(r'<a[^>]+class="result-link"[^>]+href="([^"]+)"[^>]*>(.*?)</a>', re.S)


def _search_ddg_lite(query, n):
    url = "https://lite.duckduckgo.com/lite/?q=" + urllib.parse.quote_plus(query)
    raw, r = http_get(url)
    text = raw.decode("utf-8", "ignore")
    out = []
    for href, title in LITE_RE.findall(text):
        u = _unwrap_ddg(href)
        if u.startswith("http") and "duckduckgo.com" not in u:
            out.append({"title": _clean(title), "url": u, "snippet": ""})
        if len(out) >= n:
            break
    return out


def _search_ddg_api(query, n):
    url = ("https://api.duckduckgo.com/?q=" + urllib.parse.quote_plus(query)
           + "&format=json&no_html=1&skip_disambig=0")
    raw, r = http_get(url, timeout=10)
    data = json.loads(raw.decode("utf-8", "ignore"))
    out = []
    if data.get("AbstractText") and data.get("AbstractURL"):
        out.append({"title": data.get("Heading") or query,
                    "url": data["AbstractURL"],
                    "snippet": data["AbstractText"]})
    for t in (data.get("RelatedTopics") or []):
        if len(out) >= n:
            break
        if isinstance(t, dict) and t.get("FirstURL") and t.get("Text"):
            out.append({"title": t["Text"][:80], "url": t["FirstURL"],
                        "snippet": t["Text"]})
    return out[:n]


def _search_bing(query, n):
    """Bing's HTML results - a second independent index next to DuckDuckGo."""
    url = ("https://www.bing.com/search?q=" + urllib.parse.quote_plus(query)
           + "&setlang=en&count=%d" % (n + 4))
    raw, r = http_get(url)
    if getattr(r, "status", 200) not in (200,):
        return []
    text = raw.decode("utf-8", "ignore")
    out = []
    for item in re.findall(r'<li class="b_algo".{0,4000}?</li>', text, re.S):
        m = re.search(
            r'<a[^>]+href="(https?://[^"]+)"[^>]*>\s*<h2[^>]*>(.*?)</h2>',
            item, re.S)
        if not m:
            m = re.search(
                r'<h2[^>]*>\s*<a[^>]+href="(https?://[^"]+)"[^>]*>(.*?)</a>',
                item, re.S)
        if not m:
            continue
        u = html_mod.unescape(m.group(1))
        if "bing.com" in u or "microsofttranslator" in u:
            continue
        p = re.search(r'<p[^>]*>(.*?)</p>', item, re.S)
        out.append({"title": _clean(m.group(2)), "url": u,
                    "snippet": _clean(p.group(1)) if p else ""})
        if len(out) >= n:
            break
    return out


def _wiki_summary(title):
    try:
        url = "https://en.wikipedia.org/api/rest_v1/page/summary/" + urllib.parse.quote(title.replace(" ", "_"))
        raw, r = http_get(url, timeout=4)
        data = json.loads(raw.decode("utf-8", "ignore"))
        return data.get("extract", "")
    except Exception:
        return ""


def _wiki_full(term):
    """Best-effort Wikipedia intro for a term: try the term directly, then
    fall back to Wikipedia's own search to resolve near-titles. Returns a
    result dict with full intro text (ready to store), or None."""
    t = (term or "").strip().strip('"\'?.')
    if len(t) < 2 or len(t) > 90:
        return None

    def _summary(title):
        try:
            url = ("https://en.wikipedia.org/api/rest_v1/page/summary/"
                   + urllib.parse.quote(title.replace(" ", "_")))
            raw, r = http_get(url, timeout=5)
            data = json.loads(raw.decode("utf-8", "ignore"))
            if data.get("type") == "disambiguation":
                return None
            ext = (data.get("extract") or "").strip()
            if len(ext) < 60:
                return None
            page = ((data.get("content_urls") or {}).get("desktop") or {}).get("page")
            return {"title": data.get("title") or title,
                    "url": page or ("https://en.wikipedia.org/wiki/"
                                    + urllib.parse.quote(title.replace(" ", "_"))),
                    "snippet": ext[:400], "text": ext, "engine": "wikipedia"}
        except Exception:
            return None

    got = _summary(t)
    if got:
        return got
    try:
        url = ("https://en.wikipedia.org/w/api.php?action=query&list=search"
               "&format=json&srlimit=2&srsearch=" + urllib.parse.quote_plus(t))
        raw, r = http_get(url, timeout=6)
        data = json.loads(raw.decode("utf-8", "ignore"))
        for item in (data.get("query", {}) or {}).get("search", []):
            got = _summary(item.get("title", ""))
            if got:
                return got
    except Exception:
        pass
    return None


def fast_topic(term, timeout=3.2):
    """One-request Wikipedia intro for definition questions.

    The full research path deliberately searches several engines and fetches
    pages, which is right for news but far too slow for "what is X".  This
    helper gives the symbolic core a quick, grounded fallback after local
    memory has failed, without turning every unknown word into a 20-second
    browsing session.
    """
    t = (term or "").strip().strip('"\'?.!')
    if len(t) < 3 or len(t) > 90:
        return None
    try:
        url = ("https://en.wikipedia.org/api/rest_v1/page/summary/"
               + urllib.parse.quote(t.replace(" ", "_")))
        raw, r = http_get(url, timeout=timeout, max_bytes=180000)
        data = json.loads(raw.decode("utf-8", "ignore"))
        if data.get("type") == "disambiguation":
            return None
        extract = (data.get("extract") or "").strip()
        if len(extract) < 50:
            return None
        title = data.get("title") or t
        page = ((data.get("content_urls") or {}).get("desktop") or {}).get("page")
        return {
            "title": title,
            "url": page or ("https://en.wikipedia.org/wiki/"
                            + urllib.parse.quote(title.replace(" ", "_"))),
            "text": extract,
            "snippet": extract[:400],
            "engine": "wikipedia",
        }
    except Exception:
        return None


def _search_wikipedia(query, n):
    url = ("https://en.wikipedia.org/w/api.php?action=query&list=search"
           "&format=json&srlimit=%d&srsearch=" % n + urllib.parse.quote_plus(query))
    raw, r = http_get(url, timeout=5)
    data = json.loads(raw.decode("utf-8", "ignore"))
    out = []
    for i, item in enumerate(data.get("query", {}).get("search", [])):
        t = item.get("title", "")
        snip = _clean(item.get("snippet", ""))
        if i < 2:
            summ = _wiki_summary(t)
            if summ and len(summ) > len(snip):
                snip = summ
        out.append({
            "title": t,
            "url": "https://en.wikipedia.org/wiki/" + urllib.parse.quote(t.replace(" ", "_")),
            "snippet": snip,
        })
    return out


ENGINES = [
    ("ddg-api", _search_ddg_api),
    ("wikipedia", _search_wikipedia),
    ("ddg-html", _search_ddg_html),
    ("bing", _search_bing),
    ("ddg-lite", _search_ddg_lite),
]


def web_search(query, n=6, log=None, lookup=None):
    if not config.online():
        return [], "offline"
    seen = set()
    merged = []

    def _domain(u):
        try:
            return urllib.parse.urlparse(u).netloc.lower()
        except Exception:
            return ""

    def _add(r, per_domain=2):
        key = (r.get("url") or "").split("#")[0]
        if not key or key in seen:
            return 0
        d = _domain(key)
        if d and sum(1 for x in merged if _domain(x.get("url") or "") == d) >= per_domain:
            return 0
        seen.add(key)
        merged.append(r)
        return 1

    # 0. Intelligent Entity Extraction for direct factual questions
    q_clean = query.strip()
    if not lookup:
        m = re.match(
            r'^(?:what|who|where|when|why|how)\s+(?:is|was|are|were|do|does)\s+(?:a|an|the\s+)?([a-zA-Z0-9_\-\.\s]{2,50})\??$',
            q_clean, re.I)
        if m:
            lookup = m.group(1).strip()
        else:
            m2 = re.match(r'^(?:define|explain|tell me about)\s+([a-zA-Z0-9_\-\.\s]{2,50})\??$', q_clean, re.I)
            if m2:
                lookup = m2.group(1).strip()

    if lookup:
        try:
            hit = _wiki_full(lookup)
        except Exception:
            hit = None
        if hit:
            _add(hit, per_domain=9)
            if log:
                log("entity lookup -> %s" % hit["title"])

    stop_at = n + 1    # a small buffer lets multiple engines contribute
    for name, fn in ENGINES:
        if len(merged) >= stop_at:
            break
        try:
            res = fn(query, n)
        except Exception as e:
            if log:
                log("search %s failed: %s" % (name, type(e).__name__))
            continue
        added = 0
        for r in res:
            added += _add(r)
        if log:
            log("engine %s -> %d results" % (name, added))

    # Query relaxation fallback if zero results were found
    if not merged and len(q_clean.split()) > 3:
        relaxed = re.sub(r'^(?:can you\s+|please\s+|tell me\s+|what is\s+|who is\s+|how do I\s+)', '', q_clean, flags=re.I)
        relaxed = re.sub(r'[\?\.\!]+$', '', relaxed).strip()
        if relaxed and relaxed.lower() != q_clean.lower():
            if log:
                log("query relaxation -> '%s'" % relaxed)
            for name, fn in ENGINES:
                if len(merged) >= stop_at:
                    break
                try:
                    res = fn(relaxed, n)
                    for r in res:
                        _add(r)
                except Exception:
                    pass

    return merged[:n], "ok"

BAD_EXT = (".pdf", ".zip", ".apk", ".mp4", ".mp3", ".png", ".jpg", ".jpeg",
           ".gif", ".webp", ".exe", ".dmg", ".iso", ".svg")


def fetch_many(urls, log=None, workers=3, limit=None):
    from concurrent.futures import ThreadPoolExecutor, as_completed
    out = []
    urls = list(urls)
    if limit:
        urls = urls[:limit]
    with ThreadPoolExecutor(max_workers=workers) as ex:
        futs = {ex.submit(fetch_page, u, log): u for u in urls}
        for fut in as_completed(futs):
            try:
                p = fut.result()
            except Exception:
                p = None
            if p:
                out.append(p)
    return out


def fetch_page(url, log=None):
    if any(url.lower().split("?")[0].endswith(ext) for ext in BAD_EXT):
        return None
    try:
        raw, r = http_get(url, max_bytes=800000)
    except Exception as e:
        if log:
            log("fetch failed %s (%s)" % (url[:70], type(e).__name__))
        return None
    ctype = (r.headers.get("Content-Type") or "").lower()
    if "html" not in ctype and "text" not in ctype:
        return None
    html_str = raw.decode("utf-8", "ignore")
    title, text = extract_text(html_str)
    if not text or len(text) < 250:
        return None
    return {"url": url, "title": title or url, "text": text[: config.MAX_DOC_CHARS]}
