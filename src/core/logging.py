import logging

# Configure the root logger
logging.basicConfig(
    level=logging.INFO,  # Change to DEBUG for more verbose output
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)

# Create a logger instance that can be imported anywhere
logger = logging.getLogger("loseme")  # you can choose any name

