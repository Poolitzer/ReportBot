import datetime
import sys
import traceback

from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.utils.helpers import mention_html

import strings
from database import database
from objects import Admin
from utils import build_menu, group_setting_buttons, edit, group_id_generator


def group_check(func):
    def wrapper(*args, **kwargs):
        context = args[1]
        update = args[0]
        if "group" not in context.user_data:
            update.callback_query.edit_message_text(strings.EXPIRED)
            return
        return func(*args, **kwargs)

    return wrapper


def start(update, _):
    update.effective_message.reply_text(strings.PRIVATE_START)


def settings(update, context):
    user_id = update.effective_user.id
    groups = database.get_groups_admin(user_id)
    buttons = [InlineKeyboardButton(group.title, callback_data=f"settings_{group.id}") for group in groups]
    update.effective_message.reply_text(strings.SETTINGS_COMMAND,
                                        reply_markup=InlineKeyboardMarkup(build_menu(buttons, 4)))
    context.user_data["groups"] = groups


def select_group(update, context):
    query = update.callback_query
    user_data = context.user_data
    if "groups" not in user_data:
        query.edit_message_text(strings.EXPIRED)
        query.answer()
        return
    chat_id = int(query.data.split("_")[1])
    for group in user_data["groups"]:
        if group.id == chat_id:
            user_data["group"] = group
            break
    user_id = update.effective_user.id
    buttons = group_setting_buttons(user_data["group"], user_id)
    query.edit_message_text(strings.SETTINGS_MESSAGE.format(user_data["group"].title),
                            reply_markup=InlineKeyboardMarkup(buttons), parse_mode="HTML")
    del user_data["groups"]
    query.answer()


@group_check
def group_report(update, context):
    group = context.user_data["group"]
    # wanted direction: both => @admin => /report => both
    if group.admin:
        if group.report:
            new = "a"
        else:
            new = "r"
    else:
        new = "b"
    new_group = database.insert_group_report(group.id, new)
    context.user_data["group"] = new_group
    edit(update, new_group)


@group_check
def group_reply_confirmation(update, context):
    group = context.user_data["group"]
    if group.reply and "warned" not in context.user_data:
        query = update.callback_query
        query.answer(strings.REPLY_WARNING, show_alert=True)
        context.user_data["warned"] = True
    else:
        if "warned" in context.user_data:
            del context.user_data["warned"]
        group_reply(update, context)


@group_check
def group_reply(update, context):
    group = context.user_data["group"]
    if group.reply:
        group.reply = False
        to_pass = [x for x in group.admins if x not in group.off]
    else:
        group.reply = True
        to_pass = False
    new_group = database.insert_group_reply(group.id, to_pass)
    context.user_data["group"] = new_group
    edit(update, new_group)


@group_check
def group_mention(update, context):
    group = context.user_data["group"]
    user_id = update.effective_user.id
    # mention => PM => off => mention
    if group.reply:
        if user_id in group.pm:
            new = "o"
        elif user_id in group.off:
            new = "m"
        else:
            new = "p"
    # PM => off => PM
    else:
        if user_id in group.pm:
            new = "o"
        else:
            new = "p"
    new_group = database.insert_group_mention(group.id, group.reply, new, user_id)
    context.user_data["group"] = new_group
    edit(update, new_group)


def back(update, context):
    user_id = update.effective_user.id
    groups = database.get_groups_admin(user_id)
    buttons = [InlineKeyboardButton(group.title, callback_data=f"settings_{group.id}") for group in groups]
    update.callback_query.edit_message_text(strings.SETTINGS_COMMAND,
                                            reply_markup=InlineKeyboardMarkup(build_menu(buttons, 4)))
    context.user_data["groups"] = groups
    if "group" in context.user_data:
        del context.user_data["group"]
    update.callback_query.answer()


def reload_admins(update, _):
    update.effective_message.reply_text(strings.ADMIN_RELOAD_PRIVATE)


def help_command(update, _):
    update.effective_message.reply_text(strings.PRIVATE_HELP, parse_mode="HTML")


def timeout_command(update, context):
    user_id = update.effective_user.id
    groups = database.get_groups_admin(user_id)
    group_string = group_id_generator(groups)
    now = datetime.datetime.now()
    update.effective_message.reply_text(strings.TIMEOUT_COMMAND.format(group_string, now.strftime("%H:%M")),
                                        parse_mode="HTML")
    context.user_data.update({"timeout": True, "groups": groups, "now": now})


def timeout(update, context):
    user_data = context.user_data
    if "timeout" not in user_data:
        return
    message = update.effective_message
    user_input = message.text.split(" ")
    user_id = update.effective_user.id
    if len(user_input) != 2:
        message.reply_text(strings.TIMEOUT_WHITESPACE)
        return
    if user_input[0] == "all":
        groups = user_data["groups"]
    else:
        groups = []
        for index in user_input[0].split(","):
            try:
                groups.append(user_data["groups"][int(index)])
            except IndexError or ValueError:
                message.reply_text(strings.TIMEOUT_INDEX)
                return
    try:
        dt1 = datetime.datetime.strptime(user_input[1], "%H:%M")
    except ValueError:
        message.reply_text(strings.TIMEOUT_DATE)
        return
    groups_dict = {}
    for group in groups:
        if user_id in group.pm:
            mention = "pm"
        elif user_id in group.off:
            mention = "off"
        else:
            mention = False
        groups_dict[group.id] = mention
    admin = Admin(until=user_input[1], groups=groups_dict)
    dt2 = user_data["now"]
    td = datetime.timedelta(hours=dt1.hour - dt2.hour, minutes=dt1.minute - dt2.minute)
    if td.total_seconds() < 0:
        admin.rotation = True
    job = context.job_queue.get_jobs_by_name("half-hourly")[0]
    job.context["admins"][user_id] = vars(admin)
    database.start_timeout([x.id for x in groups], user_id)
    message.reply_text(strings.TIMEOUT_SUCCEED)
    user_data.clear()


def timeoff_command(update, context):
    user_id = update.effective_user.id
    groups = database.get_groups_admin(user_id)
    group_string = group_id_generator(groups)
    now = datetime.datetime.now()
    update.effective_message.reply_text(strings.TIMEOFF_COMMAND.format(group_string, now.strftime("%a - %H:%M")),
                                        parse_mode="HTML")
    context.user_data.update({"timeoff": True, "groups": groups, "now": now})


def timeoff(update, context):
    user_data = context.user_data
    if "timeoff" not in user_data:
        return
    message = update.effective_message
    user_days = message.text.split("\n")
    user_id = update.effective_user.id
    for index, string in enumerate(user_days):
        user_days[index] = string.split(" ")
    admin = Admin(user_id)
    for index, user_day in enumerate(user_days):
        if len(user_day) != 3:
            message.reply_text(strings.TIMEOFF_WHITESPACE.format(index))
        if user_day[1] == "all":
            groups = user_data["groups"]
        else:
            groups = []
            for group_id in user_day[1].split(","):
                try:
                    groups.append(user_data["groups"][int(group_id)])
                except IndexError or ValueError:
                    message.reply_text(strings.TIMEOFF_INDEX.format(index))
                    return
        group_ids = []
        for group in groups:
            group_ids.append(group.id)
            if group.id in admin.groups:
                continue
            if user_id in group.pm:
                mention = "pm"
            elif user_id in group.off:
                mention = "off"
            else:
                mention = False
            admin.groups[group.id] = mention
        try:
            dt1 = datetime.datetime.strptime(user_day[2].split(",")[0], "%H:%M")
            dt2 = datetime.datetime.strptime(user_day[2].split(",")[1], "%H:%M")
            td = dt2 - dt1
            if td.total_seconds() < 0:
                raise ValueError
        except ValueError:
            message.reply_text(strings.TIMEOFF_DATE.format(index))
            return
        if not user_day[0].lower() in admin.days:
            message.reply_text(strings.TIMEOFF_DAY.format(index))
            return
        admin.days[user_day[0].lower()] = {"groups": group_ids, "until": user_day[2].split(",")[1],
                                           "when": float(user_day[2].split(",")[0].replace(":", "."))}
    database.insert_timeoff(admin)
    update.effective_message.reply_text(strings.TIMEOFF_SUCCEED)
    user_data.clear()


def timeoff_del(update, _):
    success = database.delete_timeoff(update.effective_user.id)
    update.effective_message.reply_text(strings.TIMEOFF_DELETE_SUCCESS if success else strings.TIMEOFF_DELETE_FAIL)


def error_handler(update, context):
    chat = update.effective_chat
    if update.callback_query:
        update.callback_query.answer(strings.ERROR, show_alert=True)
    else:
        update.effective_message.reply_text(strings.ERROR)
    payload = ""
    # normally, we always have an user. If not, its either a channel or a poll update.
    if update.effective_user:
        payload += f' with the user {mention_html(update.effective_user.id, update.effective_user.first_name)}'
    # there are more situations when you don't get a chat
    if update.effective_chat:
        payload += f' within the chat <i>{update.effective_chat.title}</i>'
        if update.effective_chat.username:
            payload += f' (@{update.effective_chat.username})'
    # but only one where you have an empty payload by now: A poll (buuuh)
    if update.poll:
        payload += f' with the poll id {update.poll.id}.'
    trace = "".join(traceback.format_tb(sys.exc_info()[2]))
    text = f"Oh no. The error <code>{context.error}</code> happened{payload}. The type of the chat is " \
           f"<code>{chat.type}</code>. The current user data is <code>{context.user_data}</code>, the chat data " \
           f"<code>{context.chat_data}</code>.\nThe full traceback:\n\n<code>{trace}</code>"
    context.bot.send_message(208589966, text, parse_mode="HTML")
    raise
