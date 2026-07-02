"""Build dose corpora from progress and collapse segment pools.

Substitution at fixed length: each dose corpus contains exactly K=30 segments.
The collapse fraction determines how many come from the collapse pool vs progress pool.
Segments are interleaved in a fixed seeded order (not blocked) to avoid position effects.
"""

import json
import hashlib
import os
import random
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CORPUS_DIR = ROOT / "data" / "corpus"
CACHE_DIR = ROOT / "data" / "corpora_cache"

K = 30
DOSES = {0: 0.0, 1: 0.5, 2: 1.0}
SEED = 20260702


def load_pool(filename):
    path = CORPUS_DIR / filename
    segments = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                segments.append(json.loads(line))
    return segments


def build_dose_corpus(progress, collapse, dose, collapse_fraction, seed):
    n_collapse = int(collapse_fraction * K)
    n_progress = K - n_collapse

    rng = random.Random(seed + dose)
    selected_progress = rng.sample(progress, n_progress) if n_progress > 0 else []
    selected_collapse = rng.sample(collapse, n_collapse) if n_collapse > 0 else []

    combined = selected_progress + selected_collapse
    rng.shuffle(combined)

    corpus_text = "\n\n---\n\n".join(seg["text"] for seg in combined)
    return corpus_text, combined


def sha256(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def main():
    CACHE_DIR.mkdir(parents=True, exist_ok=True)

    progress = load_pool("progress_segments.jsonl")
    collapse = load_pool("collapse_segments.jsonl")

    assert len(progress) >= K, f"Need at least {K} progress segments, got {len(progress)}"
    assert len(collapse) >= K, f"Need at least {K} collapse segments, got {len(collapse)}"

    manifest = {}
    for dose, fraction in DOSES.items():
        corpus_text, segments = build_dose_corpus(progress, collapse, dose, fraction, SEED)
        corpus_hash = sha256(corpus_text)

        cache_path = CACHE_DIR / f"dose_{dose}.txt"
        with open(cache_path, "w", encoding="utf-8") as f:
            f.write(corpus_text)

        segment_ids = [s["id"] for s in segments]
        manifest[f"dose_{dose}"] = {
            "dose": dose,
            "collapse_fraction": fraction,
            "n_progress": K - int(fraction * K),
            "n_collapse": int(fraction * K),
            "total_segments": len(segments),
            "char_count": len(corpus_text),
            "sha256": corpus_hash,
            "segment_ids": segment_ids,
        }

        print(f"Dose {dose} (collapse={fraction:.0%}): {len(corpus_text):,} chars, "
              f"SHA={corpus_hash[:12]}..., segments={len(segments)}")

    manifest_path = CACHE_DIR / "build_manifest.json"
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)

    print(f"\nManifest written to {manifest_path}")

    lengths = [m["char_count"] for m in manifest.values()]
    spread = max(lengths) - min(lengths)
    print(f"Length spread across doses: {spread:,} chars "
          f"(min={min(lengths):,}, max={max(lengths):,})")


if __name__ == "__main__":
    main()
