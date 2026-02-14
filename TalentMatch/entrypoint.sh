#!/bin/bash
set -e

echo "=== Starting TalentMatch Application ==="

########################################
# Wait for MySQL
########################################

echo "Waiting for MySQL to be ready..."

max_retries=30
retry_count=0

until python - <<EOF
import sys
import django
from django.conf import settings
from django.db import connections

django.setup()
conn = connections['default']
conn.cursor()
print("MySQL connection successful!")
EOF
do
    retry_count=$((retry_count + 1))
    if [ $retry_count -ge $max_retries ]; then
        echo "ERROR: MySQL did not become ready in time"
        exit 1
    fi
    echo "Waiting for MySQL... attempt $retry_count/$max_retries"
    sleep 2
done

echo "✓ MySQL is connected!"

########################################
# Wait for Qdrant
########################################

echo "Waiting for Qdrant to be ready..."

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

echo "✓ Qdrant is connected!"

########################################
# Django setup
########################################

echo "Applying database migrations..."
python manage.py migrate --noinput
echo "✓ Migrations applied!"

echo "Collecting static files..."
python manage.py collectstatic --noinput
echo "✓ Static files collected!"

########################################
# Start server
########################################

echo "=== Starting Django with Gunicorn ==="

exec gunicorn talentmatch.wsgi:application \
    --bind 0.0.0.0:$PORT \
    --workers 4 \
    --timeout 120 \
    --access-logfile - \
    --error-logfile -
