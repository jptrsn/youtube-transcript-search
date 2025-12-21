from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from backend.database import SessionLocal
from backend.services.websub_service import WebSubService
import logging

logger = logging.getLogger(__name__)

# Global scheduler instance
scheduler = None


def renew_websub_subscriptions_job():
    """
    Background job to renew expiring WebSub subscriptions.
    Runs daily and renews subscriptions expiring within 24 hours.
    """
    db = SessionLocal()
    try:
        logger.info("Starting WebSub subscription renewal job")
        websub_service = WebSubService(db)
        result = websub_service.renew_expiring_subscriptions(hours_before_expiry=24)

        logger.info(
            f"WebSub renewal job completed: "
            f"{result.get('renewed', 0)} renewed, "
            f"{result.get('failed', 0)} failed, "
            f"{result.get('total_expiring', 0)} total expiring"
        )
    except Exception as e:
        logger.error(f"Error in WebSub renewal job: {e}", exc_info=True)
    finally:
        db.close()


def start_scheduler():
    """
    Start the background scheduler with all scheduled jobs.
    """
    global scheduler

    if scheduler is not None:
        logger.warning("Scheduler already running, skipping initialization")
        return scheduler

    logger.info("Starting APScheduler")
    scheduler = BackgroundScheduler(
        timezone='UTC',
        job_defaults={
            'coalesce': True,  # Combine missed runs into one
            'max_instances': 1,  # Only one instance of each job at a time
            'misfire_grace_time': 3600  # Allow 1 hour grace period for missed jobs
        }
    )

    # Add WebSub renewal job - runs daily at 3:00 AM UTC
    scheduler.add_job(
        renew_websub_subscriptions_job,
        trigger=CronTrigger(hour=3, minute=0),
        id='renew_websub_subscriptions',
        name='Renew WebSub Subscriptions',
        replace_existing=True
    )

    scheduler.start()
    logger.info("APScheduler started successfully")

    return scheduler


def shutdown_scheduler():
    """
    Gracefully shutdown the scheduler.
    """
    global scheduler

    if scheduler is not None:
        logger.info("Shutting down APScheduler")
        scheduler.shutdown(wait=True)
        scheduler = None
        logger.info("APScheduler shut down successfully")