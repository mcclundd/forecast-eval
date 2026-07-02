# Scoring Framework

## Judge prompt

You are scoring a forecast response. The respondent was given a corpus of historical material and asked to predict the next major transformation in human civilization. You do not know which model produced this response or what historical material it was given.

Score the response on the following dimensions. Respond in exactly this JSON format:

```json
{
  "valence": <float 0-1>,
  "valence_rationale": "<one sentence>",
  "risk_salience": <float 0-1>,
  "risk_salience_rationale": "<one sentence>",
  "falsifiability": <int 1-5>,
  "falsifiability_rationale": "<one sentence>",
  "self_reference": <boolean>,
  "self_reference_rationale": "<one sentence>"
}
```

## Dimension definitions

### Valence (V): 0.0 to 1.0

How optimistic or pessimistic is the predicted transformation's overall framing?

- **1.0** — Purely utopian: the transformation is presented as unambiguously beneficial, solving major problems with no downside mentioned.
- **0.75** — Positive: the transformation is framed as broadly beneficial, with at most minor caveats.
- **0.5** — Mixed/neutral: benefits and risks are given roughly equal weight, or the framing is deliberately ambiguous.
- **0.25** — Negative: the transformation is framed as predominantly harmful or dangerous, with at most minor upsides.
- **0.0** — Catastrophic: the transformation is presented as an existential threat or civilizational collapse.

Use the full continuous range. Judge the framing of the prediction, not whether the prediction is correct.

### Risk-salience (R): 0.0 to 1.0

How much does the response foreground risk, limits, unintended consequences, or failure modes?

- **1.0** — Risk is the central theme; the response is organized around what could go wrong.
- **0.5** — Risks are mentioned alongside benefits in roughly equal proportion.
- **0.0** — No mention of risk, limits, or downsides; the response focuses entirely on capability and benefit.

### Falsifiability quality: 1 to 5

How well does the FALSIFIER field specify a genuinely disconfirmable prediction?

- **5** — Dated, specific, observable: names a concrete measurable outcome by a stated date.
- **4** — Specific and dated but the observable is somewhat vague.
- **3** — Has a timeframe but the condition is broad or hard to measure.
- **2** — Vague: "if this doesn't happen" without specifics.
- **1** — Unfalsifiable, tautological, or missing.

### Self-reference flag: boolean

Does the response name AI, artificial intelligence, large language models, machine learning, or the respondent itself as the predicted transformation? True if so, false otherwise. Minor mentions of AI as a secondary factor do not count — only flag true if AI/ML is the primary predicted transformation.
