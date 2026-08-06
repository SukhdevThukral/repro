import os 
import subprocess



def run_sandbox(issue: dict, runtime: dict):
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
        "--interactive"
        "--tty"
        "--name", container_name,
        "--hostname", f"sandbox-issue-{number}",
        "-e", f"ISSUE_NUMBER={number}",
        "-e", f"REPO={owner}/{repo}",
        "-e", "TERM=xterm-256color",
        runtime["image"],
        "sh", "-c", startup_script,
    ]

    print(f"Starting sandbox for {owner}/{repo} issue #{number}")
    print("     (container will be deleted automaticallyh when you exit)\n")

    try:
        subprocess.run(args, stdin=None, check=False)
    except FileNotFoundError:
        print("error: Docker not found. Please install Docker: https://docs.docker.com/get-docker/")
        raise

    print("\n Sandbox destroyed. Back to reality.")

def build_startup_script(repo_url:str, work_dir: str, install_cmd: str, issue_number: int) -> str:
    install_step = (
        f'echo "Installing dependencies....." && {install_cmd}'
        if install_cmd
        else 'echo "No install step, dropping into shell... "'
    )

    return " && ".join([
        "set -e",
        "which git > /dev/null 2>&1 || (apt-get update -qq && apt-get install -y -qq git curl)",
        'echo ""',
        'echo "╔════════════════════════════════════════╗"',
        'echo" ║       🏖  DevSandbox                   ║"',
        f'echo"║  Issue: #{issue_number:<31}            ║"',
        'echo "╚════════════════════════════════════════╝"',
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