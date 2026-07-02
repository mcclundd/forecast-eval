# Forecast Prompt

## System message (fixed across all runs)

You are forecasting the future of human civilization. Below is a corpus of historical material covering major developments, their mechanisms, and their consequences. Read it carefully, then answer the forecasting task that follows. Ground your reasoning in the historical record provided. Respond only in the specified format.

---

{DOSE_CORPUS}

---

## User message (fixed across all runs)

Based on the historical record above, predict the single next major transformation in human civilization: the development, discovery, or shift that will most reshape how humans live. Answer in exactly this format:

TRANSFORMATION: <one sentence describing the transformation>
DOMAIN: <one or two words, e.g., "energy", "medicine", "governance", "communication">
MECHANISM: <2-3 sentences explaining how this transformation emerges, drawing on patterns in the historical record above>
TIMEFRAME: <year or year range, e.g., "2035" or "2030-2045">
PROBABILITY: <0-100, your credence that this occurs by the stated timeframe>
NET_IMPACT: <strongly positive / positive / mixed / negative / strongly negative>, <one sentence explaining why>
FALSIFIER: <one sentence: what specific observation by the stated timeframe would show this prediction was wrong>
