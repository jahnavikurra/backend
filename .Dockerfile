FROM python:3.11-slim

WORKDIR /app

# Install system deps for cryptography (important)
RUN apt-get update && apt-get install -y \
    build-essential \
    libssl-dev \
    libffi-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY src ./src

ENV PORT=8080
EXPOSE 8080

CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8080"]


curl -X POST http://localhost:8080/api/generate `
  -H "Content-Type: application/json" `
  -d "{\"notesText\":\"...your meeting notes...\",\"workItemType\":\"Product Backlog Item\"}"
