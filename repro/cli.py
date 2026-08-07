import sys 
import argparse
import os

from repro import __version__
from repro.github.issue import parse_issue
from repro.detector.detector import detect_runtime, universal
from repro.docker.runner import (
    run_sandbox, DockerNotRunningError, DockerNotFoundError,
    parse_port_spec, InvalidPortError, InvalidRepoError
    )

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="repro",
        description="Disposable Docker environments for GitHub issues.",
        epilog=(
            "Examples:\n"
            "  repro https://github.com/org/repo/issues/42\n"
            "  repro https://github.com/org/repo/issues/42 -p 3000\n"
            "  repro https://github.com/org/private-repo/issues/7 --token ghp_xxx\n"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("issue_url", nargs="?", help="GitHub issue URL")
    parser.add_argument(
        "-p", "--port",
        action="append",
        default=[],
        metavar="PORT",
        help="Forward a port from the sandbox to your machine. "
             "Use PORT for same host/container port, or HOST:CONTAINER to map them."
             "Can be passed multiple times.",
    )
    parser.add_argument(
        "-t", "--token",
        default=None,
        metavar="TOKEN",
        help="GitHub personal access token, for private repos. "
             "Falls back to the REPRO_GITHUB_TOKEN env var if not passed.",
    )
    parser.add_argument(
        "-v", "--version",
        action="version",
        version=f"repro {__version__}",
    )
    return parser

def main():

    parser = build_parser()
    args = parser.parse_args()

    if not args.issue_url:
        parser.print_help()
        return

    if "github.com" not in args.issue_url or "/issues/" not in args.issue_url:
        print(f'ERROR: Expected a GitHub issue URL, got "{args.issue_url}"')
        print("Usage: python repro.py <issue-url> [-p PORT ...] [--token TOKEN]")
        sys.exit(1)


    try:
        ports = [parse_port_spec(p) for p in args.port]
    except InvalidPortError as e:
        print(f"error: {e}")
        sys.exit(1)

    token = args.token or os.environ.get("REPRO_GITHUB_TOKEN")

    run(args.issue_url, ports, token)

def run(issue_url: str, ports:list, token: str = None):

    # Parsing the issue
    print("Fetching issue info...")
    try:
        issue = parse_issue(issue_url, token)
    except ValueError as e:
        print(f"error: {e}")
        sys.exit(1)

    print(f"ISSUE #{issue['number']}: {issue['title']}")
    print(f"REPO: {issue['owner']}/{issue['repo']}\n")
    if token:
        print(" Using authenticated access (private repo support enabled)")
    print()

    # Detecting the runtime
    print("Detecting runtime...")
    runtime = detect_runtime(issue["owner"], issue["repo"], token)
    if runtime is None:
        print("Could not detect runtime, using universal base image")
        runtime = universal()

    print(f"Detected: {runtime['name']} (image: {runtime['image']})\n")

    if ports:
        mapping = ", ".join(f"{h}->{c}" for h, c in ports)
        print(f"Forwarding ports: {mapping}\n")

    print(" Spinning up sandbox...")
    try:
        run_sandbox(issue, runtime, ports, token)
    except DockerNotFoundError as e:
        print(f"\n❌ {e}")
        sys.exit(1)
    except DockerNotRunningError as e:
        print(f"\n❌ {e}")
        sys.exit(1)
    except InvalidRepoError as e:
        print(f"\n❌ {e}")
        sys.exit(1)

# def print_usage():
#     print("""repro - disposable Docker environments for GitHub issues

# Usage:
#     python repro.py <issue-url>       Open a sandbox for a GitHub issue
#     python repro.py --version         Print version
#     python repro.py --help            Show this help

# Examples:
#     python repro.py https://github.com/org/repo/issues/42
#     python repro.py https://github.com/golang/go/issues/1234
#     """
# )