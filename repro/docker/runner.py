import os 
import shutil
import re
import subprocess
import tempfile

class DockerNotFoundError(Exception):
    pass

class DockerNotRunningError(Exception):
    pass

class InvalidPortError(Exception):
    pass

class InvalidRepoError(Exception):
    pass

SAFE_NAME = re.compile(r"^[A-Za-z0-9._-]+$")

def check_docker_available():
    """Verify Docker CLI exists and the daemon is reachable before trying anythg"""
    if shutil.which("docker") is None:
        raise DockerNotFoundError(
            "Docker is not installed or not on your PATH.\n"
            "   Install it from: https://docs.docker.com/get-docker/"
        )

    result = subprocess.run(["docker", "info"], capture_output=True, text=True)
    if result.returncode != 0:
        raise DockerNotRunningError(
            "Docker is installed but the daemon isnt running.\n"
            "   Start Docker Desktop and wait for the icon to go steady, then try again."
        )

def validate_repo_identifiers(owner: str, repo:str):
    """ Guard against shell injection -> owner/repo gets interpolated into a shell command, so anything outside GitHub's allowed charst is rejected 
    before it even reaches da subprocess"""
    for label, value in (("owner", owner), ("repo", repo)):
        if not SAFE_NAME.match(value):
            raise InvalidRepoError(f'invalid {label} "{value}" - contains disallowed characters')
        if value in (".", ".."):
            raise InvalidRepoError(f'invalid {label} "{value}"')
        if value.startswith("."):
            raise InvalidRepoError(f'invalid {label} "{value}" - cannot start with a dot')


def parse_port_spec(spec: str) -> tuple[int, int]:
    """ Parse a --port value into (host_port, container_port).
        Accepts "3000" (same both sides) or "8080:3000" (host:container).
    """
    parts = spec.split(":")

    if len(parts) == 1:
        host, container = parts[0], parts[0]
    elif len(parts) == 2:
        host, container = parts
    else:
        raise InvalidPortError(f'invalid port spec "{spec}" - use PORT or HOST:CONTAINER')

    for label, value in (("host", host), ("container", container)):
        if not value.isdigit():
            raise InvalidPortError(f'invalid {label} port "{value}" in "{spec}" - must be a number')
        port_num = int(value)
        if not(1 <= port_num <= 65535):
            raise InvalidPortError(f'{label} port {port_num} out of range (1-65535)')

    return int(host), int(container)

def run_sandbox(issue: dict, runtime: dict, ports: list =None, token: str = None):
    check_docker_available()
    ports = ports or []

    owner = issue["owner"]
    repo = issue["repo"]
    number = issue["number"]

    validate_repo_identifiers(owner, repo)

    if not isinstance(number, int):
        raise InvalidRepoError("issue number must be an integer")

    clone_url_public = f"https://github.com/{owner}/{repo}.git"
    clone_url_auth = f"https://{token}@github.com/{owner}/{repo}.git" if token else clone_url_public

    work_dir = f"/sandbox/{repo}"
    container_name = f"repro-{owner}-{repo}-{number}"

    startup_script = build_startup_script(clone_url_auth, clone_url_public, work_dir, runtime["install"], number, ports, has_token=bool(token))

    args = [
        "docker", "run",
        "--rm",
        "-i",
        "-t",
        "--name", container_name,
        "--hostname", f"sandbox-issue-{number}",
        "-e", f"ISSUE_NUMBER={number}",
        "-e", f"REPO={owner}/{repo}",
        "-e", "TERM=xterm-256color",
    ]

    for host_port, container_port in ports:
        args += ["-p", f"127.0.0.1:{host_port}:{container_port}"]

    env_file_path = None
    if token:
        #writing the toekn to a temp file passed via --env-fle instead of -e/embedded-in-command
        fd, env_file_path = tempfile.mkstemp(prefix="repro-", suffix=".env")
        try:
            os.chmod(env_file_path, 0o600)
            with os.fdopen(fd, "w") as f:
                f.write(f"GIT_TOKEN={token}\n")
        except Exception:
            if os.path.exists(env_file_path):
                os.remove(env_file_path)
            raise

    args += [runtime["image"], "sh", "-c", startup_script]

    print(f"Starting sandbox for {owner}/{repo} issue #{number}")
    print("     (container will be deleted automatically when you exit)\n")

    env = os.environ.copy()
    env["DOCKER_CLI_HINTS"] = "false"

    try:
        result = subprocess.run(args, env=env)
    except KeyboardInterrupt:
        print("Interrupted - cleaning up the sandbox...")
        return
    
    if result.returncode not in (0,130):
        print(f"Sandbox exited with code {result.returncode} - check the output above.")
        return

    print("\n Sandbox destroyed. Back to reality.")

def build_startup_script(clone_url_auth, clone_url_public, work_dir, install_cmd, issue_number, ports) -> str:
    install_step = (
        f'echo "Installing dependencies....." && {install_cmd}'
        if install_cmd
        else 'echo "No install step, dropping into shell... "'
    )

    host_and_path = clone_url_public[len("https://"):]
    clone_cmd = (
        f'if [ -n "$GIT_TOEKN" ]; then '
        f'CLONE_URL="https://${{GIT_TOKEN}}@{host_and_path}";'
        f'else CLONE_URL="{clone_url_public}"; fi && '
        f'git clone --depth=1 "$CLONE_URL" {work_dir} 2>&1 | tail -5'
    )

    lines = [
        "set -e",
        "which git > /dev/null 2>&1 || (apk add --no-cache git curl)",
        'echo ""',
        'echo "=================================="',
        f'echo "  DevSandbox - Issue #{issue_number}"',
        'echo "=================================="',
        'echo ""',
        f'echo "Cloning repo..."',
        clone_cmd,
        f"git clone --depth=1 {clone_url_auth} {work_dir} 2>&1 | tail -5",
        f"cd {work_dir} && git remote set-url origin {clone_url_public} && unset GIT_TOKEN",
        install_step,
        'echo ""',
        f'echo "Ready! You are in: {work_dir}"',
        f'echo "Working on issue #{issue_number}"',
    ]

    if ports:
        lines.append('echo ""')
        for host_port, container_port in ports:
            lines.append(f'echo "Port {container_port} forwarded -> http://localhost:{host_port}"')
        lines.append('echo "  Start your app inside this shell (e.g. npm start / node server.js) to use it."')

    lines.append('echo ""')
    lines.append(f"cd {work_dir} && exec sh")


    return " && ".join(lines)