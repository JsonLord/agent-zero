# Hugging Face Spaces Docker SDK image.
# Keep this build aligned with DockerfileLocal while binding the public Space port directly.
FROM agent0ai/agent-zero-base:latest

ARG BRANCH=local
ENV BRANCH=${BRANCH} \
    WEB_UI_HOST=0.0.0.0 \
    WEB_UI_PORT=7860 \
    A0_PUBLIC_URL=https://leon4gr45-agent.hf.space \
    A0_CLOUDFLARE_DISABLED=true \
    SPYNEL_AGENT_ZERO_URL=http://127.0.0.1:7860 \
    HOME=/home/a0space \
    XDG_CACHE_HOME=/home/a0space/.cache \
    HF_HOME=/home/a0space/.cache/huggingface \
    MPLCONFIGDIR=/home/a0space/.cache/matplotlib \
    PIP_DISABLE_PIP_VERSION_CHECK=1

COPY ./docker/run/fs/ /
COPY ./ /git/agent-zero

RUN bash /ins/pre_install.sh "${BRANCH}" \
    && bash /ins/install_A0.sh "${BRANCH}" \
    && bash /ins/install_additional.sh "${BRANCH}" \
    && bash /ins/install_A02.sh "${BRANCH}" \
    && bash /ins/post_install.sh "${BRANCH}" \
    && /opt/venv-a0/bin/python -m spacy download en_core_web_sm \
    && chmod +x /exe/initialize.sh /exe/run_A0.sh /exe/run_searxng.sh \
       /exe/huggingface-entrypoint.sh \
    && python3 - <<'PY'
from pathlib import Path

path = Path("/etc/supervisor/conf.d/supervisord.conf")
text = path.read_text(encoding="utf-8")
start = text.index("[program:run_tunnel_api]")
end = text.index("[eventlistener:the_listener]", start)
path.write_text(text[:start] + text[end:], encoding="utf-8")
PY

RUN if ! getent group 1000 >/dev/null; then groupadd --gid 1000 a0space; fi \
    && space_group="$(getent group 1000 | cut -d: -f1)" \
    && if ! getent passwd 1000 >/dev/null; then useradd --uid 1000 --gid "$space_group" --create-home --shell /bin/bash a0space; fi \
    && space_user="$(getent passwd 1000 | cut -d: -f1)" \
    && usermod --gid "$space_group" "$space_user" \
    && install -d -o "$space_user" -g "$space_group" \
       /home/a0space /home/a0space/.cache /a0/usr /a0/tmp \
    && chown -R "$space_user":"$space_group" /a0 /home/a0space

# Runtime dependency mutation fails on immutable Space layers and is unsafe in a
# serving process. All Python dependencies and spaCy data are present above.
ENV PIP_NO_INDEX=1

EXPOSE 7860

USER 1000:1000
CMD ["/exe/huggingface-entrypoint.sh"]
