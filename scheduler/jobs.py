import logging

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

logger = logging.getLogger(__name__)

# All times are Pacific Time (America/Los_Angeles observes PDT/PST automatically)
_TZ = "America/Los_Angeles"


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


def _run_earnings_night():
    try:
        from modules.earnings_night import run
        run()
    except Exception as e:
        logger.error(f"Earnings night check cron failed: {e}")
        try:
            from clients.slack_client import send_to_alerts
            send_to_alerts(text=f"Earnings night check failed: {e}")
        except Exception:
            pass


def build_scheduler() -> BackgroundScheduler:
    scheduler = BackgroundScheduler(timezone=_TZ)

    # Outlier 50 — 15th of each month at 10:00 AM PST
    scheduler.add_job(
        _run_outlier50,
        CronTrigger(day=15, hour=10, minute=0, timezone=_TZ),
        id="outlier50",
        name="outlier50",
        replace_existing=True,
    )

    # Weekly Flows — every Sunday at 6:00 PM PST
    scheduler.add_job(
        _run_weekly,
        CronTrigger(day_of_week="sun", hour=18, minute=0, timezone=_TZ),
        id="weekly_flows",
        name="weekly_flows",
        replace_existing=True,
    )

    # Nightly check — every day at 8:00 PM PST
    scheduler.add_job(
        _run_nightly,
        CronTrigger(hour=20, minute=0, timezone=_TZ),
        id="nightly_check",
        name="nightly_check",
        replace_existing=True,
    )

    # Earnings night check — weekdays at 7:00 PM PST (before nightly check)
    scheduler.add_job(
        _run_earnings_night,
        CronTrigger(day_of_week="mon-fri", hour=19, minute=0, timezone=_TZ),
        id="earnings_night_check",
        name="earnings_night_check",
        replace_existing=True,
    )

    return scheduler
