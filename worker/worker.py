#!/usr/bin/env python3
"""Worker for Task 1: Sharded parallel teacher labelling."""
import json
import os
import sys
import time
import urllib.request
import urllib.error

def main():
    shard_index = int(os.environ.get("SHARD_INDEX", 0))
    shard_count = int(os.environ.get("SHARD_COUNT", 1))
    input_file = os.environ.get("INPUT_FILE", "data/commands_pool.jsonl")
    output_dir = os.environ.get("OUTPUT_DIR", "datasets/teacher")
    prompt_file = os.environ.get("PROMPT_FILE", "prompts/teacher_prompt.txt")
    ollama_host = os.environ.get("OLLAMA_HOST", "http://127.0.0.1:11434").rstrip("/")
    model_name = os.environ.get("TEACHER_MODEL", "phi3.5")

    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(output_dir, f"shard-{shard_index}.jsonl")

    if not os.path.exists(prompt_file):
        sys.exit(f"Prompt file not found: {prompt_file}")

    with open(prompt_file, "r", encoding="utf-8") as f:
        system_prompt = f.read()

    # Read already processed ids if output file exists (supports graceful resumption)
    existing_ids = set()
    if os.path.exists(output_path):
        with open(output_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        record = json.loads(line)
                        if "id" in record:
                            existing_ids.add(record["id"])
                    except Exception:
                        pass
        print(f"Shard {shard_index}: Found {len(existing_ids)} previously processed commands.")

    # Read input file and filter commands for this shard
    shard_commands = []
    with open(input_file, "r", encoding="utf-8") as f:
        for line_num, line in enumerate(f):
            line = line.strip()
            if not line:
                continue
            if line_num % shard_count == shard_index:
                cmd_obj = json.loads(line)
                shard_commands.append((line_num, cmd_obj))

    total = len(shard_commands)
    print(f"Worker shard {shard_index}/{shard_count}: Assigned {total} total commands.")

    api_url = f"{ollama_host}/api/chat"
    processed_count = len(existing_ids)

    with open(output_path, "a", encoding="utf-8") as out_f:
        for idx, (line_num, cmd_obj) in enumerate(shard_commands):
            cmd_id = cmd_obj["id"]
            text = cmd_obj["text"]

            if cmd_id in existing_ids:
                continue

            payload = json.dumps({
                "model": model_name,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": "Command: " + text}
                ],
                "stream": False,
                "options": {
                    "temperature": 0.0,
                    "seed": 42,
                    "num_predict": 55,
                    "stop": ["\n\n", "Command:"]
                }
            }).encode("utf-8")

            raw_reply = ""
            for attempt in range(3):
                try:
                    req = urllib.request.Request(
                        api_url,
                        data=payload,
                        headers={"Content-Type": "application/json"}
                    )
                    with urllib.request.urlopen(req, timeout=120) as resp:
                        res_data = json.loads(resp.read().decode("utf-8"))
                        raw_reply = res_data.get("message", {}).get("content", "").strip()
                        break
                except Exception as e:
                    print(f"Shard {shard_index} error on id {cmd_id} (attempt {attempt+1}): {e}")
                    time.sleep(2)

            out_record = {
                "id": cmd_id,
                "text": text,
                "teacher_raw": raw_reply
            }
            out_f.write(json.dumps(out_record, ensure_ascii=False) + "\n")
            out_f.flush()

            processed_count += 1
            if processed_count % 50 == 0 or processed_count == total:
                print(f"Shard {shard_index}: Processed {processed_count}/{total} commands.")

    print(f"Shard {shard_index}: Finished writing {output_path}")

if __name__ == "__main__":
    main()
