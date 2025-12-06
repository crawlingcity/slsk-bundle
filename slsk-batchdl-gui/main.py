import asyncio
import subprocess
import tempfile
import json
from pathlib import Path
from typing import Optional, List

from fastapi import FastAPI, File, Form, UploadFile, Request
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

app = FastAPI()

BASE_DIR = Path(__file__).resolve().parent
app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")
templates = Jinja2Templates(directory=BASE_DIR / "templates")

def build_command(
    input_text: str = "",
    input_file_path: Optional[str] = None,
    spotify_playlist_url: Optional[str] = None,
    path: Optional[str] = None,
    user: Optional[str] = None,
    password: Optional[str] = None,
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
    if path:
        command.extend(["--path", path])
    if user:
        command.extend(["--user", user])
    if password:
        command.extend(["--pass", password])

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


@app.post("/run")
async def run_command(
    request: Request,
    input_text: str = Form(""),
    input_file: UploadFile = File(None),
    spotify_playlist_url: str = Form(None),
    path: str = Form(None),
    user: str = Form(None),
    password: str = Form(None),
    desperate: bool = Form(False),
    fast_search: bool = Form(False),
    remove_ft: bool = Form(False),
    artist_maybe_wrong: bool = Form(False),
    album: bool = Form(False),
    interactive: bool = Form(False),
    use_database: bool = Form(False),
):
    """This endpoint runs the slsk-batchdl command and streams the output."""

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
        path=path,
        user=user,
        password=password,
        desperate=desperate,
        fast_search=fast_search,
        remove_ft=remove_ft,
        artist_maybe_wrong=artist_maybe_wrong,
        album=album,
        interactive=interactive,
        use_database=use_database,
    )

    # This inner function is a generator that runs the command and yields output.
    # It's used with StreamingResponse to send data to the frontend in real-time.
    async def stream_output():
        # Start the sldl process.
        # stdout and stderr are piped so we can read them.
        # The working directory is set to the app's root to ensure downloads go to the right place.
        process = await asyncio.create_subprocess_exec(
            *command,
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

        if return_code == 0:
            # Send a success signal to the frontend.
            yield f"data: {json.dumps({'event': 'DONE'})}\n\n"
        else:
            # Send a crash signal with the exit code to the frontend.
            yield f"data: {json.dumps({'event': 'CRASH', 'code': return_code})}\n\n"
    return StreamingResponse(stream_output(), media_type="text/event-stream")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
