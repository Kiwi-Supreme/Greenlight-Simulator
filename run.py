"""Main entry point to launch the Greenlight Simulator application."""
import sys
from pathlib import Path

# Add backend directory to Python path
PROJECT_ROOT = Path(__file__).resolve().parent
BACKEND_DIR = PROJECT_ROOT / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from server import app

if __name__ == "__main__":
    print("=" * 60)
    print("Greenlight Simulator Web Application")
    print("Server running at: http://127.0.0.1:5000")
    print("Press Ctrl+C to stop the server.")
    print("=" * 60)
    app.run(host="127.0.0.1", port=5000, debug=False)
