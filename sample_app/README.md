# Sample App - Docksmith Demo

This directory contains a sample application that demonstrates all Docksmith features:

## Files
- **Docksmithfile**: Build configuration using all 6 required instructions
- **app.py**: Python application that prints environment variables and system info

## Instructions Used

1. **FROM alpine:3.18** - Base image
2. **WORKDIR /app** - Set working directory
3. **COPY app.py /app/** - Copy application file from build context
4. **ENV APP_NAME=MyApp** - Set environment variable (can be overridden with -e)
5. **ENV MESSAGE=HelloFromDocksmith** - Another environment variable
6. **RUN apk add --no-cache python3** - Execute command inside image (installs Python)
7. **CMD ["python3", "app.py"]** - Default command to run

## Demo Commands

```bash
# First build (cold)
docksmith build -t myapp:latest .

# Rebuild (warm - should show cache hits)
docksmith build -t myapp:latest .

# Modify a file and rebuild (should cascade misses)
echo "# Modified" >> app.py
docksmith build -t myapp:latest .

# List images
docksmith images

# Run container
docksmith run myapp:latest

# Run with environment override
docksmith run -e MESSAGE=CustomMessage myapp:latest

# Clean up
docksmith rmi myapp:latest
```
