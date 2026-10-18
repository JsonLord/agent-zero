# OpenOperator Training Master — root-level upload layout

All custom/uploaded files are assumed to live at repository root.

Recommended root:

```text
/
├── Dockerfile
├── requirements.txt
├── requirements-training-master.txt
├── initialize_hf.sh
├── init_training_master.sh
├── training-master-doctor
├── training-master-auth-status
└── TRAINING_MASTER_RUNTIME.md
```

Your existing OpenOperator application files remain beside them.

## Python/package boundaries

### `/opt/venv-a0`

Agent Zero / OpenOperator application dependencies only.

Do not install Training Master or cloud-backend packages into this environment except `uv`, which is used to create isolated environments.

### `/opt/venv-training-master`

Control-plane Python environment:

- `optim-agent`
- light `soup-cli`
- Hugging Face Hub client
- HTTP/Pydantic/YAML/state/scheduler libraries

It deliberately excludes CUDA, Unsloth, full Soup training extras, vLLM, and worker-side ML environments.

### `/opt/uv-tools`

Independent CLI environments:

- Google Colab CLI
- Kaggle CLI

Keeping these separate prevents cloud CLI dependency upgrades from breaking Agent Zero or Training Master.

## System tools baked into Docker

- `git`
- official GitHub CLI `gh`
- `curl`
- `wget`
- `jq`
- `ssh`
- build tools
- browser system libraries

Runtime remains non-root.

## Interactive authentication

Authentication is deliberately performed manually from the Space terminal.

### GitHub

```bash
gh auth login
gh auth setup-git
```

GitHub CLI state is written under:

```text
/a0/usr/config/gh
```

through `GH_CONFIG_DIR`.

### Kaggle

```bash
kaggle auth login
```

Kaggle state is written under:

```text
/a0/usr/config/kaggle
```

through `KAGGLE_CONFIG_DIR`.

### Colab

Run a credential-requiring CLI operation, for example:

```bash
colab new -s training-auth
```

Follow the printed Google authorization URL and paste the returned authorization code into the terminal.

Colab's config directory is redirected to:

```text
/a0/usr/config/colab-cli
```

through a symlink from `~/.config/colab-cli`.

## OAuth persistence

These locations persist only if `/a0/usr` itself is backed by persistent Space storage.

If `/a0/usr` is ephemeral, authentication must be repeated after a rebuild.

Autonomous OpenOperator jobs must never invoke login/consent flows. Backend probes should return `AUTH_REQUIRED`.

## Existing `initialize_hf.sh`

Do not replace your working OpenOperator startup logic.

Add this near the start, after strict shell options and before starting OpenOperator:

```bash
source /a0/init_training_master.sh
```

or:

```bash
init-training-master
```

The Docker image installs `init_training_master.sh` as `/usr/local/bin/init-training-master`.

## Runtime checks

```bash
training-master-doctor
training-master-auth-status

git --version
gh --version
soup --help
colab --help
kaggle --help
```

The following is intentionally expected to fail at runtime:

```bash
apt install anything
```

All privileged packages belong in the Docker build.
