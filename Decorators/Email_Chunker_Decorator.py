import time
from functools import wraps

def auto_perf_logger(cls):
    """
    Decorator: Sınıftaki her methodun çalışma süresini loglar.
    """
    for attr_name in dir(cls):
        if attr_name.startswith("__"):
            continue

        attr = getattr(cls, attr_name)
        if callable(attr):

            @wraps(attr)
            def wrapper(self, *args, __attr=attr, **kwargs):
                start = time.time()
                result = __attr(self, *args, **kwargs)
                end = time.time()
                print(f"[PERF] {cls.__name__}.{__attr.__name__} çalıştı: {end-start:.4f}s")
                return result

            setattr(cls, attr_name, wrapper)

    return cls
