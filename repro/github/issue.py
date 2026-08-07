import re 
import urllib.request
import urllib.error
import json


ISSUE_PATTERN = re.compile(r"github\.com/([^/]+)/([^/]+)/issues/(\d+)")

def parse_issue(url: str, token: str = None) -> dict:
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
    headers = {"User-Agent": "repro/0.1.0", "Accept": "applications/vnd.github+json"}

    if token:
        headers["Authorization"] = f"Bearer {token}"

    try:
        req = urllib.request.Request(
            api_url,
            headers=headers,
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read())
            issue["title"] = data.get("title", issue["title"])
            issue["body"] = data.get("body", "")

    except urllib.error.HTTPError as e:
        if e.code == 404:
            if token:
                issue["title"] = "(not found - check the URL, or the token lacks access)"
            else:
                issue["title"] = "(not found - if this is a private repo, pass --token)"
        elif e.code == 401:
            issue["title"] = "(bad or expired token - check --token)"
        elif e.code == 403:
            issue["title"] = "(GitHub API rate limit hit - continuing anyway)"
        else:
            issue["title"] = f"(GitHub API returned {e.code})"
    except urllib.error.URLError:
        issue["title"] = "(no internet connection - continuing anyway)"
    except Exception:
        pass
    
    return issue