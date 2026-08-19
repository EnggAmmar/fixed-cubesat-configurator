FROM python:3.11-slim

WORKDIR /app/backend

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app:/app/backend

# Install backend requirements (kept in backend/).
COPY requirements.txt requirements-dev.txt /app/backend/
RUN pip install --no-cache-dir -r /app/backend/requirements.txt -r /app/backend/requirements-dev.txt

# Copy the full backend runtime payload needed by the CP-SAT solver.
# Required at runtime:
# - backend/solver/
# - backend/solver_libs/
# - backend/solver_precompute/
# - backend/solver_docs/
# - backend/data_base/
# - backend/app/
COPY . /app/backend

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
