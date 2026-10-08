import os
import tempfile

from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase
from django.utils import timezone

from organizations.models import FileLoad, LoadError, Organization


class LoadOrganizationsCommandTests(TestCase):
    def setUp(self):
        self.valid_csv = "inn;name;region;employees;registration_date\n7701234567;ООО Альфа;Москва;120;2024-03-15\n"
        self.bad_date_csv = "inn;name;region;employees;registration_date\n7701234567;ООО Альфа;Москва;120;2024-1-5\n"
        self.duplicate_inn_csv = (
            "inn;name;region;employees;registration_date\n"
            "7701234567;ООО Альфа;Москва;120;2024-03-15\n"
            "7701234567;ООО Альфа Повтор;Москва;125;2024-03-16\n"
        )
        self.bad_headers_csv = "inn;name;region;employees\n7701234567;ООО Альфа;Москва;120\n"

    def _create_temp_file(self, content):
        fd, path = tempfile.mkstemp(suffix=".csv")
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(content)
        return path

    def test_valid_load(self):
        path = self._create_temp_file(self.valid_csv)
        try:
            call_command("load_organizations", path)
            self.assertEqual(Organization.objects.count(), 1)
            load = FileLoad.objects.first()
            self.assertEqual(load.status, "SUCCESS")
        finally:
            os.remove(path)

    def test_strict_date_validation(self):
        path = self._create_temp_file(self.bad_date_csv)
        try:
            call_command("load_organizations", path)
            self.assertEqual(Organization.objects.count(), 0)
            self.assertEqual(LoadError.objects.count(), 1)
            self.assertIn("Некорректный формат даты", LoadError.objects.first().error_message)
        finally:
            os.remove(path)

    def test_in_file_duplicate_rejection(self):
        path = self._create_temp_file(self.duplicate_inn_csv)
        try:
            call_command("load_organizations", path)
            self.assertEqual(Organization.objects.count(), 0)
            self.assertEqual(LoadError.objects.count(), 2)
            load = FileLoad.objects.first()
            self.assertEqual(load.error_count, 2)
            self.assertEqual(load.duplicate_count, 2)
        finally:
            os.remove(path)

    def test_bad_headers_raises_error(self):
        path = self._create_temp_file(self.bad_headers_csv)
        try:
            with self.assertRaises(CommandError) as context:
                call_command("load_organizations", path)
            self.assertIn("Неверные заголовки CSV", str(context.exception))
            load = FileLoad.objects.first()
            self.assertEqual(load.status, "FAILED")
        finally:
            os.remove(path)

    # НОВЫЙ ТЕСТ: Блокировка параллельных загрузок
    def test_parallel_loading_blocked(self):
        FileLoad.objects.create(filename="test_parallel.csv", status="PROCESSING", started_at=timezone.now())
        path = self._create_temp_file(self.valid_csv)
        try:
            with self.assertRaises(CommandError) as context:
                call_command("load_organizations", path)
            self.assertIn("уже выполняется другая загрузка", str(context.exception))
        finally:
            os.remove(path)
            FileLoad.objects.filter(filename="test_parallel.csv").delete()
