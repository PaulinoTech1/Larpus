ARG BASE_IMAGE
FROM ${BASE_IMAGE}
WORKDIR /app
COPY runtime/local_ollama.py runtime/notes_worker.py /app/runtime/
COPY config/inference-broker.json /app/config/inference-broker.json
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUTF8=1 LARPUS_BROKER_ROLE=notes
USER 1000:1000
CMD ["python", "-c", "import time; time.sleep(2147483647)"]
