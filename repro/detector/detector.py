import urllib.request
import json

KNOWN_FILES = [
    ("package.json",    {"name": "Node.js",          "image": "node:20-alpine",                  "install": "npm install"}),
    ("yarn.lock",       {"name": "Node.js (yarn)",    "image": "node:20-alpine",                  "install": "yarn install"}),
    ("pnpm-lock.yaml",  {"name": "Node.js (pnpm)",    "image": "node:20-alpine",                  "install": "npm i -g pnpm && pnpm install"}),
    ("requirements.txt",{"name": "Python",            "image": "python:3.12-slim",                "install": "pip install -r requirements.txt"}),
    ("pyproject.toml",  {"name": "Python",            "image": "python:3.12-slim",                "install": "pip install -e ."}),
    ("Pipfile",         {"name": "Python (pipenv)",   "image": "python:3.12-slim",                "install": "pip install pipenv && pipenv install"}),
    ("go.mod",          {"name": "Go",                "image": "golang:1.21-alpine",              "install": "go mod download"}),
    ("Cargo.toml",      {"name": "Rust",              "image": "rust:1.75-slim",                  "install": "cargo fetch"}),
    ("Gemfile",         {"name": "Ruby",              "image": "ruby:3.3-slim",                   "install": "bundle install"}),
    ("composer.json",   {"name": "PHP",               "image": "php:8.3-cli",                     "install": "composer install"}),
    ("pom.xml",         {"name": "Java (Maven)",      "image": "maven:3.9-eclipse-temurin-21",    "install": "mvn dependency:resolve"}),
    ("build.gradle",    {"name": "Java (Gradle)",     "image": "gradle:8-jdk21",                  "install": "gradle dependencies"}),    
]

def universal() -> dict:
    return {"name":"universal", "image": "ubuntu:22.04", "install": ""}

def detect_runtime(owner: str, repo: str) -> dict | None:
    api_url = f"https://api.github.com/repos/{owner}/{repo}/contents/"
    try: 
        req = urllib.request.Request(
            api_url,
            headers={"User-Agent": "repro/0.1.0", "Accept": "applications/vnd.github+json"},
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            contents = json.loads(resp.read())
    except Exception:
        return None

    present = {f["name"] for f in contents}

    if ".devcontainer" in present or "devcontainer.json" in present:
        return {
            "name" : "devcontainer",
            "image" : "mcr.microsoft.com/devcontainers/universal:latest",
            "install": "",
        }

    for filename, runtime in KNOWN_FILES:
        if filename in present:
            return runtime

    return None