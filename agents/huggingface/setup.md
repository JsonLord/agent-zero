# Hugging Face CLI Setup

This document outlines the steps to set up and authenticate the Hugging Face CLI (`hf`).

## 1. Installation

If `hf` is not installed, you can install it using pip:

```bash
pip install -U "huggingface_hub[cli]"
```

## 2. Authentication

To use the `hf` CLI, you need to authenticate with a Hugging Face account. You will need a Hugging Face access token with `write` permissions.

Once you have a token, you can authenticate using the following command:

```bash
hf login <token>
```

You will need to request the token from the user.
