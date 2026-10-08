# Django-сервис для загрузки реестра организаций

Проект для загрузки и хранения реестра организаций из CSV-файлов с валидацией данных, отслеживанием ошибок и истории загрузок.

## Требования

- Python 3.10+
- PostgreSQL 12+
- Git

## Структура проекта и pre-commit

Django-проект размещён в папке `backend/`: предоставленный руководителем файл `.pre-commit-config.yaml` ориентирован на Python-файлы в `backend/` и не изменялся. Структура приведена к ожидаемой конфигом.

Установка хуков контроля качества (Ruff linter + formatter):
```bash
pip install pre-commit
pre-commit install -t pre-commit -t pre-push