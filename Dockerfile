# 1. Python 3.10 use karein (Deprecation warning fix)
FROM python:3.10-slim

# 2. Linux server par FFmpeg install karein
RUN apt-get update && \
    apt-get install -y ffmpeg && \
    apt-get clean

# 3. Working directory set karein
WORKDIR /app

# 4. Saari files copy karein (cookies.txt bhi copy ho jayega)
COPY . /app

# 5. Libraries install karein
RUN pip install --no-cache-dir -r requirements.txt

# 6. Port open karein
EXPOSE 10000

# 7. App start karein
CMD ["gunicorn", "app:app", "--bind", "0.0.0.0:10000", "--timeout", "120"]
