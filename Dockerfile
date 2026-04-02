# Use Python 3.12 for better compatibility
FROM python:3.12-slim-bookworm

ENV DEBIAN_FRONTEND=noninteractive
ENV HF_SPACE=true
ENV WEB_UI_PORT=7860
ENV WEB_UI_HOST=0.0.0.0
ENV HOME=/home/user
ENV PYTHONUNBUFFERED=1
ENV PATH="/home/user/.local/bin:$PATH"

RUN apt-get update && apt-get install -y \
    git \
    curl \
    openssl \
    procps \
    zstd \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install uv
RUN curl -LsSf https://astral.sh/uv/install.sh | sh

# Install Ollama
RUN curl -fsSL https://ollama.com/install.sh | sh

RUN useradd -m -u 1000 user
RUN groupadd -r ollama || true
RUN usermod -aG ollama user

# Create app directory and set ownership
RUN mkdir -p /home/user/app && chown -R user:user /home/user

USER user
WORKDIR /home/user/app

# Pre-create virtual environment
RUN python -m venv /home/user/venv
ENV VIRTUAL_ENV=/home/user/venv
ENV PATH="/home/user/venv/bin:$PATH"

# Copy adapted files and startup script
COPY --chown=user:user helpers/ helpers/
COPY --chown=user:user api/ api/
COPY --chown=user:user start_hf.sh start_hf.sh
RUN chmod +x start_hf.sh

ENTRYPOINT ["/bin/bash", "/home/user/app/start_hf.sh"]
