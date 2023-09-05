from requests.exceptions import HTTPError


def http_error(message):
    def decorator_func(func):
        def wrapper(self, *args, **kwargs):
            try:
                func(self, *args, **kwargs)
            except HTTPError as e:
                raise Exception("%s: %s", message, e)

        return wrapper

    return decorator_func
