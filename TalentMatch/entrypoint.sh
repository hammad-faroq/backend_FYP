#!/bin/bash
set -e

echo "=== Starting TalentMatch Application ==="

# Skip waiting for MySQL manually. Railway provides DATABASE_URL,
# Django with dj-database-url will handle the connection.
# So we remove the old MySQL wait block.

# Wait for Qdrant (keep this if using Qdrant service)
echo "Waiting for Qdrant to be ready..."
max_retries=30
retry_count=0
until curl -sf "${QDRANT_URL}/collections" > /dev/null 2>&1; do
    retry_count=$((retry_count + 1))
    if [ $retry_count -ge $max_retries ]; then
        echo "ERROR: Qdrant did not become ready in time"
        exit 1
    fi
    echo "Waiting for Qdrant... attempt $retry_count/$max_retries"
    sleep 2
done
echo "✓ Qdrant is ready!"

# Apply database migrations (Django will use DATABASE_URL from env)
echo "Applying database migrations..."
python manage.py migrate --noinput
echo "✓ Migrations applied!"

# Collect static files
echo "Collecting static files..."
python manage.py collectstatic --noinput
echo "✓ Static files collected!"

echo "=== Starting Django with Gunicorn ==="
exec gunicorn talentmatch.wsgi:application \
    --bind 0.0.0.0:8000 \
    --workers 4 \
    --timeout 120 \
    --access-logfile - \
    --error-logfile -
