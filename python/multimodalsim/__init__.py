import logging

from multimodalsim.logger.formatter import ColoredFormatter

logging.basicConfig(level=logging.INFO)

# Replace default handler with custom handler
console_stream_handler = logging.StreamHandler()
console_stream_handler.setFormatter(ColoredFormatter())
# Add fmt="%(message)s" as argument if you only want to see the output (without time and line numbers).

root_logger = logging.getLogger()

### If you want debug mode add the following line
# logging.getLogger().setLevel(logging.DEBUG)

# Remove default handler
for h in root_logger.handlers:
    root_logger.removeHandler(h)

# Add custom handler
root_logger.addHandler(console_stream_handler)