import os
import shutil
import sys
from config import settings
from storage.db import init_db

_REPO_BRAIN_DIR = os.path.join(os.path.dirname(__file__), "data", "brain")


def _seed_brain_files():
    """Copy repo brain files to the volume brain dir if they don't exist there yet.

    On Railway, BRAIN_DIR=/data/brain (persistent volume) which starts empty.
    The source files in data/brain/ are committed to git and contain the latest
    checkpoints and context. We copy them once on first boot so the bot has
    immediate context without waiting for a module run.
    """
    from brain.checkpoints import BRAIN_DIR
    if BRAIN_DIR == _REPO_BRAIN_DIR:
        return  # same dir locally — nothing to do
    os.makedirs(BRAIN_DIR, exist_ok=True)
    copied = []
    for fname in os.listdir(_REPO_BRAIN_DIR):
        dest = os.path.join(BRAIN_DIR, fname)
        if not os.path.exists(dest):
            shutil.copy2(os.path.join(_REPO_BRAIN_DIR, fname), dest)
            copied.append(fname)
    if copied:
        print(f"  Seeded brain files from repo: {', '.join(copied)}")
    else:
        print(f"  Brain files already present at {BRAIN_DIR}")


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

    _seed_brain_files()
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
