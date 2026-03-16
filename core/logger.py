import logging
from PyQt6.QtCore import QObject, pyqtSignal

class QtLogHandler(logging.Handler, QObject):
    """Custom LOGGING HANDLER that emits a signal for every log record."""
    new_record = pyqtSignal(str, int)  # message, level_number

    def __init__(self):
        # Initialize both parents
        logging.Handler.__init__(self)
        QObject.__init__(self)
        
        # Set a professional format
        self.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s', '%H:%M:%S'))

    def emit(self, record):
        msg = self.format(record)
        # Emit signal to be caught by the UI (Thread-safe!)
        self.new_record.emit(msg, record.levelno)

def setup_logger():
    """Configures the global logger."""
    logger = logging.getLogger("SolderBot")
    logger.setLevel(logging.DEBUG)

    # Create our custom UI handler
    ui_handler = QtLogHandler()
    logger.addHandler(ui_handler)

    #TODO: Test files 
    # # Optionally: Add a file handler so you don't lose logs if the UI crashes
    # file_handler = logging.FileHandler("solderbot.log")
    # file_handler.setFormatter(logging.Formatter('%(asctime)s [%(levelname)s] %(message)s'))
    # logger.addHandler(file_handler)

    return logger, ui_handler