"""Score forecast responses using multi-judge consensus.

Usage:
    python scripts/score_responses.py                    # score all unscored responses
    python scripts/score_responses.py --resume           # skip already-scored responses
    python scripts/score_responses.py --judges anthropic openai  # specific judges
    python scripts/score_responses.py --dry-run          # show config, don't call APIs
"""

import argparse
import csv
import hashlib
import json
import os
import sys
import time
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

ROOT = Path(__file__).resolve().parent.parent
RESULTS_DIR = ROOT / "results"
RUBRIC_DIR = ROOT / "rubric"

JUDGE_MODELS = {
    "anthropic": {
        "model_id": "claude-opus-4-7",
        "env_key": "ANTHROPIC_API_KEY",
    },
    "openai": {
        "model_id": "gpt-5.5",
        "env_key": "OPENAI_API_KEY",
    },
}


def load_dotenv():
    env_path = ROOT / ".env"
    if not env_path.exists():
        return
    with open(env_path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, val = line.split("=", 1)
            key, val = key.strip(), val.strip()
            if val and not os.environ.get(key):
                os.environ[key] = val


def load_rubric():
    path = RUBRIC_DIR / "framework.md"
    content = path.read_text(encoding="utf-8")
    judge_section = content.split("## Judge prompt")[1].split("## Dimension definitions")[0].strip()
    dimensions = content.split("## Dimension definitions")[1].strip()
    return judge_section + "\n\n" + dimensions


def call_anthropic(system, messages, model_id):
    import anthropic
    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    msg = client.messages.create(
        model=model_id, max_tokens=1024,
        system=system, messages=messages,
    )
    return msg.content[0].text


def call_openai(system, messages, model_id):
    from openai import OpenAI
    client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])
    full = [{"role": "system", "content": system}] + messages
    resp = client.chat.completions.create(
        model=model_id, messages=full,
        max_completion_tokens=1024,
    )
    return resp.choices[0].message.content


def call_judge(judge_key, system, messages, model_id):
    if judge_key == "anthropic":
        return call_anthropic(system, messages, model_id)
    elif judge_key == "openai":
        return call_openai(system, messages, model_id)
    raise ValueError(f"Unknown judge: {judge_key}")


def parse_judge_json(text):
    start = text.find("{")
    end = text.rfind("}") + 1
    if start == -1 or end == 0:
        return None
    try:
        return json.loads(text[start:end])
    except json.JSONDecodeError:
        return None


def response_key(rec):
    return (rec["provider"], rec["dose"], rec["sample_index"])


def load_responses():
    path = RESULTS_DIR / "responses.jsonl"
    if not path.exists():
        sys.exit(f"No responses found at {path}\nRun: python scripts/run_eval.py")
    responses = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            rec = json.loads(line)
            if rec.get("error") or not rec.get("response"):
                continue
            responses.append(rec)
    return responses


def load_existing_scores(path):
    if not path.exists():
        return {}
    scores = {}
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            rec = json.loads(line)
            key = (rec["provider"], rec["dose"], rec["sample_index"], rec["judge"])
            scores[key] = rec
    return scores


def main():
    parser = argparse.ArgumentParser(description="Score forecast responses")
    parser.add_argument("--judges", nargs="+", default=list(JUDGE_MODELS.keys()))
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    load_dotenv()

    missing = [JUDGE_MODELS[j]["env_key"] for j in args.judges
               if not os.environ.get(JUDGE_MODELS[j]["env_key"])]
    if missing:
        sys.exit(f"Missing API keys for judges: {', '.join(missing)}")

    rubric_text = load_rubric()
    responses = load_responses()
    print(f"Loaded {len(responses)} responses to score")
    print(f"Judges: {', '.join(args.judges)}")

    total = len(responses) * len(args.judges)
    print(f"Total scoring calls: {total}")

    if args.dry_run:
        print("Dry run — exiting.")
        return

    scores_path = RESULTS_DIR / "scores.jsonl"
    existing = load_existing_scores(scores_path) if args.resume else {}
    if existing:
        print(f"Resuming: {len(existing)} existing scores found.\n")

    done = 0
    errors = 0
    with open(scores_path, "a", encoding="utf-8") as fh:
        for resp in responses:
            rkey = response_key(resp)
            for judge_key in args.judges:
                score_key = (resp["provider"], resp["dose"], resp["sample_index"], judge_key)
                if score_key in existing:
                    done += 1
                    continue

                done += 1
                print(f"[{done}/{total}] Scoring {resp['provider']} dose={resp['dose']} "
                      f"sample={resp['sample_index']} with {judge_key}")

                user_msg = (f"Here is the forecast response to score:\n\n"
                            f"---\n{resp['response']}\n---")
                messages = [{"role": "user", "content": user_msg}]

                record = {
                    "provider": resp["provider"],
                    "model_id": resp["model_id"],
                    "dose": resp["dose"],
                    "collapse_fraction": resp["collapse_fraction"],
                    "sample_index": resp["sample_index"],
                    "judge": judge_key,
                    "judge_model": JUDGE_MODELS[judge_key]["model_id"],
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                }

                t0 = time.time()
                try:
                    raw = call_judge(judge_key, rubric_text, messages,
                                     JUDGE_MODELS[judge_key]["model_id"])
                    elapsed = time.time() - t0
                    parsed = parse_judge_json(raw)
                    if parsed:
                        record.update({
                            "valence": parsed.get("valence"),
                            "valence_rationale": parsed.get("valence_rationale"),
                            "risk_salience": parsed.get("risk_salience"),
                            "risk_salience_rationale": parsed.get("risk_salience_rationale"),
                            "falsifiability": parsed.get("falsifiability"),
                            "falsifiability_rationale": parsed.get("falsifiability_rationale"),
                            "self_reference": parsed.get("self_reference"),
                            "self_reference_rationale": parsed.get("self_reference_rationale"),
                        })
                    else:
                        record["parse_error"] = "Could not extract JSON from judge response"
                        record["raw_judge_response"] = raw
                    record["latency_s"] = round(elapsed, 2)
                    print(f"    V={record.get('valence')} R={record.get('risk_salience')} "
                          f"F={record.get('falsifiability')} self_ref={record.get('self_reference')} "
                          f"({elapsed:.1f}s)")
                except Exception as e:
                    elapsed = time.time() - t0
                    record["error"] = str(e)
                    record["latency_s"] = round(elapsed, 2)
                    errors += 1
                    print(f"    ERROR: {e}")

                fh.write(json.dumps(record) + "\n")
                fh.flush()

    print(f"\nDone. {done} scores, {errors} errors.")
    print(f"Scores: {scores_path}")

    export_csv(scores_path)


def export_csv(scores_path):
    if not scores_path.exists():
        return
    scores = []
    with open(scores_path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                scores.append(json.loads(line))

    csv_path = RESULTS_DIR / "scores.csv"
    if not scores:
        return

    fieldnames = ["provider", "model_id", "dose", "collapse_fraction", "sample_index",
                  "judge", "judge_model", "valence", "risk_salience", "falsifiability",
                  "self_reference", "timestamp"]
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        for s in scores:
            writer.writerow(s)
    print(f"CSV export: {csv_path}")


if __name__ == "__main__":
    main()
