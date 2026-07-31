#!/bin/bash
set -e

PROJECT_DIR="/opt/app/MY1409"

echo "--- Перехожу в директорию проекта $PROJECT_DIR ---"
cd "$PROJECT_DIR" || { echo "Ошибка: директория $PROJECT_DIR не найдена"; exit 1; }

echo "--- Скачиваю последние изменения из Git ---"
git pull

echo "--- Пересобираю и перезапускаю Docker контейнеры ---"
docker compose up -d --build --force-recreate

echo "--- Чищу старые образы ---"
docker image prune -f

echo "--- Развёртывание успешно завершено! ---"
