import sys 
from repro import __version__
from repro.github.issue import parse_issue
from repro.detector.detector import detect_runtime, universal
from repro.docker.runner import run_sandbox, DockerNotRunningError, DockerNotFoundError



def main():
    if len(sys.argv) < 2 or sys.argv[1] in ("-h", "-help"):
        print_usage()
        return

    if sys.argv[1] in ("-v", "--version"):
        print(f"repro {__version__}")
        return

    issue_url = sys.argv[1]

    if "github.com" not in issue_url or "/issues/" not in issue_url:
        print(f'ERROR: Expected a GitHub issue URL, got "{issue_url}"')
        print("Usage: python repro.py <issue-url>")
        sys.exit(1)

    run(issue_url)

def run(issue_url: str):

    # Parsing the issue
    print("Fetching issue info...")
    try:
        issue = parse_issue(issue_url)
    except ValueError as e:
        print(f"error: {e}")
        sys.exit(1)

    print(f"ISSUE #{issue['number']}: {issue['title']}")
    print(f"REPO: {issue['owner']}/{issue['repo']}\n")

    # Detecting the runtime
    print("Detecting runtime...")
    runtime = detect_runtime(issue["owner"], issue["repo"])
    if runtime is None:
        print("Could not detect runtime, using universal base image")
        runtime = universal()

    print(f"Detected: {runtime['name']} (image: {runtime['image']})\n")

    print(" Spinning up sandbox...")
    try:
        run_sandbox(issue, runtime)
    except DockerNotFoundError as e:
        print(f"\n❌ {e}")
        sys.exit(1)
    except DockerNotRunningError as e:
        print(f"\n❌ {e}")
        sys.exit(1)

def print_usage():
    print("""repro - disposable Docker environments for GitHub issues

Usage:
    python repro.py <issue-url>       Open a sandbox for a GitHub issue
    python repro.py --version         Print version
    python repro.py --help            Show this help

Examples:
    python repro.py https://github.com/org/repo/issues/42
    python repro.py https://github.com/golang/go/issues/1234
    """
)