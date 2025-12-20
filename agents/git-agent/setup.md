# GitHub CLI Setup

This document outlines the steps to set up and authenticate the GitHub CLI (`gh`).

## 1. Installation

If `gh` is not installed, you can install it using one of the following commands, depending on your operating system:

**Debian/Ubuntu:**
```bash
sudo apt-get update && sudo apt-get install -y gh
```

**macOS:**
```bash
brew install gh
```

## 2. Authentication

To use the `gh` CLI, you need to authenticate with a GitHub account. You will need a GitHub personal access token with the `repo` scope.

Once you have a token, you can authenticate using the following command:

```bash
gh auth login --with-token <token>
```

You will need to request the token from the user.
