import os
import json
import tempfile
import pytest
from worker.clean import clean_data

def test_clean_pipeline():
    with tempfile.TemporaryDirectory() as tmpdir:
        shard_dir = os.path.join(tmpdir, "shards")
        out_dir = os.path.join(tmpdir, "out")
        os.makedirs(shard_dir)

        # Shard 0 with good record and invalid JSON record
        shard0_path = os.path.join(shard_dir, "shard-0.jsonl")
        with open(shard0_path, "w", encoding="utf-8") as f:
            f.write(json.dumps({
                "id": "C0001",
                "text": "set an alarm for seven am",
                "teacher_raw": '{"intent": "alarm_set", "date": null, "time": "seven am", "place": null}'
            }) + "\n")
            f.write(json.dumps({
                "id": "C0003",
                "text": "bad json command",
                "teacher_raw": 'broken json {'
            }) + "\n")

        # Shard 1 with duplicate command text and invalid intent
        shard1_path = os.path.join(shard_dir, "shard-1.jsonl")
        with open(shard1_path, "w", encoding="utf-8") as f:
            f.write(json.dumps({
                "id": "C0002",
                "text": "set an alarm for seven am",  # Duplicate of C0001
                "teacher_raw": '{"intent": "alarm_set", "date": null, "time": "seven am", "place": null}'
            }) + "\n")
            f.write(json.dumps({
                "id": "C0004",
                "text": "some invalid intent",
                "teacher_raw": '{"intent": "invalid_intent_xyz", "date": null, "time": null, "place": null}'
            }) + "\n")

        stats = clean_data(shard_dir=shard_dir, out_dir=out_dir, print_report=False)
        assert stats["input"] == 4
        assert stats["a"] == 1  # 1 broken JSON
        assert stats["c"] == 1  # 1 invalid intent
        assert stats["duplicates"] == 1  # 1 duplicate command
        assert stats["kept"] == 1  # 1 kept (C0001)
        assert os.path.exists(os.path.join(out_dir, "train.jsonl"))
        assert os.path.exists(os.path.join(out_dir, "train.sha256"))

