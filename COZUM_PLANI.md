# InsightMail — Çözüm Planı ve Gerekçeleri

> Tarih: 2026-06-14
> Bu belge, `PROJE_DEGERLENDIRME.md` raporundaki eksikleri **öncelik sırasına göre** ele alır.
> Her madde için: **Sorun**, **Neden çözüyoruz / Amaç**, **Yapılmazsa ne olur**, **Planlanan çözüm**.

---

## Madde 1 — İdempotent indeksleme (deterministik point ID)

**Sorun:** `src/store_embeddings.py:33` her chunk için `uuid.uuid4()` (tamamen rastgele) ID üretiyor.

**Neden çözüyoruz / Amaç:** Aynı e-posta içeriğinin her zaman **aynı** ID'ye eşlenmesini istiyoruz. İçerikten türetilen `uuid.uuid5` (hash tabanlı, deterministik) kullanılır. Qdrant'ta `upsert` var olan ID'ye yazınca **üzerine yazar**, yeni ID'ye yazınca **yeni kayıt ekler**.

**Yapılmazsa ne olur:** `store_embeddings`'i ikinci kez çalıştırdığında (yeni mail geldikçe gerekecek) her chunk yeni rastgele ID alır ve Qdrant'a **tüm e-postalar tekrar yazılır**:
- Koleksiyon her çalıştırmada şişer (2x, 3x… kayıt) → disk/bellek israfı, yavaşlama.
- Arama sonuçlarında aynı e-posta birden çok kez döner.
- "Top-k" çeşitliliği düşer; kopyalar slotları doldurur.

**Planlanan çözüm:**
```python
INSIGHTMAIL_NAMESPACE = uuid.uuid5(uuid.NAMESPACE_URL, "insightmail/emails")

def chunk_id(text: str) -> str:
    """Chunk içeriğinden türetilen deterministik point ID."""
    return str(uuid.uuid5(INSIGHTMAIL_NAMESPACE, text))
```
`ids.append(str(uuid.uuid4()))` → `ids.append(chunk_id(item["text"]))`.

---

## Madde 2 — Model yüklenemezse uygulama çökmesin

**Sorun:** `src/global_model.py` model yüklenemezse `GLOBAL_MODEL = None` yapıyor, ama `src/Email_Embedding.py:16-17` `self.model = GLOBAL_MODEL` ardından `self.model.max_seq_length = 1024` çağırıyor. `main.py:26` bunu import sırasında oluşturduğu için, model yüklenemezse **uygulama hiç ayağa kalkmaz** (`AttributeError: 'NoneType'`).

**Neden çözüyoruz / Amaç:** Model yüklenemese bile API'nin başlaması, `/health` ucunun `model_loaded: false` döndürmesi ve anlamlı bir hata vermesi gerekiyor.

**Yapılmazsa ne olur:** GPU/model hatasında uygulama sessizce çöker, kullanıcı kafa karıştırıcı bir traceback görür; `/health` kontrolü hiçbir zaman çalışmaz çünkü servis import aşamasında ölür.

**Planlanan çözüm:** `Email_Embedding.__init__` içinde `GLOBAL_MODEL is None` durumunu kontrol et; `None` ise net bir `RuntimeError` fırlat ya da modeli atla. `main.py`'de embedder oluşturmayı try/except'e al ve `qdrant_storage` gibi `None`'a düşür; ilgili uçlar 503 dönsün.

---

## Madde 3 — Git'teki artık (stale) `.pyc` dosyaları ve gitignore çelişkileri

**Sorun:**
- `Decorators/__pycache__/*.cpython-312.pyc` git tarafından izleniyor ve artık var olmayan kaynaklara (`Email_Chunker_Decorator`, `Email_decorators`, `Email_parser_decorator`) ait.
- `.gitignore` `package-lock.json`'ı yoksayıyor ama `frontend/package-lock.json` izleniyor.
- `.gitignore` sonunda tek tek dosya yolları (`src/__pycache__/...cpython-312.pyc`, `frontend/public/hero.png` vb.) gereksiz/karışık.

**Neden çözüyoruz / Amaç:** Repoda yalnızca kaynak kod olmalı; derlenmiş çıktı (`.pyc`) izlenmemeli. Lock dosyası ise reproducible build için izlenmeli.

**Yapılmazsa ne olur:** Stale `.pyc`'ler kafa karıştırır, yanlış importlara yol açabilir, gereksiz diff/çakışma üretir. Lock dosyasının ignore edilmesi takım üyeleri arasında farklı bağımlılık sürümlerine yol açar.

**Planlanan çözüm:**
```
git rm -r --cached Decorators/__pycache__
```
`.gitignore`'dan `package-lock.json` satırını kaldır; sondaki spesifik/karışık satırları temizle (genel `__pycache__/` ve `*.pyc` kuralları zaten kapsıyor).

---

## Madde 4 — Retrieval kalitesi: sorgu embedding'i asimetrik olmalı

**Sorun:** `src/Email_Embedding.py:50` `embed_anything` hem indeksleme hem sorgu için aynı düz `model.encode(text)`'i kullanıyor. Qwen3-Embedding modelleri retrieval'da **sorgu için ayrı instruction/prompt** ister.

**Neden çözüyoruz / Amaç:** Qwen3 asimetrik retrieval'da sorguya bir instruction prefix'i (örn. "Given a web search query, retrieve relevant passages...") eklenmesini önerir. Bu, sorgu ile döküman vektörlerini doğru hizalayıp isabeti artırır.

**Yapılmazsa ne olur:** Sorgu ve dökümanlar aynı uzayda ama optimal hizalanmamış olur; alakalı chunk'lar `0.5` skor eşiğinin altında kalıp **hiç dönmeyebilir** veya alakasız sonuçlar üste çıkar. RAG cevabı "yeterli bilgi yok" demeye daha meyilli olur.

**Planlanan çözüm:** Sorgu için `model.encode(text, prompt_name="query")` veya Qwen3'ün önerdiği instruction prefix'ini kullan; indeksleme tarafı (dökümanlar) prefix'siz kalsın. `embed_anything`'e `is_query: bool = False` parametresi eklenebilir.

---

## Madde 5 — Testler ve CI

**Sorun:** `tests/` yok; kök `test.py` yalnızca elle LLM denemesi. GitHub Actions / lint yok.

**Neden çözüyoruz / Amaç:** Saf, deterministik fonksiyonlar (parser, chunker, sent-folder keşfi, prompt üretimi, reply parsing) test edilebilir. CI her push'ta bunları çalıştırıp regresyonu yakalar.

**Yapılmazsa ne olur:** Bir refactor sessizce davranışı bozar ve kimse fark etmez; "çalışıyor mu" sorusunun cevabı her zaman elle denemeye kalır.

**Planlanan çözüm:** `pytest` + `tests/` (örn. `test_email_utils.py`, `test_query_prompt.py`, `test_reply_parsing.py`). Basit bir `.github/workflows/ci.yml`: kurulum + `pytest`. Frontend için ESLint.

---

## Madde 6 — Konfigürasyonu tek yerde topla

**Sorun:** Qdrant URL/koleksiyon `main.py:29-30` ve `store_embeddings.py:19-21`'de iki kez sabit kodlu; `MODEL_PATH` `query_database.py:7` ve `test.py:4`'te tekrarlı. Sadece e-posta bilgileri `.env`'den geliyor.

**Neden çözüyoruz / Amaç:** Tek kaynak (single source of truth). Ortam değişkeniyle (örn. sunucuda farklı Qdrant host'u) yapılandırılabilirlik.

**Yapılmazsa ne olur:** Bir değeri değiştirmek için birden çok dosyayı elle güncellemek gerekir; biri unutulursa tutarsızlık ve hata oluşur. Farklı ortama (prod) taşımak kodu değiştirmeyi gerektirir.

**Planlanan çözüm:** `src/config.py` (Pydantic `BaseSettings` veya basit `os.environ` okuması): `QDRANT_URL`, `QDRANT_COLLECTION`, `MODEL_PATH`, `EMBED_MODEL_NAME`, `LLM_N_CTX` vb. Tüm dosyalar buradan okusun.

---

## Madde 7 — Türkçe içerik için chunking stratejisi

**Sorun:** `src/Email_Chunker.py:26` İngilizce `en_core_web_sm` ile cümle bölütleme yapıyor; içerik Türkçe olabiliyor (reply üretici Türkçe destekliyor).

**Neden çözüyoruz / Amaç:** Cümle sınırlarının doğru bulunması chunk kalitesini ve dolayısıyla retrieval'ı belirler. Türkçe metinde İngilizce model sınırları yanlış koyar.

**Yapılmazsa ne olur:** Chunk'lar cümle ortasından bölünür/yanlış birleşir; embedding'ler daha gürültülü olur, retrieval isabeti düşer.

**Planlanan çözüm:** Çok dilli pipeline (`xx_sent_ud_sm`) ya da spaCy'nin kural tabanlı `sentencizer`'ı (dilden bağımsız, hızlı). Alternatif: dil tespiti + dile uygun model.

---

## Madde 8 — Dockerfile + docker-compose

**Sorun:** Uygulamayı (API + frontend + Qdrant) ayağa kaldıracak Docker yapılandırması yok; README sadece Qdrant için `docker run` veriyor. `.dockerignore` yok.

**Neden çözüyoruz / Amaç:** Tek komutla, tekrarlanabilir kurulum. Bağımlılık/sürüm farklarını ortadan kaldırır.

**Yapılmazsa ne olur:** Yeni bir makinede kurulum çok adımlı ve hataya açık; "bende çalışıyordu" sorunları. Dağıtım manuel.

**Planlanan çözüm:** `Dockerfile` (API) + `docker-compose.yml` (api + qdrant servisleri, volume'lar). GPU gerektiren kısım için NVIDIA runtime notu. `.dockerignore` ekle.

---

## Madde 9 — API kimlik doğrulama

**Sorun:** `src/main.py` uçları korumasız. `:8000`'e erişen herkes e-posta içeriğini sorgulayabilir. CORS sadece origin kısıtlar, erişim kontrolü değildir.

**Neden çözüyoruz / Amaç:** "Veri makineden çıkmıyor" iddiası doğru olsa da, lokal API yetkisiz olmamalı (aynı makinedeki başka süreçler/portu açan tüneller).

**Yapılmazsa ne olur:** Aynı ağdaki/makinedeki herhangi bir istemci özel e-posta verisine erişebilir.

**Planlanan çözüm:** Basit bir API token (env'den `API_TOKEN`, `Authorization` header kontrolü) veya FastAPI dependency. Frontend `client.js` token'ı header'a eklesin.

---

## Madde 10 — LLM yanıtlarını streaming'e çevir

**Sorun:** `/search`, `/summarize`, `/reply-suggest` 5–40 sn bloklayan isteklerle çalışıyor; token-by-token streaming yok.

**Neden çözüyoruz / Amaç:** Kullanıcı uzun beklemede ilerleme görmeli (UX). llama-cpp `stream=True` destekliyor.

**Yapılmazsa ne olur:** Kullanıcı 20–40 sn boş ekran görür, donmuş sanır; UX zayıf.

**Planlanan çözüm:** FastAPI `StreamingResponse` + llama-cpp `stream=True` ile SSE. Frontend `client.js` ve ilgili view'lar akışı işlesin.

---

## Madde 11 — Ölü branch temizliği

**Sorun:** `frontend` branch'i `llamacpp` ile birebir aynı; `origin/master` çok ıraksamış (ölü). `main` ile `llamacpp` merge edilmemiş.

**Neden çözüyoruz / Amaç:** Tek bir net ana hat (main) olmalı; hangi branch'in güncel olduğu belirsizliği bitmeli.

**Yapılmazsa ne olur:** Katkı/merge karmaşası, yanlış branch üzerinde çalışma riski.

**Planlanan çözüm:** `llamacpp`'i `main`'e merge et (ya da `main`'i ona), `frontend` ve `master`'ı kapat/sil. **Bu adım kullanıcı onayı gerektirir** (geçmişi etkiler).

---

## Madde 12 — LICENSE, bağımlılık pinleme, dil/stil standardizasyonu

**Sorun:**
- LICENSE yok.
- `requirements.txt` sürüm pini içermiyor (`torch`, `llama-cpp-python` için kritik).
- Kod yorumları Türkçe/İngilizce karışık; dosya adlandırma tutarsız (`Email_Receiver.py` vs `query_database.py`).

**Neden çözüyoruz / Amaç:** Kullanım haklarının netliği (LICENSE), tekrarlanabilir kurulum (pin), okunabilirlik (tek dil/stil).

**Yapılmazsa ne olur:** Lisans belirsizliği kullanımı engeller; pinlenmemiş `torch`/`llama-cpp-python` farklı makinede uyumsuzlukla patlar; karışık dil bakımı zorlaştırır.

**Planlanan çözüm:** LICENSE ekle (örn. MIT). `requirements.txt`'i pinle (`pip freeze` veya elle sürümler). Yorumları tek dile çek; PEP8 snake_case'e geçişi kademeli yap.

---

## Ek (rapordan): Diğer düzeltmeler
- `frontend/src/api/client.js:43` `postSummarize` varsayılan `limit=5`, backend varsayılanı `15` (`custom_types.py:18`) → tutarsız; eşitle.
- README'deki `your-username` placeholder'ı → gerçek repo (`kaanguler14/InsightMail`).
- Frontend error boundary ekle.
- `performance.log` için log rotation (sınırsız büyüyor).
- Aşırı geniş `except Exception` → ham mesaj istemciye dönmesin (bilgi sızıntısı).

---

## Öncelik Sırası (uygulama planı)

| Sıra | Madde | Etki | Çaba | Onay gerekir? |
|------|-------|------|------|---------------|
| 1 | İdempotent indeksleme | Yüksek | Düşük | Hayır |
| 2 | Model=None koruması | Yüksek | Düşük | Hayır |
| 3 | Git stale .pyc + gitignore | Orta | Düşük | Hayır |
| 4 | Asimetrik sorgu embedding | Yüksek | Düşük | Hayır |
| 5 | Test + CI | Yüksek | Orta | Hayır |
| 6 | Merkezi config | Orta | Orta | Hayır |
| 7 | Türkçe chunking | Orta | Orta | Hayır |
| 8 | Docker | Orta | Orta | Hayır |
| 9 | API auth | Orta | Düşük | Hayır |
| 10 | Streaming | Orta | Orta | Hayır |
| 11 | Branch temizliği | Düşük | Düşük | **Evet** |
| 12 | LICENSE / pin / stil | Düşük | Düşük | Hayır |
