FROM python:3.13-slim

WORKDIR /app

COPY pyproject.toml README.md LICENSE ./
COPY src/ src/

RUN pip install --no-cache-dir ".[web]"

EXPOSE 8000

CMD ["uvicorn", "file2md.web:app", "--host", "0.0.0.0", "--port", "8000"]
