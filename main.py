import sys
from config import settings
from storage.db import init_db


def main():
    print("Trading Intelligence System — startup")
    print()

    print("[1/3] Validating environment...")
    try:
        settings.validate()
    except EnvironmentError as e:
        print(f"\n  ERROR: {e}")
        sys.exit(1)
    print()

    print("[2/3] Initializing database...")
    init_db()
    print(f"  Database ready: {settings.DATABASE_URL}")
    print()

    print("[3/3] Starting Slack bot...")
    from slack.bot import start
    start()


if __name__ == "__main__":
    main()
