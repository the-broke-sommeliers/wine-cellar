#!/bin/sh
set -e

if [ "$DATABASE" = "postgres" ]
then
    echo "Waiting for postgres..."

    while ! nc -z $SQL_HOST $SQL_PORT; do
      sleep 0.1
    done

    echo "PostgreSQL started"
fi

if [ "$CONTAINER_ROLE" = "web" ]
then

chown -R $(id -u):$(id -g) /home/app/web/staticfiles || true
python manage.py migrate

if ! cmp -s staticfiles_build/staticfiles.json staticfiles/staticfiles.json; then
    echo "Updating static files..."
    find staticfiles -mindepth 1 -delete
    cp -a staticfiles_build/. staticfiles/
fi

cat <<EOF | python manage.py shell || echo "Warning: admin superuser bootstrap failed" >&2
from django.contrib.auth import get_user_model

User = get_user_model()  # get the currently active user model,

User.objects.filter(username='$ADMIN_USER').exists() or \
    User.objects.create_superuser('$ADMIN_USER', '$ADMIN_USER_EMAIL', '$ADMIN_USER_PASSWORD')
EOF
fi

exec "$@"
