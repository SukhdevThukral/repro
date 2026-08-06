import os 
import shutil
import subprocess

class DockerNotFoundError(Exception):
    pass

class DockerNotRunningError(Exception):
    pass

def check_docker_available():
    """Verify Docker CLI exists and the daemon is reachable before trying anythg"""
    if shutil.whaich("docker") is None:
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

def run_sandbox(issue: dict, runtime: dict):
    check_docker_available()

    owner = issue["owner"]
    repo = issue["repo"]
    number = issue["number"]

    repo_url = f"https://github.com/{owner}/{repo}.git"
    work_dir = f"/sandbox/{repo}"
    container_name = f"repro-{owner}-{repo}-{number}"

    startup_script = build_startup_script(repo_url, work_dir, runtime["install"], number)

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
        runtime["image"],
        "sh", "-c", startup_script,
    ]

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

def build_startup_script(repo_url:str, work_dir: str, install_cmd: str, issue_number: int) -> str:
    install_step = (
        f'echo "Installing dependencies....." && {install_cmd}'
        if install_cmd
        else 'echo "No install step, dropping into shell... "'
    )

    return " && ".join([
        "set -e",
        "which git > /dev/null 2>&1 || (apk add --no-cache git curl)",
        'echo ""',
        'echo "=================================="',
        f'echo "  DevSandbox - Issue #{issue_number}"',
        'echo "=================================="',
        'echo ""',
        f'echo "Cloning repo..."',
        f"git clone --depth=1 {repo_url} {work_dir} 2>&1 | tail -1",
        f"cd {work_dir}",
        install_step,
        'echo ""',
        f'echo "Ready! You are in: {work_dir}"',
        f'echo "Working on issue #{issue_number}"',
        'echo ""',
        f"cd {work_dir} && exec sh",
    ])