import csv
from datetime import datetime
from django.core.management.base import BaseCommand
from django.db import transaction, IntegrityError
from django.utils import timezone
from organizations.models import Organization, FileLoad, LoadError


class Command(BaseCommand):
    help = 'Загрузка организаций из CSV-файла'

    def add_arguments(self, parser):
        parser.add_argument('filepath', type=str, help='Путь к CSV-файлу')

    def handle(self, *args, **options):
        filepath = options['filepath']

        # Проверка существования файла
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                pass
        except FileNotFoundError:
            self.stderr.write(self.style.ERROR(f'Файл не найден: {filepath}'))
            return

        # Создание записи FileLoad
        file_load = FileLoad.objects.create(
            filename=filepath,
            status='PROCESSING'
        )

        loaded = 0
        errors = 0
        duplicates = 0
        total = 0

        with open(filepath, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f, delimiter=';')

            for row_num, row in enumerate(reader, start=2):
                total += 1
                raw_data = ';'.join(row.values())
                error_messages = []

                # Получение значений
                inn = row.get('inn', '').strip()
                name = row.get('name', '').strip()
                region = row.get('region', '').strip()
                employees_str = row.get('employees', '').strip()
                date_str = row.get('registration_date', '').strip()

                # Валидация ИНН
                if not inn:
                    error_messages.append('ИНН не заполнен')
                elif not inn.isdigit():
                    error_messages.append('ИНН содержит нецифровые символы')
                elif len(inn) != 10:
                    error_messages.append(f'ИНН должен содержать 10 цифр, сейчас {len(inn)}')

                # Валидация названия
                if not name:
                    error_messages.append('Наименование не заполнено')

                # Валидация региона
                if not region:
                    error_messages.append('Регион не заполнен')

                # Валидация сотрудников
                employees = None
                if not employees_str:
                    error_messages.append('Количество сотрудников не заполнено')
                else:
                    try:
                        employees = int(employees_str)
                        if employees < 0:
                            error_messages.append('Количество сотрудников не может быть отрицательным')
                    except ValueError:
                        error_messages.append('Количество сотрудников не является целым числом')

                # Валидация даты
                reg_date = None
                if not date_str:
                    error_messages.append('Дата регистрации не заполнена')
                else:
                    try:
                        reg_date = datetime.strptime(date_str, '%Y-%m-%d').date()
                    except ValueError:
                        error_messages.append('Некорректный формат даты (ожидается YYYY-MM-DD)')

                # Если есть ошибки валидации - сохраняем в LoadError
                if error_messages:
                    errors += 1
                    LoadError.objects.create(
                        load=file_load,
                        row_number=row_num,
                        raw_data=raw_data,
                        error_message='; '.join(error_messages)
                    )
                    continue

                # Попытка сохранить организацию с обработкой дубликатов через savepoint
                try:
                    with transaction.atomic():
                        Organization.objects.create(
                            inn=inn,
                            name=name,
                            region=region,
                            employees=employees,
                            registration_date=reg_date
                        )
                        loaded += 1
                except IntegrityError:
                    # Дубликат ИНН
                    duplicates += 1
                    LoadError.objects.create(
                        load=file_load,
                        row_number=row_num,
                        raw_data=raw_data,
                        error_message=f'Дубликат ИНН: {inn}'
                    )

        # Обновляем FileLoad (вне основного цикла)
        file_load.rows_count = total
        file_load.loaded_count = loaded
        file_load.error_count = errors
        file_load.duplicate_count = duplicates
        file_load.status = 'SUCCESS'
        file_load.finished_at = timezone.now()
        file_load.save()

        # Вывод статистики
        self.stdout.write(self.style.SUCCESS(f'''
Файл: {filepath}
Обработано строк: {total}
Успешно загружено: {loaded}
Ошибочных строк: {errors}
Дубликатов: {duplicates}
Статус: {file_load.status}
'''))