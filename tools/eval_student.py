#!/usr/bin/env python3
"""Evaluate fine-tuned student model on validation.jsonl using score.py."""
import argparse
import json
import os
import subprocess
import sys
import torch
from transformers import AutoModelForCausalLM, AutoTokenizer

def main():
    parser = argparse.ArgumentParser(description="Evaluate student model on validation data.")
    parser.add_argument("--model-dir", default="models/v1", help="Path to student model directory")
    parser.add_argument("--gold", default="data/validation.jsonl", help="Path to validation.jsonl")
    parser.add_argument("--out-preds", default="results/student_predictions.jsonl", help="Predictions output file")
    parser.add_argument("--out-report", default="results/student_validation.json", help="Score report JSON output")
    parser.add_argument("--min-validity", type=float, default=None, help="Enforce min-validity gate")
    args = parser.parse_args()

    os.makedirs(os.path.dirname(args.out_preds) or ".", exist_ok=True)
    os.makedirs(os.path.dirname(args.out_report) or ".", exist_ok=True)

    print(f"Loading student model from {args.model_dir}...")
    tokenizer = AutoTokenizer.from_pretrained(args.model_dir)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token
    model = AutoModelForCausalLM.from_pretrained(args.model_dir)
    model.eval()

    gold_records = []
    with open(args.gold, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                gold_records.append(json.loads(line))

    print(f"Generating predictions for {len(gold_records)} validation commands...")
    predictions = []

    for idx, record in enumerate(gold_records, 1):
        cmd_id = record["id"]
        text = record["text"]
        prompt = f"Command: {text}\nJSON: "

        inputs = tokenizer(prompt, return_tensors="pt")
        with torch.no_grad():
            outputs = model.generate(
                **inputs,
                max_new_tokens=45,
                do_sample=False,
                pad_token_id=tokenizer.pad_token_id,
                eos_token_id=tokenizer.eos_token_id
            )

        full_text = tokenizer.decode(outputs[0], skip_special_tokens=True)
        generated = full_text[len(prompt):].strip()
        # Take the first line or closing bracket
        if "\n" in generated:
            generated = generated.splitlines()[0].strip()
        predictions.append({"id": cmd_id, "prediction": generated})

    with open(args.out_preds, "w", encoding="utf-8") as f:
        for p in predictions:
            f.write(json.dumps(p, ensure_ascii=False) + "\n")

    print(f"Saved student predictions to {args.out_preds}")

    # Run score.py
    cmd = [
        sys.executable,
        "tools/score.py",
        args.out_preds,
        args.gold,
        "--out",
        args.out_report
    ]
    if args.min_validity is not None:
        cmd.extend(["--min-validity", str(args.min_validity)])

    res = subprocess.run(cmd, capture_output=True, text=True)
    print("Student Evaluation Score:")
    print(res.stdout)
    if res.returncode != 0:
        print("Score evaluation failed with error:", res.stderr, file=sys.stderr)
        sys.exit(res.returncode)

if __name__ == "__main__":
    main()

