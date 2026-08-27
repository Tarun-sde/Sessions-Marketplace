#!/bin/sh
set -e

echo "Waiting for PostgreSQL..."
python << END
import sys
import time
import os
import psycopg2

db_name = os.environ.get('POSTGRES_DB', 'ahoum_db')
user = os.environ.get('POSTGRES_USER', 'postgres')
password = os.environ.get('POSTGRES_PASSWORD', 'postgres_password')
host = os.environ.get('POSTGRES_HOST', 'db')
port = os.environ.get('POSTGRES_PORT', '5432')

start = time.time()
while time.time() - start < 60:
    try:
        conn = psycopg2.connect(
            dbname=db_name,
            user=user,
            password=password,
            host=host,
            port=port
        )
        conn.close()
        print("PostgreSQL is ready!")
        sys.exit(0)
    except psycopg2.OperationalError:
        time.sleep(1)

print("Timeout waiting for PostgreSQL", file=sys.stderr)
sys.exit(1)
END

echo "Applying database migrations..."
python manage.py makemigrations
python manage.py migrate

exec "$@"
