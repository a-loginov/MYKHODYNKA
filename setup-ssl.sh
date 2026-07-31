#!/bin/bash
set -e

DOMAIN=mykhodynka.ru
EMAIL=a-loginov@school1409.ru

mkdir -p certbot/www certbot/conf

docker-compose up -d nginx

docker-compose run --rm --entrypoint "\
  certonly --webroot -w /var/www/certbot \
    --email $EMAIL \
    -d $DOMAIN \
    -d www.$DOMAIN \
    --agree-tos \
    --force-renewal" certbot/certbot

docker-compose restart nginx

(crontab -l 2>/dev/null; echo "0 3 * * * cd $(pwd) && docker compose run --rm certbot/certbot renew && docker compose restart nginx") | crontab -

echo "SSL готов. Сертификат будет продлеваться автоматически раз в сутки в 3:00."
