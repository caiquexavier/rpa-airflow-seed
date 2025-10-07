import logging

from src.services.listener_service import ListenerService


logger = logging.getLogger(__name__)


class ListenerController:
    def __init__(self) -> None:
        self.service = ListenerService()

    def run(self) -> None:
        logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
        logger.info("Starting RPA Listener controller")
        self.service.run()


