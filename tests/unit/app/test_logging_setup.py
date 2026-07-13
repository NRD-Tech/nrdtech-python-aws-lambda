from app.logging_setup import configure_logging, get_logger


def test_configure_logging_returns_logger():
    configure_logging()
    log = get_logger("test")
    log.info("unit_test_event", ok=True)
