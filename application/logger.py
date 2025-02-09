import logging

def setup_logger():
    """Configure and setup application logging"""
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    # Create a logger for this module
    logger = logging.getLogger(__name__)

    # Create a separate logger for YubiKey monitoring
    yubikey_logger = logging.getLogger('yubikey_monitor')
    yubikey_logger.setLevel(logging.WARNING)

    return logger, yubikey_logger