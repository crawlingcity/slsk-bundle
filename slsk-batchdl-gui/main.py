import asyncio
import subprocess
import tempfile
import json
import os
import re
from pathlib import Path
from typing import Optional, List, Dict, Any
from difflib import SequenceMatcher

import httpx
from fastapi import FastAPI, File, Form, UploadFile, Request
from fastapi.responses import HTMLResponse, StreamingResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

app = FastAPI()

BASE_DIR = Path(__file__).resolve().parent
app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")
templates = Jinja2Templates(directory=BASE_DIR / "templates")

async def fetch_itunes_album(artist: str, album: str) -> Optional[str]:
    """Search iTunes for Album Art"""
    try:
        query = f"{artist} {album}"
        url = "https://itunes.apple.com/search"
        params = {"term": query, "media": "music", "entity": "album", "limit": 1}
        async with httpx.AsyncClient() as client:
            resp = await client.get(url, params=params, timeout=5.0)
            if resp.status_code == 200:
                data = resp.json()
                if data["resultCount"] > 0:
                    # Get 100x100 and try to upscale effectively by hack?
                    # iTunes provides 100x100, but we can change the URL to 600x600
                    art = data["results"][0].get("artworkUrl100")
                    if art:
                        return art.replace("100x100bb", "600x600bb")
    except Exception as e:
        print(f"DEBUG: iTunes fetch error: {e}")
    return None

async def fetch_deezer_artist(artist: str) -> Optional[str]:
    """Search Deezer for Artist Image"""
    try:
        url = "https://api.deezer.com/search/artist"
        params = {"q": artist, "limit": 1}
        async with httpx.AsyncClient() as client:
            resp = await client.get(url, params=params, timeout=5.0)
            if resp.status_code == 200:
                data = resp.json()
                if data.get("data"):
                    return data["data"][0].get("picture_xl") # High res artist image
    except Exception as e:
        print(f"DEBUG: Deezer fetch error: {e}")
    return None

async def fetch_metadata(artist: str, album: str) -> Optional[str]:
    """
    Fetches album art URL from iTunes, falling back to Deezer Artist image.
    """
    if not artist:
        return None

    # 1. Try iTunes Album Art
    if album and album != "Unknown":
        art = await fetch_itunes_album(artist, album)
        if art: return art

    # 2. Try Deezer Artist Image (Fallback)
    art = await fetch_deezer_artist(artist)
    if art: return art

    return None

def parse_slsk_json(json_output: str) -> List[Dict[str, Any]]:
    """
    Parses slsk-batchdl JSON output and extracts potential albums.
    Returns a list of dictionaries with artist, album, and sample filename.
    """
    candidates = {}

    try:
        results = json.loads(json_output)
        if not isinstance(results, list):
            results = [results]

        for result in results:
            file_info = result.get("File", {})
            filename = file_info.get("Filename", "")

            if not filename:
                continue

            # Normalize path separators
            filename = filename.replace("\\", "/")
            parts = filename.split("/")

            artist = "Unknown"
            album = "Unknown"

            # Robust Parsing Strategy
            # Use the directory structure as the primary source of truth.
            # Typical structure: .../Artist/Album/Track.mp3

            if len(parts) >= 3:
                raw_artist = parts[-3]
                raw_album = parts[-2]

                # Heuristic: If artist folder is generic, try parsing album folder
                # e.g. /Music/Artist - Album/Track.mp3
                generic_folders = ['music', 'mp3', 'flac', 'uploads', 'soulseek', 'downloads', 'complete']
                if raw_artist.lower() in generic_folders and " - " in raw_album:
                     split_album = raw_album.split(" - ", 1)
                     artist = split_album[0]
                     album = split_album[1]
                else:
                    artist = raw_artist
                    album = raw_album
            elif len(parts) == 2:
                 # Just Album/Track.mp3 (Rare but possible in flat shares)
                 # Try to split album folder if it has " - "
                 raw_album = parts[-2]
                 if " - " in raw_album:
                     split_album = raw_album.split(" - ", 1)
                     artist = split_album[0]
                     album = split_album[1]
                 else:
                     # Very ambiguous. Skip or treat as Album.
                     continue

            # CLEANUP LOGIC
            # Remove common junk from Album name to improve MB search

            # 1. Remove years: (2001), [2001], 2001 -
            album = re.sub(r'^[\(\[]?\d{4}[\)\]]?\s*[-]?\s*', '', album)

            # 2. Remove formats: [FLAC], (FLAC), [MP3], [320]
            album = re.sub(r'[\(\[]?(?:FLAC|MP3|320|V0|AAC)[\)\]]?', '', album, flags=re.IGNORECASE)

            # 3. Remove other common tags: [CD], (Web), {Vinyl}
            album = re.sub(r'[\(\[\{].*?[\)\]\}]', '', album)

            # 4. Clean whitespace
            artist = artist.strip()
            album = album.strip()

            if not artist or not album or artist == "Unknown":
                continue

            key = f"{artist}|{album}"
            if key not in candidates:
                candidates[key] = {
                    "artist": artist,
                    "album": album,
                    "files": 1,
                    "sample_file": filename
                }
            else:
                candidates[key]["files"] += 1

        return list(candidates.values())

    except json.JSONDecodeError:
        print("DEBUG: Failed to decode JSON from sldl")
        return []
    except Exception as e:
        print(f"DEBUG: Parsing error: {e}")
        return []


def build_command(
    input_text: str = "",
    input_file_path: Optional[str] = None,
    spotify_playlist_url: Optional[str] = None,
    desperate: bool = False,
    fast_search: bool = False,
    remove_ft: bool = False,
    artist_maybe_wrong: bool = False,
    album: bool = False,
    interactive: bool = False,
    use_database: bool = False,
) -> List[str]:
    """Builds the slsk-batchdl command list from the given options."""
    # Construct the absolute path to the executable, assuming it's in the same directory.
    executable_path = BASE_DIR / "sldl"
    command = [str(executable_path)]

    # Determine the primary input for the command based on a clear precedence:
    # 1. Spotify URL (highest priority)
    # 2. A path to an uploaded CSV file
    # 3. A simple text string (lowest priority)
    if spotify_playlist_url:
        command.append(spotify_playlist_url)
    elif input_file_path:
        command.append(input_file_path)
    elif input_text:
        command.append(input_text)

    # Add optional arguments to the command if they have been provided.
    path = os.getenv("SLSK_PATH", "/downloads")
    command.extend(["--path", path])

    user = os.getenv("SLSK_USER")
    if user:
        command.extend(["--user", user])

    password = os.getenv("SLSK_PASS")
    if password:
        command.extend(["--pass", password])

    # Default to preferring FLAC
    command.extend(["--pref-format", "flac"])

    # Disable progress bars and interactive features in Docker
    command.append("--no-progress")

    # Add boolean flags, which are only present if their value is True.
    if desperate:
        command.append("--desperate")
    if fast_search:
        command.append("--fast-search")
    if remove_ft:
        command.append("--remove-ft")
    if artist_maybe_wrong:
        command.append("--artist-maybe-wrong")
    if album:
        command.append("--album")
    if interactive:
        command.append("--interactive")

    # If the database option is enabled, add the necessary flags.
    # This tells sldl to use a specific file to track downloads and skip existing ones.
    if use_database:
        command.extend(["--index-path", "slsk_downloads.index"])
        command.append("--skip-existing")

    return command


@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


@app.post("/search")
async def search_command(
    request: Request,
    input_text: str = Form(...),
):
    """
    Runs sldl with --print json-all to get results, parses them,
    fetches cover art from MusicBrainz, and returns a JSON list.
    """
    print(f"DEBUG: Visual Search for '{input_text}'")

    # Construct base command for search only
    # We use minimal flags just to find files.
    # --print json-all is the key.

    executable_path = BASE_DIR / "sldl"
    command = [
        str(executable_path),
        input_text,
        "--print", "json-all",
        "--user", os.getenv("SLSK_USER", ""),
        "--pass", os.getenv("SLSK_PASS", ""),
        "--fast-search", # Speed up things for visual search
        "--search-timeout", "30000", # 30s timeout to prevent SIGABRT/timeout
        "--no-progress" # Disable progress bars to avoid Console.KeyAvailable issues in Docker
    ]

    try:
        # Run sldl
        # Note: sldl might take a while to aggregate results.
        process = await asyncio.create_subprocess_exec(
            *command,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd=BASE_DIR
        )

        stdout, stderr = await process.communicate()

        if process.returncode != 0:
            stderr_text = stderr.decode()
            print(f"DEBUG: Search failed with code {process.returncode}")
            print(f"DEBUG: stderr: {stderr_text}")
            return JSONResponse({
                "error": "Search failed",
                "details": stderr_text,
                "returncode": process.returncode
            }, status_code=500)

        output = stdout.decode('utf-8')

        # Parse output
        parsed_results = parse_slsk_json(output)

        # Smart Sorting (Replicating Soularr-like logic)
        # Calculate similarity between input query and "Artist Album"
        # We want to prioritize results that match the user's intent, not just those with most files.
        for res in parsed_results:
            # Construct a target string to compare against (e.g. "Daft Punk Discovery")
            candidate_str = f"{res['artist']} {res['album']}"

            # Simple fuzzy match ratio
            # You could weight this: check if words in input appear in candidate
            score = SequenceMatcher(None, input_text.lower(), candidate_str.lower()).ratio()

            # Boost score if exact words are present (simple containment)
            # This helps if input is "Discovery" and candidate is "Daft Punk Discovery" -> ratio might be lowish but it's a substring
            if input_text.lower() in candidate_str.lower():
                score += 0.2

            res["score"] = score

        # Sort by Score (Desc), then by File Count (Desc)
        parsed_results.sort(key=lambda x: (x["score"], x["files"]), reverse=True)

        # Limit results (fetch metadata only for the best)
        top_results = parsed_results[:10]

        # Fetch metadata for top results
        final_results = []
        for res in top_results:
             # Skip very low relevance results? Soularr uses 0.8
             # But our input might be partial. Let's not be too strict, just sort.

            art_url = await fetch_metadata(res["artist"], res["album"])
            # Use a reliable external placeholder service
            res["art_url"] = art_url or "https://placehold.co/200x200?text=No+Art"
            final_results.append(res)

        return JSONResponse({"results": final_results})

    except Exception as e:
        print(f"DEBUG: Search exception: {e}")
        return JSONResponse({"error": str(e)}, status_code=500)


@app.post("/run")
async def run_command(
    request: Request,
    input_text: str = Form(""),
    input_file: UploadFile = File(None),
    spotify_playlist_url: str = Form(None),
    desperate: bool = Form(False),
    fast_search: bool = Form(False),
    remove_ft: bool = Form(False),
    artist_maybe_wrong: bool = Form(False),
    album: bool = Form(False),
    interactive: bool = Form(False),
    use_database: bool = Form(False),
):
    """This endpoint runs the slsk-batchdl command and streams the output."""
    print(f"DEBUG: Received request with input_text='{input_text}', spotify_url='{spotify_playlist_url}', file='{input_file.filename if input_file else None}'")

    if not any([input_text, (input_file and input_file.filename), spotify_playlist_url]):
        async def stream_error():
             yield "data: " + json.dumps({'text': 'Error: No input provided. Please enter search terms, a URL, or upload a file.\n', 'color': 'red'}) + "\n\n"
             yield "data: " + json.dumps({'event': 'DONE'}) + "\n\n"
        return StreamingResponse(stream_error(), media_type="text/event-stream")

    input_file_path = None
    # If a CSV file is uploaded, save it to the project's root directory.
    if input_file and input_file.filename:
        save_path = BASE_DIR / input_file.filename
        with open(save_path, "wb") as buffer:
            content = await input_file.read()
            buffer.write(content)
        input_file_path = str(save_path)

    # Build the full command list using the dedicated builder function.
    command = build_command(
        input_text=input_text,
        input_file_path=input_file_path,
        spotify_playlist_url=spotify_playlist_url,
        desperate=desperate,
        fast_search=fast_search,
        remove_ft=remove_ft,
        artist_maybe_wrong=artist_maybe_wrong,
        album=album,
        interactive=interactive,
        use_database=use_database,
    )

    print(f"DEBUG: Constructed command: {command}")

    # This inner function is a generator that runs the command and yields output.
    # It's used with StreamingResponse to send data to the frontend in real-time.
    async def stream_output():
        # Start the sldl process.
        # stdout and stderr are piped so we can read them.
        # The working directory is set to the app's root to ensure downloads go to the right place.
        process = await asyncio.create_subprocess_exec(
            *command,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd=BASE_DIR
        )

        # Read and stream stdout line by line.
        while True:
            line = await process.stdout.readline()
            if not line:
                break
            line_text = line.decode('utf-8')
            # Check for keywords to determine if the line should be colored red.
            color = 'default'
            if any(keyword in line_text.lower() for keyword in ['no results', 'not found', 'failed', 'no suitable file']):
                color = 'red'
            # Yield the data as a JSON object for the frontend.
            yield f"data: {json.dumps({'text': line_text, 'color': color})}\n\n"

        # Read and stream any stderr output, always coloring it red.
        while True:
            line = await process.stderr.readline()
            if not line:
                break
            line_text = line.decode('utf-8')
            yield f"data: {json.dumps({'text': line_text, 'color': 'red'})}\n\n"

        # Wait for the process to finish and check its exit code.
        return_code = await process.wait()

        # Relaxed Exit Code Check
        # Exit Code 1 often means "Partial Success" or "Some files failed"
        # We should treat 0 AND 1 as "Done" so the UI shows success.
        if return_code in [0, 1]:
            # Send a success signal to the frontend.
            yield f"data: {json.dumps({'event': 'DONE'})}\n\n"
        else:
            # Send a crash signal with the exit code to the frontend.
            yield f"data: {json.dumps({'event': 'CRASH', 'code': return_code})}\n\n"
    return StreamingResponse(stream_output(), media_type="text/event-stream")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
