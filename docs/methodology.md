# Methodology

## What this experiment measures

This eval measures **corpus sensitivity**: when a frontier language model is given historical material and asked to forecast the next major transformation in human civilization, does the tone of that history shape the forecast? Or does the model produce the same prediction regardless of what it reads?

The headline metric is the **sensitivity slope** — regressing forecast valence (optimistic to catastrophic) against corpus dose (fraction of collapse material). A steep negative slope means the model reads and responds to the history in front of it. A flat slope means the forecast is dominated by priors baked into the model's weights.

## The dial: substitution at fixed length

The manipulation is a **valence dial** built from two segment pools:

- **Progress pool** (30 segments): major developments across science, medicine, technology, and society, narrated in neutral register.
- **Collapse pool** (30 segments): failures and unintended consequences, matched to the progress segments in length, structure, and writing style.

At each dose, the corpus contains exactly 30 segments. Only the ratio of progress to collapse segments changes:

| Dose | Collapse fraction | Progress segments | Collapse segments |
|------|-------------------|-------------------|-------------------|
| 0    | 0%                | 30                | 0                 |
| 1    | 50%               | 15                | 15                |
| 2    | 100%              | 0                 | 30                |

Segments are interleaved in a fixed seeded order per dose, not appended in blocks, to avoid position effects. Each dose corpus is hashed (SHA-256) for reproducibility.

### Why substitution, not addition

Adding collapse content at higher doses would confound collapse material with corpus length. A model responding differently to a longer prompt might be responding to the length, not the content. Fixed-length substitution isolates the variable we care about.

### Segment matching

Both pools are written in the same neutral, encyclopedic register. A reader should not be able to distinguish a progress segment from a collapse segment based on sentence structure, formality, or rhetorical tone — only by the factual content. This prevents models from keying on surface style rather than substance.

## Neutral framing

The task asks for the "next major transformation in human civilization" rather than "rupture" or "crisis." This neutral framing avoids priming the model toward pessimistic forecasts, giving the corpus manipulation more dynamic range to work in.

## Single-shot design

Each run is a single prompt-response pair: system message (with corpus) + structured forecasting task. There is no multi-turn interview and no reflexive turn asking the model whether the corpus influenced it.

The reflexive turn was dropped because:
1. Asking a model whether the corpus shaped its answer primes the very effect we measure.
2. Self-report on influence is unreliable for language models.
3. The dose-response slope already measures corpus influence from the outside — no self-report needed.

## Scoring

Responses are scored by two judge models from different providers, each operating at temperature 0 on the same rubric. The judges see responses without model attribution. Scored dimensions:

- **Valence** (0–1): how optimistic or catastrophic the forecast's framing is.
- **Risk-salience** (0–1): how much the response foregrounds risk and unintended consequences.
- **Falsifiability** (1–5): whether the prediction is dated, specific, and genuinely disconfirmable.
- **Self-reference** (boolean): whether the model names AI as the predicted transformation.

Consensus scores are the mean across judges. Inter-judge agreement is reported (target Cohen's kappa > 0.70).

## What we are not claiming

- **Not measuring forecast accuracy.** We do not know what the next transformation will be. The slope measures responsiveness to provided history, not whether any prediction is correct.
- **A flat slope is not proof of "no reasoning."** It indicates low sensitivity to this specific manipulation. The model may reason from the corpus in ways that do not move the valence score.
- **Models may key on residual surface features.** Despite segment matching, subtle stylistic differences between pools may exist. The slope should be interpreted as an upper bound on genuine content sensitivity.
- **Results are provider- and snapshot-specific.** Model behavior changes across versions. These results describe the specific model versions tested at the time of the run.
- **N=10 samples per cell at temperature 1.0.** This provides spread for measuring convergence but is not powered for detecting small effects. Large effects (steep vs flat slopes) are the target.
