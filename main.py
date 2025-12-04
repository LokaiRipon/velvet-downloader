import sys
import logging
from PyQt6.QtWidgets import QApplication
from app import VelvetDownApp

# Configure logging for the entire application
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

if __name__ == "__main__":
    logger.info("Starting VelvetDown application")
    app = QApplication(sys.argv)
    window = VelvetDownApp()
    window.show()
    logger.info("Application window displayed")
    sys.exit(app.exec())