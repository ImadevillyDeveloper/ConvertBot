# Используем официальный образ Python
FROM python:3.11-slim-bookworm

# Устанавливаем переменные окружения для Python
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# Устанавливаем LibreOffice и необходимые зависимости
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    libreoffice-writer \
    libreoffice-common \
    fonts-liberation \
    fonts-dejavu \
    fonts-noto \
    && rm -rf /var/lib/apt/lists/*

# Проверяем установку
RUN libreoffice --version

# Создаём рабочую директорию
WORKDIR /app

# Копируем зависимости и устанавливаем их
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Копируем код бота
COPY bot.py .

# Создаём пользователя без прав root (безопасность)
RUN useradd -m -u 1000 botuser && \
    chown -R botuser:botuser /app

# Переключаемся на пользователя botuser
USER botuser

# Команда запуска
CMD ["python", "bot.py"]