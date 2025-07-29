FROM python:3.11-alpine

WORKDIR /app

# Install system dependencies for SQLite
RUN apk add --no-cache \
    gcc \
    musl-dev \
    sqlite \
    sqlite-dev

# Copy requirements first for better caching
COPY requirements.txt requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create instance directory for SQLite database and uploads
RUN mkdir -p instance uploads static/uploads

# Set environment variables
ENV FLASK_APP=app.py
ENV FLASK_ENV=production
ENV PYTHONPATH=/app
ENV PORT=56666

# Expose port
EXPOSE 56666

# Create non-root user and set permissions
RUN adduser -D -u 1000 appuser && \
    chown -R appuser:appuser /app
USER appuser

# Run the application
CMD ["python", "app.py"] 