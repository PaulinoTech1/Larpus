ARG BASE_IMAGE
FROM ${BASE_IMAGE}
WORKDIR /app
COPY runtime/inference_broker.py /app/runtime/inference_broker.py
COPY runtime/broker_scheduler.py /app/runtime/broker_scheduler.py
COPY runtime/model_selection.py /app/runtime/model_selection.py
COPY config/model-selection.json /app/config/model-selection.json
COPY config/inference-broker.json /app/config/inference-broker.json
COPY config/broker-prompts.json /app/config/broker-prompts.json
RUN mkdir -p /run/larpus-broker /run/larpus-notes && chown 1000:1000 /run/larpus-broker /run/larpus-notes && chmod 700 /run/larpus-broker /run/larpus-notes
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUTF8=1
USER 1000:1000
CMD ["python", "-m", "runtime.inference_broker"]
