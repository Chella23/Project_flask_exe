# task_schedular.py
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.date import DateTrigger
from apscheduler.triggers.cron import CronTrigger
from datetime import datetime
from app.utils.site_blocker import block_website, unblock_website
from app import db
from app.models import ScheduledTask

# Create a global scheduler instance and a variable to store the app
scheduler = BackgroundScheduler()
flask_app = None  # Will be set in init_scheduler()

def schedule_task(task):
    """
    Schedule a task from the ScheduledTask model.
    Uses DateTrigger for one-time tasks and CronTrigger for recurring tasks.
    """
    if task.recurring:
        # For recurring tasks, use CronTrigger with day_of_week, hour, and minute.
        trigger = CronTrigger(day_of_week=task.day_of_week, hour=task.hour, minute=task.minute)
    else:
        # For one-time tasks, use DateTrigger.
        trigger = DateTrigger(run_date=task.run_date)
    
    # Schedule the appropriate job based on the task type.
    if task.task_type == "block":
        job = scheduler.add_job(func=execute_block_task, trigger=trigger, args=[task.id])
    elif task.task_type == "unblock":
        job = scheduler.add_job(func=execute_unblock_task, trigger=trigger, args=[task.id])
    else:
        return

    # Save the job id in the task record and commit.
    task.job_id = job.id
    db.session.commit()
    print(f"Scheduled task {task.id} for website {task.website} (job id: {job.id})")

def execute_block_task(task_id):
    """
    Job function that retrieves the task from the DB and calls block_website.
    Wrapped in the Flask application context.
    """
    global flask_app
    with flask_app.app_context():
        task = ScheduledTask.query.get(task_id)
        if task and task.active:
            success = block_website(task.website)
            print(f"[{datetime.now()}] Block task executed for {task.website}. Success: {success}")

def execute_unblock_task(task_id):
    """
    Job function that retrieves the task from the DB and calls unblock_website.
    Wrapped in the Flask application context.
    """
    global flask_app
    with flask_app.app_context():
        task = ScheduledTask.query.get(task_id)
        if task and task.active:
            success = unblock_website(task.website)
            print(f"[{datetime.now()}] Unblock task executed for {task.website}. Success: {success}")

def init_scheduler(app):
    """
    Initialize and start the scheduler within the app context.
    """
    global flask_app
    flask_app = app  # Save the Flask app for use in job functions.
    with app.app_context():
        if not scheduler.running:
            scheduler.start()
        print("Scheduler initialized and started.")

def add_scheduled_task(user_id, website, task_type, run_date=None, recurring=False,
                       day_of_week=None, block_hour=None, block_minute=None,
                       unblock_hour=None, unblock_minute=None):
    """
    Creates a new ScheduledTask and schedules it.
    For one-time tasks, run_date is used.
    For recurring tasks, day_of_week and times (block or unblock) are used.
    For block tasks, block_hour and block_minute are used;
    for unblock tasks, unblock_hour and unblock_minute are used.
    """
    new_task = ScheduledTask(
        user_id=user_id,
        website=website,
        task_type=task_type,
        run_date=run_date,
        recurring=recurring,
        day_of_week=day_of_week,
        hour=block_hour if task_type == "block" else unblock_hour,
        minute=block_minute if task_type == "block" else unblock_minute,
        active=True
    )
    db.session.add(new_task)
    db.session.commit()
    schedule_task(new_task)
    return new_task

def remove_scheduled_task(task_id):
    """
    Removes a scheduled task and its associated job.
    """
    task = ScheduledTask.query.get(task_id)
    if task and task.job_id:
        try:
            scheduler.remove_job(task.job_id)
        except Exception as e:
            print(f"Error removing job {task.job_id}: {e}")
        task.active = False
        db.session.commit()
        print(f"Scheduled task {task_id} removed.")
        return True
    return False
