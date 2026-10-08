with open("backend/organizations/management/commands/load_organizations.py", "r", encoding="utf-8") as f:
    content = f.read()

# 1. Добавляем флаг --clear
content = content.replace(
    'parser.add_argument("filepath", type=str, help="Путь к CSV-файлу")',
    'parser.add_argument("filepath", type=str, help="Путь к CSV-файлу")\n        parser.add_argument("--clear", action="store_true", help="Очистить справочник перед загрузкой")'
)

# 2. Добавляем переменную clear_db
content = content.replace(
    'filepath = options["filepath"]',
    'filepath = options["filepath"]\n        clear_db = options["clear"]'
)

# 3. Добавляем проверку параллельных загрузок
content = content.replace(
    'file_load = FileLoad.objects.create(\n            filename=filepath, status="PROCESSING", started_at=timezone.now()\n        )',
    'if FileLoad.objects.filter(status="PROCESSING").exists():\n            raise CommandError("Загрузка прервана: уже выполняется другая загрузка со статусом PROCESSING.")\n\n        file_load = FileLoad.objects.create(\n            filename=filepath, status="PROCESSING", started_at=timezone.now()\n        )'
)

# 4. Добавляем логику очистки
content = content.replace(
    'try:\n            # 2. Безопасное чтение файла',
    'try:\n            if clear_db:\n                self.stdout.write(self.style.WARNING("ВНИМАНИЕ: Очистка существующих организаций..."))\n                Organization.objects.all().delete()\n\n            # 2. Безопасное чтение файла'
)

with open("backend/organizations/management/commands/load_organizations.py", "w", encoding="utf-8") as f:
    f.write(content)

print("✅ Файл успешно обновлен!")