FROM python:3.10-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY mav-keses.py .
CMD sh -c 'while true; do python3 /app/mav-keses.py >> /dev/stdout 2>&1; echo "Várakozás a következő futtatásra (15 perc)..." >> /dev/stdout 2>&1; sleep 900; done'
