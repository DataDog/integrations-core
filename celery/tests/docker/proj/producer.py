import logging
import time

from tasks import add, multiply

# Configure logging to output to stdout
logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s: %(message)s')

if __name__ == "__main__":
    while True:
        try:
            addi = add.delay(4, 5)
            multi = multiply.delay(9, 9)
            logging.info("Task submitted: %s", addi.id)
            logging.info("Task submitted: %s", multi.id)
        except Exception as e:
            logging.error("Error submitting task", exc_info=e)
        time.sleep(5)
