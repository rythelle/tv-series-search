# Stage 1: build the Vue frontend
FROM node:22-slim AS frontend-build
WORKDIR /frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ .
RUN npm run build

# Stage 2: Python runtime
FROM python:3.12-slim AS runtime
WORKDIR /app

RUN addgroup --system app && adduser --system --ingroup app app

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY src/ ./src/
COPY --from=frontend-build /frontend/dist ./frontend/dist

ENV PYTHONPATH=/app/src

USER app

EXPOSE 7777

CMD ["uvicorn", "interface.http.app:create_app", "--factory", "--host", "0.0.0.0", "--port", "7777"]
