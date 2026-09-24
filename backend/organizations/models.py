from django.db import models


class Organization(models.Model):
    inn = models.CharField(max_length=10, unique=True, verbose_name="ИНН")
    name = models.CharField(max_length=255, verbose_name="Наименование")
    region = models.CharField(max_length=255, verbose_name="Регион")
    employees = models.PositiveIntegerField(verbose_name="Количество сотрудников")
    registration_date = models.DateField(verbose_name="Дата регистрации")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Создано")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Обновлено")

    class Meta:
        verbose_name = "Организация"
        verbose_name_plural = "Организации"

    def __str__(self):
        return f"{self.inn} - {self.name}"


class FileLoad(models.Model):
    STATUS_CHOICES = [
        ("NEW", "Новая"),
        ("PROCESSING", "В обработке"),
        ("SUCCESS", "Успешно"),
        ("FAILED", "Ошибка"),
    ]

    filename = models.CharField(max_length=255, verbose_name="Имя файла")
    started_at = models.DateTimeField(auto_now_add=True, verbose_name="Начало загрузки")
    finished_at = models.DateTimeField(null=True, blank=True, verbose_name="Окончание")
    rows_count = models.IntegerField(default=0, verbose_name="Всего строк")
    loaded_count = models.IntegerField(default=0, verbose_name="Загружено")
    error_count = models.IntegerField(default=0, verbose_name="Ошибок")
    duplicate_count = models.IntegerField(default=0, verbose_name="Дубликатов")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="NEW", verbose_name="Статус")

    class Meta:
        verbose_name = "Загрузка файла"
        verbose_name_plural = "Загрузки файлов"

    def __str__(self):
        return f"{self.filename} - {self.status}"


class LoadError(models.Model):
    load = models.ForeignKey(FileLoad, on_delete=models.CASCADE, related_name="errors", verbose_name="Загрузка")
    row_number = models.IntegerField(verbose_name="Номер строки")
    raw_data = models.TextField(verbose_name="Исходные данные")
    error_message = models.TextField(verbose_name="Описание ошибки")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Время создания")

    class Meta:
        verbose_name = "Ошибка загрузки"
        verbose_name_plural = "Ошибки загрузки"

    def __str__(self):
        return f"Ошибка в строке {self.row_number} - {self.load.filename}"
