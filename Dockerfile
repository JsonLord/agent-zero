# Hugging Face Spaces Docker SDK image.
# Keep this build aligned with DockerfileLocal while binding the public Space port directly.
FROM agent0ai/agent-zero-base:latest

ARG BRANCH=local
ENV BRANCH=${BRANCH} \
    WEB_UI_HOST=0.0.0.0 \
    WEB_UI_PORT=7860 \
    A0_PUBLIC_URL=https://leon4gr45-openoperator.hf.space \
    A0_CLOUDFLARE_DISABLED=true \
    SPYNEL_AGENT_ZERO_URL=http://127.0.0.1:7860 \
    HOME=/home/a0space \
    XDG_CACHE_HOME=/home/a0space/.cache \
    HF_HOME=/home/a0space/.cache/huggingface \
    MPLCONFIGDIR=/home/a0space/.cache/matplotlib \
    PIP_DISABLE_PIP_VERSION_CHECK=1

COPY ./ /git/agent-zero
COPY ./docker/run/fs/ins/copy_A0.sh /ins/copy_A0.sh
COPY ./docker/run/fs/exe/huggingface-entrypoint.sh /exe/huggingface-entrypoint.sh

RUN chmod +x /exe/huggingface-entrypoint.sh /ins/*.sh

RUN set -eu; \
    for script in \
        /ins/pre_install.sh \
        /ins/install_A0.sh \
        /ins/install_additional.sh \
        /ins/install_A02.sh \
        /ins/post_install.sh \
        /exe/huggingface-entrypoint.sh; \
    do \
        test -f "$script" || { echo "Required script is missing: $script" >&2; exit 1; }; \
        first_line="$(head -n 1 "$script")"; \
        test "$first_line" != "version https://git-lfs.github.com/spec/v1" || { echo "Git LFS pointer found instead of executable script: $script" >&2; exit 1; }; \
        case "$first_line" in '#!'*) ;; *) echo "Required script has no shebang: $script" >&2; exit 1;; esac; \
    done; \
    bash /ins/pre_install.sh "${BRANCH}" \
    && bash /ins/install_A0.sh "${BRANCH}" \
    && bash /ins/install_additional.sh "${BRANCH}" \
    && bash /ins/install_A02.sh "${BRANCH}" \
    && bash /ins/post_install.sh "${BRANCH}" \
    && /opt/venv-a0/bin/python -m spacy download en_core_web_sm \
    && python3 - <<'PY'
from pathlib import Path

path = Path("/etc/supervisor/conf.d/supervisord.conf")
if path.exists():
    text = path.read_text(encoding="utf-8")
    if "[program:run_tunnel_api]" in text:
        start = text.index("[program:run_tunnel_api]")
        end = text.index("[eventlistener:the_listener]", start) if "[eventlistener:the_listener]" in text else len(text)
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
