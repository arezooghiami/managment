# Build stage
FROM python:3.12 as build_image

# نصب Poetry و وابستگی‌های سیستم لازم
RUN apt-get update && apt-get install -y libpq-dev

RUN pip install poetry

# بررسی نصب Poetry
RUN poetry --version

WORKDIR /code

# ایجاد محیط مجازی
RUN python -m venv --copies /code/venv

# کپی کردن فایل‌های وابستگی
COPY poetry.lock pyproject.toml /code/

# فعال‌سازی محیط مجازی، اطمینان از نصب Poetry و نصب وابستگی‌ها
RUN set -x && \
    . /code/venv/bin/activate && \
    pip install poetry && \
    poetry --version && \
    poetry config virtualenvs.create false --local && \
    poetry install --no-root --only main --no-interaction --no-ansi

# Run stage
FROM python:3.12-slim as run_stage

WORKDIR /code

# نصب وابستگی‌های سیستم برای psycopg2
RUN apt-get update && apt-get install -y libpq-dev tree

# Ensure the directories for static and templates exist
RUN mkdir -p /code/static /code/templates

# کپی کردن فایل‌های وابستگی و محیط مجازی از مرحله ساخت
COPY poetry.lock pyproject.toml /code/
COPY --from=build_image /code/venv /code/venv/
ENV PATH=/code/venv/bin:$PATH

# کپی کردن کد منبع
COPY ./src/ /code/
COPY ./static/ /code/static/
COPY ./templates/ /code/templates/

# Check the structure to ensure everything is copied correctly
RUN ls -la /code && tree /code

# اجرای اپلیکیشن
CMD ["python", "main.py"]
