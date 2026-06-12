"""Serve a local directory of assets over HTTP for development registry fetching."""

from __future__ import annotations

import argparse
import os
from functools import partial
from http.server import HTTPServer, SimpleHTTPRequestHandler
from pathlib import Path
from typing import Optional


def run_development_server(host: str, port: int, directory: Path) -> None:
    directory = Path(directory).resolve()
    if not directory.exists():
        raise FileNotFoundError(f"Serve directory {directory} does not exist.")

    handler = partial(SimpleHTTPRequestHandler, directory=str(directory))
    server = HTTPServer((host, port), handler)

    print(f"Serving {directory} at http://{host}:{port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down ...")
        server.server_close()


def parse_args(argv: Optional[list[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--host",
        default="localhost",
        help="Host/interface to bind. Defaults to localhost.",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8000,
        help="Port to listen on. Defaults to 8000.",
    )
    parser.add_argument(
        "-d", "--directory",
        type=Path,
        default=os.environ.get("PSI_DATA_DEV_DIR"),
        help="Directory to serve. Defaults to the $PSI_DATA_DEV_DIR environment variable.",
    )
    args = parser.parse_args(argv)
    if args.directory is None:
        parser.error("no directory given and $DEV_DIR is not set")
    return args


def main(argv: Optional[list[str]] = None) -> None:
    args = parse_args(argv)
    run_development_server(host=args.host, port=args.port, directory=args.directory)


if __name__ == "__main__":
    main()