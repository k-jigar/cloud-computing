#!/usr/bin/env python3
"""Training script for Task 2: Fine-tune EleutherAI/pythia-70m on teacher outputs."""
import argparse
import csv
import hashlib
import json
import os
import random
import sys
import numpy as np
import torch
from torch.utils.data import DataLoader, Dataset
from transformers import AutoModelForCausalLM, AutoTokenizer
import yaml

class CommandParserDataset(Dataset):
    def __init__(self, records, tokenizer, max_length=128):
        self.samples = []
        for r in records:
            cmd_text = r.get("text", "")
            if "teacher_raw" in r:
                reply = r["teacher_raw"]
            elif "intent" in r:
                reply = json.dumps({
                    "intent": r["intent"],
                    "date": r.get("date"),
                    "time": r.get("time"),
                    "place": r.get("place")
                })
            else:
                continue

            full_text = f"Command: {cmd_text}\nJSON: {reply}"
            enc = tokenizer(
                full_text,
                max_length=max_length,
                padding="max_length",
                truncation=True,
                return_tensors="pt"
            )
            input_ids = enc["input_ids"].squeeze(0)
            attention_mask = enc["attention_mask"].squeeze(0)

            # For causal LM, labels are input_ids with padding tokens set to -100
            labels = input_ids.clone()
            labels[attention_mask == 0] = -100

            self.samples.append({
                "input_ids": input_ids,
                "attention_mask": attention_mask,
                "labels": labels
            })

    def __len__(self):
        return len(self.samples)

    def __getitem__(self, idx):
        return self.samples[idx]

def compute_model_sha256(model_dir: str, output_file: str):
    """Compute sha256 checksums of all model files in directory."""
    files = sorted(os.listdir(model_dir))
    entries = []
    combined_hasher = hashlib.sha256()

    for fname in files:
        fpath = os.path.join(model_dir, fname)
        if os.path.isfile(fpath) and not fname.endswith(".sha256"):
            hasher = hashlib.sha256()
            with open(fpath, "rb") as f:
                while chunk := f.read(65536):
                    hasher.update(chunk)
                    combined_hasher.update(chunk)
            fhash = hasher.hexdigest()
            entries.append(f"{fhash}  {fname}")

    with open(output_file, "w", encoding="utf-8") as out:
        for entry in entries:
            out.write(entry + "\n")
        # Also write the overall digest
        out.write(f"# overall_sha256: {combined_hasher.hexdigest()}\n")

    print(f"Computed model SHA-256 for {len(entries)} files -> {output_file}")
    return combined_hasher.hexdigest()

def main():
    parser = argparse.ArgumentParser(description="Fine-tune pythia-70m on teacher labels.")
    parser.add_argument("--config", default="training/config.yaml", help="Path to config.yaml")
    parser.add_argument("--data", default="datasets/v1/train.jsonl", help="Path to train.jsonl")
    parser.add_argument("--subset", type=int, default=None, help="Train on first N records only")
    parser.add_argument("--out-dir", default="models/v1", help="Output directory for model and tokenizer")
    parser.add_argument("--loss-csv", default="training/loss.csv", help="Path to save loss.csv")
    parser.add_argument("--device", default="cpu", help="Device (cpu or cuda)")
    args = parser.parse_args()

    # Read config.yaml
    with open(args.config, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)

    seed = int(config.get("seed", 42))
    lr = float(config.get("learning_rate", 5e-4))
    batch_size = int(config.get("batch_size", 8))
    num_epochs = int(config.get("num_epochs", 3))
    max_seq_length = int(config.get("max_seq_length", 128))

    # Support SUBSET from environment variable if not specified on CLI
    env_subset = os.environ.get("SUBSET")
    if args.subset is None and env_subset:
        try:
            args.subset = int(env_subset)
        except ValueError:
            pass

    # Fix random seed in code
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)

    print("=" * 60)
    print("TRAINING CONFIGURATION")
    print(f"Seed:               {seed}")
    print(f"Learning Rate:      {lr}")
    print(f"Batch Size:         {batch_size}")
    print(f"Epochs:             {num_epochs}")
    print(f"Max Seq Length:     {max_seq_length}")
    print(f"Output Directory:   {args.out_dir}")
    print(f"Subset Limit:       {args.subset}")
    print(f"Device:             {args.device}")
    print("=" * 60)

    # Load records
    if not os.path.exists(args.data):
        sys.exit(f"Training data not found: {args.data}")

    records = []
    with open(args.data, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                records.append(json.loads(line))

    if args.subset is not None:
        records = records[:args.subset]
    else:
        # Use no more than 1,500 training examples as per requirement
        records = records[:1500]

    print(f"Loaded {len(records)} training examples.")

    model_name = "EleutherAI/pythia-70m"
    print(f"Loading {model_name}...")
    tokenizer = AutoTokenizer.from_pretrained(model_name)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token

    model = AutoModelForCausalLM.from_pretrained(model_name)
    model.to(args.device)

    dataset = CommandParserDataset(records, tokenizer, max_length=max_seq_length)
    dataloader = DataLoader(dataset, batch_size=batch_size, shuffle=True)

    optimizer = torch.optim.AdamW(model.parameters(), lr=lr)

    epoch_losses = []
    model.train()

    for epoch in range(1, num_epochs + 1):
        total_loss = 0.0
        num_batches = 0
        for batch in dataloader:
            input_ids = batch["input_ids"].to(args.device)
            attention_mask = batch["attention_mask"].to(args.device)
            labels = batch["labels"].to(args.device)

            optimizer.zero_grad()
            outputs = model(
                input_ids=input_ids,
                attention_mask=attention_mask,
                labels=labels
            )
            loss = outputs.loss
            loss.backward()
            optimizer.step()

            total_loss += loss.item()
            num_batches += 1

        avg_loss = total_loss / max(1, num_batches)
        epoch_losses.append((epoch, avg_loss))
        print(f"Epoch {epoch}/{num_epochs} - Training Loss: {avg_loss:.4f}")

    # Save loss.csv
    os.makedirs(os.path.dirname(args.loss_csv) or ".", exist_ok=True)
    with open(args.loss_csv, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["epoch", "loss"])
        for ep, loss_val in epoch_losses:
            writer.writerow([ep, f"{loss_val:.4f}"])
    print(f"Saved epoch losses to {args.loss_csv}")

    # Save model and tokenizer
    os.makedirs(args.out_dir, exist_ok=True)
    model.save_pretrained(args.out_dir)
    tokenizer.save_pretrained(args.out_dir)
    print(f"Saved model and tokenizer to {args.out_dir}")

    # Compute SHA-256
    sha_path = os.path.join(args.out_dir, "model.sha256")
    compute_model_sha256(args.out_dir, sha_path)
    print("Training run completed successfully.")

if __name__ == "__main__":
    main()

