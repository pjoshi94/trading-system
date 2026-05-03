import sys
from config import settings
from storage.db import init_db


def main():
    print("Trading Intelligence System — startup")
    print()

    print("[1/4] Validating environment...")
    try:
        settings.validate()
    except EnvironmentError as e:
        print(f"\n  ERROR: {e}")
        sys.exit(1)
    print()

    print("[2/4] Initializing database...")
    init_db()
    from storage.db import run_migrations
    run_migrations()
    print(f"  Database ready: {settings.DATABASE_URL}")
    print()

    print("[3/4] Starting scheduler...")
    from scheduler.jobs import build_scheduler
    scheduler = build_scheduler()
    scheduler.start()
    jobs = scheduler.get_jobs()
    for job in jobs:
        print(f"  {job.name}: next run {job.next_run_time}")
    print()

    print("[4/4] Starting Slack bot...")
    from slack.bot import start
    start()


if __name__ == "__main__":
    main()
