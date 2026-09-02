# Hugging Face Spaces Docker SDK image.
# Keep this build aligned with DockerfileLocal; the UI always binds to port 80
# (docker-run-ui hardcodes this), so the Space's app_port must match that, not
# a custom value.
FROM agent0ai/agent-zero-base:latest

ARG BRANCH=local
ENV BRANCH=${BRANCH} \
    WEB_UI_HOST=0.0.0.0 \
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

EXPOSE 80

CMD ["/exe/huggingface-entrypoint.sh"]
