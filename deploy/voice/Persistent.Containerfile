ARG BASE_IMAGE
FROM ${BASE_IMAGE}
COPY runtime/voice_worker.py /app/voice_worker.py
CMD ["python","/app/voice_worker.py","--serve"]
