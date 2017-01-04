
import time


def retry(exceptions_to_retry, exception_callback, tries=3, delay=5, backoff=2):
    """
    Retry Decorator.

    :param exceptions_to_retry: Which exception (singular object type) OR exceptions (TUPLE of object types) do we expect ?
    :param exception_callback: (Optional) A method to call before the retry sleep delay.
    :param tries:  how many tries do you want to make ?
    :param delay:  how long in between tries ?
    :param backoff: what multiplier of delay do you want so that we don't hammer a failed call ?
    :return: the decorated function.
    """
    def deco_retry(f):
        def f_retry(*args, **kwargs):
            last_exception = None
            remaining_tries, next_delay = tries, delay
            while remaining_tries > 0:
                try:
                    return f(*args, **kwargs)
                except exceptions_to_retry as e:
                    if exception_callback:
                        exception_callback(e, remaining_tries, next_delay)
                    time.sleep(next_delay)
                    remaining_tries -= 1
                    next_delay *= backoff
                    last_exception = e
            raise last_exception
        return f_retry
    return deco_retry
