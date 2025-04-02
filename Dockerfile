# Wybierz obraz bazowy
FROM python:3.12-slim

# Ustaw katalog roboczy
WORKDIR /app

# Skopiuj plik z zależnościami i zainstaluj je
COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

# Skopiuj pliki projektu do kontenera
COPY . /app/

# Uruchom migracje i serwer
CMD ["sh", "-c", "python manage.py migrate && python manage.py runserver 0.0.0.0:8000"]