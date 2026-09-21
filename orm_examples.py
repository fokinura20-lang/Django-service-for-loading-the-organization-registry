"""Примеры Django ORM, эквивалентные SQL-запросам из queries.sql."""
from django.db.models import Avg, Count

from organizations.models import FileLoad, LoadError, Organization

# 1. Все организации
# SQL: SELECT * FROM organizations_organization;
all_organizations = Organization.objects.all()

# 2. Количество организаций по регионам
# SQL: SELECT region, COUNT(*) ... GROUP BY region ORDER BY count DESC;
organizations_by_region = (
    Organization.objects.values('region')
    .annotate(count=Count('id'))
    .order_by('-count')
)

# 3. Среднее количество сотрудников по регионам
# SQL: SELECT region, AVG(employees) ... GROUP BY region;
avg_employees_by_region = (
    Organization.objects.values('region')
    .annotate(avg_employees=Avg('employees'))
    .order_by('-avg_employees')
)

# 4. Пять организаций с наибольшим количеством сотрудников
# SQL: ... ORDER BY employees DESC LIMIT 5;
top5_employees = Organization.objects.order_by('-employees')[:5]

# 6. Общее количество загрузок
# SQL: SELECT COUNT(*) FROM organizations_fileload;
total_loads = FileLoad.objects.count()

# 7. Количество ошибок по каждой загрузке
# SQL: LEFT JOIN organizations_loaderror ... GROUP BY fl.id;
errors_per_load = (
    FileLoad.objects.annotate(error_count=Count('errors'))
    .values('filename', 'started_at', 'error_count')
    .order_by('-started_at')
)

# 8. Количество ошибок по типам
# SQL: GROUP BY error_message ORDER BY count DESC;
errors_by_type = (
    LoadError.objects.values('error_message')
    .annotate(count=Count('id'))
    .order_by('-count')
)


def print_examples():
    """Проверка: python manage.py shell, затем
    exec(open('orm_examples.py', encoding='utf-8').read())
    print_examples()
    """
    print('Всего организаций:', all_organizations.count())
    print('По регионам:', list(organizations_by_region))
    print('Среднее сотрудников:', list(avg_employees_by_region))
    print('Топ-5:', list(top5_employees))
    print('Всего загрузок:', total_loads)
    print('Ошибки по загрузкам:', list(errors_per_load))
    print('Ошибки по типам:', list(errors_by_type))