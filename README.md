# slsk-batchdl-gui

This project combines the `slsk-batchdl` C# application with a Python-based web GUI (`slsk-batchdl-gui`) into a single Docker container, making it easy to deploy and use on a server.

## Getting Started

These instructions will get you a copy of the project up and running on your local machine for development and testing purposes.

### Prerequisites

*   [Docker](https://www.docker.com/products/docker-desktop)
*   [Docker Compose](https://docs.docker.com/compose/install/)

### Installation and Usage

1.  **Navigate to the Project Root:**
    Open your terminal and navigate to the root directory of this combined project (where `docker-compose.yml` and `Dockerfile` are located).

2.  **Build the Docker Image:**
    This command will build the Docker image for the combined application. This is a multi-stage build that compiles the C# backend and then sets up the Python frontend.
    ```bash
    docker-compose build
    ```

3.  **Run the Application:**
    Once the image is built, you can start the application in detached mode (in the background) using:
    ```bash
    docker-compose up -d
    ```
    This will start the FastAPI web server, and the `slsk-batchdl` executable will be available for the GUI to call internally.

4.  **Access the Web GUI:**
    Open your web browser and go to `http://localhost:8000`. You should see the `slsk-batchdl-gui` interface, allowing you to interact with the `slsk-batchdl` backend.

5.  **Downloaded Files:**
    Any files downloaded by `slsk-batchdl` will be saved into a local directory named `downloads`. This directory will be created in the same location as your `docker-compose.yml` file.

6.  **Stop the Application:**
    To stop the running application and remove the container, run:
    ```bash
    docker-compose down
    ```

## Project Structure

*   `Dockerfile`: Defines the Docker image for the combined application.
*   `docker-compose.yml`: Orchestrates the build and running of the Docker container.
*   `slsk-batchdl/`: The original C# `slsk-batchdl` project.
*   `slsk-batchdl-gui/`: The original Python `slsk-batchdl-gui` project, with minor modifications to call the C# executable correctly within the Docker environment.
*   `downloads/`: (Automatically created) Directory for downloaded files.
