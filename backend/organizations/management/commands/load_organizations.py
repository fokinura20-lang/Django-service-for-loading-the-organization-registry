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
        parser.add_argument("--clear", action="store_true", help="Очистить справочник перед загрузкой")

    def handle(self, *args, **options):
        filepath = options["filepath"]
        clear_db = options["clear"]

        if FileLoad.objects.filter(status="PROCESSING").exists():
            raise CommandError("Загрузка прервана: уже выполняется другая загрузка со статусом PROCESSING.")

        file_load = FileLoad.objects.create(filename=filepath, status="PROCESSING", started_at=timezone.now())

        try:
            if clear_db:
                self.stdout.write(self.style.WARNING("ВНИМАНИЕ: Очистка существующих организаций..."))
                Organization.objects.all().delete()

            try:
                with open(filepath, "r", encoding="utf-8-sig") as f:
                    reader = csv.DictReader(f, delimiter=";")
                    expected_headers = {"inn", "name", "region", "employees", "registration_date"}
                    if not reader.fieldnames or set(reader.fieldnames) != expected_headers:
                        raise ValueError(f"Неверные заголовки CSV. Ожидались: {expected_headers}")
                    rows = list(reader)
            except FileNotFoundError:
                raise CommandError(f"Файл не найден: {filepath}")
            except PermissionError:
                raise CommandError(f"Нет прав на чтение файла: {filepath}")
            except UnicodeDecodeError:
                raise CommandError("Ошибка кодировки файла. Ожидается UTF-8.")
            except csv.Error as e:
                raise CommandError(f"Ошибка парсинга CSV: {e}")
            except Exception as e:
                raise CommandError(f"Критическая ошибка при чтении: {e}")

            total = len(rows)
            loaded = 0
            errors = 0
            duplicates = 0

            inn_counts = {}
            for row in rows:
                inn = str(row.get("inn", "")).strip()
                if re.match(r"^\d{10}$", inn):
                    inn_counts[inn] = inn_counts.get(inn, 0) + 1

            for row_num, row in enumerate(rows, start=2):
                raw_data = ";".join("" if v is None else str(v) for v in row.values())
                error_messages = []

                inn = str(row.get("inn", "")).strip()
                name = str(row.get("name", "")).strip()
                region = str(row.get("region", "")).strip()
                employees_str = str(row.get("employees", "")).strip()
                date_str = str(row.get("registration_date", "")).strip()

                if not re.match(r"^\d{10}$", inn):
                    error_messages.append("ИНН должен содержать ровно 10 цифр")
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
                    if not re.match(r"^\d{4}-\d{2}-\d{2}$", date_str):
                        error_messages.append("Некорректный формат даты (ожидается строго YYYY-MM-DD)")
                    else:
                        try:
                            reg_date = datetime.strptime(date_str, "%Y-%m-%d").date()
                        except ValueError:
                            error_messages.append("Некорректная дата")

                if re.match(r"^\d{10}$", inn) and inn_counts.get(inn, 0) > 1:
                    error_messages.append("Повтор ИНН в текущем файле")

                if error_messages:
                    errors += 1
                    if "Повтор ИНН в текущем файле" in error_messages:
                        duplicates += 1
                    LoadError.objects.create(
                        load=file_load, row_number=row_num, raw_data=raw_data, error_message="; ".join(error_messages)
                    )
                    continue

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
                        load=file_load, row_number=row_num, raw_data=raw_data, error_message=f"Ошибка БД: {str(e)}"
                    )

            file_load.rows_count = total
            file_load.loaded_count = loaded
            file_load.error_count = errors
            file_load.duplicate_count = duplicates
            file_load.status = "SUCCESS"
            file_load.finished_at = timezone.now()
            file_load.save()

            self.stdout.write(
                self.style.SUCCESS(
                    f"\nФайл: {filepath}\nОбработано: {total}\nУспешно: {loaded}\nОшибок: {errors}\nДубликатов: {duplicates}\nСтатус: SUCCESS\n"
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
            raise CommandError(f"Загрузка прервана: {e}")
