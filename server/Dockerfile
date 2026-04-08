FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .
# Hugging Face Spaces (Docker) expects the app to listen on $PORT (typically 7860).
ENV HOST=0.0.0.0
ENV PORT=7860
CMD ["python", "-m", "server.app"]

