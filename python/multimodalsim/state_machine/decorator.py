from functools import wraps


# Decorator
def next_state(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        args[0].state_machine.next_state(args[0].__class__)

        returned_value = func(*args, **kwargs)

        return returned_value

    return wrapper
