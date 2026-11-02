FROM python:3.12-slim

WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=3000 \
    APP_ENV=production \
    AUTO_CREATE_SCHEMA=false

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
RUN mkdir -p instance

EXPOSE 3000
CMD sh -c 'flask --app app db upgrade && python -m scripts.seed && exec gunicorn --bind 0.0.0.0:${PORT} --workers 2 --access-logfile - --error-logfile - app:app'
