from unittest.mock import patch, MagicMock
import json
from repro.detector.detector import detect_runtime, universal

def _mock_response(file_list):
    body = json.dumps([{"name":name} for name in file_list]).encode()
    mock_resp = MagicMock()
    mock_resp.read.return_value = body
    mock_resp.__enter__.return_value = mock_resp
    return mock_resp

def test_detects_node_from_package_json():
    with patch("urllib.request.urlopen", return_value=_mock_response(["package.json", "README.md"])):
        runtime = detect_runtime("owner", "repo")
    assert runtime["name"] == "Node.js"
    assert runtime["image"] == "node:20-alpine"

def test_detecs_python_from_requirements_txt():
    with patch("urllib.request.urlopen", return_value=_mock_response(["requirements.txt"])):
        runtime = detect_runtime("owner", "repo")
    assert runtime["name"] == "Python"

def test_detects_go_from_go_mod():
    with patch("urllib.request.urlopen", return_value=_mock_response(["go.mod","main.go"])):
        runtime = detect_runtime("owner", "repo")
    assert runtime["name"] =="Go"

def test_devcontainer_takes_priority_over_package_json():
    with patch("urllib.request.urlopen", return_value=_mock_response([".devcontainer", "package.json"])):
        runtime = detect_runtime("owner", "repo")
    assert runtime["name"] == "devcontainer"

def test_returns_none_on_network_error():
    with patch("urllib.request.urlopen", side_effect=Exception("network down")):
        runtime = detect_runtime("owner", "repo")
    assert runtime is None

def test_universal_fallback_has_correct_shape():
    fallback = universal()
    assert fallback["name"] == "universal"
    assert fallback["image"] == "ubuntu:22.04"