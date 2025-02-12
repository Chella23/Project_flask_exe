# task_scheduler.py
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.date import DateTrigger
from apscheduler.triggers.cron import CronTrigger
from datetime import datetime
from app.utils.site_blocker import block_website, unblock_website
from app import db
from app.models import ScheduledTask

# Create a global scheduler instance
scheduler = BackgroundScheduler()

def schedule_task(task):
    """
    Schedule a task from the ScheduledTask model.
    For one-time tasks, use DateTrigger; for recurring tasks, use CronTrigger.
    """
    if task.recurring:
        # For recurring tasks, we use CronTrigger.
        # Here we assume that day_of_week, hour, and minute are set.
        trigger = CronTrigger(day_of_week=task.day_of_week, hour=task.hour, minute=task.minute)
    else:
        # For one-time tasks, run at the given run_date.
        trigger = DateTrigger(run_date=task.run_date)

    if task.task_type == "block":
        job = scheduler.add_job(func=execute_block_task, trigger=trigger, args=[task.id])
    elif task.task_type == "unblock":
        job = scheduler.add_job(func=execute_unblock_task, trigger=trigger, args=[task.id])
    else:
        return

    # Save the job id in the task
    task.job_id = job.id
    db.session.commit()
    print(f"Scheduled task {task.id} for website {task.website} (job id: {job.id})")

def execute_block_task(task_id):
    """
    Job function that retrieves the task from the DB and calls block_website.
    """
    task = ScheduledTask.query.get(task_id)
    if task and task.active:
        success = block_website(task.website)
        print(f"[{datetime.now()}] Block task executed for {task.website}. Success: {success}")

def execute_unblock_task(task_id):
    """
    Job function that retrieves the task from the DB and calls unblock_website.
    """
    task = ScheduledTask.query.get(task_id)
    if task and task.active:
        success = unblock_website(task.website)
        print(f"[{datetime.now()}] Unblock task executed for {task.website}. Success: {success}")


def init_scheduler(app):
    """
    Initialize and start the scheduler within the app context.
    Use a local import for the 'db' to avoid circular import issues.
    """
    with app.app_context():
        # Local import avoids circular dependency issues.
        from app import db  
        # (Optionally, you can now use db for scheduling tasks that interact with your database.)
        if not scheduler.running:
            scheduler.start()
        # You might also load scheduled tasks from the database here, for example:
        # tasks = ScheduledTask.query.all()
        # for task in tasks:
        #     if task.recurring:
        #         trigger = CronTrigger(day_of_week=task.day_of_week, hour=task.hour, minute=task.minute)
        #     else:
        #         trigger = DateTrigger(run_date=task.run_date)
        #     scheduler.add_job(your_task_function, trigger, args=[task])
        print("Scheduler initialized and started.")

def add_scheduled_task(user_id, website, task_type, run_date=None, recurring=False, day_of_week=None, hour=None, minute=None):
    """
    Creates a new scheduled task and schedules it.
    For one-time tasks, supply run_date (a datetime object).
    For recurring tasks, set recurring=True and provide cron parameters.
    """
    new_task = ScheduledTask(
        user_id=user_id,
        website=website,
        task_type=task_type,
        run_date=run_date,
        recurring=recurring,
        day_of_week=day_of_week,
        hour=hour,
        minute=minute,
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
