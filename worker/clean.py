#!/usr/bin/env python3
"""Data cleaning script for Task 1: Clean raw teacher shards into datasets/v1/train.jsonl."""
import argparse
import glob
import hashlib
import json
import os
import sys

ALLOWED_INTENTS = {
    "alarm_set",
    "alarm_query",
    "calendar_set",
    "calendar_query",
    "calendar_remove",
    "weather_query",
    "datetime_query",
    "recommendation_events"
}

EXPECTED_KEYS = {"intent", "date", "time", "place"}

def parse_args():
    parser = argparse.ArgumentParser(description="Clean teacher shard outputs into train.jsonl.")
    parser.add_argument("--shard-dir", default="datasets/teacher", help="Directory containing shard-*.jsonl files")
    parser.add_argument("--out-dir", default="datasets/v1", help="Output directory for train.jsonl and train.sha256")
    parser.add_argument("--report", action="store_true", help="Print detailed counts breakdown")
    return parser.parse_args()

def clean_data(shard_dir="datasets/teacher", out_dir="datasets/v1", print_report=True):
    shard_pattern = os.path.join(shard_dir, "shard-*.jsonl")
    shard_files = sorted(glob.glob(shard_pattern))
    if not shard_files:
        sys.exit(f"No shard files found matching pattern: {shard_pattern}")

    all_records = []
    seen_ids = set()

    for sf in shard_files:
        with open(sf, "r", encoding="utf-8") as f:
            for line_no, line in enumerate(f, 1):
                line = line.strip()
                if not line:
                    continue
                try:
                    record = json.loads(line)
                except Exception:
                    continue
                
                cmd_id = record.get("id")
                if not cmd_id:
                    continue
                if cmd_id in seen_ids:
                    print(f"Warning: duplicate ID {cmd_id} encountered across shard files!", file=sys.stderr)
                seen_ids.add(cmd_id)
                all_records.append(record)

    total_input = len(all_records)
    # Sort all records strictly by ID order (e.g. C0001, C0002...)
    all_records.sort(key=lambda r: r["id"])

    count_a = 0  # not valid JSON
    count_b = 0  # keys not exactly intent, date, time, place
    count_c = 0  # intent not one of the eight
    count_d = 0  # slot value neither null nor text that appears in command
    count_dup = 0  # duplicate commands
    kept_records = []

    seen_command_texts = set()

    for r in all_records:
        cmd_id = r["id"]
        text = r.get("text", "")
        raw = r.get("teacher_raw", "").strip()

        # (a) Check if reply is valid JSON
        try:
            parsed = json.loads(raw)
        except Exception:
            count_a += 1
            continue

        # (b) Check if keys are exactly intent, date, time, place
        if not isinstance(parsed, dict) or set(parsed.keys()) != EXPECTED_KEYS:
            count_b += 1
            continue

        # Check types of slots
        types_valid = True
        for slot in ("date", "time", "place"):
            if parsed[slot] is not None and not isinstance(parsed[slot], str):
                types_valid = False
                break
        if not types_valid or not isinstance(parsed.get("intent"), str):
            count_b += 1
            continue

        # (c) Check if intent is one of the eight
        if parsed["intent"] not in ALLOWED_INTENTS:
            count_c += 1
            continue

        # (d) Check if slot values are null or appear in command
        cmd_norm = text.lower()
        slot_invalid = False
        for slot in ("date", "time", "place"):
            val = parsed[slot]
            if val is not None:
                val_norm = " ".join(val.lower().strip().split())
                if val_norm not in cmd_norm:
                    slot_invalid = True
                    break
        if slot_invalid:
            count_d += 1
            continue

        # (e) Duplicate commands (keep the one with smallest id)
        norm_text = " ".join(text.lower().strip().split())
        if norm_text in seen_command_texts:
            count_dup += 1
            continue
        seen_command_texts.add(norm_text)

        # Kept record
        canonical_json = json.dumps({
            "intent": parsed["intent"],
            "date": parsed["date"],
            "time": parsed["time"],
            "place": parsed["place"]
        }, ensure_ascii=False)

        kept_record = {
            "id": cmd_id,
            "text": text,
            "intent": parsed["intent"],
            "date": parsed["date"],
            "time": parsed["time"],
            "place": parsed["place"],
            "teacher_raw": canonical_json
        }
        kept_records.append(kept_record)

    count_kept = len(kept_records)
    sum_categories = count_a + count_b + count_c + count_d + count_dup + count_kept

    # Verify input = (a) + (b) + (c) + (d) + duplicates + kept
    assert total_input == sum_categories, f"Counts mismatch: {total_input} != {sum_categories}"

    # Write output files
    os.makedirs(out_dir, exist_ok=True)
    out_jsonl_path = os.path.join(out_dir, "train.jsonl")
    out_sha_path = os.path.join(out_dir, "train.sha256")

    hasher = hashlib.sha256()
    with open(out_jsonl_path, "w", encoding="utf-8", newline="\n") as out_f:
        for r in kept_records:
            line_str = json.dumps(r, ensure_ascii=False) + "\n"
            out_f.write(line_str)
            hasher.update(line_str.encode("utf-8"))

    sha256_hash = hasher.hexdigest()
    with open(out_sha_path, "w", encoding="utf-8") as sha_f:
        sha_f.write(f"{sha256_hash}  train.jsonl\n")

    if print_report:
        print("=" * 60)
        print("DATASET CLEANING REPORT (Task 1)")
        print("=" * 60)
        print(f"Total Input Records:        {total_input}")
        print(f"(a) Rejected (Invalid JSON): {count_a}")
        print(f"(b) Rejected (Wrong Keys):   {count_b}")
        print(f"(c) Rejected (Wrong Intent): {count_c}")
        print(f"(d) Rejected (Slot Error):   {count_d}")
        print(f"(e) Rejected (Duplicates):   {count_dup}")
        print(f"Kept Records:               {count_kept}")
        print("-" * 60)
        print(f"Verification: {count_a} + {count_b} + {count_c} + {count_d} + {count_dup} + {count_kept} = {sum_categories} (Input: {total_input})")
        print(f"Saved: {out_jsonl_path}")
        print(f"SHA-256 Checksum: {sha256_hash}")
        print(f"Saved: {out_sha_path}")
        print("=" * 60)

    return {
        "input": total_input,
        "a": count_a,
        "b": count_b,
        "c": count_c,
        "d": count_d,
        "duplicates": count_dup,
        "kept": count_kept,
        "sha256": sha256_hash
    }

if __name__ == "__main__":
    args = parse_args()
    clean_data(args.shard_dir, args.out_dir, True)

