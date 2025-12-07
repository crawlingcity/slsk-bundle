# Stage 1: Build the C# application
FROM mcr.microsoft.com/dotnet/sdk:6.0 AS build
WORKDIR /source

# Copy the C# project files
COPY slsk-batchdl/ .

# Restore dependencies
RUN dotnet restore slsk-batchdl.sln

# Build and publish the C# application for Linux
RUN dotnet publish slsk-batchdl/slsk-batchdl.csproj -c Release -o /app/bin/Release/net6.0/ --runtime linux-x64 --self-contained true

# Stage 2: Set up the Python GUI
FROM python:3.9-slim
WORKDIR /app

# Install libicu for .NET globalization
RUN apt-get update && apt-get install -y libicu-dev && rm -rf /var/lib/apt/lists/*

# Copy the Python GUI application
COPY slsk-batchdl-gui/ .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy all published files (executable + dependencies)
COPY --from=build /app/bin/Release/net6.0/ ./

# Create the downloads directory
RUN mkdir -p /downloads

# Change ownership of /app and downloads directory to user 1000
RUN chown -R 1000:1000 /app /downloads

# Expose the port for the GUI
EXPOSE 8000

# Start the GUI
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
