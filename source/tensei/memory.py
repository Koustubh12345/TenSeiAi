import json
import math
import os
import re
import sqlite3
import threading
import time

from . import config, util
from .embed import Embedder

try:
    import numpy as _np
except Exception:
    _np = None

# Small IR stop list.  It is deliberately shorter than the old keyword
# extractor's list: words like "largest", "internal", "native" and "study"
# carry the relation and must never be filtered out of a BM25 query.
_FTS_STOP = frozenset("""
a an the of to in on for with about as by from at into over after before
between under above and or but if then than that this these those it its
i you he she they we me my your our their there here is are was were be
been being do does did doing have has had can could would should will
shall may might must not no yes please tell explain describe give list
name define what which who whom whose when where why how
""".split())

SCHEMA = """
CREATE TABLE IF NOT EXISTS docs (
  id INTEGER PRIMARY KEY,
  url TEXT,
  title TEXT,
  passage TEXT,
  source TEXT,
  topic TEXT,
  fetched_at REAL,
  quality REAL,
  emb BLOB,
  hash TEXT UNIQUE
);
CREATE INDEX IF NOT EXISTS idx_docs_topic ON docs(topic);
CREATE TABLE IF NOT EXISTS qa (
  id INTEGER PRIMARY KEY,
  question TEXT,
  answer TEXT,
  evidence TEXT,
  created_at REAL,
  feedback INTEGER DEFAULT 0,
  emb BLOB,
  mode TEXT DEFAULT ''
);
CREATE TABLE IF NOT EXISTS topics (
  name TEXT PRIMARY KEY,
  priority REAL DEFAULT 0.5,
  category TEXT,
  last_fetch REAL DEFAULT 0,
  fetch_count INTEGER DEFAULT 0,
  hit_count INTEGER DEFAULT 0
);
CREATE TABLE IF NOT EXISTS df (
  token TEXT PRIMARY KEY,
  n INTEGER
);
CREATE TABLE IF NOT EXISTS feed (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  ts REAL,
  kind TEXT,
  msg TEXT
);
CREATE TABLE IF NOT EXISTS kv (
  key TEXT PRIMARY KEY,
  value TEXT
);
"""


class Memory:
    def __init__(self, path=None):
        config.ensure_dirs()
        self.path = str(path or config.DB_PATH)
        self.lock = threading.RLock()
        self.conn = sqlite3.connect(self.path, check_same_thread=False)
        self.conn.execute("PRAGMA journal_mode=WAL")
        self.conn.execute("PRAGMA synchronous=NORMAL")
        self.conn.executescript(SCHEMA)
        for mig in ("ALTER TABLE qa ADD COLUMN emb0 BLOB",
                    "ALTER TABLE qa ADD COLUMN mode TEXT DEFAULT ''"):
            try:
                self.conn.execute(mig)
            except sqlite3.OperationalError:
                pass
        self.conn.commit()
        self._df_cache = {}
        self._doc_count = None
        self.embedder = Embedder()
        self._qa_base_cache = None
        self._dm_cache = None
        self._fts_ready = self._ensure_fts()

    # ------------------------------------------------------------------
    # Lexical index (SQLite FTS5).  The dense embedding is good at fuzzy
    # similarity but terrible at exact entity/relation lookup: a passage
    # about "Sierra Leone" can outrank the kangaroo article.  BM25 over the
    # question words is the complementary half of the retriever.
    def _ensure_fts(self):
        try:
            with self.lock:
                self.conn.execute(
                    "CREATE VIRTUAL TABLE IF NOT EXISTS qa_fts USING fts5("
                    "question, answer, tokenize='unicode61 remove_diacritics 2')")
                self.conn.execute(
                    "CREATE VIRTUAL TABLE IF NOT EXISTS docs_fts USING fts5("
                    "title, passage, tokenize='unicode61 remove_diacritics 2')")
                nq = self.conn.execute("SELECT COUNT(*) FROM qa").fetchone()[0]
                nd = self.conn.execute("SELECT COUNT(*) FROM docs").fetchone()[0]
                fq = self.conn.execute("SELECT COUNT(*) FROM qa_fts").fetchone()[0]
                fd = self.conn.execute("SELECT COUNT(*) FROM docs_fts").fetchone()[0]
                if fq != nq:
                    self.conn.execute("DELETE FROM qa_fts")
                    self.conn.execute(
                        "INSERT INTO qa_fts(rowid,question,answer) "
                        "SELECT id,coalesce(question,''),coalesce(answer,'') FROM qa")
                if fd != nd:
                    self.conn.execute("DELETE FROM docs_fts")
                    self.conn.execute(
                        "INSERT INTO docs_fts(rowid,title,passage) "
                        "SELECT id,coalesce(title,''),coalesce(passage,'') FROM docs")
                self.conn.commit()
            return True
        except Exception:
            return False

    @staticmethod
    def _fts_query(query):
        import re as _re
        toks = []
        for w in _re.findall(r"[A-Za-z0-9_]+", (query or "").lower()):
            if len(w) < 2:
                continue
            if w in _FTS_STOP:
                continue
            if w not in toks:
                toks.append(w)
        if not toks:
            return ""
        # OR gives high recall; bm25() does the precision work.  Quoting each
        # token prevents user punctuation from becoming FTS syntax.
        return " OR ".join('"%s"' % t for t in toks)

    def fts_search(self, table, query, k=20):
        """Return lexical BM25 hits: list of dicts with rowid/rank + fields."""
        if not self._fts_ready:
            return []
        fq = self._fts_query(query)
        if not fq:
            return []
        try:
            with self.lock:
                if table == "qa":
                    rows = self.conn.execute(
                        "SELECT qa.id,qa.question,qa.answer,qa.evidence,qa.mode,"
                        "bm25(qa_fts,4.0,1.0) AS rank "
                        "FROM qa_fts JOIN qa ON qa.id=qa_fts.rowid "
                        "WHERE qa_fts MATCH ? "
                        "ORDER BY rank LIMIT ?", (fq, int(k))).fetchall()
                    return [{"id": r[0], "question": r[1], "answer": r[2],
                             "evidence": r[3], "mode": r[4] or "",
                             "rank": float(r[5])} for r in rows]
                rows = self.conn.execute(
                    "SELECT rowid,url,title,passage,source,topic,"
                    "bm25(docs_fts,4.0,1.0) AS rank "
                    "FROM docs_fts JOIN docs ON docs.id=docs_fts.rowid "
                    "WHERE docs_fts MATCH ? ORDER BY rank LIMIT ?",
                    (fq, int(k))).fetchall()
                return [{"id": r[0], "url": r[1], "title": r[2],
                         "passage": r[3], "source": r[4], "topic": r[5],
                         "rank": float(r[6])} for r in rows]
        except Exception:
            return []

    def docs_for_title(self, title, limit=24):
        """Sibling passages of the same article, in reading order."""
        if not title:
            return []
        try:
            with self.lock:
                rows = self.conn.execute(
                    "SELECT id,url,title,passage,source,topic FROM docs "
                    "WHERE title=? ORDER BY id LIMIT ?",
                    (title, int(limit))).fetchall()
            return [{"id": r[0], "url": r[1], "title": r[2],
                     "passage": r[3], "source": r[4], "topic": r[5]}
                    for r in rows]
        except Exception:
            return []

    def _fts_put_qa(self, rid, question, answer):
        if not getattr(self, "_fts_ready", False):
            return
        try:
            self.conn.execute(
                "INSERT INTO qa_fts(rowid,question,answer) VALUES(?,?,?)",
                (rid, question or "", answer or ""))
        except Exception:
            pass

    def _fts_put_doc(self, rid, title, passage):
        if not getattr(self, "_fts_ready", False):
            return
        try:
            self.conn.execute(
                "INSERT INTO docs_fts(rowid,title,passage) VALUES(?,?,?)",
                (rid, title or "", passage or ""))
        except Exception:
            pass

    def close(self):
        with self.lock:
            self.conn.commit()
            self.conn.close()

    def kv_get(self, key, default=None):
        with self.lock:
            r = self.conn.execute("SELECT value FROM kv WHERE key=?", (key,)).fetchone()
        if not r:
            return default
        try:
            return json.loads(r[0])
        except Exception:
            return r[0]

    def kv_set(self, key, value):
        with self.lock:
            self.conn.execute(
                "INSERT INTO kv(key,value) VALUES(?,?) "
                "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
                (key, json.dumps(value)))
            self.conn.commit()

    def add_feed(self, kind, msg):
        with self.lock:
            self.conn.execute("INSERT INTO feed(ts,kind,msg) VALUES(?,?,?)",
                              (time.time(), kind, msg))
            self.conn.commit()

    def feed_since(self, since=0, limit=120):
        with self.lock:
            rows = self.conn.execute(
                "SELECT id,ts,kind,msg FROM feed WHERE id>? ORDER BY id ASC LIMIT ?",
                (since, limit)).fetchall()
        return [{"id": r[0], "ts": r[1], "kind": r[2], "msg": r[3]} for r in rows]

    def touch_df(self, text):
        toks = set(util.content_words(text))
        if not toks:
            return
        with self.lock:
            for t in toks:
                if t in self._df_cache:
                    continue
                self.conn.execute(
                    "INSERT INTO df(token,n) VALUES(?,1) "
                    "ON CONFLICT(token) DO UPDATE SET n=n+1", (t,))
            self.conn.commit()
        for t in toks:
            self._df_cache[t] = True

    def idf(self, token):
        n_docs = self.doc_count()
        if n_docs == 0:
            return 1.0
        with self.lock:
            r = self.conn.execute("SELECT n FROM df WHERE token=?", (token,)).fetchone()
        df = r[0] if r else 0
        return math.log((n_docs + 1.0) / (df + 1.0)) + 1.0

    def doc_count(self):
        if self._doc_count is None:
            with self.lock:
                self._doc_count = self.conn.execute("SELECT COUNT(*) FROM docs").fetchone()[0]
        return self._doc_count

    def bm25_score(self, query, passage, idf_map=None, k1=1.4, b=0.75,
                   avg_len=180.0):
        """BM25 - the symbolic (lexical) half of TenSeiAi's hybrid retrieval.

        Classic information-retrieval scoring: term frequency saturates, long
        passages are discounted, and rare terms count more (idf from the
        corpus-wide document-frequency table).  Combined with the dense neural
        similarity it gives the Neuro-Symbolic RAG behaviour."""
        from collections import Counter
        try:
            q_toks = set(util.content_words(query or ""))
            toks = util.content_words(passage or "")
        except Exception:
            return 0.0
        if not q_toks or not toks:
            return 0.0
        if idf_map is None:
            idf_map = {}
            for t in q_toks:
                idf_map[t] = self.idf(t)
        tf = Counter(toks)
        dl = float(len(toks))
        score = 0.0
        for t in q_toks:
            f = tf.get(t, 0)
            if not f:
                continue
            idf = idf_map.get(t, 1.0)
            score += idf * (f * (k1 + 1.0)) / (f + k1 * (1.0 - b + b * dl / avg_len))
        return score

    def bm25_map(self, tokens):
        out = {}
        for t in set(tokens or []):
            out[t] = self.idf(t)
        return out

    def add_passages(self, url, title, text, source="web", topic="", passages=None):
        """Split text into passages, dedupe, embed, store. Returns list of new ids."""
        if passages is None:
            passages = self.split_passages(text)
        if not passages:
            return []
        now = time.time()
        added = []
        for p in passages:
            if util.is_blocked(p):
                continue
            h = util.digest_key(p)
            with self.lock:
                exists = self.conn.execute("SELECT id FROM docs WHERE hash=?", (h,)).fetchone()
                if exists:
                    continue
            emb = self.embedder.encode(p)
            quality = min(1.0, len(p) / 900.0) * (0.7 if len(p) < 200 else 1.0)
            # Curated sources are worth keeping even when short: short verified
            # facts used to score low and were the first thing size-pruning
            # deleted. Give them a floor so they always survive pruning.
            if source in ("facts", "knowledge", "teacher", "origin", "curated"):
                quality = max(quality, 0.85)
            with self.lock:
                cur = self.conn.execute(
                    "INSERT OR IGNORE INTO docs(url,title,passage,source,topic,fetched_at,"
                    "quality,emb,hash) VALUES(?,?,?,?,?,?,?,?,?)",
                    (url, title, p, source, topic, now, quality,
                     util.pack_f32(emb), h))
                if cur.rowcount:
                    rid = cur.lastrowid
                    added.append(rid)
                    self._fts_put_doc(rid, title, p)
                self.conn.commit()
        if added:
            self._doc_count = None
            self.touch_df(title + " " + " ".join(passages))
        return added

    @staticmethod
    def split_passages(text, size=None):
        size = size or config.PASSAGE_CHARS
        sents = util.sentences(text)
        out = []
        buf = ""
        for s in sents:
            if len(buf) + len(s) + 1 > size and buf:
                out.append(buf.strip())
                buf = s
            else:
                buf = (buf + " " + s).strip()
        if buf and len(buf) > 80:
            out.append(buf.strip())
        return out

    def add_qa(self, question, answer, evidence, emb, emb0=None, mode=""):
        with self.lock:
            cur = self.conn.execute(
                "INSERT INTO qa(question,answer,evidence,created_at,emb,emb0,mode) "
                "VALUES(?,?,?,?,?,?,?)",
                (question, answer, json.dumps(evidence), time.time(),
                 util.pack_f32(emb),
                 util.pack_f32(emb0) if emb0 is not None else None,
                 mode or ""))
            rid = cur.lastrowid
            self._fts_put_qa(rid, question, answer)
            self.conn.commit()
            self._qa_base_cache = None
            return rid

    def best_qa_base(self, qbase, min_sim=0.95):
        """Match a question against past Q&As in the stable base space
        (hash projection - never changes when the brain retrains)."""
        if self._qa_base_cache is None:
            with self.lock:
                rows = self.conn.execute(
                    "SELECT id,question,answer,evidence,emb0,mode FROM qa "
                    "WHERE emb0 IS NOT NULL AND (feedback IS NULL OR feedback >= 0) "
                    "ORDER BY id DESC LIMIT 20000"
                ).fetchall()
            meta = [(r[0], r[1], r[2], r[3], r[5] or "") for r in rows]
            if _np is not None and rows:
                dim = len(util.unpack_f32(rows[0][4]))
                mat = _np.zeros((len(rows), dim), dtype=_np.float32)
                for i, r in enumerate(rows):
                    mat[i] = _np.frombuffer(r[4], dtype=_np.float32)[:dim]
                self._qa_base_cache = (meta, mat)
            else:
                vecs = [list(util.unpack_f32(r[4])) for r in rows]
                self._qa_base_cache = (meta, vecs)
        meta, mat = self._qa_base_cache
        if not meta:
            return None
        if _np is not None and not isinstance(mat, list):
            sims = mat @ _np.asarray(qbase, dtype=_np.float32)
            best = None
            best_key = None
            for i, s in enumerate(sims):
                s = float(s)
                if s < min_sim:
                    continue
                rid, q, a, ev, mode = meta[i]
                if not a or "couldn't find solid sources" in a:
                    continue
                trusted = 1 if "teacher://" in (ev or "") else 0
                if not trusted and mode:
                    # engine-composed answers must be a much closer match
                    if s < max(min_sim, 0.93):
                        continue
                direct = 0 if a.startswith("**From my trained memory") else 1
                key = (round(s, 4), trusted, direct, len(a))
                if best_key is None or key > best_key:
                    best_key = key
                    best = {"id": rid, "question": q, "answer": a,
                            "evidence": json.loads(ev or "[]"),
                            "sim": round(s, 4), "mode": mode}
            return best
        best = None
        best_sim = min_sim
        for (rid, q, a, ev, mode), v in zip(meta, mat):
            if not a or "couldn't find solid sources" in a:
                continue
            trusted = 1 if "teacher://" in (ev or "") else 0
            sim = util.dot(qbase, v)
            if not trusted and mode:
                if sim < max(min_sim, 0.93):
                    continue
            if sim >= best_sim:
                best_sim = sim
                best = {"id": rid, "question": q, "answer": a,
                        "evidence": json.loads(ev or "[]"),
                        "sim": round(sim, 4), "mode": mode}
        return best

    def find_relevant_qa(self, query, qbase, min_score=0.55):
        """High-accuracy hybrid retrieval across past Q&As:
        combines neural base projection similarity, content-word overlap,
        and subject/entity weighting."""
        if self._qa_base_cache is None:
            self.best_qa_base(qbase, min_sim=0.1)
        if not self._qa_base_cache:
            return None
        meta, mat = self._qa_base_cache
        if not meta:
            return None

        import re

        def _norm_words(text):
            return set(re.sub(r"'s$", "", w) for w in util.content_words(text))

        qw = _norm_words(query)
        ql = query.strip().lower()
        _is_explain = bool(re.search(
            r"\b(?:what\s+is|what\s+are|define|meaning\s+of|explain|"
            r"who\s+is|who\s+was|how\s+(?:does|do))\b", ql))

        _GENERIC_QA = frozenset({"capital", "city", "country", "name", "tell", "what", "when",
                                 "who", "how", "which", "explain", "meaning", "definition",
                                 "does", "works", "mean", "state", "list", "difference", "between",
                                 "term", "word", "phrase", "slang", "stand", "for", "called",
                                 "about", "describe", "origin", "etymology"})
        subj_words = {w for w in qw if w not in _GENERIC_QA and len(w) > 2}

        def _q_type(text):
            t = text.lower()
            if re.search(r"\bwho\b", t):
                return "who"
            if re.search(r"\bwhen\b|\byear\b|\bdate\b|\bcentury\b", t):
                return "when"
            if re.search(r"\bwhere\b|\bcountry\b|\blocation\b|\bplace\b", t):
                return "where"
            if re.search(r"\bhow many\b|\bhow much\b|\bcount\b", t):
                return "count"
            if re.search(r"\bwhy\b|\breason\b", t):
                return "why"
            return "other"

        qt_curr = _q_type(query)

        best = None
        best_key = None

        if _np is not None and not isinstance(mat, list):
            sims = mat @ _np.asarray(qbase, dtype=_np.float32)
            for i, s in enumerate(sims):
                s = float(s)
                exact = 1.0 if meta[i][1].strip().lower() == ql else 0.0
                if s < 0.52 and not exact:
                    continue
                rid, q, a, ev, qmode = meta[i]
                if not a or "couldn't find solid sources" in a:
                    continue
                past_words = _norm_words(q)
                if not exact:
                    if len(past_words) > 3 * max(len(qw), 1) and s < 0.65:
                        continue
                    if len(qw) > 3 * max(len(past_words), 1) and s < 0.65:
                        continue
                cov_query = (len(qw & past_words) / max(len(qw), 1)) if qw else 0.0
                cov_past = (len(qw & past_words) / max(len(past_words), 1)) if past_words else 0.0
                ov = max(cov_query, cov_past * 0.90 if cov_past >= 0.80 else 0.0)

                if subj_words:
                    subj_hits = len(subj_words & past_words)
                    subj_ratio = subj_hits / len(subj_words)
                    past_subj = {w for w in past_words if w not in _GENERIC_QA and len(w) > 2}
                    if past_subj and len(past_subj & subj_words) / len(past_subj) >= 0.80:
                        subj_ratio = 1.0
                    # A recalled row must share the distinctive subject, not
                    # just a generic framing word.  This blocks "what does
                    # wtf mean" matching an anime page that happens to
                    # contain "meaning".
                    if subj_ratio < 0.34:
                        continue
                    if subj_ratio < 0.60 and s < 0.90:
                        continue
                else:
                    subj_ratio = 1.0

                score = 0.35 * s + 0.35 * ov + 0.30 * subj_ratio + 0.15 * exact

                if cov_past >= 0.80:
                    len_ratio = 1.0
                else:
                    len_ratio = min(len(past_words), len(qw)) / max(len(past_words), len(qw), 1)
                score += 0.10 * len_ratio

                qt_past = _q_type(q)
                if qt_curr != "other" and qt_past != "other" and qt_curr != qt_past:
                    score -= 0.40

                if score < min_score:
                    continue

                trusted = 1 if "teacher://" in (ev or "") else 0
                if not trusted and qmode in ("memory", "web"):
                    # Long web-composed answers are often spliced from several
                    # articles; do not let a past bad research result block a
                    # clean, grounded lookup for a definition.
                    if _is_explain and len(a) > 300:
                        continue
                    # engine-composed (unverified) answers are only replayed on
                    # a near-identical subject match - this keeps past mistakes
                    # from becoming "learned facts".
                    if s < 0.62 or (subj_words and subj_ratio < 0.80):
                        continue
                    if score < min_score + 0.15:
                        continue
                direct = 0 if a.startswith("**From my trained memory") else 1
                key = (round(score, 4), trusted, direct, -len(q))

                if best_key is None or key > best_key:
                    best_key = key
                    best = {
                        "id": rid, "question": q, "answer": a,
                        "evidence": json.loads(ev or "[]"),
                        "sim": round(s, 4), "score": round(score, 4),
                        "overlap": round(ov, 4), "trusted": trusted,
                        "mode": qmode
                    }
            return best
        return self.best_qa_base(qbase, min_sim=0.70)

    def set_feedback(self, qa_id, rating):
        with self.lock:
            self.conn.execute("UPDATE qa SET feedback=? WHERE id=?", (int(rating), qa_id))
            self.conn.commit()

    def recent_questions(self, limit=60):
        with self.lock:
            rows = self.conn.execute(
                "SELECT question, feedback FROM qa ORDER BY id DESC LIMIT ?",
                (limit,)).fetchall()
        return [{"q": r[0], "fb": r[1]} for r in rows]

    def _doc_matrix(self):
        """Cached embedding matrix of every stored passage.

        Cosine ranking over the WHOLE corpus beats the old SQL prefilter
        window, which pushed older curated passages out whenever newer pages
        happened to share a keyword."""
        try:
            import numpy as np
        except Exception:
            return None
        with self.lock:
            n = self.conn.execute("SELECT COUNT(*) FROM docs").fetchone()[0]
        c = self._dm_cache
        if c and c[0] == n:
            return c[1]
        try:
            with self.lock:
                rows = self.conn.execute(
                    "SELECT id,url,title,passage,topic,fetched_at,emb "
                    "FROM docs").fetchall()
        except Exception:
            return None
        keep, vecs, dim = [], [], None
        for r in rows:
            v = util.unpack_f32(r[6])
            if not v:
                continue
            if dim is None:
                dim = len(v)
            if len(v) != dim:
                continue
            keep.append(r)
            vecs.append(v)
        if not keep:
            return None
        M = np.asarray(vecs, dtype=np.float32)
        M /= (np.linalg.norm(M, axis=1, keepdims=True) + 1e-9)
        self._dm_cache = (n, (keep, M))
        return self._dm_cache[1]

    def _search_docs_np(self, query_emb, k, min_sim):
        cached = self._doc_matrix()
        if not cached:
            return None
        import numpy as np
        rows, M = cached
        q = np.asarray(query_emb, dtype=np.float32)
        if q.shape[0] != M.shape[1]:
            return None
        q = q / (np.linalg.norm(q) + 1e-9)
        sims = M @ q
        idx = np.argsort(-sims)[:max(k * 4, 40)]
        out = []
        for i in idx:
            sim = float(sims[int(i)])
            if sim < min_sim:
                break
            r = rows[int(i)]
            out.append({"sim": round(sim, 4), "id": r[0], "url": r[1],
                        "title": r[2], "passage": r[3], "topic": r[4],
                        "fetched_at": r[5]})
        return out

    def search_emb(self, table, query_emb, k=6, min_sim=0.12, keywords=None,
                   must_contain=None):
        """Hybrid retrieval: exact cosine rank over the whole corpus (numpy
        matrix when available) combined with a lexical coverage bonus, and an
        optional hard filter on a subject string so answers about a named
        entity only come from passages that actually mention it."""
        if table == "docs":
            kws = [w.lower() for w in (keywords or [])[:4] if w]
            mc = (must_contain or "").lower().strip().strip('"\'')
            allowed = None
            if mc and len(mc) >= 2:
                # The subject filter is a hard constraint.  It used to be
                # silently disabled when the exact phrase had zero hits,
                # which let unrelated passages (e.g. an anime page for
                # "what is wtf") win on generic words such as "meaning".
                try:
                    with self.lock:
                        rows = self.conn.execute(
                            "SELECT id FROM docs WHERE passage LIKE ? LIMIT 2001",
                            ("%" + mc + "%",)).fetchall()
                        if not rows:
                            terms = [w for w in
                                     re.findall(r"[a-z0-9]+", mc)
                                     if len(w) >= 3 and w not in _FTS_STOP]
                            # Keep only the rare/distinctive words; "the" and
                            # "what" must never be enough to admit a passage.
                            terms = [w for w in dict.fromkeys(terms) if len(w) >= 4][:4]
                            if terms:
                                clause = " AND ".join(
                                    ["passage LIKE ?"] * len(terms))
                                rows = self.conn.execute(
                                    "SELECT id FROM docs WHERE " + clause +
                                    " LIMIT 2001",
                                    tuple("%" + w + "%" for w in terms)).fetchall()
                    if rows and len(rows) <= 2000:
                        allowed = set(r[0] for r in rows)
                    elif not rows:
                        # No stored passage is about the requested subject.
                        # Return nothing rather than dropping the constraint.
                        return []
                except Exception:
                    # A failed filter must fail closed: a wrong answer is worse
                    # than a fast "I don't have this locally".
                    return []
            cached = self._doc_matrix()
            if cached:
                rows, M = cached
                import numpy as np
                q = np.asarray(query_emb, dtype=np.float32)
                if q.shape[0] == M.shape[1]:
                    q = q / (np.linalg.norm(q) + 1e-9)
                    sims = M @ q
                    if allowed is not None:
                        mask = np.fromiter(
                            (r[0] in allowed for r in rows), dtype=bool,
                            count=len(rows))
                        sims = np.where(mask, sims, -1.0)
                    # --- hybrid retrieval (Neural + Symbolic) ---------------
                    # candidate pool 1: best by dense neural similarity
                    cand = {}
                    for i in np.argsort(-sims)[:200]:
                        s = float(sims[int(i)])
                        if s > -0.5:
                            cand[int(i)] = s
                    # candidate pool 2: best by lexical match (SQL, cheap) -
                    # catches passages the dense encoder scores low but the
                    # query words clearly point to
                    if kws:
                        try:
                            expr = " + ".join(["(passage LIKE ?)"] * len(kws))
                            clause = " OR ".join(["passage LIKE ?"] * len(kws))
                            with self.lock:
                                lx = self.conn.execute(
                                    "SELECT id, (%s) AS kwm FROM docs WHERE %s "
                                    "ORDER BY kwm DESC, id DESC LIMIT 250"
                                    % (expr, clause),
                                    tuple("%" + w + "%" for w in kws) * 2).fetchall()
                            if getattr(self, "_dm_index", None) is None or len(self._dm_index) != len(rows):
                                self._dm_index = {r[0]: n for n, r in enumerate(rows)}
                            for rid, _m in lx:
                                n = self._dm_index.get(rid)
                                if n is None or n in cand:
                                    continue
                                if allowed is not None and rid not in allowed:
                                    continue
                                cand[n] = float(sims[n])
                        except Exception:
                            pass
                    idf_map = self.bm25_map(util.content_words(" ".join(kws))) if kws else {}
                    out = []
                    for i, sim in cand.items():
                        r = rows[i]
                        h = {"sim": sim, "id": r[0], "url": r[1], "title": r[2],
                             "passage": r[3], "topic": r[4],
                             "fetched_at": r[5]}
                        if kws:
                            low = h["passage"].lower()
                            cov = (sum(1 for w in kws if w in low)
                                   / float(len(kws)))
                            bm = self.bm25_score(" ".join(kws), h["passage"],
                                                 idf_map=idf_map)
                            bm_n = bm / (bm + 2.5) if bm > 0 else 0.0
                            h["cov"] = round(cov, 3)
                            h["bm25"] = round(bm, 3)
                            h["sim"] = round(min(0.99, sim + 0.42 * bm_n
                                                 + 0.07 * cov), 4)
                        out.append(h)
                    out.sort(key=lambda h: -h["sim"])
                    out = [h for h in out
                           if h["sim"] >= min_sim and h["sim"] >= min_sim * 0.4]
                    if out:
                        return out[:k]
        cols = {"docs": "id,url,title,passage,topic,fetched_at,emb",
                "qa": "id,question,answer,evidence,created_at,emb"}[table]
        cand = []
        with self.lock:
            if keywords:
                kws = [k for k in keywords[:4] if k]
                if kws:
                    # Rank the SQL prefilter by how many keywords the passage
                    # actually contains (a passage with ALL query words is a much
                    # stronger candidate than one that merely mentions "the").
                    expr = " + ".join(["(passage LIKE ?)"] * len(kws))
                    clause = " OR ".join(["passage LIKE ?"] * len(kws))
                    sql = ("SELECT %s, (%s) AS kwm FROM docs WHERE %s "
                           "ORDER BY kwm DESC, id DESC LIMIT 900"
                           % (cols, expr, clause))
                    params = tuple("%" + kw + "%" for kw in kws) * 2
                    rows = [r[:-1] for r in self.conn.execute(sql, params).fetchall()]
                    cand.extend(rows)
                if len(cand) < 120:
                    rows2 = self.conn.execute(
                        "SELECT %s FROM docs ORDER BY id DESC LIMIT 3000" % cols).fetchall()
                    cand.extend(rows2)
            else:
                cand = self.conn.execute(
                    "SELECT %s FROM %s ORDER BY id DESC LIMIT 1200" % (cols, table)).fetchall()
        seen = set()
        scored = []
        kws_sql = [w.lower() for w in (keywords or [])[:4] if w] if table == "docs" else []
        idf_map2 = self.bm25_map(util.content_words(" ".join(kws_sql))) if kws_sql else {}
        for r in cand:
            if r[0] in seen:
                continue
            seen.add(r[0])
            emb = util.unpack_f32(r[-1])
            if not emb:
                continue
            sim = util.dot(query_emb, emb)
            if sim < min_sim:
                continue
            if kws_sql:
                pass_low = (r[3] or "").lower()
                cov = (sum(1 for w in kws_sql if w in pass_low)
                       / float(len(kws_sql)))
                bm = self.bm25_score(" ".join(kws_sql), r[3], idf_map=idf_map2)
                bm_n = bm / (bm + 2.5) if bm > 0 else 0.0
                sim = sim + 0.42 * bm_n + 0.07 * cov
            scored.append((sim, r))
        scored.sort(key=lambda t: -t[0])
        out = []
        for sim, r in scored[:k]:
            item = {"sim": round(sim, 4), "id": r[0]}
            if table == "docs":
                item.update({"url": r[1], "title": r[2], "passage": r[3],
                             "topic": r[4], "fetched_at": r[5]})
            else:
                try:
                    item.update({"question": r[1], "answer": r[2],
                                 "evidence": json.loads(r[3] or "[]"),
                                 "created_at": r[4]})
                except Exception:
                    item.update({"question": r[1], "answer": r[2], "evidence": []})
            out.append(item)
        return out

    def passages_for_urls(self, urls, limit=8):
        urls = [u for u in (urls or []) if u][:8]
        if not urls:
            return []
        q = " OR ".join(["url=?"] * len(urls))
        with self.lock:
            rows = self.conn.execute(
                "SELECT id,url,title,passage,emb FROM docs WHERE %s LIMIT ?" % q,
                tuple(urls) + (limit,)).fetchall()
        return [{"id": r[0], "url": r[1], "title": r[2], "passage": r[3],
                 "emb": util.unpack_f32(r[4])} for r in rows]

    def random_passages(self, n=40, exclude_ids=()):
        with self.lock:
            rows = self.conn.execute(
                "SELECT id,url,title,passage,emb FROM docs ORDER BY RANDOM() LIMIT ?",
                (n + len(exclude_ids),)).fetchall()
        out = []
        ex = set(exclude_ids)
        for r in rows:
            if r[0] in ex:
                continue
            out.append({"id": r[0], "url": r[1], "title": r[2], "passage": r[3],
                        "emb": util.unpack_f32(r[4])})
            if len(out) >= n:
                break
        return out

    def qa_rows(self, limit=500):
        with self.lock:
            rows = self.conn.execute(
                "SELECT question,answer,evidence,feedback,emb FROM qa "
                "ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
        out = []
        for q, a, ev, fb, emb in rows:
            try:
                evidence = json.loads(ev or "[]")
            except Exception:
                evidence = []
            out.append({"question": q, "answer": a or "", "evidence": evidence,
                        "feedback": fb, "emb": util.unpack_f32(emb)})
        return out

    def get_docs_by_source(self, source, limit=10):
        with self.lock:
            rows = self.conn.execute(
                "SELECT id,url,title,passage,topic,fetched_at,emb FROM docs "
                "WHERE source=? ORDER BY id ASC LIMIT ?", (source, limit)).fetchall()
        return [{"sim": 0.0, "id": r[0], "url": r[1], "title": r[2], "passage": r[3],
                 "topic": r[4], "fetched_at": r[5], "emb": util.unpack_f32(r[6])}
                for r in rows]

    def corpus_texts(self, limit_chars=1500000):
        """Everything the model has learned, as training text."""
        texts = []
        total = 0
        with self.lock:
            rows = self.conn.execute(
                "SELECT passage FROM docs ORDER BY quality DESC, fetched_at DESC "
                "LIMIT 6000").fetchall()
        for (p,) in rows:
            if not p:
                continue
            texts.append(p)
            total += len(p)
            if total >= limit_chars:
                break
        with self.lock:
            qrows = self.conn.execute(
                "SELECT question, answer FROM qa ORDER BY id DESC LIMIT 400").fetchall()
        for q, a in qrows:
            a = re.sub(r"\*\*|\*|_", "", a or "")
            a = re.sub(r"\[[^\]]*\]\([^)]*\)", "", a)
            a = re.sub(r"\[\d+\]", "", a)
            texts.append((q or "") + " " + a)
        return texts

    def keyword_rank(self, passages, query, k=6):
        q = set(util.content_words(query))
        if not q:
            return []
        scored = []
        for p in passages:
            pt = set(util.content_words(p.get("passage", "")))
            if not pt:
                continue
            inter = q & pt
            if not inter:
                continue
            score = sum(self.idf(t) for t in inter) / (1.0 + math.log(1 + len(pt)))
            scored.append((score, p))
        scored.sort(key=lambda t: -t[0])
        return [p for _, p in scored[:k]]

    def bump_topic(self, name, priority=0.5, category=None, hit=False):
        name = (name or "").strip().lower()
        if not name or len(name) < 3:
            return
        with self.lock:
            row = self.conn.execute("SELECT priority, fetch_count FROM topics WHERE name=?",
                                    (name,)).fetchone()
            if row:
                if hit:
                    self.conn.execute(
                        "UPDATE topics SET hit_count=hit_count+1, "
                        "priority=MIN(1.0, priority+0.15) WHERE name=?", (name,))
                else:
                    self.conn.execute(
                        "UPDATE topics SET priority=MAX(priority, ?), "
                        "category=COALESCE(?, category) WHERE name=?",
                        (priority, category, name))
            else:
                self.conn.execute(
                    "INSERT INTO topics(name,priority,category,last_fetch,fetch_count,hit_count)"
                    " VALUES(?,?,?,0,0,?)", (name, priority, category, 1 if hit else 0))
            self.conn.commit()

    def mark_topic_fetched(self, name):
        with self.lock:
            self.conn.execute(
                "UPDATE topics SET last_fetch=?, fetch_count=fetch_count+1 WHERE name=?",
                (time.time(), name))
            self.conn.commit()

    def next_topics(self, limit=1):
        with self.lock:
            rows = self.conn.execute(
                "SELECT name, priority, category, last_fetch, fetch_count, hit_count "
                "FROM topics ORDER BY priority DESC, last_fetch ASC LIMIT 60").fetchall()
        now = time.time()
        scored = []
        for name, pri, cat, lf, fc, hc in rows:
            age = now - (lf or 0)
            score = pri * 100.0 + min(age / 60.0, 30.0) - math.log1p(fc) * 2.0
            scored.append((score, {"name": name, "priority": pri, "category": cat,
                                   "last_fetch": lf, "fetch_count": fc, "hits": hc}))
        scored.sort(key=lambda t: -t[0])
        return [s[1] for s in scored[:limit]]

    def all_topics(self, limit=60):
        with self.lock:
            rows = self.conn.execute(
                "SELECT name, priority, category, fetch_count, hit_count FROM topics "
                "ORDER BY priority DESC LIMIT ?", (limit,)).fetchall()
        return [{"name": r[0], "priority": round(r[1], 3), "category": r[2],
                 "fetch_count": r[3], "hits": r[4]} for r in rows]

    def prune_topics(self, cap=None):
        cap = cap or config.AF_MAX_TOPICS
        with self.lock:
            n = self.conn.execute("SELECT COUNT(*) FROM topics").fetchone()[0]
            if n <= cap:
                return 0
            self.conn.execute(
                "DELETE FROM topics WHERE name IN (SELECT name FROM topics "
                "ORDER BY priority ASC, fetch_count ASC LIMIT ?)", (n - cap,))
            self.conn.commit()
            return n - cap

    def enforce_size(self, max_mb=None):
        max_mb = max_mb or config.MAX_BRAIN_MB
        size_mb = self.db_size_mb()
        try:
            if os.path.exists(self.path + "-wal") and os.path.getsize(self.path + "-wal") > 2 * 1024 * 1024:
                with self.lock:
                    self.conn.execute("PRAGMA wal_checkpoint(TRUNCATE)")
        except Exception:
            pass
        if size_mb <= max_mb:
            return 0
        with self.lock:
            n = self.conn.execute("SELECT COUNT(*) FROM docs").fetchone()[0]
            target = max(500, int(n * 0.92))
            # Prune low-quality WEB material first; curated packs (facts,
            # knowledge intros, teacher) are protected and deleted last.
            self.conn.execute(
                "DELETE FROM docs WHERE id IN (SELECT id FROM docs "
                "ORDER BY (source IN ('facts','knowledge','teacher','origin')) ASC, "
                "quality ASC, fetched_at ASC LIMIT ?)", (n - target,))
            if getattr(self, "_fts_ready", False):
                try:
                    self.conn.execute(
                        "DELETE FROM docs_fts WHERE rowid NOT IN "
                        "(SELECT id FROM docs)")
                except Exception:
                    pass
            self.conn.commit()
            try:
                self.conn.execute("PRAGMA wal_checkpoint(TRUNCATE)")
            except Exception:
                pass
        self._doc_count = None
        return n - target

    def cleanup_blocked(self):
        """One-time removal of toxic fragments ingested before filtering."""
        gone = 0
        with self.lock:
            rows = self.conn.execute("SELECT id, passage FROM docs").fetchall()
            for rid, p in rows:
                if util.is_blocked(p):
                    self.conn.execute("DELETE FROM docs WHERE id=?", (rid,))
                    if getattr(self, "_fts_ready", False):
                        try:
                            self.conn.execute(
                                "DELETE FROM docs_fts WHERE rowid=?", (rid,))
                        except Exception:
                            pass
                    gone += 1
            if gone:
                self.conn.commit()
                self._doc_count = None
        return gone

    def db_size_mb(self):
        total = 0
        for suffix in ("", "-wal", "-shm"):
            p = self.path + suffix
            if os.path.exists(p):
                total += os.path.getsize(p)
        return total / (1024 * 1024)

    def stats(self):
        with self.lock:
            docs = self.conn.execute("SELECT COUNT(*) FROM docs").fetchone()[0]
            qa = self.conn.execute("SELECT COUNT(*) FROM qa").fetchone()[0]
            topics = self.conn.execute("SELECT COUNT(*) FROM topics").fetchone()[0]
            df = self.conn.execute("SELECT COUNT(*) FROM df").fetchone()[0]
        db_mb = self.db_size_mb()
        brain_mb = 0.0
        try:
            for f in os.listdir(config.BRAINS):
                brain_mb += os.path.getsize(config.BRAINS / f)
            brain_mb /= (1024 * 1024)
        except Exception:
            pass
        return {"passages": docs, "qa_pairs": qa, "topics": topics, "vocab": df,
                "db_mb": round(db_mb, 2), "brain_mb": round(brain_mb, 2),
                "model_kb": round((db_mb + brain_mb) * 1024)}
