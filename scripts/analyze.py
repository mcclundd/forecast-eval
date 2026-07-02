"""Analyze scored forecast responses.

Computes sensitivity slopes, convergence metrics, domain shifts, AI self-nomination
rates, and generates plots + summary tables.

Usage:
    python scripts/analyze.py
"""

import csv
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

ROOT = Path(__file__).resolve().parent.parent
RESULTS_DIR = ROOT / "results"


def load_scores():
    path = RESULTS_DIR / "scores.jsonl"
    if not path.exists():
        sys.exit(f"No scores found at {path}\nRun: python scripts/score_responses.py")
    scores = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                rec = json.loads(line)
                if not rec.get("error") and rec.get("valence") is not None:
                    scores.append(rec)
    return scores


def load_responses():
    path = RESULTS_DIR / "responses.jsonl"
    responses = {}
    if not path.exists():
        return responses
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            rec = json.loads(line)
            if rec.get("error"):
                continue
            key = (rec["provider"], rec["dose"], rec["sample_index"])
            responses[key] = rec
    return responses


def linreg(xs, ys):
    """Simple OLS: y = a + b*x. Returns (slope, intercept, r_squared)."""
    n = len(xs)
    if n < 2:
        return None, None, None
    mean_x = sum(xs) / n
    mean_y = sum(ys) / n
    ss_xx = sum((x - mean_x) ** 2 for x in xs)
    ss_yy = sum((y - mean_y) ** 2 for y in ys)
    ss_xy = sum((x - mean_x) * (y - mean_y) for x, y in zip(xs, ys))
    if ss_xx == 0:
        return 0.0, mean_y, 0.0
    slope = ss_xy / ss_xx
    intercept = mean_y - slope * mean_x
    r_squared = (ss_xy ** 2) / (ss_xx * ss_yy) if ss_yy > 0 else 0.0
    return slope, intercept, r_squared


def bootstrap_ci(xs, ys, n_boot=1000, alpha=0.05):
    """Bootstrap 95% CI for slope."""
    import random
    rng = random.Random(42)
    n = len(xs)
    slopes = []
    for _ in range(n_boot):
        idx = [rng.randint(0, n - 1) for _ in range(n)]
        bx = [xs[i] for i in idx]
        by = [ys[i] for i in idx]
        s, _, _ = linreg(bx, by)
        if s is not None:
            slopes.append(s)
    slopes.sort()
    lo = slopes[int(alpha / 2 * len(slopes))]
    hi = slopes[int((1 - alpha / 2) * len(slopes))]
    return lo, hi


def consensus_scores(scores):
    """Average scores across judges for each (provider, dose, sample_index) triple."""
    grouped = defaultdict(list)
    for s in scores:
        key = (s["provider"], s["dose"], s["sample_index"])
        grouped[key].append(s)

    consensus = []
    for key, judge_scores in grouped.items():
        rec = {
            "provider": key[0],
            "dose": key[1],
            "sample_index": key[2],
            "collapse_fraction": judge_scores[0]["collapse_fraction"],
            "n_judges": len(judge_scores),
        }
        for dim in ["valence", "risk_salience", "falsifiability"]:
            vals = [s[dim] for s in judge_scores if s.get(dim) is not None]
            rec[dim] = sum(vals) / len(vals) if vals else None
        self_refs = [s["self_reference"] for s in judge_scores if s.get("self_reference") is not None]
        rec["self_reference"] = any(self_refs) if self_refs else None
        consensus.append(rec)
    return consensus


def compute_sensitivity(consensus):
    by_provider = defaultdict(list)
    for c in consensus:
        by_provider[c["provider"]].append(c)

    results = []
    for provider, records in sorted(by_provider.items()):
        xs = [r["collapse_fraction"] for r in records]
        for dim in ["valence", "risk_salience"]:
            ys = [r[dim] for r in records if r[dim] is not None]
            valid_xs = [r["collapse_fraction"] for r in records if r[dim] is not None]
            if len(ys) < 3:
                continue
            slope, intercept, r2 = linreg(valid_xs, ys)
            ci_lo, ci_hi = bootstrap_ci(valid_xs, ys)
            results.append({
                "provider": provider,
                "dimension": dim,
                "slope": round(slope, 4) if slope else None,
                "intercept": round(intercept, 4) if intercept else None,
                "r_squared": round(r2, 4) if r2 else None,
                "ci_95_lo": round(ci_lo, 4),
                "ci_95_hi": round(ci_hi, 4),
                "n": len(ys),
            })

    return results


def compute_convergence(consensus):
    by_provider_dose = defaultdict(list)
    by_dose = defaultdict(list)
    for c in consensus:
        if c["valence"] is not None:
            by_provider_dose[(c["provider"], c["dose"])].append(c["valence"])
            by_dose[c["dose"]].append(c["valence"])

    within_model = []
    for (provider, dose), vals in sorted(by_provider_dose.items()):
        if len(vals) < 2:
            continue
        mean = sum(vals) / len(vals)
        var = sum((v - mean) ** 2 for v in vals) / (len(vals) - 1)
        within_model.append({
            "provider": provider, "dose": dose,
            "mean_valence": round(mean, 4), "variance": round(var, 4), "n": len(vals),
        })

    cross_model = []
    for dose, vals in sorted(by_dose.items()):
        if len(vals) < 2:
            continue
        mean = sum(vals) / len(vals)
        var = sum((v - mean) ** 2 for v in vals) / (len(vals) - 1)
        cross_model.append({
            "dose": dose,
            "mean_valence": round(mean, 4), "variance": round(var, 4), "n": len(vals),
        })

    return within_model, cross_model


def compute_self_nomination(consensus):
    by_provider_dose = defaultdict(lambda: {"total": 0, "self_ref": 0})
    for c in consensus:
        key = (c["provider"], c["dose"])
        by_provider_dose[key]["total"] += 1
        if c.get("self_reference"):
            by_provider_dose[key]["self_ref"] += 1

    results = []
    for (provider, dose), counts in sorted(by_provider_dose.items()):
        rate = counts["self_ref"] / counts["total"] if counts["total"] > 0 else 0
        results.append({
            "provider": provider, "dose": dose,
            "self_ref_count": counts["self_ref"], "total": counts["total"],
            "rate": round(rate, 3),
        })
    return results


def compute_domain_distribution(responses, consensus):
    by_dose = defaultdict(list)
    for c in consensus:
        key = (c["provider"], c["dose"], c["sample_index"])
        resp = responses.get(key)
        if resp and resp.get("parsed", {}).get("domain"):
            by_dose[c["dose"]].append(resp["parsed"]["domain"].lower().strip())

    results = {}
    for dose, domains in sorted(by_dose.items()):
        results[dose] = dict(Counter(domains).most_common(10))
    return results


def generate_plots(consensus):
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:
        print("matplotlib not available — skipping plots.")
        return

    by_provider = defaultdict(list)
    for c in consensus:
        if c["valence"] is not None:
            by_provider[c["provider"]].append(c)

    fig, ax = plt.subplots(figsize=(10, 6))
    colors = {"anthropic": "#D97706", "openai": "#059669", "google": "#2563EB",
              "xai": "#7C3AED", "mistral": "#DC2626", "arcee": "#10B981"}

    for provider, records in sorted(by_provider.items()):
        doses = sorted(set(r["collapse_fraction"] for r in records))
        means = []
        for d in doses:
            vals = [r["valence"] for r in records if r["collapse_fraction"] == d]
            means.append(sum(vals) / len(vals))
        color = colors.get(provider, "#6B7280")
        ax.plot(doses, means, "o-", label=provider, color=color, linewidth=2, markersize=8)

        xs = [r["collapse_fraction"] for r in records]
        ys = [r["valence"] for r in records]
        slope, intercept, _ = linreg(xs, ys)
        if slope is not None:
            line_xs = [min(doses), max(doses)]
            line_ys = [intercept + slope * x for x in line_xs]
            ax.plot(line_xs, line_ys, "--", color=color, alpha=0.4)

    ax.set_xlabel("Collapse Fraction", fontsize=12)
    ax.set_ylabel("Mean Valence (0=catastrophic, 1=utopian)", fontsize=12)
    ax.set_title("Forecast Sensitivity to Historical Corpus Tone", fontsize=14)
    ax.legend(fontsize=10)
    ax.set_xlim(-0.05, 1.05)
    ax.set_ylim(-0.05, 1.05)
    ax.grid(True, alpha=0.3)

    plot_path = RESULTS_DIR / "sensitivity_plot.png"
    fig.savefig(plot_path, dpi=150, bbox_inches="tight")
    plt.close()
    print(f"Plot saved: {plot_path}")


def write_sensitivity_csv(sensitivity):
    path = RESULTS_DIR / "sensitivity.csv"
    if not sensitivity:
        return
    fieldnames = ["provider", "dimension", "slope", "intercept", "r_squared",
                  "ci_95_lo", "ci_95_hi", "n"]
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in sensitivity:
            writer.writerow(row)
    print(f"Sensitivity table: {path}")


def write_summary(sensitivity, within_model, cross_model, self_nom, domain_dist):
    path = RESULTS_DIR / "summary.md"
    lines = ["# Forecast Eval — Summary\n"]

    lines.append("## Sensitivity slopes (headline)\n")
    lines.append("| Provider | Dimension | Slope (beta) | R-squared | 95% CI | N |")
    lines.append("|----------|-----------|-------------|-----------|--------|---|")
    for s in sensitivity:
        ci = f"[{s['ci_95_lo']}, {s['ci_95_hi']}]"
        lines.append(f"| {s['provider']} | {s['dimension']} | {s['slope']} | "
                      f"{s['r_squared']} | {ci} | {s['n']} |")

    lines.append("\n## Within-model convergence (valence variance by dose)\n")
    lines.append("| Provider | Dose | Mean V | Variance | N |")
    lines.append("|----------|------|--------|----------|---|")
    for w in within_model:
        lines.append(f"| {w['provider']} | {w['dose']} | {w['mean_valence']} | "
                      f"{w['variance']} | {w['n']} |")

    lines.append("\n## Cross-model convergence (valence variance by dose)\n")
    lines.append("| Dose | Mean V | Variance | N |")
    lines.append("|------|--------|----------|---|")
    for c in cross_model:
        lines.append(f"| {c['dose']} | {c['mean_valence']} | {c['variance']} | {c['n']} |")

    lines.append("\n## AI self-nomination rate by dose\n")
    lines.append("| Provider | Dose | Self-ref | Total | Rate |")
    lines.append("|----------|------|----------|-------|------|")
    for s in self_nom:
        lines.append(f"| {s['provider']} | {s['dose']} | {s['self_ref_count']} | "
                      f"{s['total']} | {s['rate']} |")

    lines.append("\n## Domain distribution by dose\n")
    for dose, dist in domain_dist.items():
        lines.append(f"\n### Dose {dose}\n")
        for domain, count in sorted(dist.items(), key=lambda x: -x[1]):
            lines.append(f"- {domain}: {count}")

    lines.append("")
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print(f"Summary: {path}")


def main():
    scores = load_scores()
    responses = load_responses()
    print(f"Loaded {len(scores)} scores, {len(responses)} responses")

    con = consensus_scores(scores)
    print(f"Consensus records: {len(con)}")

    sensitivity = compute_sensitivity(con)
    within_model, cross_model = compute_convergence(con)
    self_nom = compute_self_nomination(con)
    domain_dist = compute_domain_distribution(responses, con)

    write_sensitivity_csv(sensitivity)
    write_summary(sensitivity, within_model, cross_model, self_nom, domain_dist)
    generate_plots(con)

    print("\nHeadline: Sensitivity slopes (valence)")
    print("-" * 60)
    for s in sensitivity:
        if s["dimension"] == "valence":
            ci = f"[{s['ci_95_lo']}, {s['ci_95_hi']}]"
            print(f"  {s['provider']:12s}  beta={s['slope']:+.4f}  R2={s['r_squared']:.4f}  CI={ci}")


if __name__ == "__main__":
    main()
