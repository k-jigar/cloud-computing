# AI Usage Disclosure (AI_USE.md)

**Student Name:** Jigar Kumar  
**Roll Number:** 230103022  
**Course:** Cloud Computing (CS3081) Mini Project  

---

## 1. Overview of AI Tools Utilized

In accordance with the project guidelines ("You'll be using AI and no one can stop you. But do use it with your eyes wide open"), artificial intelligence tools were utilized in a disciplined, transparent, and verified manner throughout this project.

The primary AI tools used:
1. **Google Antigravity (Advanced Agentic Assistant):**
   - Used for project architecture scaffolding, test-driven validation, script development, and technical report drafting.
2. **Ollama with Phi-3.5-mini-instruct (3.8B parameters):**
   - Used strictly as the mandated teacher model for sequence-level knowledge distillation on the SLURP command dataset.
3. **EleutherAI Pythia-70M (70M parameters):**
   - Used as the student model trained via sequence-level distillation on CPU hardware.

---

## 2. Tasks and Specific AI Contributions

| Project Task | AI Tool Used | Purpose / Scope | Verification & Validation Methodology |
| :--- | :--- | :--- | :--- |
| **Task 1: Object Storage & Teacher Labelling** | Ollama (`phi3.5:latest`) | Teacher inference on `commands_pool.jsonl` | Output filtered through `worker/clean.py` enforcing strict JSON schema, intent enums, slot substring checks, and SHA-256 verification. |
| **Task 2: Student Model Training** | Pythia-70M & PyTorch | Sequence-level knowledge distillation target | Evaluated independently with `tools/score.py` against `data/validation.jsonl` to calculate exact JSON validity and full-frame accuracy. |
| **Task 3: Containerized Inference Service** | Antigravity AI Assistant | FastAPI service boilerplate and fault injection handler | Validated with unit test suite (`pytest`) and live HTTP requests testing `/parse`, `/healthz`, `/readyz`, and `FAULT_INJECT=1`. |
| **Task 4: Kubernetes Deployment & Scaling** | Antigravity AI Assistant | Manifest templating (Deployment, Service, Traefik Ingress, HPA) | Checked syntax against Kubernetes v1.30 schema, validated with dry-run and k3d integration tests. |
| **Task 5: Subnetting & Stateless NACLs** | Antigravity AI Assistant | CIDR math calculation and NACL JSON ruleset definition | Rules mathematically verified from first principles and tested against sample packets using `tools/nacl_sim.py --check` (100% pass). |
| **Task 6: CI/CD Pipeline & Reproducibility** | Antigravity AI Assistant | GitHub Actions YAML workflow design | Tested with `pytest`, secret scanning with Gitleaks, and verified that untrained model deliberately fails the 95% quality gate. |
| **Task 7: Benchmarking, Cost & Review** | Locust & Antigravity Assistant | Load test execution and analytical cost estimation | Step-by-step arithmetic verified against `data/rate_card.json` formulas and Locust metrics. |

---

## 3. Human Verification and Quality Control Process

All code and outputs generated or assisted by AI were subjected to rigorous independent verification:
1. **Static Analysis & Linting:** Code was checked using `flake8` to prevent syntax bugs, undefined variables, or formatting defects.
2. **Automated Unit & Integration Testing:** 6 unit tests across service validation, NACL logic, and dataset cleaning were executed via `pytest`, achieving 100% pass rate.
3. **Deterministic Evaluation:** Model accuracy was verified using the official benchmark tool `tools/score.py` rather than subjective inspection.
4. **Security Auditing:** Gitleaks was configured to guarantee zero exposed API keys, tokens, or credentials in Git history.
5. **Empirical Measurement:** All performance numbers (latency, RPS, memory, cold start) represent real measured metrics rather than fabricated estimations.

