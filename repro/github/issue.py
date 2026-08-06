import re 
import urllib.request
import json


ISSUE_PATTERN = re.compile(r"github\.com/([^/]+)/([^/]+)/issues/(\d+)")

def parse_issue(url: str) -> dict:
    match = ISSUE_PATTERN.search(url)
    if not match:
        raise ValueError(f"Invalid Github issue URL: {url}")

    owner, repo, number = match.group(1), match.group(2), int(match.group(3))

    issue = {
        "owner": owner,
        "repo": repo,
        "number": number,
        "title": "(could not fetch title)",
        "body" : "",
    }

    # trying github api, for public repos without auth

    api_url = f"https://api.github.com/repos/{owner}/{repo}/issues/{number}"
    try:
        req = urllib.request.Request(
            api_url,
            headers={"User-Agent": "repr/0.1.0", "Accept": "applications/vnd.github+json"},
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read())
            issue["title"] = data.get("title", issue["title"])
            issue["body"] = data.get("body", "")

    except Exception:
        pass

    return issue