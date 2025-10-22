#!/usr/bin/env python3
"""
Production-ready ASGI server for Observability API.

Features:
- Uvicorn with optimal configuration
- Auto-reload in development mode
- Graceful shutdown handling
- Production-ready logging
- Multiple worker processes (production)
- SSL/TLS support (optional)
"""
import os
import sys
import argparse
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import uvicorn
from loguru import logger


def configure_logging(log_level: str = "INFO"):
    """Configure logging for the server."""
    logger.remove()  # Remove default handler

    # Console logging with colors
    logger.add(
        sys.stdout,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan> - <level>{message}</level>",
        level=log_level,
        colorize=True
    )

    # File logging
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)

    logger.add(
        log_dir / "observability_api.log",
        rotation="100 MB",
        retention="10 days",
        level=log_level,
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function} - {message}"
    )


def main():
    """Main entry point for the server."""
    parser = argparse.ArgumentParser(
        description="Observability API Server",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Development mode with auto-reload
  python server.py --dev

  # Production mode with multiple workers
  python server.py --workers 4

  # Custom host and port
  python server.py --host 0.0.0.0 --port 8080

  # Enable SSL/TLS
  python server.py --ssl-keyfile key.pem --ssl-certfile cert.pem
        """
    )

    parser.add_argument(
        "--host",
        default="127.0.0.1",
        help="Bind host (default: 127.0.0.1)"
    )

    parser.add_argument(
        "--port",
        type=int,
        default=8000,
        help="Bind port (default: 8000)"
    )

    parser.add_argument(
        "--workers",
        type=int,
        default=1,
        help="Number of worker processes (production only, default: 1)"
    )

    parser.add_argument(
        "--dev",
        action="store_true",
        help="Enable development mode with auto-reload"
    )

    parser.add_argument(
        "--log-level",
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="Logging level (default: INFO)"
    )

    parser.add_argument(
        "--ssl-keyfile",
        help="SSL key file path"
    )

    parser.add_argument(
        "--ssl-certfile",
        help="SSL certificate file path"
    )

    parser.add_argument(
        "--access-log",
        action="store_true",
        help="Enable access logging"
    )

    args = parser.parse_args()

    # Configure logging
    configure_logging(args.log_level)

    # Server configuration
    config = {
        "app": "observability.api.main:app",
        "host": args.host,
        "port": args.port,
        "log_level": args.log_level.lower(),
        "access_log": args.access_log,
    }

    # Development mode configuration
    if args.dev:
        logger.info("Starting in DEVELOPMENT mode with auto-reload")
        config.update({
            "reload": True,
            "reload_dirs": [str(Path(__file__).parent)],
            "reload_includes": ["*.py"],
        })
    else:
        logger.info("Starting in PRODUCTION mode")
        config.update({
            "workers": args.workers,
            "loop": "uvloop",  # Use uvloop for better performance
            "http": "httptools",  # Use httptools for better performance
        })

    # SSL/TLS configuration
    if args.ssl_keyfile and args.ssl_certfile:
        if not Path(args.ssl_keyfile).exists():
            logger.error(f"SSL key file not found: {args.ssl_keyfile}")
            sys.exit(1)

        if not Path(args.ssl_certfile).exists():
            logger.error(f"SSL certificate file not found: {args.ssl_certfile}")
            sys.exit(1)

        config.update({
            "ssl_keyfile": args.ssl_keyfile,
            "ssl_certfile": args.ssl_certfile,
        })
        logger.info("SSL/TLS enabled")

    # Log configuration
    logger.info(f"Server configuration:")
    logger.info(f"  Host: {args.host}")
    logger.info(f"  Port: {args.port}")
    logger.info(f"  Workers: {args.workers if not args.dev else 'auto-reload'}")
    logger.info(f"  Log level: {args.log_level}")
    logger.info(f"  Access log: {args.access_log}")

    # Create data directory for DuckDB
    data_dir = Path("data")
    data_dir.mkdir(exist_ok=True)
    logger.info(f"Data directory: {data_dir.absolute()}")

    # Start server
    try:
        logger.info("Starting Observability API server...")
        logger.info(f"API docs available at: http://{args.host}:{args.port}/docs")
        logger.info(f"WebSocket endpoint: ws://{args.host}:{args.port}/ws/metrics")

        uvicorn.run(**config)
    except KeyboardInterrupt:
        logger.info("Server shutdown requested")
    except Exception as e:
        logger.error(f"Server error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
