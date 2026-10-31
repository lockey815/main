# Hugging Face Spaces (Docker SDK) - free CPU basic: 2 vCPU / 16 GB RAM
FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    TF_CPP_MIN_LOG_LEVEL=2 \
    KERAS_BACKEND=tensorflow

# HF Spaces runs the container as uid 1000
RUN useradd -m -u 1000 user
USER user
ENV PATH="/home/user/.local/bin:$PATH"
WORKDIR /home/user/app

COPY --chown=user requirements.txt .
RUN pip install --user -r requirements.txt

COPY --chown=user . .

EXPOSE 7860
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "7860"]
