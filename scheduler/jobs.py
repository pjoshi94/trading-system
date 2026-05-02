import logging

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

logger = logging.getLogger(__name__)

# All times are Mountain Time (America/Denver observes MDT/MST automatically)
_TZ = "America/Denver"


def _run_outlier50():
    try:
        from modules.outlier50_module import run
        run()
    except Exception as e:
        logger.error(f"Outlier 50 cron failed: {e}")
        try:
            from clients.slack_client import send_to_main
            send_to_main(text=f"Outlier 50 scheduled run failed: {e}")
        except Exception:
            pass


def _run_weekly():
    try:
        from modules.weekly_module import run
        run()
    except Exception as e:
        logger.error(f"Weekly Flows cron failed: {e}")
        try:
            from clients.slack_client import send_to_main
            send_to_main(text=f"Weekly Flows scheduled run failed: {e}")
        except Exception:
            pass


def _run_nightly():
    try:
        from modules.daily_module import run
        run()
    except Exception as e:
        logger.error(f"Nightly check cron failed: {e}")
        try:
            from clients.slack_client import send_to_main
            send_to_main(text=f"Nightly check scheduled run failed: {e}")
        except Exception:
            pass


def build_scheduler() -> BackgroundScheduler:
    scheduler = BackgroundScheduler(timezone=_TZ)

    # Outlier 50 — 15th of each month at 7:00 AM MT
    scheduler.add_job(
        _run_outlier50,
        CronTrigger(day=15, hour=7, minute=0, timezone=_TZ),
        id="outlier50",
        name="outlier50",
        replace_existing=True,
    )

    # Weekly Flows — every Saturday at 9:00 AM MT
    scheduler.add_job(
        _run_weekly,
        CronTrigger(day_of_week="sat", hour=9, minute=0, timezone=_TZ),
        id="weekly_flows",
        name="weekly_flows",
        replace_existing=True,
    )

    # Nightly check — weekdays (Mon–Fri) at 9:30 PM MT
    scheduler.add_job(
        _run_nightly,
        CronTrigger(day_of_week="mon-fri", hour=21, minute=30, timezone=_TZ),
        id="nightly_check",
        name="nightly_check",
        replace_existing=True,
    )

    return scheduler
