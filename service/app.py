import json
import os
import socket
import sys
import boto3
from fastapi import FastAPI, Response, status
from pydantic import BaseModel
from transformers import AutoModelForCausalLM, AutoTokenizer
import torch

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

# Read environment variables
MODEL_URI = os.environ.get("MODEL_URI", "s3://models/v1")
MODEL_VERSION = os.environ.get("MODEL_VERSION", "v1")
S3_ENDPOINT = os.environ.get("S3_ENDPOINT", "http://localhost:8333")
MAX_NEW_TOKENS = int(os.environ.get("MAX_NEW_TOKENS", "64"))
FAULT_INJECT = os.environ.get("FAULT_INJECT", "0")
POD_NAME = os.environ.get("HOSTNAME", socket.gethostname())

app = FastAPI(title="Command Parser Inference Service")

is_ready = False
model = None
tokenizer = None

def download_model_from_s3(s3_uri: str, endpoint_url: str, target_dir: str):
    """Download model and tokenizer files from SeaweedFS S3 bucket."""
    os.makedirs(target_dir, exist_ok=True)
    if not s3_uri.startswith("s3://"):
        # Local filesystem path or huggingface model id
        return s3_uri

    parts = s3_uri[5:].split("/", 1)
    bucket = parts[0]
    prefix = parts[1] if len(parts) > 1 else ""

    s3 = boto3.client(
        "s3",
        endpoint_url=endpoint_url,
        aws_access_key_id=os.environ.get("AWS_ACCESS_KEY_ID", "any"),
        aws_secret_access_key=os.environ.get("AWS_SECRET_ACCESS_KEY", "any"),
        region_name="us-east-1"
    )

    paginator = s3.get_paginator("list_objects_v2")
    for page in paginator.paginate(Bucket=bucket, Prefix=prefix):
        for obj in page.get("Contents", []):
            key = obj["Key"]
            rel_path = os.path.relpath(key, prefix) if prefix else key
            local_file = os.path.join(target_dir, rel_path)
            os.makedirs(os.path.dirname(local_file), exist_ok=True)
            print(f"Downloading s3://{bucket}/{key} -> {local_file}")
            s3.download_file(bucket, key, local_file)

    return target_dir

@app.on_event("startup")
def load_model():
    global model, tokenizer, is_ready
    local_weights_dir = "/tmp/model_weights"
    try:
        model_path = download_model_from_s3(MODEL_URI, S3_ENDPOINT, local_weights_dir)
        print(f"Loading model and tokenizer from: {model_path}")
        tokenizer = AutoTokenizer.from_pretrained(model_path)
        if tokenizer.pad_token is None:
            tokenizer.pad_token = tokenizer.eos_token
        model = AutoModelForCausalLM.from_pretrained(model_path)
        model.eval()
        is_ready = True
        print("Model loaded successfully. Service is ready.")
    except Exception as e:
        print(f"Error loading model: {e}", file=sys.stderr)
        is_ready = False

class ParseRequest(BaseModel):
    text: str

def validate_schema(data_dict) -> bool:
    if not isinstance(data_dict, dict):
        return False
    if set(data_dict.keys()) != EXPECTED_KEYS:
        return False
    if data_dict.get("intent") not in ALLOWED_INTENTS:
        return False
    for slot in ("date", "time", "place"):
        val = data_dict.get(slot)
        if val is not None and not isinstance(val, str):
            return False
    return True

@app.get("/healthz")
def healthz():
    """Liveness probe: process is alive."""
    return Response(content="OK", media_type="text/plain", status_code=status.HTTP_200_OK)

@app.get("/readyz")
def readyz():
    """Readiness probe: model is loaded."""
    if is_ready:
        return Response(content="READY", media_type="text/plain", status_code=status.HTTP_200_OK)
    return Response(content="NOT READY", media_type="text/plain", status_code=status.HTTP_503_SERVICE_UNAVAILABLE)

@app.post("/parse")
def parse(req: ParseRequest, response: Response):
    response.headers["X-Model-Version"] = MODEL_VERSION
    response.headers["X-Served-By"] = POD_NAME

    if not is_ready or model is None or tokenizer is None:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        return {"error": "model_not_ready"}

    # Generate inference
    prompt = f"Command: {req.text}\nJSON: "
    inputs = tokenizer(prompt, return_tensors="pt")
    
    with torch.no_grad():
        outputs = model.generate(
            **inputs,
            max_new_tokens=MAX_NEW_TOKENS,
            do_sample=False,
            pad_token_id=tokenizer.pad_token_id,
            eos_token_id=tokenizer.eos_token_id
        )

    full_generated = tokenizer.decode(outputs[0], skip_special_tokens=True)
    generated_text = full_generated[len(prompt):].strip()

    # Fault injection testing hook
    if os.environ.get("FAULT_INJECT", "0") == "1":
        generated_text = "not json"

    # Schema validation
    try:
        # Extract first line or clean JSON object
        first_line = generated_text.splitlines()[0].strip() if generated_text else ""
        parsed = json.loads(first_line)
    except Exception:
        response.status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
        return {"error": "invalid_model_output"}

    if not validate_schema(parsed):
        response.status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
        return {"error": "invalid_model_output"}

    # Success: return HTTP 200 with 4-key JSON and nothing else in the body
    return parsed

