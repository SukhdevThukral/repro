# REPRO

> Disposable Docker environments for any GitHub issue.
One command. No setup.

```bash
pip install repro-cli
repro https://github.com/org/repo/issues/42
```

That's it, your terminal boots an isolated sandbox - repo cloned, dependencies installed and IF you have VS Code, it opens automatically **attached directly to the container** so you get a real editor and a single unified terminal, not just a shell. Type `exit` and the container disappears. Your files stay on disk, exactly where they were.

---

## Install

```bash
pip install repro-cli
```

**Requirements:**
- Python 3.9+
- [Docker](https://docs.docker.com/get-docker/) (INSTALLED AND RUNNING)
- [VS Code] (optional, but recommended - enables the unified editor/terminal experience below)

---

## Usage

```bash
# Open a sandbox for any publish GitHub issue
repro https://github.com/org/repo/issues/123

#Forward a port (e.g. to view a web app running inside the sandbox)
repro https://github.com/org/repo/issues/123 -p 3000

# Map a different host port to a container port
repro https://github.com/org/repo/issues/123 -p 8080:3000

# Private repos - pass a GitHub token
repro https://github.com/org/private-repo/issues/7 --token ghp_xxx

#Or set it once as an env var instead of typing it every single time!
export DEVSANDBOX_GITHUB_TOKEN=ghp_xxx
repro https://github.com/org/private-repo/issues/7

# Skip auto-opening an editor
repro https://github.com/org/repo/issues/123 --no-editor


#Help
repro --help
```

## What it does

1. **Parses** the GitHub issue URL
2. **Detects** the repo's runtime - Node, Python, Go, Rust, Ruby, PHP, Java, or a devcontainer, based on whats actually in the repo.
3. **Spins up** a disposable, isolated Docker container with the right base image.
4. **Bind-mounts** a real folder on your machine into the container, so nothing is trapped - files persist after you exit
5. **Clones** the repo directly into that shared folder and install dependencies
6. **Attaches VS Code directly to the running container** (auto-installing the Dev Containers extension if needed) - one window, one terminal, running *inside* the sandbox.
7. *Destroys* the container the moment you exit. Your edited files remain exactly where they were.

---

## The unified editor experience

- **Real editor** — VS Code attaches directly into the container, so its built-in terminal *is* the sandbox shell. No second window to juggle.
- **Real persistence** — because the folder is bind-mounted, not just cloned inside the container, your work survives after `exit`. Nothing is lost.
If VS Code isn't installed, `repro` falls back gracefully — you still get a real folder path printed at the end, ready to open in whatever editor you use.

---

## Supported runtimes
| File detected | Runtime | Base image |
|---|---|---|
| `package.json` | Node.js | `node:20-alpine` |
| `yarn.lock` | Node.js (yarn) | `node:20-alpine` |
| `pnpm-lock.yaml` | Node.js (pnpm) | `node:20-alpine` |
| `requirements.txt` | Python | `python:3.12-slim` |
| `pyproject.toml` | Python | `python:3.12-slim` |
| `Pipfile` | Python (pipenv) | `python:3.12-slim` |
| `go.mod` | Go | `golang:1.21-alpine` |
| `Cargo.toml` | Rust | `rust:1.75-slim` |
| `Gemfile` | Ruby | `ruby:3.3-slim` |
| `composer.json` | PHP | `php:8.3-cli` |
| `pom.xml` | Java (Maven) | `maven:3.9-eclipse-temurin-21` |
| `build.gradle` | Java (Gradle) | `gradle:8-jdk21` |
| `.devcontainer` | devcontainer | MS universal image |
| *(none matched)* | Universal fallback | `ubuntu:22.04` |

---

## The GitHub App

Install [**repro-sandbox-bot**](https://github.com/apps/repro-sandbox-bot) on any repo and it automatically comments the exact `repro` command on every new issue - so contributors never have to think about setup.

```
🏖 Open this issue in DevSandbox
 
Spin up a disposable Docker environment with this repo already checked out:
 
    repro https://github.com/org/repo/issues/42
 
Don't have repro yet? Install it here.
 
Comment /sandbox on any issue to get this again.
```

You can also trigger it on demand by commenting `/sandbox` on any issue. The bot runs 24/7, independent of your machine.

---
## Contributing 
PRs welcome. Open an issue first for anything beyond small fixes - and yes, you can use `repro` itself to work on `repro`.

## License

MIT