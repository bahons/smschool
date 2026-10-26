import uvicorn
import sys
import os

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

if __name__ == "__main__":
    print("=" * 60)
    print("  Smart School AI: Веб-сайт және REST API сервері")
    print("  Веб-сайт: http://localhost:8000")
    print("  Swagger API құжаттамасы: http://localhost:8000/docs")
    print("=" * 60)
    uvicorn.run("src.api.app:app", host="0.0.0.0", port=8000, reload=False)
