FROM agent0ai/agent-zero-base:latest

USER root
RUN useradd -m -u 1000 user || true
ENV HOME=/home/user \
    PATH=/home/user/.local/bin:$PATH \
    PYTHONPATH=/a0 \
    WEB_UI_PORT=7860 \
    PORT=7860

WORKDIR /a0
COPY --chown=user:user . /a0/

RUN mkdir -p /a0/usr /a0/logs /a0/tmp /a0/exe /a0/ins /a0/per && \
    chown -R user:user /a0 && \
    chmod -R 755 /a0/exe

# Install dependencies into the primary virtual environment
RUN /opt/venv-a0/bin/pip install --upgrade pip && \
    /opt/venv-a0/bin/pip install --no-cache-dir python-dotenv litellm PyYAML webcolors simpleeval flask-basicauth flask-socketio

COPY --chown=user:user docker/hf/supervisord.conf /etc/supervisor/conf.d/supervisord.conf

USER user
EXPOSE 7860
CMD ["bash", "/a0/docker/hf/initialize_hf.sh"]
