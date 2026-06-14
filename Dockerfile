# InsightMail API imajı.
#
# WHY: Tek komutla, tekrarlanabilir kurulum sağlar; "bende çalışıyordu" sorunlarını
# ortadan kaldırır. Önceden uygulamayı ayağa kaldırmak çok adımlı ve hataya açıktı.
#
# NOT (GPU): Bu imaj varsayılan olarak CPU içindir. GPU hızlandırması için
# nvidia/cuda tabanlı bir base image kullanın, llama-cpp-python'u
# `CMAKE_ARGS="-DGGML_CUDA=on"` ile derleyin ve konteyneri
# `--gpus all` (veya compose'da deploy.resources.reservations.devices) ile çalıştırın.

FROM python:3.10-slim

# llama-cpp-python kaynaktan derlenir -> derleyici + cmake gerekir.
RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential cmake git \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Önce sadece requirements -> katman önbelleği (kod değişince yeniden kurmasın).
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

# Uygulama kodu.
COPY src/ ./src/
COPY Decorators/ ./Decorators/
COPY static/ ./static/

# Model dosyaları imaja GÖMÜLMEZ (2GB+); compose'da volume olarak bağlanır.
# models/ dizini runtime'da mount edilir.

EXPOSE 8000

# QDRANT_URL gibi ayarlar ortam değişkeninden gelir (src/config.py).
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]
