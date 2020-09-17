from .pfcu import PFCU


def main():
    import sys
    import logging
    from tango import GreenMode
    from tango.server import run

    args = ["PFCU"] + sys.argv[1:]
    fmt = "%(asctime)s %(threadName)s %(levelname)s %(name)s %(message)s"
    logging.basicConfig(level=logging.INFO, format=fmt)
    run((PFCU,), args=args, green_mode=GreenMode.Asyncio)
