import time
from functools import wraps

def auto_perf_logger(cls):
    """
    Sınıftaki tüm metotları sarmalar ve çalıştırma süresini loglar.
    """
    for attr_name, attr_value in cls.__dict__.items():
        if callable(attr_value) and not attr_name.startswith("__"):
            setattr(cls, attr_name, _log_wrapper(attr_value))
    return cls

def _log_wrapper(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        start = time.time()
        result = func(*args, **kwargs)
        end = time.time()
        print(f"[PERF] {func.__qualname__} çalıştı: {end-start:.4f}s")
        return result
    return wrapper
