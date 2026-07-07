#!/bin/sh
# Apply migrations before handing control to the server command.
set -e

python manage.py migrate --noinput

exec "$@"
