import csv
import re
from datetime import datetime

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from organizations.models import Organization, FileLoad, LoadError


class Command(BaseCommand):
    help = "Загрузка организаций из CSV-файла с валидацией и обработкой дубликатов"

    def add_arguments(self, parser):
        parser.add_argument("filepath", type=str, help="Путь к CSV-файлу")

    def handle(self, *args, **options):
        filepath = options["filepath"]

        # 1. Немедленно создаём запись FileLoad, чтобы любая ошибка зафиксировалась
        file_load = FileLoad.objects.create(filename=filepath, status="PROCESSING", started_at=timezone.now())

        try:
            # 2. Безопасное чтение файла
            try:
                with open(filepath, "r", encoding="utf-8-sig") as f:
                    reader = csv.DictReader(f, delimiter=";")

                    # 3. Проверка заголовков
                    expected_headers = {"inn", "name", "region", "employees", "registration_date"}
                    if not reader.fieldnames or set(reader.fieldnames) != expected_headers:
                        raise ValueError(
                            f"Неверные заголовки CSV. "
                            f"Ожидались: {expected_headers}, "
                            f"получены: {set(reader.fieldnames) if reader.fieldnames else 'None'}"
                        )

                    # Читаем все строки в память для двухпроходной обработки
                    rows = list(reader)
            except FileNotFoundError:
                raise CommandError(f"Файл не найден: {filepath}")
            except PermissionError:
                raise CommandError(f"Нет прав на чтение файла: {filepath}")
            except UnicodeDecodeError:
                raise CommandError("Ошибка кодировки файла. Ожидается UTF-8 (с BOM или без).")
            except csv.Error as e:
                raise CommandError(f"Ошибка парсинга CSV: {e}")
            except Exception as e:
                raise CommandError(f"Критическая ошибка при чтении файла: {e}")

            total = len(rows)
            loaded = 0
            errors = 0
            duplicates = 0

            # 4. Первый проход: подсчёт вхождений ИНН в текущем файле
            inn_counts = {}
            for row in rows:
                inn = str(row.get("inn", "")).strip()
                if re.match(r"^\d{10}$", inn):
                    inn_counts[inn] = inn_counts.get(inn, 0) + 1

            # 5. Второй проход: валидация и сохранение
            for row_num, row in enumerate(rows, start=2):
                # Безопасная сериализация raw_data (защита от None и списков)
                raw_data = ";".join("" if v is None else str(v) for v in row.values())
                error_messages = []

                inn = str(row.get("inn", "")).strip()
                name = str(row.get("name", "")).strip()
                region = str(row.get("region", "")).strip()
                employees_str = str(row.get("employees", "")).strip()
                date_str = str(row.get("registration_date", "")).strip()

                # Валидация ИНН (строго 10 цифр)
                if not re.match(r"^\d{10}$", inn):
                    error_messages.append("ИНН должен содержать ровно 10 цифр")

                # Валидация остальных полей
                if not name:
                    error_messages.append("Наименование не заполнено")
                if not region:
                    error_messages.append("Регион не заполнен")

                employees = None
                if not employees_str:
                    error_messages.append("Количество сотрудников не заполнено")
                else:
                    try:
                        employees = int(employees_str)
                        if employees < 0:
                            error_messages.append("Количество сотрудников не может быть отрицательным")
                    except ValueError:
                        error_messages.append("Количество сотрудников не является целым числом")

                reg_date = None
                if not date_str:
                    error_messages.append("Дата регистрации не заполнена")
                else:
                    # Строгая проверка формата YYYY-MM-DD
                    if not re.match(r"^\d{4}-\d{2}-\d{2}$", date_str):
                        error_messages.append("Некорректный формат даты (ожидается строго YYYY-MM-DD)")
                    else:
                        try:
                            reg_date = datetime.strptime(date_str, "%Y-%m-%d").date()
                        except ValueError:
                            error_messages.append("Некорректная дата (например, 30 февраля)")

                # Проверка на повтор ИНН внутри текущего файла
                if re.match(r"^\d{10}$", inn) and inn_counts.get(inn, 0) > 1:
                    error_messages.append("Повтор ИНН в текущем файле")

                # 6. Обработка ошибок
                if error_messages:
                    errors += 1
                    # Если это дубликат ИНН, дополнительно увеличиваем счётчик
                    if "Повтор ИНН в текущем файле" in error_messages:
                        duplicates += 1

                    LoadError.objects.create(
                        load=file_load, row_number=row_num, raw_data=raw_data, error_message="; ".join(error_messages)
                    )
                    continue

                # 7. Сохранение или обновление (update_or_create)
                try:
                    with transaction.atomic():
                        Organization.objects.update_or_create(
                            inn=inn,
                            defaults={
                                "name": name,
                                "region": region,
                                "employees": employees,
                                "registration_date": reg_date,
                            },
                        )
                        loaded += 1
                except Exception as e:
                    errors += 1
                    LoadError.objects.create(
                        load=file_load,
                        row_number=row_num,
                        raw_data=raw_data,
                        error_message=f"Ошибка базы данных: {str(e)}",
                    )

            # 8. Успешное завершение
            file_load.rows_count = total
            file_load.loaded_count = loaded
            file_load.error_count = errors
            file_load.duplicate_count = duplicates
            file_load.status = "SUCCESS"
            file_load.finished_at = timezone.now()
            file_load.save()

            self.stdout.write(
                self.style.SUCCESS(
                    f"\nФайл: {filepath}\n"
                    f"Обработано строк: {total}\n"
                    f"Успешно загружено/обновлено: {loaded}\n"
                    f"Ошибочных строк: {errors}\n"
                    f"Дубликатов (в файле): {duplicates}\n"
                    f"Статус: SUCCESS\n"
                )
            )

        except CommandError:
            file_load.status = "FAILED"
            file_load.finished_at = timezone.now()
            file_load.save()
            raise
        except Exception as e:
            file_load.status = "FAILED"
            file_load.finished_at = timezone.now()
            file_load.save()
            self.stdout.write(self.style.ERROR(f"\nКРИТИЧЕСКАЯ ОШИБКА: {e}"))
            raise CommandError(f"Загрузка прервана из-за критической ошибки: {e}")
