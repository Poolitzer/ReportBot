import datetime
import html
import sys
import traceback

from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.utils.helpers import mention_html

import strings
from database import database
from objects import Admin
from tokens import DEV_ID
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
                                        reply_markup=InlineKeyboardMarkup(build_menu(buttons, 2)))
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
    user_data["groups"].remove(context.user_data["group"])
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


@group_check
def group_administration(update, context):
    # this changes the admin mode setting
    group = context.user_data["group"]
    # checks current setting of administration, we need to flip that around
    if group.administration:
        # disabling an active administration mode is easy
        group.administration = False
    else:
        # activating it is not. we need to make sure the bot is an admin with the appropriate rights
        bot_admin = context.bot.get_chat_member(chat_id=group.id, user_id=context.bot.id)
        query = update.callback_query
        # if the bot is not an admin, the other attributes won't be there, that is why we have two checks
        if bot_admin.status != "administrator":
            query.answer(strings.NOT_ADMIN, show_alert=True)
            return
        # bot is admin, but does it have the correct rights?
        if not bot_admin.can_delete_messages or not bot_admin.can_restrict_members:
            query.answer(strings.NOT_ADMIN, show_alert=True)
            return
        # the both returns previously made sure we can only be here with the correct admin rights so we good
        group.administration = True
    # here we add the information to the db
    new_group = database.insert_group_administration(group.id, group.administration)
    # updating our cache
    context.user_data["group"] = new_group
    # returning it to the edit function for the message
    edit(update, new_group)


@group_check
def group_link(update, context):
    # this changes the linked groups for administration mode
    group = context.user_data["group"]
    query = update.callback_query
    # these are all the groups the admin is admin in, minus the one we edit, thanks to the select group function
    # we are going to iterate through them and add them to a list of buttons which we are going to attach to the message
    buttons = []
    linked_to_text = ""
    # i is the index in the list, so we know which group the admin selects
    for i, g in enumerate(context.user_data["groups"]):
        # here we decide if the callback is the one to link or unlink the group, sparing us the logic later. If the
        # group is already in linked_groups, the admin wants to unlink them, otherwise link
        if g.id in group.linked_groups:
            buttons.append(InlineKeyboardButton(g.title, callback_data=f"set_linked_del_{i}"))
            linked_to_text += f"<b>{g.title}</b>, "
        else:
            buttons.append(InlineKeyboardButton(g.title, callback_data=f"set_linked_add_{i}"))
    # if no group is linked, we change our string to say this to the user
    if not linked_to_text:
        linked_to_text = "None"
    # here we delete the last `, ` from the string
    else:
        linked_to_text = linked_to_text[:-2]
    # this back button will be used to get back to the settings menu of the group
    back_button = InlineKeyboardButton("Back", callback_data="set_linked_back")
    # here we put it in a reply markup, and generate the string to send it to the user (speak: edit the message)
    reply_markup = InlineKeyboardMarkup(build_menu(buttons, 2, footer_buttons=back_button))
    text = strings.LINK_GROUP.format(group.title, linked_to_text)
    query.edit_message_text(text=text, reply_markup=reply_markup, parse_mode="HTML")
    # this call is needed, otherwise some clients will show a loading indication
    query.answer()


@group_check
def group_do_link(update, context):
    # this changes the linked groups for administration mode
    group = context.user_data["group"]
    query = update.callback_query
    # we take data from the callback_query. 2 is what we should do (add or delete), 3 is the group's id
    data = query.data.split("_")
    # we take the group object from cache
    linked_group = context.user_data["groups"][int(data[3])]
    # now if we add we call insert group, if we delete remove, then we get the two new group objects back from db
    if data[2] == "add":
        if not linked_group.administration:
            query.answer(strings.LINK_GROUP_NO_ADMINISTRATION, show_alert=True)
            return
        group, linked_group = database.insert_group_link(group.id, linked_group.id)
    else:
        group, linked_group = database.remove_group_link(group.id, linked_group.id)
    # which we give back to our cache
    context.user_data["group"] = group
    context.user_data["groups"][int(data[3])] = linked_group
    # then we call the link function to override the current message, since the cache changes, the text's message does
    # as well
    group_link(update, context)


@group_check
def group_link_back(update, context):
    # this changes the message + buttons back to the normal settings
    query = update.callback_query
    user_id = update.effective_user.id
    # this is the same as select_group outcome
    buttons = group_setting_buttons(context.user_data["group"], user_id)
    query.edit_message_text(strings.SETTINGS_MESSAGE.format(context.user_data["group"].title),
                            reply_markup=InlineKeyboardMarkup(buttons), parse_mode="HTML")
    # this call is needed, otherwise some clients will show a loading indication
    query.answer()


def back(update, context):
    user_id = update.effective_user.id
    groups = database.get_groups_admin(user_id)
    buttons = [InlineKeyboardButton(group.title, callback_data=f"settings_{group.id}") for group in groups]
    update.callback_query.edit_message_text(strings.SETTINGS_COMMAND,
                                            reply_markup=InlineKeyboardMarkup(build_menu(buttons, 2)))
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
    if update.effective_chat and update.effective_chat.type != "private":
        payload += f' within the chat <i>{html.escape(update.effective_chat.title)}</i>'
        if update.effective_chat.username:
            payload += f' (@{html.escape(update.effective_chat.username)})'
    # but only one where you have an empty payload by now: A poll (buuuh)
    if update.poll:
        payload += f' with the poll id {update.poll.id}.'
    context.bot.send_message(DEV_ID, "Error happened:", parse_mode="HTML")
    trace = html.escape("".join(traceback.format_tb(sys.exc_info()[2])))
    text = f"Oh no. The error <code>{context.error}</code> happened{payload}. The type of the chat " \
           f"is <code>{chat.type}</code>. The current user data is <code>{context.user_data}</code>," \
           f"the chat data <code>{context.chat_data}</code>.\nThe full traceback:\n\n<code>{trace}</code>"
    context.bot.send_message(DEV_ID, text, parse_mode="HTML")
    raise
