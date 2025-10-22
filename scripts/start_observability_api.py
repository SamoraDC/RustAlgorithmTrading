#!/usr/bin/env python3
"""
Start the Observability API server.

This script starts the FastAPI backend with WebSocket streaming
for the real-time observability dashboard.

Usage:
    python scripts/start_observability_api.py [--host HOST] [--port PORT] [--reload]

Example:
    python scripts/start_observability_api.py --port 8000 --reload
"""
import argparse
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))


def main():
    """Start the FastAPI server."""
    parser = argparse.ArgumentParser(description="Start Observability API server")
    parser.add_argument(
        "--host",
        default="0.0.0.0",
        help="Host to bind to (default: 0.0.0.0)"
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8000,
        help="Port to bind to (default: 8000)"
    )
    parser.add_argument(
        "--reload",
        action="store_true",
        help="Enable auto-reload for development"
    )
    parser.add_argument(
        "--workers",
        type=int,
        default=1,
        help="Number of worker processes (default: 1)"
    )
    parser.add_argument(
        "--log-level",
        default="info",
        choices=["critical", "error", "warning", "info", "debug", "trace"],
        help="Log level (default: info)"
    )

    args = parser.parse_args()

    # Import uvicorn here to avoid import issues
    import uvicorn

    print("=" * 60)
    print("Starting Observability API Server")
    print("=" * 60)
    print(f"Host: {args.host}")
    print(f"Port: {args.port}")
    print(f"Workers: {args.workers}")
    print(f"Reload: {args.reload}")
    print(f"Log Level: {args.log_level}")
    print("=" * 60)
    print()
    print("API Documentation: http://localhost:{}/docs".format(args.port))
    print("WebSocket Endpoint: ws://localhost:{}/ws/metrics".format(args.port))
    print("Health Check: http://localhost:{}/health".format(args.port))
    print()
    print("Press Ctrl+C to stop the server")
    print("=" * 60)

    # Run the server
    uvicorn.run(
        "observability.api.main:app",
        host=args.host,
        port=args.port,
        reload=args.reload,
        workers=args.workers if not args.reload else 1,  # Can't use workers with reload
        log_level=args.log_level,
        access_log=True
    )


if __name__ == "__main__":
    main()
