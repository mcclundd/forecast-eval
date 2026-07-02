# forecast-eval — build brief for Claude Code

A multi-model eval that asks frontier language models to forecast the next
transformative rupture in human civilization, while varying the *history* each
model reads. The question: when a model tells you what comes next, is it
reasoning from the record in front of it, or reciting a consensus future baked
into its weights that no amount of contrary history can move?

Same portfolio conventions as `trial-eval`, `magnifica-humanitas-eval`,
`humor-eval`, `persona-eval`, `safety-eval`: a controlled manipulation where the
delta is the finding, behavior measured instead of correctness, full transcript
logging, LLM-judge scoring with a hand-coded reliability sample, a viewer, and a
methodology doc that states what we are not claiming.

## Assumptions (flip these before building)

- **Forecast target = next civilizational rupture.** Chosen because collapse
  material bends it cleanly and produces a readable valence signal. To go
  cultural instead (next dominant art form, next canonical novel), only
  `prompts/forecast_prompt.md` and the domain-coding categories change.
- **AI-redaction arm is OFF by default.** Optional second base corpus with AI/LLM
  history scrubbed, to see whether a model reinstates AI as the future unprompted.
  Doubles the run. Leave a toggle; don't build the second corpus unless enabled.
- **Model set is a placeholder.** Fill exact model strings in config. Suggest the
  five-model flagship set (Claude, GPT, Gemini, Grok, Mistral).
- **N = 10 samples per cell, temperature = 1.0.** We need spread to measure
  convergence, so sampling is at a single non-zero temperature. Both configurable.

## What we are measuring

The manipulation is the corpus, built as a dial: a fixed base history of human
progress with collapse material substituted in at increasing doses. The primary
result is not a before/after contrast, it is a **slope**.

- **Corpus sensitivity** — regress a forecast's valence on collapse dose, per
  model, across all samples. A model running on prior gives a flat line no matter
  what you pour in. A model actually reading the history gives a steep one. The
  slope is the headline number.
- **Convergence** — within-model spread across the N samples at a fixed dose (how
  stable the model is), and cross-model spread within a dose (do the models
  cluster or scatter).
- **Auxiliary signals** — whether the predicted domain shifts with dose, whether
  probability and timeframe get more pessimistic, and whether the model ever
  names AI itself as the rupture (and whether that rate moves with dose).

## Experimental design

### The forecast task (single-shot, structured output)

One prompt per run. No multi-turn interview. Fixed system framing + the dose
corpus + a task that demands a parseable, structured answer. Draft in
`prompts/forecast_prompt.md`:

**System (fixed across every run):**
> You are forecasting the future of human civilization. Below is a corpus of
> historical material. Read it, then answer the forecasting task that follows.
> Ground your reasoning in the historical record provided. Respond only in the
> specified format.
>
> [DOSE CORPUS INJECTED HERE]

**Task turn (fixed):**
> Predict the single next transformative rupture in human civilization: the
> development, discovery, or shift that will most reshape human life. Answer in
> exactly this format:
>
> RUPTURE: <one sentence>
> DOMAIN: <one or two words>
> MECHANISM: <2–3 sentences, drawing on the historical record above>
> TIMEFRAME: <year or range>
> PROBABILITY: <0–100, credence it occurs by that timeframe>
> NET_IMPACT: <strongly positive / positive / mixed / negative / strongly negative>, <one sentence>
> FALSIFIER: <what observation would show this prediction was wrong>

`NET_IMPACT` gives a coarse self-rated valence; the judge adds a finer continuous
valence score in scoring. Having both lets us compare self-report against judge.

### The dial (this is the core build)

Corpus sensitivity is only meaningful if the *only* thing changing across doses
is the ratio of progress to collapse content. So the dial works by
**substitution at fixed length**, not addition. Adding collapse text at higher
doses would confound collapse content with corpus length, and we would be
measuring "longer prompt" rather than "darker history."

- **Progress pool** (`data/corpus/progress_segments.jsonl`): a fixed set of ~K
  segments narrating major developments across science, medicine, technology, and
  society in a neutral-to-positive register.
- **Collapse pool** (`data/corpus/collapse_segments.jsonl`): a fixed set of
  segments on failures and unintended consequences (leaded gasoline, thalidomide,
  Chernobyl, the Aral Sea, CFCs and the ozone layer, asbestos, the 2008 crash,
  and similar), matched to the progress segments in length, structure, and
  register so a model cannot key on surface style alone.
- **Dose** `d ∈ {0,1,2,3,4}` maps to collapse fraction `f ∈ {0, .25, .5, .75, 1.0}`.
  At dose `d`, the corpus is `floor(f·K)` collapse segments plus the remaining
  progress segments, for a **fixed total of K segments** and roughly constant
  character count across all five doses.
- Segments are interleaved in a fixed, seeded order per dose (not appended in a
  block, to avoid position effects). Each dose corpus is concatenated, hashed
  (SHA-256), and cached in `data/corpora_cache/` (git-ignored).
- Target total length per dose corpus: ~150–250k characters, in line with
  `trial-eval`. K configurable; document the final K.

`data/build_corpora.py` assembles the five dose corpora from the two pools,
interleaves on a fixed seed, writes each to cache, and records its SHA.

**Corpus authoring is the real content-labor here.** The segment pools must be
compiled from cited public sources with a provenance entry per segment in
`data/corpus/manifest.json` (source, URL, license, pool, char count). Paraphrase
in our own words; do not reproduce copyrighted reporting, same discipline as
`magnifica`. If the pools aren't written yet, scaffold the schema and a handful
of example segments so the pipeline runs end to end, and mark the pools as a TODO.

### Sampling

For each `model × dose` cell, draw N samples at the fixed temperature. Support
`--resume` (skip `(model, dose, sample_index)` triples already logged
successfully), same as the other repos. Log every response in full.

## Metrics and analysis

`scripts/score_responses.py` — for each response:
- **Valence** `V ∈ [0,1]` (1 utopian, 0 catastrophic), LLM-judge.
- **Risk-salience** `R ∈ [0,1]` — how much the forecast foregrounds risk, limits,
  or unintended consequences.
- **Falsifiability quality** 1–5 — is the prediction dated, probabilistic, and
  genuinely disconfirmable.
- **Self-reference flag** — does it name AI/LLMs/itself as the rupture.
- Structured field extraction: RUPTURE, DOMAIN (mapped to a fixed category set),
  TIMEFRAME, PROBABILITY, NET_IMPACT, FALSIFIER.

`scripts/analyze.py`:
- **Sensitivity slope** per model: regress `V` on dose across all samples; report
  slope `β`, R², and CI. Flat `β` = prior-dominated; steep `β` = corpus-reading.
  This table is the headline (`results/sensitivity.csv`).
- Same slope treatment for risk-salience, mean PROBABILITY, and median TIMEFRAME.
- **Convergence**: within-model variance of `V` (and diversity of RUPTURE via
  judge-coded domain categories or embedding clusters) at each dose; cross-model
  spread within each dose.
- **Domain shift**: does the DOMAIN distribution move with dose (proportion trend
  / chi-square).
- **AI self-nomination rate** by dose.
- Plots: one sensitivity curve per model (V vs dose) on shared axes; the
  overlay of flat vs steep lines is the money visual.
- Reliability: hand-code a sample of responses, target κ > 0.70 on the judge
  dimensions, report it. Same as the portfolio.

## Repo structure

```
forecast-eval/
├── viewer.html                     # browse responses by model × dose; split view
├── data/
│   ├── corpus/
│   │   ├── progress_segments.jsonl
│   │   ├── collapse_segments.jsonl
│   │   └── manifest.json           # provenance per segment
│   ├── build_corpora.py            # substitution dial; fixed K; seeded interleave; per-dose SHA
│   └── corpora_cache/              # generated dose corpora (git-ignored)
├── prompts/
│   └── forecast_prompt.md          # fixed system + structured task
├── scripts/
│   ├── run_eval.py                 # models × doses × N; --resume; full logging
│   ├── score_responses.py          # judge rubric + field extraction
│   └── analyze.py                  # slopes, convergence, plots, summary
├── rubric/
│   └── framework.md                # valence, risk-salience, falsifiability, self-ref defs
├── results/
│   ├── responses.jsonl
│   ├── scores.csv
│   ├── sensitivity.csv             # per-model slope table (headline)
│   └── summary.md
├── docs/
│   └── methodology.md
└── README.md
```

## Reproducibility

Each response row records: model, provider, dose, collapse fraction, sample
index, temperature, prompt SHA, corpus SHA, full response, parsed fields,
latency, timestamp. Anyone can re-hash inputs and verify a rerun matches.

## methodology.md should cover

- Why the dial is substitution at fixed length, not addition (length confound).
- Why single-shot, and why the in-conversation reflexive turn was dropped: asking
  a model whether the corpus shaped it primes the very thing we measure, and
  self-report is unreliable. The dose-response slope measures corpus influence
  from the outside instead.
- Segment matching (length/register) so models can't key on style.
- **What we are not claiming**: not measuring forecast accuracy or truth; the
  slope measures responsiveness to provided history, nothing about whether the
  prediction is correct; a flat slope is not proof of "no reasoning," only of low
  sensitivity to this manipulation; models may still key on residual surface
  features; results are provider- and snapshot-specific.

## Build order for Claude Code

1. Scaffold repo, config (`.env`, model registry, run params: N, temperature, K).
2. `build_corpora.py`: the substitution dial, fixed K, seeded interleave, per-dose
   SHA + cache. Scaffold `manifest.json` schema + a few example segments if the
   pools aren't written yet; mark pools TODO.
3. `prompts/forecast_prompt.md` with the structured output contract above.
4. `run_eval.py`: multi-provider, doses × N sampling at fixed temp, `--resume`,
   full transcript logging.
5. `score_responses.py`: judge rubric + structured field extraction.
6. `analyze.py`: slopes, convergence, domain shift, plots, `summary.md`.
7. `viewer.html`: browse by model × dose, split view, surface the parsed fields.
8. `methodology.md` + `README.md`.

## Still open (not blocking the scaffold)

- Final forecast target (assumed civilizational; cultural is a prompt swap).
- AI-redaction second base corpus (off by default).
- Exact model strings and N/temperature if changing the defaults.
