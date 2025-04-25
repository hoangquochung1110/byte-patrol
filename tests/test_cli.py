import subprocess
import sys

def test_help_shows_usage():
    result = subprocess.run(
        [sys.executable, "-m", "byte_patrol.cli", "--help"],
        capture_output=True
    )
    assert result.returncode == 0
    assert "Review code documentation via an LLM" in result.stdout.decode()

def test_missing_file_errors():
    result = subprocess.run(
        [sys.executable, "-m", "byte_patrol.cli", "nonexistent.py"],
        capture_output=True
    )
    assert result.returncode != 0
    assert "not found" in result.stderr.decode()
