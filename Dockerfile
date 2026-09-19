FROM python:3.12-slim
WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
COPY cip ./cip
COPY pyproject.toml ./
RUN pip install --no-cache-dir .
COPY data ./data
COPY reports ./reports
COPY scripts ./scripts
COPY alembic ./alembic
COPY alembic.ini ./alembic.ini
RUN chmod +x scripts/schedule.sh
EXPOSE 8000
CMD ["uvicorn", "cip.api:app", "--host", "0.0.0.0", "--port", "8000"]
