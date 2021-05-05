import datetime
import io
import subprocess

from database import database
from objects import Admin

from tokens import BACKUP_CHANNEL


def half_hourly(context):
    now = datetime.datetime.now()
    # check if an admin in timeout exists
    if context.job.context["admins"]:
        if context.job.context["date"] != now.strftime("%d.%m"):
            rotation = True
            context.job.context["date"] = now.strftime("%d.%m")
        else:
            rotation = False
        # key is the user_id
        for key in list(context.job.context["admins"].keys()):
            # create admin object for better access
            admin = Admin(**context.job.context["admins"][key])
            # if we passed 00, we need to set rotation to false cause we rotated
            if rotation:
                if admin.rotation:
                    admin.rotation = False
            # if we still have rotation, its not our time yet, so we pass on the admin
            if admin.rotation:
                continue
            dt1 = datetime.datetime.strptime(admin.until, "%H:%M")
            td = datetime.timedelta(
                hours=dt1.hour - now.hour, minutes=dt1.minute - now.minute
            )
            # if the total seconds are more then 0, its not our time yet
            if int(td.total_seconds()) > 0:
                continue
            database.end_timeout(key, admin.groups)
            del context.job.context["admins"][key]
    day = now.strftime("%a").lower()
    timeoff_admins = database.get_timeoff(day, float(now.strftime("%H.%M")))
    for admin in timeoff_admins:
        dt1 = datetime.datetime.strptime(admin.days[day]["until"], "%H:%M")
        td = datetime.timedelta(
            hours=dt1.hour - now.hour, minutes=dt1.minute - now.minute
        )
        if td.total_seconds() < 0:
            rotation = True
        else:
            rotation = False
        groups = {}
        for group_id in admin.days[day]["groups"]:
            groups[group_id] = admin.groups[group_id]
        context_dict = {
            "rotation": rotation,
            "until": admin.days[day]["until"],
            "groups": groups,
        }
        context.job.context["admins"][admin.id] = context_dict
        database.start_timeout(groups.keys(), admin.id)


def backup_job(context):
    run = subprocess.run(
        ["mongodump", "-dreportbot", "--gzip", "--archive"], capture_output=True
    )
    output = io.BytesIO(run.stdout)
    time = datetime.datetime.now().strftime("%d-%m-%Y")
    context.bot.send_document(BACKUP_CHANNEL, output, filename=f"{time}.archive.gz")
