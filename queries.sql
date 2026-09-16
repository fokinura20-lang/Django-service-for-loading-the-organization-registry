-- 1. Все организации
SELECT * FROM organizations_organization;

-- 2. Количество организаций по регионам
SELECT region, COUNT(*) as count
FROM organizations_organization
GROUP BY region
ORDER BY count DESC;

-- 3. Среднее количество сотрудников по регионам
SELECT region, AVG(employees) as avg_employees
FROM organizations_organization
GROUP BY region
ORDER BY avg_employees DESC;

-- 4. 5 организаций с наибольшим количеством сотрудников
SELECT name, inn, employees, region
FROM organizations_organization
ORDER BY employees DESC
LIMIT 5;

-- 5. Организации, зарегистрированные после 2023-01-01
SELECT name, inn, registration_date
FROM organizations_organization
WHERE registration_date > '2023-01-01'
ORDER BY registration_date DESC;

-- 6. Общее количество загрузок
SELECT COUNT(*) as total_loads
FROM organizations_fileload;

-- 7. Количество ошибок по каждой загрузке
SELECT fl.filename, fl.started_at, COUNT(le.id) as error_count
FROM organizations_fileload fl
LEFT JOIN organizations_loaderror le ON fl.id = le.load_id
GROUP BY fl.id, fl.filename, fl.started_at
ORDER BY fl.started_at DESC;

-- 8. Количество ошибок по типам
SELECT error_message, COUNT(*) as count
FROM organizations_loaderror
GROUP BY error_message
ORDER BY count DESC; 
