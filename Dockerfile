FROM agent0ai/agent-zero-base:latest

# ============================================================
# OpenOperator Training Master
#
# Custom files are expected at the repository/build-context root.
#
# Build:   root
# Runtime: non-root UID 1000
#
# Heavy training does NOT live here.
# DGX / Colab / Kaggle execute training jobs.
# ============================================================

USER root

ARG COLAB_CLI_VERSION=0.7.4
ARG KAGGLE_CLI_VERSION=2.2.4
ARG SOUP_CLI_VERSION=0.75.2
ARG TRAINING_MASTER_PYTHON=3.12
ARG TORCH_CPU_VERSION=2.5.1+cpu
ARG TORCHVISION_CPU_VERSION=0.20.1+cpu

RUN id user >/dev/null 2>&1 || useradd -m -u 1000 -s /bin/bash user

ENV HOME=/home/user \
    PYTHONPATH=/a0 \
    WEB_UI_PORT=7860 \
    PORT=7860 \
    A0_PUBLIC_URL=https://leon4gr45-openoperator.hf.space \
    PLAYWRIGHT_BROWSERS_PATH=/a0/tmp/playwright \
    HF_HOME=/a0/usr/cache/huggingface \
    XDG_CACHE_HOME=/a0/usr/cache \
    XDG_CONFIG_HOME=/a0/usr/config \
    GH_CONFIG_DIR=/a0/usr/config/gh \
    KAGGLE_CONFIG_DIR=/a0/usr/config/kaggle \
    UV_CACHE_DIR=/a0/usr/cache/uv \
    UV_TOOL_DIR=/opt/uv-tools \
    UV_TOOL_BIN_DIR=/usr/local/bin \
    UV_PYTHON_INSTALL_DIR=/opt/uv-python \
    TRAINING_MASTER_VENV=/opt/venv-training-master \
    TRAINING_MASTER_PYTHON_BIN=/opt/venv-training-master/bin/python \
    TRAINING_MASTER_STATE_DIR=/a0/usr/training-master \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH=/home/user/.local/bin:/usr/local/bin:/opt/venv-a0/bin:$PATH

# ------------------------------------------------------------
# Privileged OS dependencies
# ------------------------------------------------------------

RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        ca-certificates \
        curl \
        wget \
        gnupg \
        git \
        jq \
        procps \
        openssh-client \
        build-essential \
        unzip \
        rsync \
        fonts-unifont \
        libnss3 \
        libnspr4 \
        libatk1.0-0 \
        libatspi2.0-0 \
        libxcomposite1 \
        libxdamage1 \
        libatk-bridge2.0-0 \
        libcups2 \
    && rm -rf /var/lib/apt/lists/*

# ------------------------------------------------------------
# Official GitHub CLI (gh)
# ------------------------------------------------------------

RUN mkdir -p -m 755 /etc/apt/keyrings && \
    wget -nv -O /etc/apt/keyrings/githubcli-archive-keyring.gpg \
        https://cli.github.com/packages/githubcli-archive-keyring.gpg && \
    chmod go+r /etc/apt/keyrings/githubcli-archive-keyring.gpg && \
    mkdir -p -m 755 /etc/apt/sources.list.d && \
    echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/githubcli-archive-keyring.gpg] https://cli.github.com/packages stable main" \
        > /etc/apt/sources.list.d/github-cli.list && \
    apt-get update && \
    apt-get install -y --no-install-recommends gh && \
    rm -rf /var/lib/apt/lists/*

# ------------------------------------------------------------
# Application files
#
# Everything uploaded by the user is expected at repository root.
# COPY . therefore places those files directly under /a0.
# ------------------------------------------------------------

WORKDIR /a0
COPY --chown=1000:1000 . /a0/

# Agent Zero assumes Docker runtime can call chpasswd. Our HF runtime is
# intentionally non-root, so patch root-password management to no-op for UID 1000.
RUN /opt/venv-a0/bin/python /a0/patch_agent_zero_nonroot.py


# ------------------------------------------------------------
# Writable runtime state/config
# ------------------------------------------------------------

RUN mkdir -p \
        /a0/usr/cache/huggingface \
        /a0/usr/cache/uv \
        /a0/usr/config/colab-cli \
        /a0/usr/config/kaggle \
        /a0/usr/config/gh \
        /a0/usr/training-master/jobs \
        /a0/usr/training-master/experiments \
        /a0/usr/training-master/logs \
        /a0/usr/training-master/indexes \
        /a0/usr/supervisor \
        /a0/usr/workdir \
        /a0/logs \
        /a0/tmp/playwright \
        /a0/exe \
        /a0/ins \
        /a0/per \
        /opt/uv-tools \
        /opt/uv-python \
    && chown -R 1000:1000 /a0 \
    && chmod -R 755 /a0/exe

# ------------------------------------------------------------
# Agent Zero primary Python environment
#
# Keep OpenOperator isolated from Training Master dependencies.
# ------------------------------------------------------------

# Keep the control-plane image CPU-only.
# Installing plain `torch` from PyPI on Linux can pull the full NVIDIA CUDA
# dependency stack, which is unnecessary in this Hugging Face CPU Space.
RUN /opt/venv-a0/bin/pip install --upgrade pip && \
    /opt/venv-a0/bin/pip uninstall -y torch torchvision && \
    /opt/venv-a0/bin/pip install --no-cache-dir \
        --index-url https://download.pytorch.org/whl/cpu \
        "torch==${TORCH_CPU_VERSION}" \
        "torchvision==${TORCHVISION_CPU_VERSION}" && \
    /opt/venv-a0/bin/pip install --no-cache-dir \
        "sentence-transformers==3.0.1" \
        -r /a0/requirements.txt

# ------------------------------------------------------------
# uv + dedicated Training Master Python
# ------------------------------------------------------------

RUN /opt/venv-a0/bin/pip install --no-cache-dir uv && \
    /opt/venv-a0/bin/uv python install "${TRAINING_MASTER_PYTHON}" && \
    /opt/venv-a0/bin/uv venv \
        --python "${TRAINING_MASTER_PYTHON}" \
        /opt/venv-training-master

RUN /opt/venv-a0/bin/uv pip install \
        --python /opt/venv-training-master/bin/python \
        --no-cache \
        -r /a0/requirements-training-master.txt

# Light Soup control package only.
# Full training extras, Unsloth, CUDA, vLLM etc. belong on workers.
RUN /opt/venv-a0/bin/uv pip install \
        --python /opt/venv-training-master/bin/python \
        --no-cache \
        "soup-cli==${SOUP_CLI_VERSION}"

# Expose Soup without prepending the complete Training Master venv
# to Agent Zero's PATH.
RUN ln -sf /opt/venv-training-master/bin/soup /usr/local/bin/soup

# ------------------------------------------------------------
# Replaceable remote-compute CLIs
#
# These are independent uv-tool environments.
# Authentication is interactive from the terminal; no auth secret
# is baked into this image.
# ------------------------------------------------------------

RUN /opt/venv-a0/bin/uv tool install \
        --python "${TRAINING_MASTER_PYTHON}" \
        "google-colab-cli==${COLAB_CLI_VERSION}" && \
    /opt/venv-a0/bin/uv tool install \
        --python "${TRAINING_MASTER_PYTHON}" \
        "kaggle==${KAGGLE_CLI_VERSION}"

# ------------------------------------------------------------
# Interactive OAuth/config persistence paths
#
# Colab currently stores OAuth cache below ~/.config/colab-cli,
# so redirect that directory into /a0/usr/config.
#
# GitHub CLI uses GH_CONFIG_DIR directly.
# Kaggle uses KAGGLE_CONFIG_DIR directly.
# ------------------------------------------------------------

RUN mkdir -p /home/user/.config && \
    rm -rf /home/user/.config/colab-cli && \
    ln -s /a0/usr/config/colab-cli /home/user/.config/colab-cli && \
    chown -h 1000:1000 /home/user/.config/colab-cli && \
    chown -R 1000:1000 \
        /a0/usr/config \
        /a0/usr/training-master

# ------------------------------------------------------------
# Patchright Chromium
# ------------------------------------------------------------

RUN /opt/venv-a0/bin/patchright install chromium --no-shell && \
    chown -R 1000:1000 /a0/tmp/playwright

# ------------------------------------------------------------
# Root-level helper scripts -> /usr/local/bin
# ------------------------------------------------------------

RUN install -o root -g root -m 0755 \
        /a0/training-master-doctor \
        /usr/local/bin/training-master-doctor && \
    install -o root -g root -m 0755 \
        /a0/training-master-auth-status \
        /usr/local/bin/training-master-auth-status && \
    install -o root -g root -m 0755 \
        /a0/init_training_master.sh \
        /usr/local/bin/init-training-master && \
    install -o root -g root -m 0755 \
        /a0/sctl \
        /usr/local/bin/sctl && \
    install -o root -g root -m 0755 \
        /a0/supervisor-service-install \
        /usr/local/bin/supervisor-service-install && \
    install -o root -g root -m 0755 \
        /a0/supervisor-service-remove \
        /usr/local/bin/supervisor-service-remove && \
    chmod 0755 /a0/start_openoperator.sh && \
    chmod -R a+rX \
        /opt/venv-training-master \
        /opt/uv-tools \
        /opt/uv-python


# ------------------------------------------------------------
# Supervisor control plane
#
# The immutable root-level config owns the control socket and includes
# runtime-managed service definitions from /a0/usr/supervisor/*.conf.
# Agent Zero can write that directory as UID 1000.
# ------------------------------------------------------------

RUN mkdir -p /etc/supervisor/conf.d /a0/usr/supervisor && \
    chown -R 1000:1000 /a0/usr/supervisor

COPY supervisord.conf /etc/supervisor/conf.d/supervisord.conf

RUN chmod 0644 /etc/supervisor/conf.d/supervisord.conf && \
    test -s /etc/supervisor/conf.d/supervisord.conf && \
    grep -Fq '/a0/usr/supervisor/*.conf' /etc/supervisor/conf.d/supervisord.conf

# ============================================================
# Runtime boundary
# ============================================================

USER user
WORKDIR /a0

# Smoke-test the exact non-root runtime environment.
RUN whoami && \
    test "$(id -u)" != "0" && \
    grep -q "Skipping root password change in non-root runtime" /a0/helpers/settings.py && \
    test -s /etc/supervisor/conf.d/supervisord.conf && \
    test -x /usr/local/bin/sctl && \
    test -x /usr/local/bin/supervisor-service-install && \
    test -x /usr/local/bin/supervisor-service-remove && \
    git --version && \
    gh --version && \
    /opt/venv-a0/bin/python -c "import torch; assert torch.version.cuda is None, torch.version.cuda; print('torch', torch.__version__, 'CPU-only')" && \
    /opt/venv-training-master/bin/python --version && \
    soup --help >/dev/null && \
    colab --help >/dev/null && \
    kaggle --help >/dev/null && \
    training-master-doctor --build-check

EXPOSE 7860

# Existing OpenOperator startup file, now expected at repository root.
CMD ["bash", "/a0/start_openoperator.sh"]
