#!/usr/bin/env python3
"""Package final assignment contents into strictly named <roll_number>.zip (230103022.zip).
Ensures all required files, directories, reports, reflection notes, and code levels are included,
while excluding large binary weights, virtual environments, and git metadata.
"""
import os
import zipfile

def package_submission(zip_filename="230103022.zip"):
    # Target files and directories to include
    include_paths = [
        "report/report.pdf",
        "230103022.pdf",
        "README.md",
        "AI_USE.md",
        "Makefile",
        "pytest.ini",
        ".gitignore",
        ".github/workflows/ci.yml",
        "cluster",
        "data",
        "datasets",
        "models",
        "network",
        "prompts",
        "results",
        "service",
        "tests",
        "tools",
        "training",
        "worker",
    ]

    # Exclusions
    exclude_extensions = {".safetensors", ".bin", ".pt", ".pyc", ".pyo"}
    exclude_dirs = {"__pycache__", ".pytest_cache", ".venv", "venv", ".git"}

    if os.path.exists(zip_filename):
        os.remove(zip_filename)

    packed_count = 0
    with zipfile.ZipFile(zip_filename, "w", zipfile.ZIP_DEFLATED) as zipf:
        for entry in include_paths:
            if os.path.isfile(entry):
                zipf.write(entry, arcname=entry)
                packed_count += 1
                print(f"Packed file: {entry}")
            elif os.path.isdir(entry):
                for root, dirs, files in os.walk(entry):
                    # Filter out excluded directories
                    dirs[:] = [d for d in dirs if d not in exclude_dirs]
                    for f in sorted(files):
                        ext = os.path.splitext(f)[1].lower()
                        if ext in exclude_extensions:
                            print(f"Skipping binary weight: {os.path.join(root, f)}")
                            continue
                        fpath = os.path.join(root, f)
                        rel_path = os.path.relpath(fpath, ".")
                        zipf.write(fpath, arcname=rel_path)
                        packed_count += 1

    zip_size = os.path.getsize(zip_filename)
    print("=" * 60)
    print(f"Successfully packaged {packed_count} files into {zip_filename}")
    print(f"Total archive size: {zip_size / (1024 * 1024):.2f} MB ({zip_size} bytes)")
    print("=" * 60)

if __name__ == "__main__":
    package_submission()
