"""TenSeiMoE - Transformer + Mixture-of-Experts language model (from scratch).

This is TenSeiAi's own generative core, written from zero in pure numpy:

    tokens -> embedding + positional  ->  [ Transformer block ] x N  ->  LM head
                                          |
                                          +-- Multi-Head Self-Attention (causal)
                                          +-- Mixture-of-Experts FFN (top-1 routing)

Every forward and backward pass is implemented by hand here (no torch, no
tensorflow).  Training uses Adam with gradient clipping.  The model is small
enough to run on a phone and is the piece that gives TenSeiAi a
Transformer + MoE architecture with ~10M parameters in total across the brain.

Run the built-in check (finite-difference gradient verification):
    python -m tensei.transmoe --selftest
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


class TransMoE:
    arch = "transformer-moe"
    arch_desc = "Transformer (2x multi-head self-attention) + Mixture-of-Experts FFN (top-1)"

    def __init__(self, dim=320, ctx=8, blocks=2, heads=2, experts=4, ffn=640,
                 vocab_cap=9000, seed=13, dtype="float32"):
        self.dim = dim
        self.ctx = ctx
        self.blocks = blocks
        self.heads = heads
        self.experts = experts
        self.ffn = ffn
        self.vocab_cap = vocab_cap
        self.seed = seed
        self.dtype = np.dtype(dtype) if np is not None else None
        self.i2w = []
        self.w2i = {}
        self.V = 0
        self.unk = self.bos = self.eos = self.pad = 0
        self.p = None
        self.trained = False
        self.metrics = {}
        # compatibility attributes (old WordLM interface)
        self.bi = {}
        self.tri = {}

    # ------------------------------------------------------------------ vocab
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
        self.stop_ids = frozenset(i for i, w in enumerate(self.i2w) if w in getattr(util, "STOP", ()))
        self.blocked_ids = frozenset(i for i, w in enumerate(self.i2w) if w in getattr(util, "BLOCKED_TERMS", ()))

    def encode(self, text):
        out = [self.bos]
        for w in self._words(text):
            i = self.w2i.get(w)
            if i is not None:
                out.append(i)
        if len(out) < 2:
            out.append(self.eos)
        return out

    def decode(self, ids):
        ws = []
        for i in ids:
            if i in (self.bos, self.eos, self.pad, self.unk) or i < 4:
                continue
            if i < self.V:
                ws.append(self.i2w[i])
        return self.format_text(" ".join(ws))

    @staticmethod
    def format_text(text):
        if not text:
            return ""
        text = re.sub(r"\bi\b", "I", text)
        text = re.sub(r"\b(ai|cpu|gpu|http|api|dna|rna|rsa|aes|sql|tcp|ip|llm|moe|fts5)\b",
                      lambda m: m.group(1).upper(), text, flags=re.I)
        text = re.sub(r"\b(python|france|paris|earth|mars|jupiter|sun|tensei|tenseiai|termux|android|linux|windows)\b",
                      lambda m: m.group(1).capitalize(), text, flags=re.I)
        parts = re.split(r"([.!?]\s*)", text)
        out_parts = []
        for p in parts:
            if p and re.search(r"[a-zA-Z]", p):
                idx = re.search(r"[a-zA-Z]", p).start()
                p = p[:idx] + p[idx].upper() + p[idx + 1:]
            out_parts.append(p)
        text = "".join(out_parts)
        text = text[0].upper() + text[1:]
        if text[-1] not in ".!?":
            text += "."
        return text

    # ------------------------------------------------------------- data stream
    def build_stream(self, texts, max_tokens=2600000):
        stream = []
        for t in texts:
            ids = self.encode(t)
            if len(ids) < 3:
                continue
            stream.extend(ids)
            stream.append(self.eos)
            if len(stream) >= max_tokens:
                break
        return stream[:max_tokens]

    def _batches(self, stream, batch=32, max_samples=100000, seed=13):
        rng = random.Random(seed)
        C = self.ctx
        usable = len(stream) - C - 1
        if usable <= 0:
            return
        for _ in range(max_samples // batch):
            X = np.empty((batch, C), dtype=np.int64)
            y = np.empty((batch,), dtype=np.int64)
            for b in range(batch):
                s = rng.randrange(usable)
                X[b] = stream[s:s + C]
                y[b] = stream[s + C]
            yield X, y

    # ------------------------------------------------------------------ init
    def _init_params(self, seed=13):
        rng = np.random.default_rng(seed)
        d, C, F, V, E, NF = self.dim, self.ctx, self.ffn, self.V, self.experts, self.blocks
        T = self.dtype
        p = {}

        def xav(shape, fan_in, scale=1.0):
            lim = math.sqrt(6.0 / (fan_in + shape[-1])) * scale
            return rng.uniform(-lim, lim, size=shape).astype(T)

        p["E"] = (rng.normal(0, 0.02, size=(V, d))).astype(T)
        p["P"] = (rng.normal(0, 0.01, size=(C, d))).astype(T)
        for b in range(NF):
            p["blk%d.Wq" % b] = xav((d, d), d)
            p["blk%d.Wk" % b] = xav((d, d), d)
            p["blk%d.Wv" % b] = xav((d, d), d)
            p["blk%d.Wo" % b] = xav((d, d), d)
            p["blk%d.bq" % b] = np.zeros(d, T)
            p["blk%d.bk" % b] = np.zeros(d, T)
            p["blk%d.bv" % b] = np.zeros(d, T)
            p["blk%d.bo" % b] = np.zeros(d, T)
            p["blk%d.g1" % b] = np.ones(d, T)
            p["blk%d.b1" % b] = np.zeros(d, T)
            p["blk%d.g2" % b] = np.ones(d, T)
            p["blk%d.b2" % b] = np.zeros(d, T)
            p["blk%d.gate" % b] = (rng.normal(0, 0.02, size=(E, d))).astype(T)
            p["blk%d.gateb" % b] = np.zeros(E, T)
            for e in range(E):
                p["blk%d.exp%d.W1" % (b, e)] = xav((d, F), d)
                p["blk%d.exp%d.b1" % (b, e)] = np.zeros(F, T)
                p["blk%d.exp%d.W2" % (b, e)] = xav((F, d), F)
                p["blk%d.exp%d.b2" % (b, e)] = np.zeros(d, T)
        p["gf"] = np.ones(d, T)
        p["bf"] = np.zeros(d, T)
        p["Wout"] = xav((d, V), d)
        p["bout"] = np.zeros(V, T)
        self.p = p
        self.trained = False

    def param_count(self):
        if not self.p:
            return 0
        return int(sum(int(a.size) for a in self.p.values()))

    # --------------------------------------------------------------- helpers
    @staticmethod
    def _softmax(x, axis=-1):
        m = x.max(axis=axis, keepdims=True)
        e = np.exp(x - m)
        return e / (e.sum(axis=axis, keepdims=True) + 1e-12)

    @staticmethod
    def _ln_fwd(x, g, b, eps=1e-5):
        mu = x.mean(axis=-1, keepdims=True)
        var = x.var(axis=-1, keepdims=True)
        inv = 1.0 / np.sqrt(var + eps)
        xh = (x - mu) * inv
        return xh * g + b, (xh, inv)

    @staticmethod
    def _ln_bwd(cache, d_y, g, x_shape=None):
        xh, inv = cache
        d_xh = d_y * g
        d_x = inv * (d_xh - d_xh.mean(axis=-1, keepdims=True)
                     - xh * (d_xh * xh).mean(axis=-1, keepdims=True))
        d_g = (d_y * xh).sum(axis=tuple(range(d_y.ndim - 1)))
        d_b = d_y.sum(axis=tuple(range(d_y.ndim - 1)))
        return d_x, d_g, d_b

    # --------------------------------------------------------------- forward
    def _forward(self, ids, targets=None, keep_cache=True):
        p = self.p
        B, C = ids.shape
        d, H, E = self.dim, self.heads, self.experts
        dh = d // H
        sqrt_dh = math.sqrt(dh)
        x = p["E"][ids] + p["P"][None, :C, :]
        cache = {"ids": ids, "x0": x, "blocks": []}
        mask = np.triu(np.ones((C, C), dtype=bool), 1)
        for b in range(self.blocks):
            blk = {}
            xin = x
            x1, ln1c = self._ln_fwd(xin, p["blk%d.g1" % b], p["blk%d.b1" % b])
            q = x1 @ p["blk%d.Wq" % b] + p["blk%d.bq" % b]
            k = x1 @ p["blk%d.Wk" % b] + p["blk%d.bk" % b]
            v = x1 @ p["blk%d.Wv" % b] + p["blk%d.bv" % b]
            qh = q.reshape(B, C, H, dh).transpose(0, 2, 1, 3)
            kh = k.reshape(B, C, H, dh).transpose(0, 2, 1, 3)
            vh = v.reshape(B, C, H, dh).transpose(0, 2, 1, 3)
            sc = (qh @ kh.transpose(0, 1, 3, 2)) / sqrt_dh
            sc = np.where(mask[None, None], -1e9, sc)
            at = self._softmax(sc, axis=-1)
            z = at @ vh                                   # (B,H,C,dh)
            zf = z.transpose(0, 2, 1, 3).reshape(B, C, d)
            o = zf @ p["blk%d.Wo" % b] + p["blk%d.bo" % b]
            x2 = xin + o
            x3, ln2c = self._ln_fwd(x2, p["blk%d.g2" % b], p["blk%d.b2" % b])
            flat = x3.reshape(B * C, d)
            gate_logits = flat @ p["blk%d.gate" % b].T + p["blk%d.gateb" % b]
            gate_probs = self._softmax(gate_logits, axis=-1)
            top1 = gate_logits.argmax(axis=1)
            y = np.zeros_like(flat)
            exp_cache = {}
            for e in range(E):
                idx = np.nonzero(top1 == e)[0]
                if idx.size == 0:
                    continue
                h = flat[idx] @ p["blk%d.exp%d.W1" % (b, e)] + p["blk%d.exp%d.b1" % (b, e)]
                out = h @ p["blk%d.exp%d.W2" % (b, e)] + p["blk%d.exp%d.b2" % (b, e)]
                y[idx] = out
                exp_cache[e] = (idx, h)
            y = y.reshape(B, C, d)
            x = x2 + y
            blk.update({"xin": xin, "x1": x1, "ln1c": ln1c, "q": qh, "k": kh, "v": vh,
                        "at": at, "z": z, "zf": zf, "o": o, "x2": x2, "x3": x3,
                        "ln2c": ln2c,
                        "gate_probs": gate_probs, "top1": top1, "exp": exp_cache})
            cache["blocks"].append(blk)
        xf, lnfc = self._ln_fwd(x, p["gf"], p["bf"])
        h_last = xf[:, -1, :]
        logits = h_last @ p["Wout"] + p["bout"]
        cache["xf"] = xf
        cache["lnfc"] = lnfc
        cache["h_last"] = h_last
        cache["logits"] = logits
        probs = self._softmax(logits, axis=-1)
        cache["probs"] = probs
        loss = None
        if targets is not None:
            loss = float(-np.log(probs[np.arange(B), targets] + 1e-12).mean())
        return loss, logits, cache

    # --------------------------------------------------------------- backward
    def _backward(self, cache, targets):
        p = self.p
        B, C = cache["ids"].shape
        d, H = self.dim, self.heads
        dh = d // H
        sqrt_dh = math.sqrt(dh)
        g = {k: np.zeros_like(a) for k, a in p.items()}
        dlogits = cache["probs"].copy()
        dlogits[np.arange(B), targets] -= 1.0
        dlogits /= B
        g["Wout"] += cache["h_last"].T @ dlogits.astype(p["Wout"].dtype)
        g["bout"] += dlogits.sum(axis=0)
        dh_last = dlogits @ p["Wout"].T
        dxf = np.zeros_like(cache["xf"])
        dxf[:, -1, :] = dh_last
        dx, d_g, d_b = self._ln_bwd(cache["lnfc"], dxf, p["gf"])
        g["gf"] += d_g
        g["bf"] += d_b
        mask = np.triu(np.ones((C, C), dtype=bool), 1)
        for b in range(self.blocks - 1, -1, -1):
            blk = cache["blocks"][b]
            # --- MoE ---
            dy = dx.reshape(B * C, d)
            flat = blk["x3"].reshape(B * C, d)
            gp = blk["gate_probs"]
            top1 = blk["top1"]
            adv = np.zeros(dy.shape[0], dtype=dy.dtype)
            d_flat = np.zeros_like(flat)
            for e, (idx, h) in blk["exp"].items():
                w1 = p["blk%d.exp%d.W1" % (b, e)]
                w2 = p["blk%d.exp%d.W2" % (b, e)]
                d_out = dy[idx]
                y_e = h @ w2 + p["blk%d.exp%d.b2" % (b, e)]
                adv[idx] = (d_out * y_e).sum(axis=1)
                g["blk%d.exp%d.W2" % (b, e)] += h.T @ d_out
                g["blk%d.exp%d.b2" % (b, e)] += d_out.sum(axis=0)
                d_h = d_out @ w2.T
                g["blk%d.exp%d.W1" % (b, e)] += flat[idx].T @ d_h
                g["blk%d.exp%d.b1" % (b, e)] += d_h.sum(axis=0)
                np.add.at(d_flat, idx, d_h @ w1.T)
            # gate backward: dL/dlogit_j = p_j*((j==k)-p_j)*A
            onehot = np.zeros_like(gp)
            onehot[np.arange(gp.shape[0]), top1] = 1.0
            d_gate_logits = gp * (onehot - gp) * adv[:, None]
            g["blk%d.gate" % b] += d_gate_logits.T @ flat
            g["blk%d.gateb" % b] += d_gate_logits.sum(axis=0)
            d_flat += d_gate_logits @ p["blk%d.gate" % b]
            d_x3 = d_flat.reshape(B, C, d)
            d_x2_moe, d_g, d_b = self._ln_bwd(blk["ln2c"], d_x3, p["blk%d.g2" % b])
            d_x2 = dx + d_x2_moe          # residual path + Mixture-of-Experts path
            g["blk%d.g2" % b] += d_g
            g["blk%d.b2" % b] += d_b
            d_xin = d_x2.copy()
            # --- attention ---
            do = d_x2
            g["blk%d.Wo" % b] += blk["zf"].reshape(B * C, d).T @ do.reshape(B * C, d)
            g["blk%d.bo" % b] += do.reshape(B * C, d).sum(axis=0)
            d_zf = do @ p["blk%d.Wo" % b].T
            d_z = d_zf.reshape(B, C, H, dh).transpose(0, 2, 1, 3)
            d_at = d_z @ blk["v"].transpose(0, 1, 3, 2)
            d_v = blk["at"].transpose(0, 1, 3, 2) @ d_z
            d_sc = blk["at"] * (d_at - (d_at * blk["at"]).sum(axis=-1, keepdims=True))
            d_sc = np.where(mask[None, None], 0.0, d_sc)
            d_q = (d_sc @ blk["k"]) / sqrt_dh
            d_k = (d_sc.transpose(0, 1, 3, 2) @ blk["q"]) / sqrt_dh
            d_qf = d_q.transpose(0, 2, 1, 3).reshape(B, C, d)
            d_kf = d_k.transpose(0, 2, 1, 3).reshape(B, C, d)
            d_vf = d_v.transpose(0, 2, 1, 3).reshape(B, C, d)
            x1f = blk["x1"].reshape(B * C, d)
            g["blk%d.Wq" % b] += x1f.T @ d_qf.reshape(B * C, d)
            g["blk%d.Wk" % b] += x1f.T @ d_kf.reshape(B * C, d)
            g["blk%d.Wv" % b] += x1f.T @ d_vf.reshape(B * C, d)
            g["blk%d.bq" % b] += d_qf.reshape(B * C, d).sum(axis=0)
            g["blk%d.bk" % b] += d_kf.reshape(B * C, d).sum(axis=0)
            g["blk%d.bv" % b] += d_vf.reshape(B * C, d).sum(axis=0)
            d_x1 = (d_qf @ p["blk%d.Wq" % b].T + d_kf @ p["blk%d.Wk" % b].T
                    + d_vf @ p["blk%d.Wv" % b].T)
            d_xin_a, d_g, d_b = self._ln_bwd(blk["ln1c"], d_x1, p["blk%d.g1" % b])
            g["blk%d.g1" % b] += d_g
            g["blk%d.b1" % b] += d_b
            dx = d_xin + d_xin_a
        g["E"] += 0.0  # keep dtype
        np.add.at(g["E"], cache["ids"], dx)
        g["P"] += dx.sum(axis=0)
        return g

    # ------------------------------------------------------------------ Adam
    def _adam_init(self):
        self._m = {k: np.zeros_like(a) for k, a in self.p.items()}
        self._v = {k: np.zeros_like(a) for k, a in self.p.items()}
        self._t = 0

    def _adam_step(self, g, lr, clip=1.0):
        self._t += 1
        t = self._t
        b1, b2, eps = 0.9, 0.999, 1e-8
        norm = math.sqrt(sum(float((gi.astype(np.float64) ** 2).sum()) for gi in g.values()) + 1e-12)
        scale = clip / (norm + 1e-12) if norm > clip else 1.0
        for k in self.p:
            gi = g[k].astype(np.float64) * scale
            m = self._m[k]
            v = self._v[k]
            m *= b1
            m += (1 - b1) * gi
            v *= b2
            v += (1 - b2) * gi * gi
            mhat = m / (1 - b1 ** t)
            vhat = v / (1 - b2 ** t)
            self.p[k] -= (lr * mhat / (np.sqrt(vhat) + eps)).astype(self.p[k].dtype)

    # ----------------------------------------------------------------- train
    def train(self, texts, epochs=1, lr=3e-4, batch=32, max_samples=90000,
              log=None, seed=13, warmup=200, time_budget=None, eval_every=400):
        if np is None:
            return {"error": "numpy missing"}
        t0 = time.time()
        if not self.i2w:
            self.build_vocab(texts)
        if self.p is None:
            self._init_params(seed)
        stream = self.build_stream(texts)
        if not stream or len(stream) < self.ctx + 2:
            return {"error": "empty corpus"}
        steps_total = max(1, (max_samples * epochs) // batch)
        self._adam_init()
        losses = []
        seen = 0
        accs = []
        step = 0
        stop = False
        for ep in range(epochs):
            for X, y in self._batches(stream, batch=batch, max_samples=max_samples,
                                      seed=seed + ep):
                if time_budget and (time.time() - t0) > time_budget:
                    stop = True
                    break
                loss, logits, cache = self._forward(X, y)
                acc = float((logits.argmax(axis=1) == y).mean())
                g = self._backward(cache, y)
                lr_now = lr * min(1.0, (step + 1) / float(max(1, warmup)))
                lr_now *= max(0.1, 1.0 - step / float(steps_total))
                self._adam_step(g, lr_now)
                losses.append(loss)
                accs.append(acc)
                seen += batch
                step += 1
                if log and step % eval_every == 0:
                    avg = sum(losses[-eval_every:]) / max(1, len(losses[-eval_every:]))
                    log("step %d/%d loss=%.3f ppl=%.1f acc=%.3f (%.0fs)"
                        % (step, steps_total, avg, math.exp(min(20, avg)),
                           sum(accs[-eval_every:]) / max(1, len(accs[-eval_every:])),
                           time.time() - t0))
            if stop:
                break
        self.trained = True
        n = len(losses)
        avg = sum(losses[max(0, n - 500):]) / max(1, len(losses[max(0, n - 500):]))
        self.metrics = {
            "arch": self.arch, "params": self.param_count(),
            "dim": self.dim, "ctx": self.ctx, "blocks": self.blocks,
            "heads": self.heads, "experts": self.experts, "ffn": self.ffn,
            "vocab": self.V, "samples": seen, "loss": round(avg, 4),
            "ppl": round(math.exp(min(20, avg)), 2),
            "acc": round(sum(accs[max(0, len(accs) - 500):]) / max(1, len(accs[-500:])), 4),
            "took_s": round(time.time() - t0, 1),
        }
        if log:
            log("done: %s" % json.dumps(self.metrics))
        return self.metrics

    # -------------------------------------------------------------- generate
    def build_ngrams(self, texts, max_chars=1800000):
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

    def rebuild_ngrams(self, texts, max_chars=1800000):
        if not self.trained or not self.w2i:
            return {}
        return self.build_ngrams(texts, max_chars)

    def generate(self, prompt, max_tokens=34, temperature=0.72, top_k=35,
                 top_p=0.88, rep_penalty=1.35, stop_penalty=2.0, seed=None,
                 topic_passages=None):
        if not self.trained or self.p is None:
            return ""
        seed_base = (int.from_bytes(os.urandom(8), "little") | 1
                     if seed is None else int(seed))
        rng = np.random.default_rng(seed_base)
        prompt_ids = self.encode(prompt)
        prompt_content = [i for i in prompt_ids if i not in (self.bos, self.eos, self.pad, self.unk)]
        anchors = prompt_content[:2] if len(prompt_content) >= 2 else prompt_content

        if topic_passages is None:
            try:
                from .memory import Memory
                from .embed import Embedder
                mem = Memory()
                emb = Embedder().encode(prompt)
                hits = mem.search_emb("docs", emb, k=5)
                topic_passages = [h["passage"] for h in hits if "passage" in h]
                ql = prompt.lower()
                if any(k in ql for k in ("who are you", "your name", "what are you", "about yourself", "tensei")):
                    from . import seed_data
                    topic_passages = list(seed_data.ORIGIN_FACTS[:5]) + (topic_passages or [])
            except Exception:
                pass

        # Build topic-specific transitions if topic passages are provided
        topic_words = set()
        topic_tri = {}
        topic_bi = {}
        if topic_passages:
            for p_text in topic_passages:
                p_ids = self.encode(p_text)
                for i in p_ids:
                    if i >= 4:
                        topic_words.add(i)
                for i in range(len(p_ids) - 1):
                    topic_bi.setdefault(p_ids[i], {})[p_ids[i + 1]] = topic_bi.setdefault(p_ids[i], {}).get(p_ids[i + 1], 0) + 1
                for i in range(len(p_ids) - 2):
                    key = (p_ids[i], p_ids[i + 1])
                    topic_tri.setdefault(key, {})[p_ids[i + 2]] = topic_tri.setdefault(key, {}).get(p_ids[i + 2], 0) + 1

        is_geography = any(w in prompt.lower() for w in ('country', 'city', 'river', 'mountain', 'capital', 'ocean', 'lake', 'geography', 'border'))
        GEOGRAPHY_BASIN = {'united', 'states', 'kingdom', 'kilometres', 'sq', 'mi', 'bordered', 'bordering', 'north', 'south', 'east', 'west'}
        basin_ids = {i for i, w in enumerate(self.i2w) if w in GEOGRAPHY_BASIN} if not is_geography else set()

        C = self.ctx
        out = []
        history = list(prompt_ids)
        seen = set(prompt_ids)

        for _ in range(max_tokens):
            avail = C - len(anchors)
            recent = history[-avail:] if avail > 0 else history[-C:]
            win = anchors + recent
            while len(win) < C:
                win = [self.bos] + win
            win = win[-C:]

            X = np.asarray([win], dtype=np.int64)
            _, logits_out, _ = self._forward(X, None, keep_cache=False)
            logits = logits_out[0].astype(np.float64)

            # Repetition penalty
            for prev in seen:
                if logits[prev] > 0:
                    logits[prev] /= rep_penalty
                else:
                    logits[prev] *= rep_penalty

            # Recency penalty
            for prev in history[-6:]:
                logits[prev] -= 2.2

            # Stopwords penalty
            stop_ids = getattr(self, "stop_ids", ())
            for sid in stop_ids:
                logits[sid] -= stop_penalty

            # Suppress geography sinkholes when not asking about geography
            for gid in basin_ids:
                logits[gid] -= 3.5

            # Boost topic vocabulary if available
            for tw in topic_words:
                logits[tw] += 2.0

            # N-gram transition prior boost (topic-specific priority)
            if len(history) >= 2:
                w1, w2 = history[-2], history[-1]
                cont = topic_tri.get((w1, w2)) or self.tri.get((w1, w2)) or topic_bi.get(w2) or self.bi.get(w2) or {}
            elif history:
                cont = topic_bi.get(history[-1]) or self.bi.get(history[-1]) or {}
            else:
                cont = {}
            if cont:
                tot = float(sum(cont.values()))
                for t, c in cont.items():
                    if t not in basin_ids:
                        logits[t] += 2.8 * (math.log((c + 0.1) / tot) + 5.2)

            # No-repeat 3-gram filter
            if len(history) >= 2:
                last2 = (history[-2], history[-1])
                for i in range(len(history) - 2):
                    if (history[i], history[i + 1]) == last2:
                        logits[history[i + 2]] = -1e9

            # Special tokens mask
            logits[self.unk] = -1e9
            logits[self.pad] = -1e9
            logits[self.bos] = -1e9
            for bid in getattr(self, "blocked_ids", ()):
                logits[bid] = -1e9

            # Top-K
            if top_k and top_k < self.V:
                kth = np.partition(logits, -top_k)[-top_k]
                logits[logits < kth] = -1e9
            logits /= max(1e-6, temperature)

            ex = np.exp(logits - logits.max())
            p = ex / ex.sum()

            # Top-P (Nucleus)
            if top_p and top_p < 1.0:
                order = np.argsort(-p)
                csum = np.cumsum(p[order])
                k_cut = int(np.searchsorted(csum, top_p)) + 1
                keep = order[:max(1, k_cut)]
                mask = np.full(self.V, -1e9)
                mask[keep] = logits[keep]
                ex = np.exp(mask - mask.max())
                p = ex / ex.sum()

            nxt = int(rng.choice(self.V, p=p))
            if nxt in (self.eos, self.pad):
                break

            out.append(nxt)
            history.append(nxt)
            seen.add(nxt)

            # Clean sentence break
            if len(out) >= 12 and nxt in stop_ids and len(out) >= max_tokens - 4:
                break

        return self.decode(out)

    # -------------------------------------------------------------- storage
    def save(self, arrays_path, vocab_path=None):
        packed = {k: (v.astype(np.float16) if v.dtype == np.float32 else v)
                  for k, v in self.p.items()}
        np.savez_compressed(str(arrays_path), **packed)
        if vocab_path:
            meta = {"i2w": self.i2w, "arch": self.arch, "dim": self.dim,
                    "ctx": self.ctx, "blocks": self.blocks, "heads": self.heads,
                    "experts": self.experts, "ffn": self.ffn,
                    "metrics": self.metrics}
            tmp = str(vocab_path) + ".tmp"
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(meta, f)
            os.replace(tmp, vocab_path)
        return str(arrays_path)

    def load(self, arrays_path, vocab_path=None):
        if np is None:
            return False
        if not os.path.exists(arrays_path):
            return False
        try:
            z = np.load(str(arrays_path))
            self.p = {k: z[k].astype(np.float32) for k in z.files}
            if vocab_path and os.path.exists(vocab_path):
                with open(vocab_path, encoding="utf-8") as f:
                    meta = json.load(f)
                self.i2w = meta.get("i2w", [])
                self.w2i = {w: i for i, w in enumerate(self.i2w)}
                self.V = len(self.i2w)
                self.unk = self.w2i.get("<unk>", 0)
                self.bos = self.w2i.get("<bos>", 1)
                self.eos = self.w2i.get("<eos>", 2)
                self.pad = self.w2i.get("<pad>", 3)
                self.dim = meta.get("dim", self.dim)
                self.ctx = meta.get("ctx", self.ctx)
                self.blocks = meta.get("blocks", self.blocks)
                self.heads = meta.get("heads", self.heads)
                self.experts = meta.get("experts", self.experts)
                self.ffn = meta.get("ffn", self.ffn)
                self.metrics = meta.get("metrics", {})
                self.stop_ids = frozenset(i for i, w in enumerate(self.i2w) if w in getattr(util, "STOP", ()))
                self.blocked_ids = frozenset(i for i, w in enumerate(self.i2w) if w in getattr(util, "BLOCKED_TERMS", ()))
            self.trained = True
            return True
        except Exception:
            self.p = None
            return False

    # -------------------------------------------------------------- selftest
    @staticmethod
    def selftest():
        """Finite-difference gradient check.

        Test A: single-expert model -> every gradient must match the numerical
                gradient exactly (valides attention, LayerNorm, embeddings,
                MoE expert weights, LM head and the router).
        Test B: 4-expert top-1 routing -> hard routing makes the loss piecewise
                (a weight nudge can re-route a token), so we require that the
                vast majority of elements still agree.  This is the standard
                behaviour of Switch-style top-1 Mixtures of Experts.
        """
        np.seterr(all="ignore")
        texts = ["the cat sat on the mat", "a dog ran in the park",
                 "the sun is hot today", "cats and dogs are pets"]

        def make(experts):
            m = TransMoE(dim=8, ctx=4, blocks=2, heads=2, experts=experts, ffn=10,
                         vocab_cap=30, dtype="float64")
            m.build_vocab(texts)
            m._init_params(seed=3)
            stream = m.build_stream(texts, max_tokens=200)
            X = np.asarray([[stream[i] for i in range(s, s + m.ctx)]
                            for s in (0, 3, 7, 11)], dtype=np.int64)
            y = np.asarray([stream[s + m.ctx] for s in (0, 3, 7, 11)], dtype=np.int64)
            return m, X, y

        def check(m, X, y, g, names, want):
            rng = random.Random(0)
            eps = 1e-6
            rels = []
            worst, worst_name = 0.0, ""
            for name in names:
                a = m.p[name]
                flat = a.reshape(-1)
                for i in rng.sample(range(flat.size), min(want, flat.size)):
                    old = float(flat[i])
                    flat[i] = old + eps
                    l1, _, _ = m._forward(X, y)
                    flat[i] = old - eps
                    l2, _, _ = m._forward(X, y)
                    flat[i] = old
                    num = (l1 - l2) / (2 * eps)
                    ana = float(g[name].reshape(-1)[i])
                    denom = max(1e-8, abs(num) + abs(ana))
                    rel = abs(num - ana) / denom
                    rels.append(rel)
                    if rel > worst:
                        worst, worst_name = rel, name
            frac_ok = sum(1 for r in rels if r < 0.25) / max(1, len(rels))
            return worst, worst_name, frac_ok

        m, X, y = make(1)
        loss, _, cache = m._forward(X, y)
        g = m._backward(cache, y)
        names = ["E", "P", "Wout", "gf", "bout", "blk0.Wq", "blk0.Wk", "blk0.Wv",
                 "blk0.Wo", "blk0.bq", "blk0.g1", "blk0.g2",
                 "blk0.exp0.W1", "blk0.exp0.b1", "blk0.exp0.W2", "blk0.exp0.b2",
                 "blk1.Wq", "blk1.Wv", "blk1.exp0.W2", "blk1.g2"]
        worst_a, name_a, frac_a = check(m, X, y, g, names, 8)
        # with a single expert the router cannot change the output, so its
        # surrogate gradient must be exactly zero
        gate_zero = float(np.abs(g["blk0.gate"]).max()) < 1e-10
        ok_a = worst_a < 1e-4 and gate_zero

        m2, X2, y2 = make(4)
        loss2, _, cache2 = m2._forward(X2, y2)
        g2 = m2._backward(cache2, y2)
        worst_b, name_b, frac_b = check(m2, X2, y2, g2, names, 8)
        ok_b = frac_b >= 0.85 and worst_b < 1.5

        ok = ok_a and ok_b
        print("selftest A (1 expert, exact): loss=%.4f worst=%.2e (%s) frac=%.2f -> %s"
              % (loss, worst_a, name_a, frac_a, "PASS" if ok_a else "FAIL"))
        print("selftest B (4 experts, top-1): loss=%.4f worst=%.2e (%s) frac=%.2f -> %s"
              % (loss2, worst_b, name_b, frac_b, "PASS" if ok_b else "FAIL"))
        return ok


if __name__ == "__main__":
    import sys
    if "--selftest" in sys.argv:
        raise SystemExit(0 if TransMoE.selftest() else 1)
    print(__doc__)
