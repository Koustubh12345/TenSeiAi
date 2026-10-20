import json
import math
import os
import random

try:
    import numpy as np
except Exception:
    np = None


def _sigmoid(z):
    if z < -60:
        return 0.0
    if z > 60:
        return 1.0
    return 1.0 / (1.0 + math.exp(-z))


def _softmax(z):
    m = max(z)
    ex = [math.exp(v - m) for v in z]
    s = sum(ex) or 1.0
    return [v / s for v in ex]


class MLP:
    """From-scratch multi-layer perceptron with backprop + momentum SGD.

    Trains with numpy when available, pure python otherwise. Identical
    save format either way.
    """

    def __init__(self, sizes, seed=1, out_act=None):
        self.sizes = list(sizes)
        self.out_act = out_act or ("sigmoid" if self.sizes[-1] == 1 else "softmax")
        rnd = random.Random(seed)
        self.W = []
        self.B = []
        for i in range(len(self.sizes) - 1):
            fan_in, fan_out = self.sizes[i], self.sizes[i + 1]
            last = (i == len(self.sizes) - 2)
            scale = math.sqrt(1.0 / fan_in) if last else math.sqrt(2.0 / fan_in)
            self.W.append([[rnd.gauss(0, scale) for _ in range(fan_in)]
                           for _ in range(fan_out)])
            self.B.append([0.0] * fan_out)
        self.metrics = {}

    def _forward_py(self, x):
        a = x
        acts = [a]
        zs = []
        L = len(self.W)
        for i in range(L):
            W, B = self.W[i], self.B[i]
            z = [sum(wj * xj for wj, xj in zip(row, a)) + b for row, b in zip(W, B)]
            if i == L - 1:
                a = _softmax(z) if self.out_act == "softmax" else [_sigmoid(z[0])]
            else:
                zs.append(z)
                a = [v if v > 0.0 else 0.0 for v in z]
            acts.append(a)
        return acts, zs

    def predict_proba(self, x):
        acts, _ = self._forward_py(list(x))
        return acts[-1]

    def predict_class(self, x):
        p = self.predict_proba(x)
        if len(p) == 1:
            return 1 if p[0] >= 0.5 else 0
        return max(range(len(p)), key=lambda i: p[i])

    def _train_np(self, X, y, epochs, lr, l2, batch, val_frac, seed, log):
        X = np.asarray(X, dtype=np.float64)
        y = np.asarray(y)
        n = len(X)
        rng = np.random.default_rng(seed)
        idx = np.arange(n)
        rng.shuffle(idx)
        nval = max(1, int(n * val_frac)) if n >= 10 else 0
        val_idx = idx[:nval]
        tr_idx = idx[nval:] if nval else idx
        W = [np.asarray(w, dtype=np.float64) for w in self.W]
        B = [np.asarray(b, dtype=np.float64) for b in self.B]
        Vel = [np.zeros_like(w) for w in W]
        Vb = [np.zeros_like(b) for b in B]
        L = len(W)
        best = (1e18, None)
        patience = 0

        def eval_set(Xs, ys):
            a = Xs
            for i in range(L):
                z = a @ W[i].T + B[i]
                if i == L - 1:
                    if self.out_act == "softmax":
                        ex = np.exp(z - z.max(axis=1, keepdims=True))
                        a = ex / ex.sum(axis=1, keepdims=True)
                    else:
                        a = 1.0 / (1.0 + np.exp(-np.clip(z, -60, 60)))
                else:
                    a = np.maximum(z, 0.0)
            if self.out_act == "softmax":
                idxs = np.arange(len(ys))
                p = np.clip(a[idxs, ys], 1e-9, 1.0)
                loss = float(-np.log(p).mean())
                acc = float((a.argmax(axis=1) == ys).mean())
            else:
                p = np.clip(a[:, 0], 1e-9, 1.0 - 1e-9)
                loss = float(-(ys * np.log(p) + (1 - ys) * np.log(1 - p)).mean())
                acc = float(((p >= 0.5).astype(int) == ys.astype(int)).mean())
            return loss, acc

        epr = 0
        for ep in range(epochs):
            epr = ep + 1
            rng.shuffle(tr_idx)
            for s in range(0, len(tr_idx), batch):
                bidx = tr_idx[s:s + batch]
                xb = X[bidx]
                yb = y[bidx]
                acts = [xb]
                zs = []
                a = xb
                for i in range(L):
                    z = a @ W[i].T + B[i]
                    if i == L - 1:
                        if self.out_act == "softmax":
                            ex = np.exp(z - z.max(axis=1, keepdims=True))
                            a = ex / ex.sum(axis=1, keepdims=True)
                        else:
                            a = 1.0 / (1.0 + np.exp(-np.clip(z, -60, 60)))
                    else:
                        zs.append(z)
                        a = np.maximum(z, 0.0)
                    acts.append(a)
                delta = acts[-1].copy()
                if self.out_act == "softmax":
                    delta[np.arange(len(bidx)), yb] -= 1.0
                else:
                    delta = delta - yb.reshape(-1, 1)
                for i in range(L - 1, -1, -1):
                    gW = delta.T @ acts[i] / len(bidx) + l2 * W[i]
                    gB = delta.mean(axis=0)
                    Vel[i] = 0.9 * Vel[i] - lr * gW
                    Vb[i] = 0.9 * Vb[i] - lr * gB
                    W[i] += Vel[i]
                    B[i] += Vb[i]
                    if i > 0:
                        d = delta @ W[i]
                        delta = d * (zs[i - 1] > 0.0)
            tr_loss, tr_acc = eval_set(X[tr_idx], y[tr_idx])
            if nval:
                va_loss, va_acc = eval_set(X[val_idx], y[val_idx])
            else:
                va_loss, va_acc = tr_loss, tr_acc
            if log:
                log("epoch %d train_loss=%.4f acc=%.3f val_loss=%.4f val_acc=%.3f"
                    % (epr, tr_loss, tr_acc, va_loss, va_acc))
            if va_loss < best[0] - 1e-6:
                best = (va_loss, ([w.copy() for w in W], [b.copy() for b in B]))
                patience = 0
            else:
                patience += 1
                if patience >= 4:
                    break
        if best[1] is not None:
            W, B = best[1]
        self.W = [w.tolist() for w in W]
        self.B = [b.tolist() for b in B]
        self.metrics = {"epochs_run": epr, "train_loss": round(tr_loss, 4),
                        "train_acc": round(tr_acc, 4), "val_loss": round(va_loss, 4),
                        "val_acc": round(va_acc, 4), "backend": "numpy"}

    def _train_py(self, X, y, epochs, lr, l2, val_frac, seed, log):
        n = len(X)
        rnd = random.Random(seed)
        idx = list(range(n))
        rnd.shuffle(idx)
        nval = max(1, int(n * val_frac)) if n >= 10 else 0
        val_idx = idx[:nval]
        tr_idx = idx[nval:] if nval else idx
        Vw = [[[0.0] * len(row) for row in m] for m in self.W]
        Vb = [[0.0] * len(b) for b in self.B]
        L = len(self.W)
        eps = 1e-9

        def fwd(x):
            a = list(x)
            acts = [a]
            zs = []
            for i in range(L):
                W, B = self.W[i], self.B[i]
                z = [sum(wj * xj for wj, xj in zip(row, a)) + b
                     for row, b in zip(W, B)]
                if i == L - 1:
                    a = _softmax(z) if self.out_act == "softmax" else [_sigmoid(z[0])]
                else:
                    zs.append(z)
                    a = [v if v > 0.0 else 0.0 for v in z]
                acts.append(a)
            return acts, zs

        for ep in range(epochs):
            rnd.shuffle(tr_idx)
            for s in tr_idx:
                x = X[s]
                target = y[s]
                acts, zs = fwd(x)
                out = acts[-1]
                if self.out_act == "softmax":
                    delta = [out[k] - (1.0 if k == target else 0.0)
                             for k in range(len(out))]
                else:
                    delta = [out[0] - float(target)]
                deltas = [None] * L
                deltas[L - 1] = delta
                for i in range(L - 1, 0, -1):
                    zi = zs[i - 1]
                    d = [0.0] * len(zi)
                    Wi = self.W[i]
                    for k in range(len(zi)):
                        g = 0.0
                        for j in range(len(delta)):
                            g += Wi[j][k] * delta[j]
                        d[k] = g if zi[k] > 0.0 else 0.0
                    delta = d
                    deltas[i - 1] = delta
                for i in range(L):
                    delta = deltas[i]
                    a = acts[i]
                    Wi, Bi = self.W[i], self.B[i]
                    Vwi, Vbi = Vw[i], Vb[i]
                    for j in range(len(delta)):
                        dj = delta[j]
                        row = Wi[j]
                        vrow = Vwi[j]
                        for k in range(len(a)):
                            vrow[k] = 0.9 * vrow[k] - lr * (dj * a[k] + l2 * row[k])
                            row[k] += vrow[k]
                        Vbi[j] = 0.9 * Vbi[j] - lr * dj
                        Bi[j] += Vbi[j]

            def eval_set(ids):
                loss = 0.0
                acc = 0
                for s2 in ids:
                    acts, _ = fwd(X[s2])
                    out = acts[-1]
                    if self.out_act == "softmax":
                        loss += -math.log(max(out[y[s2]], eps))
                        if max(range(len(out)), key=lambda i: out[i]) == y[s2]:
                            acc += 1
                    else:
                        p = min(max(out[0], eps), 1 - eps)
                        t = float(y[s2])
                        loss += -(t * math.log(p) + (1 - t) * math.log(1 - p))
                        if (p >= 0.5) == (t >= 0.5):
                            acc += 1
                cnt = max(1, len(ids))
                return loss / cnt, acc / cnt

            tr_loss, tr_acc = eval_set(tr_idx)
            va_loss, va_acc = eval_set(val_idx) if nval else (tr_loss, tr_acc)
            if log:
                log("epoch %d train_loss=%.4f acc=%.3f val_loss=%.4f val_acc=%.3f"
                    % (ep + 1, tr_loss, tr_acc, va_loss, va_acc))
        self.metrics = {"epochs_run": ep + 1, "train_loss": round(tr_loss, 4),
                        "train_acc": round(tr_acc, 4), "val_loss": round(va_loss, 4),
                        "val_acc": round(va_acc, 4), "backend": "python"}

    def train(self, X, y, epochs=12, lr=0.05, l2=1e-4, batch=8, val_frac=0.15,
              seed=7, log=None):
        if not X:
            return self.metrics
        if np is not None and len(X) >= 40:
            self._train_np(X, y, epochs, lr, l2, batch, val_frac, seed, log)
        else:
            self._train_py(X, y, min(epochs, 5), lr, l2, val_frac, seed, log)
        return self.metrics

    def save(self, path):
        d = {
            "sizes": self.sizes,
            "out_act": self.out_act,
            "W": [[[round(v, 5) for v in row] for row in m] for m in self.W],
            "B": [[round(v, 5) for v in b] for b in self.B],
            "metrics": self.metrics,
        }
        tmp = str(path) + ".tmp"
        with open(tmp, "w") as f:
            json.dump(d, f, separators=(",", ":"))
        os.replace(tmp, path)

    @classmethod
    def load(cls, path):
        try:
            with open(path) as f:
                d = json.load(f)
        except Exception:
            return None
        m = cls(d["sizes"], out_act=d.get("out_act"))
        m.W = d["W"]
        m.B = d["B"]
        m.metrics = d.get("metrics", {})
        return m
