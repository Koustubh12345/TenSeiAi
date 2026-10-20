"""TenSeiLM - a from-scratch word-level neural language model.

Trains on TenSeiAi's own accumulated memory (nothing pretrained). It is what
makes TenSeiAi answer by GENERATING text on its own instead of looking up
pre-written replies.
"""

import json
import math
import os
import random
import re
import time

from . import util

try:
    import numpy as np
except Exception:
    np = None

_JUNK = {"displaystyle", "mathbf", "mathrm", "frac", "href", "http", "https",
         "www", "com", "org", "html", "nbsp", "amp", "quot", "px", "rgb"}

_CS = None
_CS_LOADED = False



_RUST = None
_RUST_LOADED = False


def _rust_speed():
    """Rust speed module (tensei_rust.dll / libtensei_rust.so); None if unavailable."""
    global _RUST, _RUST_LOADED
    if _RUST_LOADED:
        return _RUST
    _RUST_LOADED = True
    try:
        import ctypes
        import shutil
        dirs = [
            os.path.dirname(os.path.abspath(__file__)),
            os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "rust", "target", "release"),
        ]
        home = os.environ.get("TENSEI_HOME")
        if home:
            dirs.append(home)
            dirs.append(os.path.join(home, "lib"))
        dirs.append(os.path.expanduser("~/.tensei_ai"))
        for d in dirs:
            for name in ("tensei_rust.dll", "libtensei_rust.so", "libtensei_rust.dylib", "tensei_rust.so"):
                p = os.path.join(d, name)
                if os.path.exists(p):
                    target_p = p
                    if "/storage/" in p:
                        int_dir = os.path.expanduser("~/.tensei_ai")
                        os.makedirs(int_dir, exist_ok=True)
                        cp_target = os.path.join(int_dir, name)
                        try:
                            if not os.path.exists(cp_target) or os.path.getmtime(p) > os.path.getmtime(cp_target):
                                shutil.copy2(p, cp_target)
                            target_p = cp_target
                        except Exception:
                            pass
                    try:
                        lib = ctypes.CDLL(target_p)
                        if hasattr(lib, "tensei_rust_sample"):
                            lib.tensei_rust_sample.restype = ctypes.c_int
                            lib.tensei_rust_sample.argtypes = [
                                ctypes.POINTER(ctypes.c_float), ctypes.c_int,
                                ctypes.c_float, ctypes.c_int, ctypes.c_ulonglong]
                        if hasattr(lib, "tensei_rust_dot"):
                            lib.tensei_rust_dot.restype = ctypes.c_float
                            lib.tensei_rust_dot.argtypes = [
                                ctypes.POINTER(ctypes.c_float), ctypes.POINTER(ctypes.c_float), ctypes.c_int]
                        _RUST = lib
                        return _RUST
                    except Exception:
                        continue
    except Exception:
        _RUST = None
    return _RUST


def _cspeed():
    """C speed module (cspeed.so) built from cspeed.c; None if unavailable."""
    global _CS, _CS_LOADED
    if _CS_LOADED:
        return _CS
    _CS_LOADED = True
    try:
        import ctypes
        import shutil
        dirs = [os.path.dirname(os.path.abspath(__file__))]
        home = os.environ.get("TENSEI_HOME")
        if home:
            dirs.append(home)
        dirs.append(os.path.expanduser("~/.tensei_ai"))
        for d in dirs:
            for name in ("cspeed.so", "cspeed.dylib", "cspeed.dll"):
                p = os.path.join(d, name)
                if os.path.exists(p):
                    target_p = p
                    if "/storage/" in p:
                        int_dir = os.path.expanduser("~/.tensei_ai")
                        os.makedirs(int_dir, exist_ok=True)
                        cp_target = os.path.join(int_dir, name)
                        try:
                            if not os.path.exists(cp_target) or os.path.getmtime(p) > os.path.getmtime(cp_target):
                                shutil.copy2(p, cp_target)
                            target_p = cp_target
                        except Exception:
                            pass
                    try:
                        lib = ctypes.CDLL(target_p)
                        lib.tensei_sample.restype = ctypes.c_int
                        lib.tensei_sample.argtypes = [
                            ctypes.POINTER(ctypes.c_float), ctypes.c_int,
                            ctypes.c_float, ctypes.c_int, ctypes.c_ulonglong]
                        _CS = lib
                        return _CS
                    except Exception:
                        continue
    except Exception:
        _CS = None
    return _CS


class WordLM:
    def __init__(self, dim=128, ctx=5, hidden=256, vocab_cap=9000):
        self.dim = dim
        self.ctx = ctx
        self.hidden = hidden
        self.vocab_cap = vocab_cap
        self.i2w = []
        self.w2i = {}
        self.V = 0
        self.unk = self.bos = self.eos = self.pad = 0
        self.stop_ids = frozenset()
        self.blocked_ids = frozenset()
        self.bi = {}
        self.tri = {}
        self.E = self.W1 = self.b1 = self.W2 = self.b2 = None
        self.trained = False
        self.metrics = {}

    @staticmethod
    def _words(text):
        out = []
        for w in util.words(text):
            if len(w) < 2 or w in _JUNK:
                continue
            if w.isdigit() and len(w) > 4:
                continue
            out.append(w)
        return out

    # ---------- vocab ----------
    def build_vocab(self, texts):
        from collections import Counter
        c = Counter()
        for t in texts:
            c.update(self._words(t))
        words = [w for w, _ in c.most_common(self.vocab_cap - 4)]
        self.i2w = ["<unk>", "<bos>", "<eos>", "<pad>"] + words
        self.V = len(self.i2w)
        self.w2i = {w: i for i, w in enumerate(self.i2w)}
        self.unk, self.bos, self.eos, self.pad = 0, 1, 2, 3
        self.stop_ids = frozenset(i for i, w in enumerate(self.i2w)
                                  if w in util.STOP)
        self.blocked_ids = frozenset(i for i, w in enumerate(self.i2w)
                                     if w in util.BLOCKED_TERMS)

    def build_ngrams(self, texts, max_chars=1200000):
        self.bi = {}
        self.tri = {}
        total = 0
        for t in texts:
            ids = self.encode(t)
            total += len(t)
            for i in range(len(ids) - 1):
                a, b = ids[i], ids[i + 1]
                d = self.bi.setdefault(a, {})
                d[b] = d.get(b, 0) + 1
            for i in range(len(ids) - 2):
                key = (ids[i], ids[i + 1])
                d = self.tri.setdefault(key, {})
                c = ids[i + 2]
                d[c] = d.get(c, 0) + 1
            if total >= max_chars:
                break
        return {"bigram_keys": len(self.bi), "trigram_keys": len(self.tri)}

    def rebuild_ngrams(self, texts, max_chars=1200000):
        if not self.trained or not self.w2i:
            return {}
        return self.build_ngrams(texts, max_chars)

    def encode(self, text):
        return [self.w2i.get(w, self.unk) for w in self._words(text)]

    def decode(self, ids):
        return [self.i2w[i] for i in ids if 4 <= i < self.V]

    # ---------- data ----------
    def _samples(self, texts, max_samples, stride=2):
        X, Y = [], []
        for t in texts:
            ids = self.encode(t)
            if len(ids) < 3:
                continue
            stream = [self.bos] * self.ctx + ids + [self.eos]
            i = self.ctx
            while i < len(stream):
                X.append(stream[i - self.ctx:i])
                Y.append(stream[i])
                if len(X) >= max_samples:
                    return np.asarray(X, dtype=np.int32), np.asarray(Y, dtype=np.int32)
                i += stride
        return np.asarray(X, dtype=np.int32), np.asarray(Y, dtype=np.int32)

    def _init_params(self, seed=7):
        rng = np.random.default_rng(seed)
        ci = self.ctx * self.dim
        self.E = rng.normal(0, 0.1, (self.V, self.dim)).astype(np.float32)
        self.W1 = rng.normal(0, math.sqrt(2.0 / ci), (self.hidden, ci)).astype(np.float32)
        self.b1 = np.zeros(self.hidden, np.float32)
        self.W2 = rng.normal(0, 0.01, (self.V, self.hidden)).astype(np.float32)
        self.b2 = np.zeros(self.V, np.float32)

    # ---------- training ----------
    def train(self, texts, epochs=4, lr=0.06, batch=128, max_samples=90000,
              log=None):
        if np is None:
            if log:
                log("lm: numpy missing, generation disabled")
            return {}
        t0 = time.time()
        self.dim, self.ctx, self.hidden = 128, 5, 256
        texts = list(texts)
        # sample training windows evenly across the whole corpus, not just the
        # first documents (the corpus is ordered by insertion time)
        random.Random(4).shuffle(texts)
        self.build_vocab(texts)
        X, Y = self._samples(texts, max_samples)
        if len(X) < 40:
            if log:
                log("lm: corpus too small (%d samples), needs more knowledge" % len(X))
            return {}
        self._init_params(seed=7 + (self.V % 97))
        n = len(X)
        idx = np.arange(n)
        rng = np.random.default_rng(11)
        params = [self.E, self.W1, self.b1, self.W2, self.b2]
        mom = [np.zeros_like(p) for p in params]

        def clip(g, lim=5.0):
            nn = float(np.linalg.norm(g))
            if nn > lim:
                g = g * (lim / nn)
            return g

        for ep in range(epochs):
            rng.shuffle(idx)
            total, correct, seen = 0.0, 0, 0
            for s in range(0, n, batch):
                b = idx[s:s + batch]
                xb, yb = X[b], Y[b]
                B = len(b)
                Ex = self.E[xb].reshape(B, -1)
                z1 = Ex @ self.W1.T + self.b1
                h = np.maximum(z1, 0.0)
                logits = h @ self.W2.T + self.b2
                logits -= logits.max(axis=1, keepdims=True)
                ex = np.exp(logits)
                p = ex / ex.sum(axis=1, keepdims=True)
                loss = -np.log(np.clip(p[np.arange(B), yb], 1e-9, 1.0)).mean()
                total += float(loss) * B
                correct += int((p.argmax(axis=1) == yb).sum())
                seen += B

                dl = p
                dl[np.arange(B), yb] -= 1.0
                dl /= B
                gW2 = clip(dl.T @ h)
                gb2 = clip(dl.sum(0))
                dh = dl @ self.W2
                dz1 = dh * (z1 > 0.0)
                gW1 = clip(dz1.T @ Ex)
                gb1 = clip(dz1.sum(0))
                dEx = dz1 @ self.W1
                dE = np.zeros_like(self.E)
                np.add.at(dE, xb.reshape(-1), dEx.reshape(B * self.ctx, -1))
                dE = clip(dE)
                for i, g in enumerate((dE, gW1, gb1, gW2, gb2)):
                    mom[i] = 0.9 * mom[i] - lr * g
                    params[i] += mom[i]
            lr *= 0.85
            ppl = math.exp(total / max(1, seen))
            if log:
                log("lm epoch %d loss=%.3f ppl=%.1f acc=%.3f"
                    % (ep + 1, total / max(1, seen), ppl, correct / max(1, seen)))
        ngram_stats = self.build_ngrams(texts)
        self.trained = True
        self.metrics = {"loss": round(total / max(1, seen), 3),
                        "ppl": round(math.exp(total / max(1, seen)), 1),
                        "acc": round(correct / max(1, seen), 3),
                        "vocab": self.V, "samples": n,
                        "ngrams": ngram_stats,
                        "took_s": round(time.time() - t0, 1)}
        return self.metrics

    # ---------- generation ----------
    def generate(self, prompt, max_tokens=34, temperature=0.75, top_k=40,
                 rep_penalty=1.25, stop_penalty=2.2, seed=None, top_p=0.95):
        if not self.trained or np is None or self.V < 10:
            return ""
        best, best_score = "", -1.0
        for attempt in range(3):
            text = self._generate_once(prompt, max_tokens, temperature, top_k,
                                       rep_penalty, stop_penalty + attempt * 0.9,
                                       None if seed is None else seed + attempt,
                                       top_p=top_p)
            words = util.words(text)
            if not words:
                continue
            content = sum(1 for w in words if w not in util.STOP)
            ratio = content / len(words)
            score = ratio * min(1.0, len(words) / 6.0)
            if len(words) >= 2:
                from collections import Counter
                bigrams = list(zip(words, words[1:]))
                hits = Counter(bigrams).most_common(1)[0][1]
                if hits >= 3:
                    score *= 0.2
            if score > best_score:
                best, best_score = text, score
            if ratio >= 0.4 and len(words) >= 6:
                break
        return best

    def _generate_once(self, prompt, max_tokens, temperature, top_k,
                       rep_penalty, stop_penalty, seed, top_p=0.95):
        ids = self.encode(prompt)
        window = ([self.bos] * self.ctx + ids)[-self.ctx:]
        seen = set(ids[-32:])
        seed_base = (int.from_bytes(os.urandom(8), "little") | 1
                     if seed is None else int(seed))
        rng = np.random.default_rng(seed_base)
        out = []
        for _ in range(max_tokens):
            x = np.asarray([window], dtype=np.int32)
            Ex = self.E[x].reshape(1, -1)
            h = np.maximum(Ex @ self.W1.T + self.b1, 0.0)
            logits = (h @ self.W2.T + self.b2)[0].astype(np.float64)
            for t in seen:
                logits[t] /= rep_penalty
            for t in window[-10:]:
                logits[t] -= 3.0
            for t in self.stop_ids:
                logits[t] -= stop_penalty
            if self.tri or self.bi:
                w1, w2 = window[-2], window[-1]
                cont = self.tri.get((w1, w2)) or self.bi.get(w2) or {}
                if cont:
                    tot = float(sum(cont.values()))
                    for t, c in cont.items():
                        logits[t] += 2.6 * (math.log((c + 0.1) / tot) + 5.8)
            logits[self.unk] = -1e9
            logits[self.pad] = -1e9
            logits[self.bos] = -1e9
            for t in self.blocked_ids:
                logits[t] = -1e9
            nxt = -1
            rlib = _rust_speed()
            if rlib is not None and hasattr(rlib, "tensei_rust_sample"):
                import ctypes
                arr = np.ascontiguousarray(logits, dtype=np.float32)
                cseed = seed_base + len(out) * 7919
                nxt = int(rlib.tensei_rust_sample(
                    arr.ctypes.data_as(ctypes.POINTER(ctypes.c_float)),
                    int(self.V), float(temperature), int(top_k or 0), cseed))
            if nxt < 0:
                lib = _cspeed()
                if lib is not None:
                    import ctypes
                    arr = np.ascontiguousarray(logits, dtype=np.float32)
                    cseed = seed_base + len(out) * 7919
                    nxt = int(lib.tensei_sample(
                        arr.ctypes.data_as(ctypes.POINTER(ctypes.c_float)),
                        int(self.V), float(temperature), int(top_k or 0), cseed))
            if nxt < 0:
                if top_k and top_k < self.V:
                    kth = np.partition(logits, -top_k)[-top_k]
                    logits[logits < kth] = -1e9
                logits /= max(1e-6, temperature)
                ex = np.exp(logits - logits.max())
                p = ex / ex.sum()
                if top_p and top_p < 1.0:
                    order = np.argsort(-p)
                    csum = np.cumsum(p[order])
                    k_cut = int(np.searchsorted(csum, top_p)) + 1
                    keep = order[:max(1, k_cut)]
                    mask = np.full(self.V, -1e9)
                    mask[keep] = logits[keep]
                    logits = mask
                    ex = np.exp(logits - logits.max())
                    p = ex / ex.sum()
                nxt = int(rng.choice(self.V, p=p))
            if nxt == self.eos:
                break
            out.append(nxt)
            seen.add(nxt)
            window = (window + [nxt])[-self.ctx:]
            if len(out) >= 3 and out[-1] == out[-2] == out[-3]:
                out = out[:-2]
                break
        words = self.decode(out)
        if not words:
            return ""
        text = " ".join(words)
        text = re.sub(r"\bi\b", "I", text)
        text = re.sub(r"\s+([,.!?;:])", r"\1", text)
        text = text[0].upper() + text[1:]
        if text[-1] not in ".!?":
            text += "."
        return text

    # ---------- persistence ----------
    def save(self, arrays_path, vocab_path):
        if np is None or self.E is None:
            return False
        # float16 on disk keeps the model file small; training/generation run
        # in float32 after load.
        np.savez(arrays_path, E=self.E.astype(np.float16),
                 W1=self.W1.astype(np.float16), b1=self.b1,
                 W2=self.W2.astype(np.float16), b2=self.b2)
        with open(vocab_path, "w") as f:
            json.dump({"i2w": self.i2w, "dim": self.dim, "ctx": self.ctx,
                       "hidden": self.hidden, "metrics": self.metrics,
                       "trained": self.trained}, f)
        return True

    def load(self, arrays_path, vocab_path):
        if np is None:
            return False
        try:
            with open(vocab_path) as f:
                meta = json.load(f)
            z = np.load(arrays_path)
            self.i2w = meta["i2w"]
            self.V = len(self.i2w)
            self.w2i = {w: i for i, w in enumerate(self.i2w)}
            self.unk, self.bos, self.eos, self.pad = 0, 1, 2, 3
            self.stop_ids = frozenset(i for i, w in enumerate(self.i2w)
                                      if w in util.STOP)
            self.blocked_ids = frozenset(i for i, w in enumerate(self.i2w)
                                         if w in util.BLOCKED_TERMS)
            self.dim = meta.get("dim", self.dim)
            self.ctx = meta.get("ctx", self.ctx)
            self.hidden = meta.get("hidden", self.hidden)
            self.metrics = meta.get("metrics", {})
            self.trained = bool(meta.get("trained"))
            self.E = np.asarray(z["E"], dtype=np.float32)
            self.W1 = np.asarray(z["W1"], dtype=np.float32)
            self.b1 = np.asarray(z["b1"], dtype=np.float32)
            self.W2 = np.asarray(z["W2"], dtype=np.float32)
            self.b2 = np.asarray(z["b2"], dtype=np.float32)
            return True
        except Exception:
            return False
