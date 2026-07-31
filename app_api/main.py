"""Заглушка FastAPI-сервиса.

Вся текущая логика живёт во Flask (main.py). Этот сервис зарезервирован под
будущий REST/async API и проксируется nginx по префиксу /api/. Пока он просто
держит контейнер живым и отвечает на health-check, чтобы сборка и деплой
проходили без ошибок.
"""
from fastapi import FastAPI

app = FastAPI(title="MYKHODYNKA API", description="Заглушка под будущий API")


@app.get("/api/health")
def health():
    return {"status": "ok", "service": "fastapi"}
