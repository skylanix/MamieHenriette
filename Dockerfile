FROM python:3.9-slim

WORKDIR /app

COPY requirements.txt .
COPY bot.py .
COPY statuts.txt .

RUN pip install --no-cache-dir -r requirements.txt

CMD ["python", "bot.py"]