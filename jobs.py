import datetime

from database import database
from objects import Admin

from telegram.error import BadRequest


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
            td = datetime.timedelta(hours=dt1.hour - now.hour, minutes=dt1.minute - now.minute)
            # if the total seconds are more then 0, its not our time yet
            if int(td.total_seconds()) > 0:
                continue
            database.end_timeout(key, admin.groups)
            del context.job.context["admins"][key]
    day = now.strftime("%a").lower()
    timeoff_admins = database.get_timeoff(day, float(now.strftime("%H.%M")))
    for admin in timeoff_admins:
        dt1 = datetime.datetime.strptime(admin.days[day]["until"], "%H:%M")
        td = datetime.timedelta(hours=dt1.hour - now.hour, minutes=dt1.minute - now.minute)
        if td.total_seconds() < 0:
            rotation = True
        else:
            rotation = False
        groups = {}
        for group_id in admin.days[day]["groups"]:
            groups[group_id] = admin.groups[group_id]
        context_dict = {"rotation": rotation, "until": admin.days[day]["until"], "groups": groups}
        context.job.context["admins"][admin.id] = context_dict
        database.start_timeout(groups.keys(), admin.id)


def group_check(context):
    for group in database.get_groups():
        try:
            admins = context.bot.get_chat_administrators(group.id)
        except BadRequest as e:
            if e.message == "Chat not found":
                database.remove_group(group.id)
                continue
            else:
                break
        admin_ids = [admin.user.id for admin in admins]
        if group.admins == admin_ids:
            continue
        for saved_id in group.admins:
            if saved_id not in admin_ids:
                database.remove_group_admin(group.id, saved_id)
            else:
                admin_ids.pop(saved_id)
        if admin_ids:
            database.add_group_admins(group.id, admin_ids)
