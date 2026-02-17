import time
import logging
import types

logging.basicConfig(
    filename='performance.log',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)


def auto_perf_logger(cls):
    """
    Class decorator: wraps all methods and logs execution time.
    For fetch_mails, also logs mail count and total byte size.
    """
    for attr_name, attr_value in cls.__dict__.items():
        if isinstance(attr_value, types.FunctionType):
            original_func = attr_value

            def wrapper(self, *args, __orig_func=original_func, **kwargs):
                start = time.time()
                result = __orig_func(self, *args, **kwargs)
                end = time.time()
                duration = end - start

                message = f"{cls.__name__}.{__orig_func.__name__}: {duration:.3f}s"

                if __orig_func.__name__ == "fetch_mails" and isinstance(result, list):
                    mail_count = len(result)
                    total_bytes = sum(len(m.as_bytes()) for m in result)
                    message += f", mail count: {mail_count}, total size: {total_bytes} bytes"

                print(message)
                logging.info(message)
                return result

            setattr(cls, attr_name, wrapper)
    return cls
