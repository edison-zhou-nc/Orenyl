"""Development-only stdio entrypoint for orenyl server."""

import asyncio

from .server import get_transport_mode, run_stdio_server, validate_transport_mode


def main() -> None:
    mode = get_transport_mode()
    validate_transport_mode(mode)
    asyncio.run(run_stdio_server())


if __name__ == "__main__":
    main()
