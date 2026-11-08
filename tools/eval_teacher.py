#!/usr/bin/env python3
"""Run teacher model (Phi-3.5 via Ollama) on validation.jsonl and evaluate with score.py."""
import json
import os
import sys
import time
import urllib.request
import subprocess

VALIDATION_FILE = "data/validation.jsonl"
PROMPT_FILE = "prompts/teacher_prompt.txt"
PREDICTIONS_OUT = "results/teacher_predictions.jsonl"
SCORE_OUT = "results/teacher_validation.json"
OLLAMA_URL = "http://127.0.0.1:11434/api/chat"

os.makedirs("results", exist_ok=True)

with open(PROMPT_FILE, "r", encoding="utf-8") as f:
    system_prompt = f.read()

gold_records = []
with open(VALIDATION_FILE, "r", encoding="utf-8") as f:
    for line in f:
        line = line.strip()
        if line:
            gold_records.append(json.loads(line))

print(f"Loaded {len(gold_records)} validation records.")

predictions = []
start_time = time.time()

for idx, record in enumerate(gold_records, 1):
    cmd_id = record["id"]
    text = record["text"]
    
    payload = json.dumps({
        "model": "phi3.5",
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": "Command: " + text}
        ],
        "stream": False,
        "options": {
            "temperature": 0.0,
            "seed": 42
        }
    }).encode("utf-8")

    req = urllib.request.Request(OLLAMA_URL, data=payload, headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            raw_reply = data.get("message", {}).get("content", "").strip()
    except Exception as e:
        print(f"Error querying Ollama for {cmd_id}: {e}")
        raw_reply = ""

    predictions.append({"id": cmd_id, "prediction": raw_reply})
    if idx % 10 == 0 or idx == len(gold_records):
        elapsed = time.time() - start_time
        print(f"[{idx}/{len(gold_records)}] ({elapsed:.1f}s) - Last ID: {cmd_id}")

with open(PREDICTIONS_OUT, "w", encoding="utf-8") as f:
    for p in predictions:
        f.write(json.dumps(p, ensure_ascii=False) + "\n")

print(f"Saved predictions to {PREDICTIONS_OUT}")

# Run score.py
cmd = [
    sys.executable,
    "tools/score.py",
    PREDICTIONS_OUT,
    VALIDATION_FILE,
    "--out",
    SCORE_OUT
]
res = subprocess.run(cmd, capture_output=True, text=True)
print("Score output:")
print(res.stdout)
if res.stderr:
    print("Score stderr:", res.stderr)

