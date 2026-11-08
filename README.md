# Cloud Computing (CS3081) Mini Project
## Knowledge Distillation and Deployment of a Lightweight Command-Parsing Language Model on a Local Cloud

**Student Name:** Jigar Kumar  
**Roll Number:** 230103022  
**Instructor:** Michael Salam  
**GitHub Repository:** [https://github.com/jigarkumar23/cloud-assistant-kd](https://github.com/jigarkumar23/cloud-assistant-kd)  
**Final Submission Commit Tag:** `final`  

---

## 1. Project Overview

This project implements an end-to-end cloud computing workflow for a lightweight voice-assistant command parser:
1. **Teacher Model Inference & Parallel Sharding:** Sequence-level knowledge distillation using Ollama with `phi3.5` (Phi-3.5-mini-instruct, 3.8B parameters) running parallel worker shards across `data/commands_pool.jsonl`.
2. **Data Cleaning Pipeline:** Filtering invalid JSON, key mismatches, hallucinated slots, and duplicate utterances with SHA-256 verification into `datasets/v1/train.jsonl`.
3. **Student Distillation:** Fine-tuning `EleutherAI/pythia-70m` on CPU using PyTorch and Hugging Face Transformers.
4. **Containerized Inference Service:** Production FastAPI microservice running under 1 CPU / 1 GiB constraints with S3 dynamic weight retrieval, strict JSON schema validation, and fault-injection hooks.
5. **Local Cloud Orchestration:** Kubernetes deployment on k3d with SeaweedFS object storage, Traefik Ingress routing, liveness/readiness probes, and Horizontal Pod Autoscaling (HPA).
6. **Network Engineering:** Subnet allocation on CIDR block `10.20.0.0/16` and stateless NACL simulation with 100% verification.
7. **CI/CD & Reliability:** GitHub Actions pipeline featuring Flake8 linting, unit tests, Gitleaks secret scanning, release asset model evaluation, and an automated quality gate (`score.py --min-validity 95`).

---

## 2. Repository Structure

```
├── .github/workflows/ci.yml    # CI/CD workflow (lint, unit tests, secret scan, quality gate)
├── cluster/
│   ├── k3d.yaml                # k3d cluster specification with port mappings
│   ├── seaweedfs.yaml          # SeaweedFS object storage manifests (namespace data)
│   ├── app.yaml                # App Deployment, Service, Ingress, HPA, Secret (namespace app)
│   └── pipeline.yaml           # Parallel worker pipeline jobs (namespace pipeline)
├── data/
│   ├── commands_pool.jsonl     # 3,000 raw SLURP command utterances
│   ├── validation.jsonl        # 100 labelled benchmark records
│   ├── schema.json             # Four-key JSON schema & intent definitions
│   └── rate_card.json          # Billing card for cost estimation
├── network/
│   ├── subnets.md              # Subnet allocation table & stateless NACL reasoning
│   ├── nacl.json               # Public subnet NACL ruleset
│   └── packets_sample.jsonl    # Sample network test packets
├── prompts/
│   └── teacher_prompt.txt      # Fixed system prompt for teacher distillation
├── report/
│   └── report.pdf              # Comprehensive project report (max 8 pages)
├── results/
│   ├── teacher_validation.json # Teacher model score report
│   ├── teacher_predictions.jsonl # Teacher raw outputs on validation set
│   ├── untrained_validation.json # Untrained Pythia-70M score report (0% quality gate demo)
│   ├── untrained_predictions.jsonl # Untrained model predictions
│   ├── student_validation.json # Fine-tuned student score report
│   ├── student_predictions.jsonl # Student predictions
│   ├── loadtest_stats.csv      # Locust load testing latency & throughput metrics
│   └── loadtest_headers.json   # Locust replica and version header distribution
├── service/
│   ├── app.py                  # FastAPI inference web service
│   ├── Dockerfile              # Minimal container image (< 2 GB, CPU-only wheels)
│   └── requirements.txt        # Pinned production dependencies
├── tests/
│   ├── test_service.py         # Unit tests for schema validation & API behavior
│   ├── test_nacl.py            # Unit tests for stateless NACL rule evaluation
│   └── test_clean.py           # Unit tests for data cleaning & deduplication
├── tools/
│   ├── score.py                # Official scoring script
│   ├── nacl_sim.py             # Stateless NACL rule simulator
│   └── locustfile.py           # Locust load testing suite
├── training/
│   ├── config.yaml             # Reproducible hyperparameters & library versions
│   ├── train.py                # Model distillation script
│   └── loss.csv                # Training loss recorded per epoch
├── worker/
│   ├── worker.py               # Parallel sharded teacher labelling worker
│   └── clean.py                # Dataset validator, cleaner & SHA-256 generator
├── 230103022.pdf               # Handwritten reflection notes (scanned, 3 pages)
├── AI_USE.md                   # AI tool usage and verification disclosure
├── Makefile                    # System lifecycle automation (up, down, train, test)
└── README.md                   # This project guide
```

---

## 3. Quick Start: Build, Deploy, Test & Teardown

### Prerequisites
- Python 3.11+
- Docker Engine / Docker Desktop
- k3d (v5.0+) and kubectl
- Ollama (running locally with `phi3.5` model pulled)

### 1. Build and Deploy Full Cloud Environment
Deploy the entire local Kubernetes cloud infrastructure from a fresh clone in a single command:
```bash
make up
```
This automatically:
1. Creates the k3d cluster `mini-cloud` with Traefik Ingress on port `8080` and S3 object storage on port `8333`.
2. Deploys SeaweedFS in namespace `data`.
3. Creates Kubernetes secrets and deploys the containerized inference service with 2 replicas in namespace `app`.
4. Exposes `/parse` through the Ingress controller.

### 2. Run Student Distillation Training
To train the student model on CPU using configuration from `training/config.yaml`:
```bash
# Run training on the full cleaned dataset:
make train

# Run verification test on first 50 records only:
make train SUBSET=50
```
This generates `training/loss.csv` and outputs model weights and tokenizer to `models/v1/` with checksum `models/v1/model.sha256`.

### 3. Run Automated Unit Tests
Run the test suite covering service validation, NACL logic, and dataset cleaning:
```bash
make test
```

### 4. Execute Performance Load Testing
Run the official Locust benchmark against the ingress:
```bash
locust -f tools/locustfile.py --headless --users 4 --spawn-rate 4 --run-time 2m --host http://localhost:8080 --csv results/loadtest
```

### 5. Shutdown and Teardown
To cleanly terminate and delete the local Kubernetes cluster:
```bash
make down
```

---

## 4. GitHub Release Assets & Model Artifacts

Model weights are strictly decoupled from the Git repository. The trained model files and checksums are published as assets on GitHub Release `v1.0.0`:
- `pytorch_model.bin` / `model.safetensors`
- `config.json`
- `tokenizer.json`
- `tokenizer_config.json`
- `special_tokens_map.json`
- `model.sha256`

Checksum verification:
```bash
sha256sum -c models/v1/model.sha256
```

