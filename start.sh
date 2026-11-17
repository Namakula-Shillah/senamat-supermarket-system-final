
#!/usr/bin/env bash
set -e

python manage.py migrate --noinput
python bootstrap_demo_admin.py

exec gunicorn supermarket.wsgi:application --bind 0.0.0.0:${PORT:-10000}
