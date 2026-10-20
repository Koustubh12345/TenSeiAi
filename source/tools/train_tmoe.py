"""Train TenSeiMoE - the Transformer + Mixture-of-Experts language model.

Trains from scratch (pure numpy) on everything the model has accumulated in its
memory database (plus its self-facts).  Saves brains/tmoe.npz (+ vocab).

Usage:
    python tools/train_tmoe.py --samples 100000          # full train
    python tools/train_tmoe.py --samples 30000 --init    # fine-tune the saved model
    python tools/train_tmoe.py --time-budget 1200        # train for up to 20 min
"""
import argparse
import os
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from tensei import config                      # noqa: E402
from tensei.brain import Brain                 # noqa: E402
from tensei.memory import Memory               # noqa: E402
from tensei.transmoe import TransMoE           # noqa: E402

TM_PATH = config.BRAINS / "tmoe.npz"
TM_VOCAB = config.BRAINS / "tmoe_vocab.json"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--samples", type=int, default=100000)
    ap.add_argument("--epochs", type=int, default=1)
    ap.add_argument("--batch", type=int, default=32)
    ap.add_argument("--lr", type=float, default=3e-4)
    ap.add_argument("--dim", type=int, default=320)
    ap.add_argument("--ctx", type=int, default=8)
    ap.add_argument("--blocks", type=int, default=2)
    ap.add_argument("--heads", type=int, default=2)
    ap.add_argument("--experts", type=int, default=4)
    ap.add_argument("--ffn", type=int, default=640)
    ap.add_argument("--vocab", type=int, default=9000)
    ap.add_argument("--init", action="store_true", help="resume from saved weights")
    ap.add_argument("--time-budget", type=float, default=None)
    a = ap.parse_args()

    t0 = time.time()
    mem = Memory()
    brain = Brain(mem)
    texts = brain._lm_texts()
    print("[tmoe] corpus: %d texts, %.1f chars (%.1fs)"
          % (len(texts), sum(len(t) for t in texts), time.time() - t0), flush=True)

    m = TransMoE(dim=a.dim, ctx=a.ctx, blocks=a.blocks, heads=a.heads,
                 experts=a.experts, ffn=a.ffn, vocab_cap=a.vocab)
    if a.init and os.path.exists(TM_PATH):
        if m.load(str(TM_PATH), str(TM_VOCAB)):
            print("[tmoe] resumed: %d params, vocab %d" % (m.param_count(), m.V),
                  flush=True)
    met = m.train(texts, epochs=a.epochs, lr=a.lr, batch=a.batch,
                  max_samples=a.samples,
                  log=lambda s: print(" [tmoe]", s, flush=True),
                  time_budget=a.time_budget)
    if met.get("error"):
        print("[tmoe] ERROR:", met)
        return 1
    m.save(str(TM_PATH), str(TM_VOCAB))
    print("[tmoe] saved %s (%.1f MB)" % (TM_PATH,
          os.path.getsize(TM_PATH) / 1048576.0), flush=True)
    print("[tmoe] metrics:", met)

    # quick qualitative sample so the trainer log shows real generation
    for prompt in ("the capital of france is", "a python program that"):
        try:
            print("[tmoe] sample %r -> %r" % (prompt, m.generate(prompt, max_tokens=12)))
        except Exception as e:
            print("[tmoe] sample failed:", e)
    mem.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
