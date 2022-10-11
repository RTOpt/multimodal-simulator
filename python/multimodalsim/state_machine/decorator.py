import logging

logger = logging.getLogger(__name__)


# Decorator
def next_state(func):
    def wrapper(*args, **kwargs):
        args[0].state_machine.next_state(args[0].__class__)

        returned_value = func(*args, **kwargs)

        return returned_value

    return wrapper
