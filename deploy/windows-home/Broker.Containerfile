ARG BASE_IMAGE
FROM ${BASE_IMAGE}
WORKDIR /app
COPY runtime/inference_broker.py /app/runtime/inference_broker.py
COPY config/inference-broker.json /app/config/inference-broker.json
RUN mkdir -p /run/larpus-broker && chown 1000:1000 /run/larpus-broker && chmod 700 /run/larpus-broker
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUTF8=1
USER 1000:1000
CMD ["python", "-m", "runtime.inference_broker"]
