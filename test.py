from llama_cpp import Llama

# İndirdiğiniz GGUF dosyasının yolunu buraya yazın
MODEL_PATH = "models/Llama-3.2-3B-Instruct-Q4_K_M.gguf"

print("Model yükleniyor...")
# n_gpu_layers=-1 -> Tüm katmanları GPU'ya atar (RTX 2060 için ideal)
llm = Llama(
    model_path=MODEL_PATH,
    n_ctx=4096,          # Context penceresi
    n_gpu_layers=-1,     # GPU kullanımı (Hepsini GPU'ya yükle)
    verbose=True
)

# Örnek Sorgu
prompt = """
<|start_header_id|>system<|end_header_id|>
Sen yardımsever bir asistansın.
<|eot_id|>
<|start_header_id|>user<|end_header_id|>
Merhaba, nasılsın?
<|eot_id|>
<|start_header_id|>assistant<|end_header_id|>
"""

output = llm(
    prompt,
    max_tokens=256,
    stop=["<|eot_id|>"],
    echo=False
)

print(output['choices'][0]['text'])