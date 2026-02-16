FROM python:3.12-slim

WORKDIR /app

COPY tasks/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY tasks/ ./tasks/

VOLUME /app/data

ENV TASKS_DB_PATH=/app/data/tasks.db

EXPOSE 8000

CMD ["uvicorn", "tasks.api:app", "--host", "0.0.0.0", "--port", "8000"]
