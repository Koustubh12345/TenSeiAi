import json
import math
import os
import re

from . import config, util

try:
    import numpy as np
except Exception:
    np = None

_U64 = None
if np is not None:
    _U64 = np.uint64


class Embedder:
    """From-scratch text encoder.

    Layer 1: hashed bag of word / bigram / char-4gram features (sublinear tf).
    Layer 2: deterministic random projection (signed, seedless - pure hash math,
             identical output in numpy and pure-python paths).
    Layer 3: learned projection W (dim x dim) trained on our own accumulated
             data - this is what makes the model smarter over time.
    """

    def __init__(self, dim=config.EMB_DIM, hash_dim=config.HASH_DIM):
        self.dim = int(dim)
        self.hash_dim = int(hash_dim)
        self.W = None
        self._Wnp = None

    def featurize(self, text):
        feats = {}
        ws = util.words(text)
        for w in ws:
            feats[w] = feats.get(w, 0) + 1
        for i in range(len(ws) - 1):
            bg = ws[i] + "_" + ws[i + 1]
            feats[bg] = feats.get(bg, 0) + 1
        compact = re.sub(r"[^a-z0-9]+", "", (text or "").lower())[:4000]
        for i in range(len(compact) - 3):
            cg = "#" + compact[i:i + 4]
            feats[cg] = feats.get(cg, 0) + 1
        out = {}
        for tok, c in feats.items():
            idx = util.h64(tok, 0) % self.hash_dim
            out[idx] = out.get(idx, 0.0) + (1.0 + math.log(c))
        return out

    def _project_np(self, feats):
        d = self.dim
        idxs = np.fromiter(feats.keys(), dtype=np.uint64, count=len(feats))
        wv = np.fromiter(feats.values(), dtype=np.float64, count=len(feats))
        j = np.arange(d, dtype=np.uint64)
        k = idxs[:, None] * _U64(0x9E3779B97F4A7C15) + j[None, :]
        x = k + _U64(0x9E3779B97F4A7C15)
        x = ((x ^ (x >> _U64(30))) * _U64(0xBF58476D1CE4E5B9))
        x = ((x ^ (x >> _U64(27))) * _U64(0x94D049BB133111EB))
        h = x ^ (x >> _U64(31))
        sign = np.where(h >> _U64(63), -1.0, 1.0)
        out = (wv[:, None] * sign).sum(axis=0) * (1.0 / math.sqrt(d))
        return out

    def _project_py(self, feats):
        d = self.dim
        out = [0.0] * d
        for idx, wv in feats.items():
            base = (idx * 0x9E3779B97F4A7C15) & util.MASK64
            for j in range(d):
                h = util.splitmix64((base + j) & util.MASK64)
                out[j] += wv if h < (1 << 63) else -wv
        inv = 1.0 / math.sqrt(d)
        return [x * inv for x in out]

    def project(self, feats):
        if not feats:
            return [0.0] * self.dim
        if np is not None and len(feats) >= 24:
            return self._project_np(feats)
        return self._project_py(feats)

    def apply_W(self, v):
        if not self.W:
            return v
        d = self.dim
        if np is not None:
            if self._Wnp is None:
                self._Wnp = np.asarray(self.W, dtype=np.float64).reshape(d, d)
            return (self._Wnp @ np.asarray(v, dtype=np.float64))
        rows = self.W
        out = []
        for i in range(d):
            row = rows[i * d:(i + 1) * d]
            out.append(sum(wj * xj for wj, xj in zip(row, v)))
        return out

    def encode(self, text):
        feats = self.featurize(text)
        v = self.project(feats)
        v = self.apply_W(v)
        if np is not None and isinstance(v, np.ndarray):
            v = v.tolist()
        return util.nrm([float(x) for x in v])

    def base_encode(self, text):
        feats = self.featurize(text)
        v = self.project(feats)
        if np is not None and isinstance(v, np.ndarray):
            v = v.tolist()
        return util.nrm([float(x) for x in v])

    def init_W_identity(self):
        d = self.dim
        if self.W is None:
            self.W = [0.0] * (d * d)
            for i in range(d):
                self.W[i * d + i] = 1.0
            self._Wnp = None

    def save(self, path):
        if self.W is None:
            return False
        tmp = str(path) + ".tmp"
        with open(tmp, "w") as f:
            json.dump({"dim": self.dim, "W": [round(x, 5) for x in self.W]}, f)
        os.replace(tmp, path)
        return True

    def load(self, path):
        try:
            with open(path) as f:
                d = json.load(f)
        except Exception:
            return False
        if not d or "W" not in d or int(d.get("dim", 0)) != self.dim:
            return False
        self.W = [float(x) for x in d["W"]]
        self._Wnp = None
        return True

    def learned(self):
        return self.W is not None
