# InsightMail — Proje Değerlendirme ve Eksikler Raporu

> Tarih: 2026-06-14
> İncelenen branch: `llamacpp` (= `frontend` ile birebir aynı; `main`'in 4 commit gerisinde, kendisi 2 commit önünde)
> Kapsam: Tüm kaynak kod (`src/`, `frontend/`, `Decorators/`), repo hijyeni ve branch durumu

---

## 1. Genel Bakış

InsightMail, e-postaları lokal bir RAG hattına sokan, lokal LLM (Llama 3.2 3B) ve embedding modeli (Qwen3-0.6B) ile çalışan, FastAPI + React tabanlı bir uygulama. Mimari temiz, sorumluluklar dosyalara iyi bölünmüş ve README oldukça detaylı. Aşağıdaki bulgular **çalışmayan bir şey** değil, **eksik veya riskli** noktaları kategorize eder.

### Depo / Branch Durumu
- Tek bir git deposu var, submodule yok. "Tüm repolar" = branch'ler olarak yorumlandı.
- `frontend` branch'i `llamacpp` ile **birebir aynı** (0/0 fark) → muhtemelen artık gereksiz, silinebilir.
- `origin/master` çok ıraksamış (28/13) → **ölü/eski branch**, temizlenmeli.
- `main`, `llamacpp`'ten 4 commit ileride ama `llamacpp` 2 commit ileride → branch'ler **birbirine merge edilmemiş**, hangisinin "doğru" olduğu belirsiz. Tek bir ana hat (main) belirlenip diğerleri kapatılmalı.

---

## 2. Kritik Eksikler (öncelik: yüksek)

### 2.1 Hiç test yok
- `tests/` dizini, `pytest.ini`, `pyproject.toml` yok. Kök dizindeki `test.py` sadece elle çalıştırılan bir LLM smoke-test'i (Türkçe yorumlu, başka hiçbir şeyi test etmiyor).
- Parser, chunker, IMAP folder-discovery, prompt üretimi, reply parsing gibi saf/deterministik fonksiyonlar kolayca test edilebilir ama edilmemiş.
- **Risk:** Regresyonlar fark edilmeden geçer.

### 2.2 CI/CD yok
- `.github/workflows` yok. Lint, test, build otomasyonu yok.
- Frontend'de ESLint/Prettier konfigürasyonu yok.

### 2.3 API'de kimlik doğrulama yok
- `src/main.py` — uçların hiçbiri korunmuyor. `:8000`'e erişen herkes e-posta içeriğini sorgulayabilir, özet/yanıt üretebilir.
- CORS sadece `localhost:5173`'e açık (`main.py:37`) ama bu CORS'tur, gerçek bir erişim kontrolü değil. Makineye erişebilen bir süreç doğrudan API'yi çağırabilir.
- "No data leaves your machine" iddiası doğru olsa da, lokal API yetkisizdir.

### 2.4 Yeniden indeksleme = kopya kayıt (duplicate) üretir
- `src/store_embeddings.py:33` her chunk için `uuid.uuid4()` ile ID üretiyor. `store_embeddings` ikinci kez çalıştırılırsa Qdrant'a **aynı e-postalar tekrar yazılır**, koleksiyon şişer.
- Deterministik ID yok (örn. `message-id + chunk_index` hash'i). İdempotent indeksleme yok.
- Arama tarafındaki `_deduplicate_by_email` (`vector_database.py:42`) bunu kısmen maskeliyor ama kök sorun indeksleme aşamasında.

### 2.5 Model yükleme başarısızlığı uygulamayı çökertir
- `global_model.py` model yüklenemezse `GLOBAL_MODEL = None` yapıyor (iyi), **ama** `Email_Embedding.__init__` (`Email_Embedding.py:16-17`) `self.model = GLOBAL_MODEL` ardından `self.model.max_seq_length = 1024` çağırıyor → `None` ise `AttributeError`.
- `main.py:26` import sırasında `global_embedder = Embedder(...)` oluşturduğundan, model yüklenemezse **uygulama hiç ayağa kalkmaz** ve `/health` içindeki `model_loaded` kontrolü hiç anlam ifade etmez.

---

## 3. Önemli Eksikler (öncelik: orta)

### 3.1 Retrieval kalitesi: sorgu embedding'i asimetrik değil
- Qwen3-Embedding modelleri retrieval'da **sorgu için ayrı instruction/prompt** kullanmayı önerir (asimetrik query/document embedding).
- `Email_Embedding.embed_anything` (`Email_Embedding.py:50`) hem indeksleme hem sorgu için aynı düz `model.encode(text)`'i kullanıyor; `prompt_name="query"` veya instruction prefix yok. Bu, retrieval isabetini düşürür.

### 3.2 Sadece İngilizce chunking, çok dilli içerik
- `Email_Chunker` spaCy `en_core_web_sm` kullanıyor (`Email_Chunker.py:26`). README "multilingual embeddings" diyor ve reply üretici Türkçe yanıtları destekliyor, **ama cümle bölütleme İngilizce modelle yapılıyor.** Türkçe e-postalarda cümle sınırları yanlış çıkar → chunk kalitesi düşer.

### 3.3 İndeksleme kapsamı sabit ve sınırlı
- `Email_Parser.__init__` (`Email_Parser.py:16`) `fetch_mails(100)` ile **yalnızca son ~100 e-postayı** indeksliyor; bu değer sabit kodlanmış, parametreleştirilemiyor.
- Artımlı (incremental) senkronizasyon yok: yeni gelen e-postaları eklemenin yolu tüm hattı yeniden çalıştırmak, o da 2.4'teki kopya sorununu tetikler.
- Silinen e-postalar vektör veritabanından temizlenmiyor.

### 3.4 LLM yanıtları streaming değil
- `/search`, `/summarize`, `/reply-suggest` 5–40 sn bloklayan isteklerle çalışıyor (README perf tablosu). Streaming (SSE/token-by-token) yok → kullanıcı uzun süre boş ekran görür, ilerleme geri bildirimi yok.

### 3.5 Konfigürasyon dağınık ve sabit kodlu
- Qdrant URL'i ve koleksiyon adı `main.py:29-30` ve `store_embeddings.py:19-21`'de iki kez sabit kodlu.
- `MODEL_PATH` hem `query_database.py:7` hem `test.py:4`'te tekrarlanıyor.
- Hiçbiri ortam değişkeninden okunmuyor; sadece `EMAIL_ADDRESS`/`EMAIL_PASSWORD` `.env`'den geliyor. Tek bir `config.py`/Pydantic Settings yapısı yok.

### 3.6 Aşırı geniş hata yönetimi
- `query_database`, `conversation_summarizer`, `reply_suggester` ve `Email_Receiver` boyunca `except Exception as e: return {"error": str(e)}` deseni. Ham exception mesajı API üzerinden istemciye dönüyor (bilgi sızıntısı + zayıf hata sınıflandırması).
- `Email_Receiver.fetch_mails` ve `fetch_recent_contacts` hataları yutup boş liste dönüyor → sessiz başarısızlık.

---

## 4. Repo Hijyeni / Tutarlılık

### 4.1 Git'te artık derlenmiş dosyalar (stale .pyc) takip ediliyor
- `Decorators/__pycache__/*.cpython-312.pyc` **git tarafından izleniyor** (3 dosya), üstelik bunlar artık var olmayan kaynaklara ait: `Email_Chunker_Decorator`, `Email_decorators`, `Email_parser_decorator`. Mevcut `Decorators/` klasöründe sadece `perf_logger.py` var.
- `.gitignore`'da `__pycache__/` yazsa da bu dosyalar daha önce eklenmiş, hâlâ izleniyor. `git rm -r --cached Decorators/__pycache__` ile temizlenmeli.
- (`main` branch'inde `src/__pycache__/*.pyc`'lerin de bir noktada izlendiği, llamacpp'te silindiği diff'ten görülüyor.)

### 4.2 `.gitignore` ile gerçeklik çelişiyor
- `.gitignore` `package-lock.json`'ı yoksayıyor **ama** `frontend/package-lock.json` git'te izleniyor. Lock dosyası aslında izlenmeli (reproducible build) → gitignore satırı yanlış, kaldırılmalı.
- `.gitignore` sonunda spesifik dosya yolları (`src/__pycache__/...cpython-312.pyc` tek tek, `frontend/public/hero.png` vb.) var → genel kurallar varken bunlar gereksiz/karışık, temizlenmeli.

### 4.3 Bağımlılıklar pinlenmemiş
- `requirements.txt` sürüm pini içermiyor (`fastapi`, `torch`, `llama-cpp-python` ...). `torch` ve `llama-cpp-python` gibi paketlerde sürüm/CUDA uyumu kritik. Reproducibility riski. `pip freeze` veya pinli sürümler + opsiyonel `requirements-lock` gerekli.
- Frontend `package.json` semver caret (`^`) kullanıyor; lock dosyası var (iyi) ama 4.2'deki ignore çelişkisi mevcut.

### 4.4 Artık dosyalar
- Kök dizindeki `test.py` — elle LLM denemesi, Türkçe yorumlu; ya `tests/`'e taşınmalı ya silinmeli.
- `performance.log` çalışma dizininde 287 KB (gitignore'da, izlenmiyor — iyi) ama log rotation yok, sınırsız büyür.

### 4.5 Karışık dil ve stil
- Kod genelinde Türkçe + İngilizce yorumlar karışık (`Email_Receiver.py`, `Email_Parser.py` Türkçe; diğerleri İngilizce). Tek dile (tercihen İngilizce) standardize edilmeli.
- Dosya adlandırma tutarsız: `Email_Receiver.py`, `Email_Parser.py` (PascalCase_Snake) vs `query_database.py`, `email_utils.py` (snake_case). PEP8 snake_case'e çekilebilir.

---

## 5. Dokümantasyon Tutarsızlıkları (README)

- **`/ask` vs `/search` adlandırması kafa karıştırıcı:** `/ask` LLM'siz semantik arama, `/search` ise LLM'li RAG (`main.py:67` ve `:86`). İsimler sezgiye ters; README'de doğru açıklanmış ama isimlendirme yine de yanıltıcı.
- README "LLM ~3s yüklenir" (satır 84/212) derken başka yerde "~8s embedding" diyor; ölçümler tutarsız ve donanıma bağlı, "tipik" olduğu vurgulanmalı.
- README "swapping in any GGUF model by changing one path in `query_database.py`" diyor ama `MODEL_PATH` `test.py`'de de tekrarlı → tek kaynak (config) olmalı.
- Kurulum adımı `git clone https://github.com/your-username/InsightMail.git` placeholder içeriyor; gerçek repo `kaanguler14/InsightMail`.
- README'de bahsi geçmeyen ama gitignore'da referans verilen `frontend/public/hero.png` / `testimonial.png` görselleri repoda yok → frontend bunlara referans vermiyor (kontrol edildi, kullanılmıyor) ama gitignore satırları kafa karıştırıcı.

---

## 6. Dağıtım / Operasyon Eksikleri

- **Dockerfile / docker-compose yok.** README sadece Qdrant için `docker run` veriyor; uygulamanın kendisi (API + frontend + Qdrant) için bir compose dosyası yok. Tek komutla ayağa kaldırma imkânı yok.
- **LICENSE yok.** Açık kaynak olarak paylaşılıyorsa lisans şart (kullanım hakları belirsiz).
- `CONTRIBUTING.md`, `CHANGELOG.md` yok.
- `.dockerignore` yok.
- Üretim için process yöneticisi / gunicorn-uvicorn worker yapılandırması yok; README `uvicorn --reload` (geliştirme modu) öneriyor.
- Sağlık kontrolü var (`/health`) ama Qdrant ve IMAP bağlanabilirliğini kapsamıyor (sadece `model_loaded`).

---

## 7. Frontend Eksikleri

- Test yok, ESLint/Prettier yok.
- Error boundary yok; bir bileşen patlarsa tüm uygulama beyaz ekran olabilir.
- `api/client.js` BASE='' kullanıyor; prod'da farklı host'a deploy edilirse proxy varsayımı kırılır (yapılandırılabilir base URL yok).
- `postSummarize` varsayılan `limit=5` (`client.js:43`) ama backend varsayılanı `15` (`custom_types.py:18`) → tutarsız varsayılan.

---

## 8. Öncelikli Aksiyon Listesi (önerilen sıra)

| # | Aksiyon | Etki | Çaba |
|---|---------|------|------|
| 1 | İndekslemede deterministik ID + idempotent upsert (kopya kaydı bitir) | Yüksek | Düşük |
| 2 | `Email_Embedding` model=None durumunu ele al; uygulama çökmesin | Yüksek | Düşük |
| 3 | `git rm --cached Decorators/__pycache__/*.pyc` + gitignore çelişkilerini düzelt | Orta | Düşük |
| 4 | Sorgu embedding'inde Qwen3 query instruction kullan (retrieval kalitesi) | Yüksek | Düşük |
| 5 | Saf fonksiyonlar için `tests/` + temel pytest; basit GitHub Actions CI | Yüksek | Orta |
| 6 | Tüm konfigürasyonu tek `Settings` (env tabanlı) altında topla | Orta | Orta |
| 7 | Türkçe içerik için çok dilli/uygun chunking stratejisi | Orta | Orta |
| 8 | Dockerfile + docker-compose (API + Qdrant + statik) | Orta | Orta |
| 9 | API'ye basit auth (token/header) ekle | Orta | Düşük |
| 10 | LLM yanıtlarını streaming'e çevir (UX) | Orta | Orta |
| 11 | Ölü branch'leri kapat (`frontend`, `origin/master`), tek ana hat belirle | Düşük | Düşük |
| 12 | LICENSE + requirements sürüm pinleme + dil/stil standardizasyonu | Düşük | Düşük |

---

## 9. Güçlü Yönler (kayıt için)

- Temiz modüler ayrım (receiver / parser / chunker / embedder / store / query).
- Çok sağlayıcılı IMAP ve dinamik "Sent" klasörü keşfi sağlam çözülmüş (`Email_Receiver._find_sent_folder`).
- IPv4-forced IMAP socket'i (gerçek bir ağ gecikmesi sorununa pratik çözüm).
- LLM rolü `[ME]`/`[THEM]` etiketleme yaklaşımı (perspektif karışmasını önlüyor).
- Bağlam penceresine göre dinamik gövde kısaltma.
- README mimari ve teknik karar gerekçeleri açısından örnek niteliğinde detaylı.
