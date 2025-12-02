# Python ka base image use karein
FROM python:3.9-slim

# Working directory set karein
WORKDIR /app

# Sabse Zaroori: FFmpeg install karein
RUN apt-get update && \
    apt-get install -y ffmpeg && \
    apt-get clean

# Files copy karein
COPY . /app

# Libraries install karein
RUN pip install --no-cache-dir -r requirements.txt

# Port open karein
EXPOSE 10000

# Server start karein (Gunicorn use karke)
CMD ["gunicorn", "app:app", "--bind", "0.0.0.0:10000", "--timeout", "120"]