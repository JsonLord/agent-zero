# Hugging Face Spaces Docker SDK image.
# Keep this build aligned with DockerfileLocal while binding the public Space
# port directly. Hugging Face requires app_port >= 1025, so the UI is started
# on 7860 via WEB_UI_PORT (docker-run-ui reads this instead of its normal
# port-80 default; see docker/run/fs/exe/self_update_manager.py).
FROM agent0ai/agent-zero-base:latest

ARG BRANCH=local
ENV BRANCH=${BRANCH} \
    WEB_UI_HOST=0.0.0.0 \
    WEB_UI_PORT=7860 \
    A0_PUBLIC_URL=https://leon4gr45-agent.hf.space \
    A0_CLOUDFLARE_DISABLED=true

COPY ./docker/run/fs/ /
COPY ./ /git/agent-zero

RUN bash /ins/pre_install.sh "${BRANCH}" \
    && bash /ins/install_A0.sh "${BRANCH}" \
    && bash /ins/install_additional.sh "${BRANCH}" \
    && bash /ins/install_A02.sh "${BRANCH}" \
    && bash /ins/post_install.sh "${BRANCH}" \
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

EXPOSE 7860

CMD ["/exe/huggingface-entrypoint.sh"]
