"""turbovec air-gapped RAG workload — runs INSIDE ns-sandbox under default-deny egress.

This is the pure-local capability the turbovec sandbox exposes. It builds a turbovec index over
DETERMINISTIC seeded vectors (no Ollama, no network, no clock) and self-queries it, printing a
machine-parseable verdict line. Run inside the OpenShell sandbox by containment_rag_probe.py; if it
returns recall_at1=1.0 while egress is default-denied, the source's "nothing leaves the machine" claim
is a machine fact, not prose.

Honest boundary (Slop #18): synthetic seeded vectors — NOT Ollama embeddings. A real embedded corpus is
declined-pool for v1 (keeps this gate deterministic + offline). See absorption-form.md.

Determinism (DDR-031): fixed seed, fixed shapes, zero clock reads → identical output every run.
"""
from __future__ import annotations

import sys


def run(d: int = 64, n: int = 2000, k: int = 5, bit_width: int = 4, seed: int = 0) -> float:
    """Build a turbovec index over seeded vectors, self-query, return recall@1 of the self-query."""
    import numpy as np
    from turbovec import TurboQuantIndex

    rng = np.random.default_rng(seed)
    vecs = rng.standard_normal((n, d)).astype("float32")
    idx = TurboQuantIndex(dim=d, bit_width=bit_width)
    idx.add(vecs)
    scores, ids = idx.search(vecs[:k], k=1)
    # search returns top-1 per query; normalize shape to a flat list of top-1 ids.
    rows = ids.tolist() if hasattr(ids, "tolist") else list(ids)
    top1 = [int(r[0]) if isinstance(r, (list, tuple)) else int(r) for r in rows]
    hits = sum(1 for i, t in enumerate(top1) if t == i)
    return hits / float(k)


def main() -> int:
    try:
        recall = run()
    except Exception as e:  # fail-loud: never a silent green
        import traceback

        traceback.print_exc()
        print(f"RAG_FAIL {type(e).__name__} {str(e)[:160]}")
        return 2
    print(f"RAG_OK recall_at1={recall:.1f} n=2000 dim=64 bit=4")
    return 0 if recall == 1.0 else 3


if __name__ == "__main__":
    raise SystemExit(main())
