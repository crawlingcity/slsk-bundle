# slsk-batchdl-gui

A simple, cross-platform web-based graphical user interface for the `sldl` command-line tool. This application provides an easy-to-use interface to control the power of `slsk-batchdl` without needing to use the command line.

## Features

- **Simple Web Interface:** Controls for all major `sldl` options, including input types, user credentials, and download flags.
- **Multiple Inputs:** Supports direct text/URL input, Spotify playlist URLs, and CSV file uploads.
- **Real-time Output:** Streams the output from the `sldl` command directly to your web browser, with color-coding for errors and failures.
- **Cross-Platform:** The Python-based web server runs on Windows, macOS, and Linux.

## Requirements

1.  **Python 3.7+:** Must be installed on your system.
2.  **sldl Executable:** The compiled `sldl` executable (`sldl.exe` on Windows, `sldl` on macOS/Linux) must be located in the parent directory of this project.

## Setup and Usage

1.  **Clone the repository:**
    ```bash
    git clone https://github.com/yayoboy/slsk-batchdl-gui.git
    cd slsk-batchdl-gui
    ```

2.  **Install Dependencies:**
    ```bash
    pip3 install -r requirements.txt
    ```

3.  **Place the sldl executable:**
    Download the `sldl` executable from the [slsk-batchdl releases](https://github.com/fiso64/slsk-batchdl/releases) and place it in the parent directory of this project.

4.  **Run the Web Server:**
    ```bash
    python3 main.py
    ```
    The server will start on `http://0.0.0.0:8000`.

5.  **Access the GUI:**
    Open your web browser and navigate to:
    [http://127.0.0.1:8000](http://127.0.0.1:8000)

You can now use the web interface to run your `sldl` commands.

---

## Acknowledgements

This Web GUI is a companion tool for the original **slsk-batchdl** project, created by [fiso64](https://github.com/fiso64).

The main project repository can be found here: [https://github.com/fiso64/slsk-batchdl](https://github.com/fiso64/slsk-batchdl)

