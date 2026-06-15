# InsightMail — Sorun Giderme Günlüğü (Operasyonel)

> Bu belge, uygulamayı **çalıştırırken** (runtime) karşılaşılan sorunları, kök
> nedenlerini ve çözümlerini kaydeder. Kod-denetimi/refactor planı için bkz.
> [`COZUM_PLANI.md`](COZUM_PLANI.md) ve [`PROJE_DEGERLENDIRME.md`](PROJE_DEGERLENDIRME.md).
>
> Donanım bağlamı: tek kullanıcı, **RTX 2060 (6 GB VRAM, Turing)**, conda env `RagApp`
> (CUDA'lı `llama-cpp-python` + `torch`). Mimari: tek FastAPI süreci içinde **torch
> embedder (Qwen3-Embedding-0.6B)** + **llama-cpp LLM (Llama-3.2-3B Q4)**, ayrı bir
> Qdrant (Docker, `:6333`).

## Hızlı başvuru

| # | Belirti | Kök neden | Çözüm |
|---|---------|-----------|-------|
| 1 | Arama boş dönüyor, sanki index kaybolmuş | `docker compose up` yeni **boş** volume yaratıyor | Veri dolu container'ı başlat (`docker start insightmail-qdrant`) |
| 2 | `CUDA error: an illegal memory access` | embedder (torch) + LLM (llama-cpp) **aynı GPU'da çakışıyor** | Embedder'ı CPU'ya al + `flash_attn=False` |
| 3 | `Qdrant 400: Format error in JSON body` | embedder **NaN vektör** üretiyor (2 numaranın sessiz hâli) | Aynı çözüm: embedder CPU |
| 4 | Kısa sorgular ("temu") boş dönüyor | `score_threshold=0.5` çok katı | `RETRIEVAL_SCORE_THRESHOLD=0.4` |
| 5 | "football" → "yeterli bilgi yok" | Prompt soru-odaklı; tek kelime soru değil | Python'da konu-tespiti → "özetle" promptu |
| 6 | Sorgular takılıyor / timeout | Üst üste timeout'lu istekler + hızlı restart | Operasyonel (kod değil): temiz restart, tek tek test |

---

## 1 — Qdrant verisi "kayboldu" (aslında yanlış volume)

**Belirti:** Servisler ayağa kalktı ama arama/sorgu boş sonuç veriyor; sanki indekslenmiş e-postalar gitmiş.

**Kök neden:** Önceki Qdrant, `qdrant_storage` adlı Docker volume'ünü kullanan `insightmail-qdrant` container'ında çalışıyordu (482 MB, `emails` koleksiyonu ~1108 vektör). `docker compose up -d qdrant` çalıştırılınca compose **`insightmail_qdrant_storage`** adında **yeni ve boş** bir volume yaratıp ona bağlanıyor → gerçek veriye erişilemiyor.

**Çözüm:** Boş container/volume'ü kaldırıp veri dolu container'ı geri başlat:
```bash
docker stop insightmail-qdrant-1 && docker rm insightmail-qdrant-1
docker volume rm insightmail_qdrant_storage     # boş olan
docker start insightmail-qdrant                 # 482 MB veri burada
```

**Doğrulama:** `GET http://localhost:6333/collections/emails` → `points_count: 1108`.

---

## 2 — CUDA: illegal memory access (embedder + LLM aynı GPU'da)

**Belirti:**
```
LLM query error: CUDA error: an illegal memory access was encountered
... CUDA kernel errors might be asynchronously reported at some other API call ...
```
Tipik desen: ilk sorgu geçiyor, **ikinci** sorgu çöküyor. Çökme sonrası süreç bozuluyor; her sorgu patlıyor (restart şart).

**Kök neden:** Aynı süreçte **torch embedder** ve **llama-cpp LLM** ikisi de CUDA kullanıyor. İlk sorgu embedding'i LLM yüklenmeden yapıyor (sorun yok). İlk sorguda LLM lazy-load olup GPU'yu tutunca, **ikinci** sorgunun torch embedding'i çakışıyor. Hata torch'tan (`TORCH_USE_CUDA_DSA`) görünse de mesaj "asenkron raporlanır" diyor: asıl bozulma llama-cpp tarafında, bir sonraki torch çağrısında patlıyor. RTX 2060 (Turing) üzerinde **`flash_attn=True`** bilinen bir tetikleyici.
**Önemli:** VRAM dolması **değil** — çökme sırasında ~3 GB VRAM boştu (ölçüldü). LM Studio gibi diğer uygulamalar suçlu değil (kapalıyken 158 MB).

**Çözüm (iki parça):**
1. `src/query_database.py` — `get_llm()`: `flash_attn=True → False`.
2. Embedder'ı **CPU**'ya al, böylece torch ile llama-cpp aynı GPU'da çakışmaz:
   - `src/main.py` (en üstte, `src.*` importlarından **önce**): `os.environ.setdefault("EMBED_DEVICE", "cpu")`
   - `src/config.py`: `EMBED_DEVICE = os.environ.get("EMBED_DEVICE")`
   - `src/global_model.py`: `EMBED_DEVICE` set'liyse onu kullan; CPU'da `torch.float16` yerine `torch.float32`.

Embedder CPU'da (Qwen3-0.6B) sorgu başına ~0.1-0.3 s ekler — ihmal edilebilir. Toplu indeksleme (`python -m src.store_embeddings`) **ayrı süreçtir, llama-cpp yoktur**, dolayısıyla GPU'da kalır (EMBED_DEVICE set etmeyin).

**Doğrulama:** Arka arkaya 3 `/search` → hepsi `200 OK` (eskiden 2.'de çöküyordu). Log: `Embedder device: cpu`.

---

## 3 — Qdrant 400: "Format error in JSON body" (2 numaranın sessiz yüzü)

**Belirti:** `flash_attn=False` yapıldıktan sonra CUDA çökmesi gitti ama 2.-3. sorgular:
```
LLM query error: Unexpected Response: 400 (Bad Request)
{"status":{"error":"Format error in JSON body: Expected some form of vector ... at line 1 column 5215"}}
```

**Kök neden:** Aynı GPU çakışması (madde 2) artık sert çökme yerine **sessiz bozulma** üretiyor: llama-cpp resident'ken torch embedder **NaN/Inf** içeren vektör döndürüyor. `NaN` geçerli JSON değil → Qdrant reddediyor. İlk sorgu (LLM yüklenmeden) temiz, sonrakiler bozuk.

**Çözüm:** Madde 2 ile aynı — embedder'ı CPU'ya almak hem çökmeyi hem NaN'ı bitirir.

---

## 4 — Kısa / diller-arası sorgular boş dönüyor

**Belirti:** "temu" veya "what temu says" → "The provided sources do not contain enough information..." Oysa Temu e-postaları index'te var.

**Kök neden:** `src/vector_database.py` `search()` içinde **`score_threshold=0.5`** çok katı. Ölçülen cosine skorları:

| Sorgu | En iyi ilgili skor | 0.5'i geçti mi? |
|-------|--------------------|------------------|
| `what temu says` | 0.451 | ❌ elendi |
| `temu` | 0.420 | ❌ |
| `What did Temu send me?` | 0.593 | ✅ |

Qwen3-Embedding kısa ve diller-arası (İngilizce sorgu → Türkçe içerik) sorgularda daha düşük mutlak benzerlik verir; ilgili e-postalar 0.45 civarında eşiğin hemen altında kalıyor.

**Çözüm:** Eşiği 0.4'e indir ve env ile ayarlanabilir yap:
- `src/config.py`: `RETRIEVAL_SCORE_THRESHOLD = float(os.environ.get("RETRIEVAL_SCORE_THRESHOLD", "0.4"))`
- `src/vector_database.py`: sabit `0.5` yerine bu değeri kullan.

**Not:** Bu, embedder-CPU değişikliğinden bağımsız, önceden var olan bir ayardı.

---

## 5 — "football" → "yeterli bilgi yok" (tek-kelime/konu sorgusu)

**Belirti:** "football" yazınca retrieval doğru 5 futbol kaynağı getiriyor ama cevap yine "yeterli bilgi yok". Düzgün soru ("What is happening in football according to my emails?") çalışıyor.

**Kök neden:** `build_prompt`'taki görev "soruyu cevapla, kaynakta yoksa reddet" şeklinde. "football" bir soru değil, tek kelime → cevaplanacak soru olmayınca model hazır reddetme cümlesine düşüyor. LLM sampling **non-deterministik** olduğu için bare kelimede bazen özetliyor, bazen reddediyor (UI `/search-stream` kullanıyor; tek `/search` testi şanslı sonuç vermişti).

**Çözüm:** Kararı **modelden alıp Python'a** ver (mevcut tasarım felsefesi: "Python decides the task; model gets one simple instruction"). `src/query_database.py`:
- `_looks_like_topic(query)` heuristic'i: "?" yok + ≤4 kelime + soru kelimesi (what/how/is/...) yok → konu sorgusu.
- `build_prompt` üç yol seçer:
  - tüm kaynaklar one-directional → kaynak-başı özet,
  - **konu/anahtar-kelime → "özetle" (reddetme seçeneği YOK)**,
  - gerçek soru → "cevapla, ilgili kaynak yoksa reddet".

Ayrıca UI ipucu: `SearchView.jsx` placeholder → `Ask a full question, e.g. "What did Temu send me?"`.

**Doğrulama:**
| Girdi | Sonuç |
|-------|-------|
| `football` (3 deneme) | hepsi kaynaklı özet, reddetme yok ✅ |
| `What did Temu send me?` | cevap ✅ |
| `What is my flight booking reference?` (ilgisiz) | doğru şekilde reddet ✅ |

---

## 6 — Sorgular takılıyor / timeout (operasyonel — kod hatası DEĞİL)

**Belirti:** Bir noktada her `/search` (hatta LLM kullanmayan `/ask` bile) 30-200 sn'de timeout; VRAM bir ara 5.8 GB'a çıkmış görünüyor.

**Kök neden (iki operasyonel etken, kod değil):**
1. **Seri kuyruk:** Client-side timeout olan istek, server'da generation'ı **çalışmaya devam ettiriyor** (FastAPI thread'i iptal etmez). llama-cpp çağrıları **seri** işler. Art arda timeout'a uğratılan sorgular birikip süreci kilitliyor.
2. **Hızlı restart:** Öldürülen backend'in llama-cpp VRAM'i birkaç saniye **geç** serbest kalıyor. Hemen yeni backend başlatınca iki LLM birden VRAM tutup (~5.8 GB) shared memory'ye taşıyor → generation çok yavaşlıyor.

**Çözüm / çalışma kuralı:**
- Restart ederken eski süreci öldür, **VRAM baseline'a (~160 MB) düşene kadar bekle**, sonra başlat.
- Test ederken **tek tek**, bol timeout'la ve önceki istek bitmeden yenisini gönderme.

**Sağlıklı referans değerler:** ilk sorgu (LLM cold-load) ~50-110 s; warm sorgu ~3-8 s; embedder (CPU) sorgu başı ~0.1-0.3 s. Tek backend'de VRAM ~2.1-2.9 GB.

---

## Yerel çalıştırma sırası (özet)

```bash
# 1) Qdrant (veri dolu container)
docker start insightmail-qdrant            # :6333

# 2) Backend (embedder otomatik CPU, LLM GPU)
conda run --no-capture-output -n RagApp \
  uvicorn src.main:app --host 127.0.0.1 --port 8001

# 3) Frontend
cd frontend && npm run dev                 # :5173  (proxy -> :8001)
```

İlgili ayar değişkenleri (`.env`, hepsi opsiyonel): `EMBED_DEVICE`, `RETRIEVAL_SCORE_THRESHOLD`.
