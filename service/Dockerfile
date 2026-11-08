FROM python:3.11-slim

WORKDIR /app

# Install dependencies with no cache to keep image small (<2 GB)
COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir --extra-index-url https://download.pytorch.org/whl/cpu -r /app/requirements.txt

# Copy service code (weights are downloaded at startup from object storage, NOT baked into the image)
COPY app.py /app/app.py

EXPOSE 8000

ENV MODEL_URI="s3://models/v1" \
    MODEL_VERSION="v1" \
    S3_ENDPOINT="http://seaweedfs-s3.data.svc.cluster.local:8333" \
    MAX_NEW_TOKENS="64" \
    FAULT_INJECT="0" \
    PYTHONUNBUFFERED="1"

CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]

