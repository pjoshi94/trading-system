import sys
from config import settings
from storage.db import init_db


def main():
    print("Trading Intelligence System — startup")
    print()

    print("[1/2] Validating environment...")
    try:
        settings.validate()
    except EnvironmentError as e:
        print(f"\n  ERROR: {e}")
        sys.exit(1)
    print()

    print("[2/2] Initializing database...")
    init_db()
    print(f"  Database ready: {settings.DATABASE_URL}")
    print()

    print("Step 1 scaffold complete. Ready to build.")


if __name__ == "__main__":
    main()
