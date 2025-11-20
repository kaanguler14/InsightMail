import time
import logging
import types
import email

logging.basicConfig(
    filename='performance.log',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

def auto_perf_logger(cls):
    """
    Sınıf dekoratörü: tüm metodları sarar, süreyi ölçer.
    fetch_mails metodunda mail sayısı ve toplam byte boyutu da loglanır.
    """
    for attr_name, attr_value in cls.__dict__.items():
        if isinstance(attr_value, types.FunctionType):
            original_func = attr_value

            def wrapper(self, *args, __orig_func=original_func, **kwargs):
                start = time.time()
                result = __orig_func(self, *args, **kwargs)
                end = time.time()
                duration = end - start

                message = f"{cls.__name__}.{__orig_func.__name__} çalıştı: {duration:.3f}s"

                # fetch_mails için özel log: mail sayısı ve toplam boyut
                if __orig_func.__name__ == "fetch_mails" and isinstance(result, list):
                    mail_count = len(result)
                    total_bytes = sum(len(m.as_bytes()) for m in result)
                    message += f", mail sayısı: {mail_count}, toplam boyut: {total_bytes} byte"

                print(message)
                logging.info(message)
                return result

            setattr(cls, attr_name, wrapper)
    return cls
