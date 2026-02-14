#!/bin/bash
set -e

echo "=== Starting TalentMatch Application ==="

# Wait for MySQL using Python (most reliable method)
echo "Waiting for MySQL to be ready..."
python3 << PYTHON_SCRIPT
import MySQLdb
import sys
import time

max_retries = 30
retry_count = 0

while retry_count < max_retries:
    try:
        conn = MySQLdb.connect(
            host='${DB_HOST}',
            user='${DB_USER}',
            passwd='${DB_PASSWORD}',
            db='${DB_NAME}'
        )
        conn.close()
        print('✓ MySQL is ready!')
        break
    except Exception as e:
        retry_count += 1
        print(f'Attempt {retry_count}/{max_retries}: Waiting for MySQL...')
        time.sleep(3)

if retry_count >= max_retries:
    print('ERROR: Could not connect to MySQL')
    sys.exit(1)
PYTHON_SCRIPT

# Wait for Qdrant
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

# Apply database migrations
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