FROM python:3.11-bookworm

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    DEBIAN_FRONTEND=noninteractive \
    HOME=/home/user \
    APP_HOME=/home/user/app

# Install system dependencies
# Including tools for builds and a0 framework (ffmpeg for whisper, etc)
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    curl \
    build-essential \
    libffi-dev \
    libssl-dev \
    pkg-config \
    python3-dev \
    gfortran \
    libopenblas-dev \
    liblapack-dev \
    cmake \
    ninja-build \
    libgomp1 \
    ffmpeg \
    libsm6 \
    libxext6 \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

RUN curl -LsSf https://astral.sh/uv/install.sh | sh
ENV PATH="/root/.local/bin:$PATH"

RUN useradd -m -u 1000 user
WORKDIR /home/user/app
RUN chown -R user:user /home/user

# Pre-create patches directory to ensure correct structure
RUN mkdir -p /home/user/app/patches/helpers /home/user/app/patches/api

COPY --chown=user:user . /home/user/app

USER user
RUN chmod +x /home/user/app/start_hf.sh

EXPOSE 7860
CMD ["./start_hf.sh"]
