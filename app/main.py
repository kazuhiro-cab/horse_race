from app.gui.main_window import run
from app.logging_util import setup_logging


def main():
    setup_logging()
    run()


if __name__ == "__main__":
    main()
