import pytest
from repro.docker.runner import validate_repo_identifiers, InvalidRepoError


def test_accepts_normal_owner_repo():
    validate_repo_identifiers("epressjs", "express")

def test_accpets_hyphens_and_underscores():
    validate_repo_identifiers("my-org", "my_repo.name")

def test_rejects_shell_injection_semicolon():
    with pytest.raises(InvalidRepoError):
        validate_repo_identifiers("owner; rm -rf /", "repo")

def test_rejects_shell_injection_backtick():
    with pytest.raises(InvalidRepoError):
        validate_repo_identifiers("owner`whoami`", "repo")

def test_rejects_shell_injection_dollar():
    with pytest.raises(InvalidRepoError):
        validate_repo_identifiers("owner$(whoami)", "repo")


def test_rejects_path_traversal_dotdot():
    with pytest.raises(InvalidRepoError):
        validate_repo_identifiers("owner", "..")


def test_rejects_single_dot():
    with pytest.raises(InvalidRepoError):
        validate_repo_identifiers("owner", ".")


def test_rejects_leading_dot():
    with pytest.raises(InvalidRepoError):
        validate_repo_identifiers("owner", ".hidden")


def test_rejects_slash_in_repo_name():
    with pytest.raises(InvalidRepoError):
        validate_repo_identifiers("owner", "repo/../../etc")


def test_rejects_space():
    with pytest.raises(InvalidRepoError):
        validate_repo_identifiers("owner name", "repo")