import socket
import sys
import os
import uvicorn

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')


def find_free_port(start_port: int = 8080) -> int:
    """Finds an available TCP port starting from start_port."""
    port = start_port
    while port < start_port + 100:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                s.bind(('127.0.0.1', port))
                return port
            except OSError:
                port += 1
    return start_port


if __name__ == "__main__":
    port = find_free_port(8080)
    print("=" * 65)
    print("  🏫 SMART SCHOOL AI: Веб-сайт және REST API сервері")
    print(f"  👉 Веб-сайтты ашыңыз:      http://localhost:{port}")
    print(f"  👉 Swagger API құжаттамасы: http://localhost:{port}/docs")
    print("=" * 65)

    uvicorn.run("src.api.app:app", host="127.0.0.1", port=port, reload=False)
