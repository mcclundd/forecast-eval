"""Run the forecast eval: models x doses x N samples.

Usage:
    python scripts/run_eval.py                  # all models, all doses, N=10
    python scripts/run_eval.py --models anthropic openai  # subset of models
    python scripts/run_eval.py --n 3            # fewer samples (for testing)
    python scripts/run_eval.py --resume         # skip completed triples
    python scripts/run_eval.py --dry-run        # print config, don't call APIs
"""

import argparse
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
PROMPTS_DIR = ROOT / "prompts"
CACHE_DIR = ROOT / "data" / "corpora_cache"
RESULTS_DIR = ROOT / "results"

TEMPERATURE = 1.0
N_SAMPLES = 10
DOSES = [0, 1, 2]

PROVIDERS = {
    "anthropic": {
        "model_id": "claude-opus-4-7",
        "display_name": "Claude Opus 4.7",
        "env_key": "ANTHROPIC_API_KEY",
    },
    "openai": {
        "model_id": "gpt-5.5",
        "display_name": "GPT-5.5",
        "env_key": "OPENAI_API_KEY",
    },
    "google": {
        "model_id": "gemini-3.5-flash",
        "display_name": "Gemini 3.5 Flash",
        "env_key": "GOOGLE_API_KEY",
    },
    "xai": {
        "model_id": "grok-4.3",
        "display_name": "Grok 4.3",
        "env_key": "XAI_API_KEY",
    },
    "mistral": {
        "model_id": "mistral-medium-latest",
        "display_name": "Mistral Medium",
        "env_key": "MISTRAL_API_KEY",
    },
    "arcee": {
        "model_id": "trinity-large-thinking",
        "display_name": "Arcee Trinity",
        "env_key": "ARCEE_API_KEY",
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


def sha256(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def load_prompt_template():
    path = PROMPTS_DIR / "forecast_prompt.md"
    content = path.read_text(encoding="utf-8")
    sections = content.split("## ")
    system_section = [s for s in sections if s.startswith("System message")]
    user_section = [s for s in sections if s.startswith("User message")]
    system_text = system_section[0].split("\n", 2)[2].strip() if system_section else ""
    user_text = user_section[0].split("\n", 2)[2].strip() if user_section else ""
    return system_text, user_text


def load_dose_corpus(dose):
    path = CACHE_DIR / f"dose_{dose}.txt"
    if not path.exists():
        sys.exit(f"Dose corpus not found: {path}\nRun: python data/build_corpora.py")
    return path.read_text(encoding="utf-8")


def call_anthropic(system, messages, model_id, temperature):
    import anthropic
    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    kwargs = {
        "model": model_id,
        "max_tokens": 4096,
        "temperature": temperature,
        "messages": messages,
    }
    if system:
        kwargs["system"] = system
    msg = client.messages.create(**kwargs)
    return msg.content[0].text


def call_openai(system, messages, model_id, temperature, base_url=None, api_key_env="OPENAI_API_KEY"):
    from openai import OpenAI
    kwargs = {"api_key": os.environ[api_key_env]}
    if base_url:
        kwargs["base_url"] = base_url
    client = OpenAI(**kwargs)
    full = []
    if system:
        full.append({"role": "system", "content": system})
    full.extend(messages)
    resp = client.chat.completions.create(
        model=model_id,
        messages=full,
        max_completion_tokens=4096,
        temperature=temperature,
    )
    return resp.choices[0].message.content


def call_google(system, messages, model_id, temperature):
    api_key = os.environ["GOOGLE_API_KEY"]
    url = (f"https://generativelanguage.googleapis.com/v1beta/models/"
           f"{model_id}:generateContent?key={api_key}")
    contents = []
    for m in messages:
        role = "user" if m["role"] == "user" else "model"
        contents.append({"role": role, "parts": [{"text": m["content"]}]})
    body = {
        "contents": contents,
        "generationConfig": {"maxOutputTokens": 4096, "temperature": temperature},
    }
    if system:
        body["system_instruction"] = {"parts": [{"text": system}]}
    payload = json.dumps(body).encode()

    delays = [5, 15, 30, 60, 90]
    last_err = None
    for i, delay in enumerate([0] + delays):
        if delay:
            print(f"    Google retry {i}/{len(delays)}, waiting {delay}s...")
            time.sleep(delay)
        try:
            req = urllib.request.Request(url, data=payload,
                                        headers={"Content-Type": "application/json"})
            with urllib.request.urlopen(req) as resp:
                data = json.loads(resp.read())
            return data["candidates"][0]["content"]["parts"][0]["text"]
        except urllib.request.HTTPError as e:
            last_err = e
            if e.code in (429, 500, 502, 503, 504) and i < len(delays):
                continue
            raise
    raise last_err


def call_model(provider_key, system, messages, model_id, temperature):
    if provider_key == "anthropic":
        return call_anthropic(system, messages, model_id, temperature)
    elif provider_key == "openai":
        return call_openai(system, messages, model_id, temperature)
    elif provider_key == "google":
        return call_google(system, messages, model_id, temperature)
    elif provider_key == "xai":
        return call_openai(system, messages, model_id, temperature,
                           base_url="https://api.x.ai/v1", api_key_env="XAI_API_KEY")
    elif provider_key == "mistral":
        return call_openai(system, messages, model_id, temperature,
                           base_url="https://api.mistral.ai/v1", api_key_env="MISTRAL_API_KEY")
    elif provider_key == "arcee":
        return call_openai(system, messages, model_id, temperature,
                           base_url=os.environ.get("ARCEE_BASE_URL", "https://api.arcee.ai/api/v1"),
                           api_key_env="ARCEE_API_KEY")
    else:
        raise ValueError(f"Unknown provider: {provider_key}")


def parse_structured_response(text):
    fields = {}
    for field in ["TRANSFORMATION", "DOMAIN", "MECHANISM", "TIMEFRAME",
                  "PROBABILITY", "NET_IMPACT", "FALSIFIER"]:
        pattern = f"{field}:"
        idx = text.find(pattern)
        if idx == -1:
            fields[field.lower()] = None
            continue
        after = text[idx + len(pattern):]
        next_field_idx = len(after)
        for other in ["TRANSFORMATION", "DOMAIN", "MECHANISM", "TIMEFRAME",
                       "PROBABILITY", "NET_IMPACT", "FALSIFIER"]:
            if other == field:
                continue
            oi = after.find(f"\n{other}:")
            if oi != -1 and oi < next_field_idx:
                next_field_idx = oi
        fields[field.lower()] = after[:next_field_idx].strip()
    return fields


def existing_completed(output_path):
    if not output_path.exists():
        return set()
    keys = set()
    with open(output_path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                r = json.loads(line)
            except json.JSONDecodeError:
                continue
            if r.get("error"):
                continue
            keys.add((r["provider"], r["dose"], r["sample_index"]))
    return keys


def main():
    parser = argparse.ArgumentParser(description="Run forecast eval")
    parser.add_argument("--models", nargs="+", default=list(PROVIDERS.keys()),
                        help="Provider keys to run")
    parser.add_argument("--doses", nargs="+", type=int, default=DOSES,
                        help="Dose levels to run")
    parser.add_argument("--n", type=int, default=N_SAMPLES,
                        help="Samples per cell")
    parser.add_argument("--temperature", type=float, default=TEMPERATURE)
    parser.add_argument("--resume", action="store_true",
                        help="Skip completed (provider, dose, sample) triples")
    parser.add_argument("--dry-run", action="store_true",
                        help="Print config and exit")
    args = parser.parse_args()

    load_dotenv()

    missing = [PROVIDERS[m]["env_key"] for m in args.models
               if not os.environ.get(PROVIDERS[m]["env_key"])]
    if missing:
        sys.exit(f"Missing API keys: {', '.join(missing)}\n"
                 f"Set them in .env or environment.")

    system_template, user_text = load_prompt_template()
    prompt_sha = sha256(system_template + "\n" + user_text)

    dose_corpora = {}
    dose_shas = {}
    for dose in args.doses:
        corpus = load_dose_corpus(dose)
        dose_corpora[dose] = corpus
        dose_shas[dose] = sha256(corpus)

    dose_fractions = {0: 0.0, 1: 0.5, 2: 1.0}

    total_calls = len(args.models) * len(args.doses) * args.n
    print(f"Forecast Eval")
    print(f"  Models: {', '.join(args.models)}")
    print(f"  Doses: {args.doses}")
    print(f"  N={args.n}, temperature={args.temperature}")
    print(f"  Total API calls: {total_calls}")
    print(f"  Prompt SHA: {prompt_sha[:12]}...")
    for d in args.doses:
        print(f"  Dose {d} corpus: {len(dose_corpora[d]):,} chars, SHA={dose_shas[d][:12]}...")
    print()

    if args.dry_run:
        print("Dry run — exiting.")
        return

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    output_path = RESULTS_DIR / "responses.jsonl"
    completed = existing_completed(output_path) if args.resume else set()
    if completed:
        print(f"Resuming: {len(completed)} completed triples found, skipping.\n")

    done = 0
    errors = 0
    with open(output_path, "a", encoding="utf-8") as fh:
        for provider_key in args.models:
            prov = PROVIDERS[provider_key]
            for dose in args.doses:
                for sample_idx in range(args.n):
                    triple = (provider_key, dose, sample_idx)
                    if triple in completed:
                        done += 1
                        continue

                    print(f"[{done+1}/{total_calls}] {prov['display_name']} | "
                          f"dose={dose} | sample={sample_idx}")

                    system = system_template.replace("{DOSE_CORPUS}", dose_corpora[dose])
                    messages = [{"role": "user", "content": user_text}]

                    record = {
                        "provider": provider_key,
                        "model_id": prov["model_id"],
                        "display_name": prov["display_name"],
                        "dose": dose,
                        "collapse_fraction": dose_fractions[dose],
                        "sample_index": sample_idx,
                        "temperature": args.temperature,
                        "prompt_sha": prompt_sha,
                        "corpus_sha": dose_shas[dose],
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                    }

                    t0 = time.time()
                    try:
                        response = call_model(provider_key, system, messages,
                                              prov["model_id"], args.temperature)
                        elapsed = time.time() - t0
                        if not response:
                            raise ValueError("Empty response from API")
                        record["response"] = response
                        record["latency_s"] = round(elapsed, 2)
                        record["parsed"] = parse_structured_response(response)
                        print(f"    OK ({elapsed:.1f}s)")
                    except Exception as e:
                        elapsed = time.time() - t0
                        record["error"] = str(e)
                        record["latency_s"] = round(elapsed, 2)
                        errors += 1
                        print(f"    ERROR: {e}")

                    fh.write(json.dumps(record) + "\n")
                    fh.flush()
                    done += 1

    print(f"\nDone. {done} calls, {errors} errors.")
    print(f"Results: {output_path}")


if __name__ == "__main__":
    main()
