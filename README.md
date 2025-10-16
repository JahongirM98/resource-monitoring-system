
# 🧠 Resource Monitoring System

**Django 5 + Celery + Redis + MySQL + Docker**  
Полнофункциональная система мониторинга ресурсов, разработанная как тестовое задание.  
Собирает метрики с удалённых машин, фиксирует инциденты и отображает их в реальном времени.

---

## 🚀 Функциональность

### **Задача 1: Сбор данных**
- Периодический опрос 30 удалённых машин (mock API).
- Получение метрик CPU, MEM, DISK, uptime каждые 15 минут.
- Хранение данных в MySQL.
- Асинхронное выполнение через Celery.

### **Задача 2: Мониторинг и инциденты**
- Анализ метрик и фиксация инцидентов при превышении порогов:
  - CPU > 85% — одномоментно;
  - MEM > 90% — 30 минут подряд;
  - DISK > 95% — 2 часа подряд.
- Активные инциденты не дублируются.
- Автоматическое закрытие при нормализации метрик.

### **Задача 3: Веб-интерфейс**
- Отображение инцидентов с автообновлением (vanilla JS, без фреймворков).
- Простая авторизация через custom middleware (не Django Auth).
- REST API для получения инцидентов в JSON.

---

## ⚙️ Стек технологий

| Компонент | Используется для |
|------------|------------------|
| **Python 3.12** | Основной язык проекта |
| **Django 5** | Backend и ORM |
| **Celery 5** | Планировщик фоновых задач |
| **Redis 7** | Брокер задач и кэш |
| **MySQL 8** | Хранение данных |
| **Docker Compose** | Контейнеризация и оркестрация |
| **Gunicorn** | WSGI сервер |
| **FastAPI (mock)** | Тестовый API для эмуляции машин |

---

## 🧩 Структура проекта

```
.
├── docker-compose.yml
├── dockerfile
├── monitor_site/
│   ├── celery.py
│   ├── settings.py
│   └── urls.py
├── monitoring/
│   ├── models.py
│   ├── tasks.py
│   ├── views.py
│   ├── middleware.py
│   ├── seed_machines.py
│   └── templates/
│       └── monitoring/incidents.html
├── mock/
│   └── main.py
└── README.md
```

---

## 🔧 Установка и запуск

### 1. Клонирование проекта
```bash
git clone git@github.com:JahongirM98/resource-monitoring-system.git
cd resource-monitoring-system
```

### 2. Настройка окружения
Создай `.env` из примера:
```bash
cp .env.example .env
```

### 3. Запуск проекта
```bash
docker compose up --build -d
```

Все сервисы будут доступны после инициализации:
- **Django app** → [http://localhost:8000](http://localhost:8000)
- **Mock API** → [http://localhost:8001/m/1/metrics](http://localhost:8001/m/1/metrics)
- **MySQL** → порт `3306`
- **Redis** → порт `6379`

---

## 💾 Демо-данные

После запуска создаются:
- 30 машин (`Machine`);
- Тестовые метрики;
- Примеры инцидентов для отображения.

При необходимости можно добавить вручную:
```bash
docker compose exec app python manage.py seed_machines --host http://mock:8001
```

---

## 🔍 Проверка инцидентов

```bash
docker compose exec app python manage.py shell -c "from monitoring.models import Incident; print(Incident.objects.count())"
```

или в браузере — открой  
👉 [http://localhost:8000/incidents/](http://localhost:8000/incidents/)

---

## 👨‍💻 Автор
**Jahongir Mirhalikov**  
Python Developer / QA Automation Engineer  
📧 [mirhalikovj@gmail.com](mailto:mirhalikovj@gmail.com)  
💼 [GitHub: JahongirM98](https://github.com/JahongirM98)

---

## 🧱 Лицензия
MIT License © 2025 Jahongir Mirhalikov
