"""Pylint quality gate — ensures the integration source stays clean."""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
SOURCE_PATH = REPO_ROOT / "custom_components" / "marstek_local_api"
PYLINTRC = REPO_ROOT / ".pylintrc"


def test_pylint_integration_source() -> None:
    """Run pylint on the integration source."""

    assert PYLINTRC.exists(), ".pylintrc not found"
    assert SOURCE_PATH.exists(), "Integration source not found"

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "pylint",
            "--rcfile",
            str(PYLINTRC),
            "--fail-under=10.0",
            str(SOURCE_PATH),
        ],
        capture_output=True,
        text=True,
        check=False,
        timeout=300,
    )

    if result.returncode != 0:
        output = "\n".join(
            part for part in (result.stdout, result.stderr) if part
        )

        report = "\n".join(
            line
            for line in output.splitlines()
            if line.strip() and not line.startswith("---")
        )

        pytest.fail(f"Pylint reported issues:\n\n{report}")
