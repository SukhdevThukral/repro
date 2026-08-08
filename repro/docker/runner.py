import os 
import shutil
import re
import subprocess
import tempfile
import threading
import time

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

def has_devcontainers_extension() -> bool:
    """Check if VS Code's DEV containers extension is installed"""
    try:
        result = subprocess.run(
            ["code", "--list-extensions"],
            capture_output=True, text=True, timeout=5,
            shell=(os.name == "nt"),
        )
        return "ms-vscode-remote.remote-containers" in result.stdout
    except Exception:
        return False

def attach_vscode_to_container(container_name: str, work_dir:str):
    for _ in range(20):
        result = subprocess.run(
            ["docker", "inspect", "--format", "{{.State.Runnning}}", container_name],
            capture_output=True, text=True,
        )
        if result.returncode == 0 and result.stdout.strip() == "true":
            break
        time.sleep(0.5)
    else:
        return

    id_result = subprocess.run(
        ["docker", "inspect", "--format", "{{.State.Running}}", container_name],
        capture_output=True, text=True,
    )
    if id_result.returncode != 0:
        return

    container_id =  id_result.stdout.strip()
    hex_id = container_id.encode().hex()
    uri = f"vscode-remote://attached-container+{hex_id}{work_dir}"

    try:
        subprocess.Popen(["code", "--folder-uri", uri], shell=(os.name=="nt"))
    except Exception:
        pass

def run_sandbox(issue: dict, runtime: dict, ports: list =None, token: str = None, no_editor: bool = False):
    check_docker_available()
    ports = ports or []

    owner = issue["owner"]
    repo = issue["repo"]
    number = issue["number"]

    validate_repo_identifiers(owner, repo)

    if not isinstance(number, int):
        raise InvalidRepoError("issue number must be an integer")

    clone_url_public = f"https://github.com/{owner}/{repo}.git"
    work_dir = f"/sandbox/{repo}"
    container_name = f"repro-{owner}-{repo}-{number}"

    host_dir = tempfile.mkdtemp(prefix=f"repro-{owner}-{repo}-{number}-")

    print(f"📁 Sandbox files will live at: {host_dir}")
    print("     (this folder survives after you exit - edit here with your own editor)\n")

    editor_mode = None
    if not no_editor and shutil.which("code"):
        if has_devcontainers_extension():
            editor_mode="attached"
            print("🖊️  VS Code will attach directly to the container once it's up...")
            print("   (its built-in terminal will run INSIDE the sandbox — one window, no split)\n")
        else:
            editor_mode= "folder"
            print("🖊️  Opening the folder in VS Code (editing only)...")
            print("   💡 Install the 'Dev Containers' extension for a fully unified terminal.\n")
    elif not no_editor:
        print("💡 Tip: install VS Code's 'code' CLI command to auto-open the sandbox folder.\n")

    startup_script = build_startup_script(clone_url_public, work_dir, runtime["install"], number, ports, has_token=bool(token))

    args = [
        "docker", "run",
        "--rm",
        "-i",
        "-t",
        "--name", container_name,
        "--hostname", f"sandbox-issue-{number}",
        "-v", f"{host_dir}:{work_dir}",
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
            args+=["--env-file", env_file_path]
        except Exception:
            if os.path.exists(env_file_path):
                os.remove(env_file_path)
            raise

    args += [runtime["image"], "sh", "-c", startup_script]

    print(f"🚀 Starting sandbox for {owner}/{repo} issue #{number}")
    print("     (container will be deleted automatically when you exit)\n")

    env = os.environ.copy()
    env["DOCKER_CLI_HINTS"] = "false"

    if editor_mode == "attached":
        threading.Thread(
            target=attach_vscode_to_container,
            args=(container_name, work_dir),
            daemon=True,
        ).start()
    elif editor_mode == "folder":
        try:
            subprocess.Popen(["code", host_dir], shell=(os.name=="nt"))
        except Exception as e:
            print(f"⚠️  Couldn't auto-open VS Code: {e}\n")

    try:
        try:
            result = subprocess.run(args, env=env)
        except KeyboardInterrupt:
            print("Interrupted - cleaning up the sandbox...")
            return
        
        if result.returncode not in (0,130):
            print(f"Sandbox exited with code {result.returncode} - check the output above.")
            return

        print("\n Sandbox destroyed. Back to reality.")

    finally:
        if env_file_path and os.path.exists(env_file_path):
            os.remove(env_file_path)
    print(f"📁 Your files are still here: {host_dir}")
    print("   (delete manually whenever you're done)")

def build_startup_script(clone_url_public, work_dir, install_cmd, issue_number, ports, has_token: bool = False) -> str:
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
        f'echo "  Repro - Issue #{issue_number}"',
        'echo "=================================="',
        'echo ""',
        f'echo "Cloning repo..."',
        clone_cmd,
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