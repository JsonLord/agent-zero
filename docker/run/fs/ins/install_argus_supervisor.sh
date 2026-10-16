#!/bin/bash
set -euo pipefail
# Build-time only. Never use or mutate /opt/venv-a0 for these runtimes.
argus_sha=fdfeb715b0749db176c7d8b3212a717fb81087ba
foreman_sha=381ca2de90af9efc2781a58055cc3028c7cabbb9
for name in argus foreman; do
    if [ "$name" = argus ]; then
        upstream=https://github.com/microsoft/ArgusAgent.git
        revision=$argus_sha
    else
        upstream=https://github.com/JsonLord/foreman-supervisor.git
        revision=$foreman_sha
    fi
    git init "/opt/$name"
    git -C "/opt/$name" remote add origin "$upstream"
    git -C "/opt/$name" fetch --depth 1 origin "$revision"
    git -C "/opt/$name" checkout --detach FETCH_HEAD
    test "$(git -C "/opt/$name" rev-parse HEAD)" = "$revision"
    python3 -m venv "/opt/venv-$name"
    "/opt/venv-$name/bin/python" -m pip install --no-cache-dir \
        -c "/git/agent-zero/plugins/argus_supervisor/runtime/$name-constraints.txt" "/opt/$name"
    chmod -R a+rX "/opt/$name" "/opt/venv-$name"
done
/opt/venv-argus/bin/python -m argus --version
/opt/venv-foreman/bin/python -c 'from foreman.foreman.jev import JevForemanModel; from foreman.observation import FactoryObservation'
