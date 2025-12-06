
import pytest

# This is a bit of a hack to make the app importable
# In a real project, you'd structure this as a proper Python package
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

from main import build_command

# Expected path to the executable. All tests will check against this.
EXECUTABLE_PATH = "../slsk-batchdl/bin/Debug/net6.0/sldl"

def test_build_command_simple_text():
    """Tests basic text input."""
    command = build_command(input_text="Artist - Song")
    assert command == [EXECUTABLE_PATH, "Artist - Song"]

def test_build_command_spotify_precedence():
    """Tests that Spotify URL takes precedence over other inputs."""
    command = build_command(
        input_text="some other text",
        input_file_path="/path/to/file.csv",
        spotify_playlist_url="https://open.spotify.com/playlist/123"
    )
    assert command == [EXECUTABLE_PATH, "https://open.spotify.com/playlist/123"]

def test_build_command_file_path_precedence():
    """Tests that a file path takes precedence over text input."""
    command = build_command(
        input_text="some other text",
        input_file_path="/path/to/file.csv"
    )
    assert command == [EXECUTABLE_PATH, "/path/to/file.csv"]

def test_build_command_boolean_flags():
    """Tests that boolean flags are correctly appended."""
    command = build_command(
        input_text="test", 
        desperate=True, 
        album=True
    )
    assert command == [EXECUTABLE_PATH, "test", "--desperate", "--album"]

def test_build_command_database():
    """Tests that the database flag correctly adds two arguments."""
    command = build_command(input_text="test", use_database=True)
    assert command == [EXECUTABLE_PATH, "test", "--index-path", "slsk_downloads.index", "--skip-existing"]

def test_build_command_user_pass():
    """Tests that user and password are correctly added."""
    command = build_command(input_text="test", user="testuser", password="testpass")
    assert command == [EXECUTABLE_PATH, "test", "--user", "testuser", "--pass", "testpass"]

def test_build_command_all_options():
    """Tests a combination of all options."""
    command = build_command(
        spotify_playlist_url="https://spotify.com/playlist/abc",
        user="testuser",
        password="testpass",
        album=True,
        interactive=True,
        use_database=True,
        remove_ft=True
    )
    expected = [
        EXECUTABLE_PATH,
        "https://spotify.com/playlist/abc",
        "--user", "testuser",
        "--pass", "testpass",
        "--remove-ft",
        "--album",
        "--interactive",
        "--index-path", "slsk_downloads.index",
        "--skip-existing"
    ]
    # Order of boolean flags doesn't matter, so we check for presence
    assert len(command) == len(expected)
    assert sorted(command) == sorted(expected)

def test_build_command_no_input():
    """Tests that the command is correct when no input is provided."""
    command = build_command()
    assert command == [EXECUTABLE_PATH]

