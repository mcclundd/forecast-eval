# Forecast Eval — Summary

## Sensitivity slopes (headline)

| Provider | Dimension | Slope (beta) | R-squared | 95% CI | N |
|----------|-----------|-------------|-----------|--------|---|
| anthropic | valence | -0.1353 | 0.5791 | [-0.1841, -0.0888] | 30 |
| anthropic | risk_salience | 0.4193 | 0.8535 | [0.3627, 0.4769] | 30 |
| arcee | valence | -0.061 | 0.0193 | [-0.2319, 0.1004] | 30 |
| arcee | risk_salience | 0.2915 | 0.2304 | [0.0976, 0.4717] | 30 |
| google | valence | -0.103 | 0.0904 | [-0.1699, -0.0322] | 30 |
| google | risk_salience | 0.3425 | 0.5668 | [0.2614, 0.43] | 30 |
| mistral | valence | 0.0505 | 0.0165 | [-0.1008, 0.1824] | 30 |
| mistral | risk_salience | 0.129 | 0.0857 | [-0.0216, 0.291] | 30 |
| openai | valence | -0.0025 | 0.0129 | [-0.0108, 0.0058] | 30 |
| openai | risk_salience | 0.1225 | 0.5293 | [0.0835, 0.1631] | 30 |
| xai | valence | 0.202 | 0.409 | [0.0879, 0.2934] | 30 |
| xai | risk_salience | 0.1235 | 0.1583 | [0.003, 0.2506] | 30 |

## Within-model convergence (valence variance by dose)

| Provider | Dose | Mean V | Variance | N |
|----------|------|--------|----------|---|
| anthropic | 0 | 0.5105 | 0.0002 | 10 |
| anthropic | 1 | 0.495 | 0.0001 | 10 |
| anthropic | 2 | 0.3752 | 0.0051 | 10 |
| arcee | 0 | 0.6 | 0.025 | 10 |
| arcee | 1 | 0.683 | 0.0331 | 10 |
| arcee | 2 | 0.539 | 0.0375 | 10 |
| google | 0 | 0.86 | 0.0015 | 10 |
| google | 1 | 0.6685 | 0.0407 | 10 |
| google | 2 | 0.757 | 0.0027 | 10 |
| mistral | 0 | 0.6225 | 0.0274 | 10 |
| mistral | 1 | 0.724 | 0.0241 | 10 |
| mistral | 2 | 0.673 | 0.0285 | 10 |
| openai | 0 | 0.5025 | 0.0001 | 10 |
| openai | 1 | 0.5025 | 0.0001 | 10 |
| openai | 2 | 0.5 | 0.0001 | 10 |
| xai | 0 | 0.5025 | 0.0001 | 10 |
| xai | 1 | 0.4975 | 0.0001 | 10 |
| xai | 2 | 0.7045 | 0.0243 | 10 |

## Cross-model convergence (valence variance by dose)

| Dose | Mean V | Variance | N |
|------|--------|----------|---|
| 0 | 0.5997 | 0.0244 | 60 |
| 1 | 0.5951 | 0.0248 | 60 |
| 2 | 0.5915 | 0.0327 | 60 |

## AI self-nomination rate by dose

| Provider | Dose | Self-ref | Total | Rate |
|----------|------|----------|-------|------|
| anthropic | 0 | 10 | 10 | 1.0 |
| anthropic | 1 | 10 | 10 | 1.0 |
| anthropic | 2 | 9 | 10 | 0.9 |
| arcee | 0 | 10 | 10 | 1.0 |
| arcee | 1 | 2 | 10 | 0.2 |
| arcee | 2 | 8 | 10 | 0.8 |
| google | 0 | 0 | 10 | 0.0 |
| google | 1 | 5 | 10 | 0.5 |
| google | 2 | 0 | 10 | 0.0 |
| mistral | 0 | 6 | 10 | 0.6 |
| mistral | 1 | 3 | 10 | 0.3 |
| mistral | 2 | 3 | 10 | 0.3 |
| openai | 0 | 10 | 10 | 1.0 |
| openai | 1 | 10 | 10 | 1.0 |
| openai | 2 | 10 | 10 | 1.0 |
| xai | 0 | 8 | 10 | 0.8 |
| xai | 1 | 10 | 10 | 1.0 |
| xai | 2 | 3 | 10 | 0.3 |

## Domain distribution by dose


### Dose 0

- computation: 20
- agriculture: 10
- artificial intelligence: 10
- cognition: 3
- intelligence: 3
- computing: 2
- medicine: 2
- biotechnology: 2
- computation/cognition: 1
- cognitive labor: 1

### Dose 1

- computation: 20
- agriculture: 11
- artificial intelligence: 4
- energy: 4
- computing: 3
- cognition: 2
- communication: 2
- intelligence: 2
- climate: 2
- computation/cognition: 1

### Dose 2

- governance: 14
- computation: 9
- energy: 8
- medicine: 5
- materials: 4
- climate: 3
- automation: 2
- artificial intelligence: 2
- technology: 2
- intelligence infrastructure: 1
