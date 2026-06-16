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

# Güvenlik: root yerine ayrıcalıksız bir kullanıcı ile çalış (container sertleştirmesi).
# Kod ve modeller yalnızca okunur; yazma gerekmez.
RUN useradd --create-home --uid 10001 appuser
USER appuser

EXPOSE 8000

# Güvenlik: imaj 0.0.0.0'e bağlanıp port'u ağa açtığından, kimlik doğrulamasını
# zorunlu kılıyoruz. API_TOKEN verilmeden konteyner başlamayı reddeder (fail-closed),
# böylece kişisel e-posta API'si yanlışlıkla token'sız ağa açılmaz.
ENV REQUIRE_AUTH=1

# QDRANT_URL gibi ayarlar ortam değişkeninden gelir (src/config.py).
# Çalıştırırken API_TOKEN verin: `docker run -e API_TOKEN=... ` veya compose env_file.
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]
