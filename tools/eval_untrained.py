#!/usr/bin/env python3
"""Run original untrained Pythia-70M on validation.jsonl and evaluate with score.py."""
import json
import os
import sys
import subprocess
import torch
from transformers import AutoModelForCausalLM, AutoTokenizer

VALIDATION_FILE = "data/validation.jsonl"
PREDICTIONS_OUT = "results/untrained_predictions.jsonl"
SCORE_OUT = "results/untrained_validation.json"
MODEL_NAME = "EleutherAI/pythia-70m"

os.makedirs("results", exist_ok=True)

print(f"Loading untrained model {MODEL_NAME}...")
tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)
if tokenizer.pad_token is None:
    tokenizer.pad_token = tokenizer.eos_token
model = AutoModelForCausalLM.from_pretrained(MODEL_NAME)
model.eval()

gold_records = []
with open(VALIDATION_FILE, "r", encoding="utf-8") as f:
    for line in f:
        line = line.strip()
        if line:
            gold_records.append(json.loads(line))

print(f"Evaluating {len(gold_records)} validation commands on untrained model...")
predictions = []

for idx, record in enumerate(gold_records, 1):
    cmd_id = record["id"]
    text = record["text"]
    prompt = f"Command: {text}\nJSON: "
    
    inputs = tokenizer(prompt, return_tensors="pt")
    with torch.no_grad():
        outputs = model.generate(
            **inputs,
            max_new_tokens=40,
            do_sample=False,
            pad_token_id=tokenizer.pad_token_id,
            eos_token_id=tokenizer.eos_token_id
        )
    
    full_text = tokenizer.decode(outputs[0], skip_special_tokens=True)
    generated = full_text[len(prompt):].strip()
    predictions.append({"id": cmd_id, "prediction": generated})

with open(PREDICTIONS_OUT, "w", encoding="utf-8") as f:
    for p in predictions:
        f.write(json.dumps(p, ensure_ascii=False) + "\n")

print(f"Saved untrained predictions to {PREDICTIONS_OUT}")

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
print("Score output for untrained Pythia-70M:")
print(res.stdout)

