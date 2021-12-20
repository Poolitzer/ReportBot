import datetime

from telegram import ChatPermissions
from telegram.error import BadRequest
from telegram.ext import CallbackContext

import strings
from database import database


def admin_check(func):
    def wrapper(*args, **kwargs):
        # this is send by ptb
        update = args[0]
        # query
        query = update.callback_query
        # we get the chat_id from the query_data
        chat_id = int(query.data.split("_")[2])
        # and user_id from update
        user_id = update.effective_user.id
        # if the person is not an admin we aint gonna let them use this
        if not database.admin_in_group(user_id, chat_id):
            # the guy who discovered this feature missing so he gets an unique string
            if user_id == 441689112:
                query.answer(strings.NO_ADMIN_AM, show_alert=True)
            # everyone else gets a proper one
            else:
                query.answer(strings.NO_ADMIN, show_alert=True)
            return
        # otherwise we continue
        return func(*args, **kwargs)

    return wrapper


def _delete_messages(context, query, data, already_deleted, delete_report=True):
    # we set this to true and will change it later if the report is actually solved from the group. if its a PM, we need
    # to delete this message later

    # this will provide us the data we need from the callback data, split up in a nice list
    # 2 will be chat_id, 3 the reported message, 4 the sender of that, 5 the reporting message
    # in bot data we find the report message which the bot generated in the group if that happened
    chat_id = int(data[2])
    report_message_id = int(data[3])
    reporting_message_id = int(data[5])
    # if we should delete the report
    if delete_report:
        try:
            # lets try to delete the reported message first
            context.bot.delete_message(chat_id, report_message_id)
        except BadRequest as e:
            # someone already deleted the message. we are going to report that to the user then continue with the code
            if e.message == "Message to delete not found":
                query.answer(strings.REPORTED_ALREADY_DELETED, show_alert=True)
                already_deleted = True
            else:
                # all other bad requests are an issue so we raise
                raise
    # we set this to True now, if it turns out the query message id is the same as the bot ones, its a group, so we
    # set it to false
    pm = True
    # this means at least one message by the bot was send in the group and we try to delete them now
    if chat_id in context.bot_data and report_message_id in context.bot_data[chat_id]:
        for bot_message_id in context.bot_data[chat_id][report_message_id]:
            # if the bot_message_id is the same as the one from the message of this query, then this didn't happen
            # in the group
            if bot_message_id == query.message.message_id:
                pm = False
            try:
                context.bot.delete_message(chat_id, bot_message_id)
            except BadRequest as e:
                # someone already deleted the message. we are going to report that to the user then continue
                # with the code, if we didn't report something already
                if e.message == "Message to delete not found":
                    if already_deleted:
                        pass
                    else:
                        # now we can report this
                        query.answer(strings.BOT_MESSAGE_ALREADY_DELETED, show_alert=True)
                        # one report is enough
                        already_deleted = True
                else:
                    # all other bad requests are an issue so we raise
                    raise
    # now try to delete the original message. if that fails, we don't care
    try:
        context.bot.delete_message(chat_id, reporting_message_id)
    except BadRequest as e:
        if e.message == "Message to delete not found":
            pass
        else:
            # all other bad requests are an issue so we raise
            raise
    return pm, already_deleted


@admin_check
def ignore(update, context):
    # this function does nothing except saying it ignored the message
    query = update.callback_query
    # see in delete_messages what this returns
    data = query.data.split("_")
    # we try to delete the bot message from group
    pm, already_deleted = _delete_messages(context, query, data, False, False)
    # this means we didn't already answer the report
    if not already_deleted:
        query.answer(strings.IGNORE)
    # if its a PM we need to delete the original message
    if pm:
        query.delete_message()


@admin_check
def delete(update, context):
    # this function deletes the message, but does nothing to the user
    query = update.callback_query
    # see in delete_messages what this returns
    data = query.data.split("_")
    pm, already_deleted = _delete_messages(context, query, data, False)
    if not already_deleted:
        # this only happens if everything went alright, no need to show it as an alert in that case
        query.answer(strings.DELETE)
    # now we delete the actual report if it happened in a PM
    if pm:
        query.delete_message()


@admin_check
def restrict(update, context):
    # this function restricts the user for two weeks and deletes the bad message
    query = update.callback_query
    # see in delete_messages what this returns
    data = query.data.split("_")
    # we need these two to restrict the user later
    bad_user_id = int(data[4])
    chat_id = int(data[2])
    pm, already_deleted = _delete_messages(context, query, data, False)
    # if no error happened, already_deleted is False, so we are good to go
    if not already_deleted:
        # now we calculate two weeks from now
        now = datetime.datetime.now()
        weeks = datetime.timedelta(days=14)
        in_weeks = now + weeks
        # we want them to be restricted from everything, and everything in here is False, so nothing to change
        permission = ChatPermissions()
        # now we restrict 'em
        context.bot.restrict_chat_member(chat_id=chat_id, user_id=bad_user_id, until_date=in_weeks,
                                         permissions=permission)
        # now we check if there are linked groups and if yes, we restrict from there
        linked_groups = database.get_group_link(chat_id=chat_id)
        if linked_groups:
            for group_id in linked_groups:
                context.bot.restrict_chat_member(chat_id=group_id, user_id=bad_user_id, until_date=in_weeks,
                                                 permissions=permission)
        # and tell the user that
        query.answer(strings.RESTRICT, show_alert=True)
    if pm:
        query.delete_message()


@admin_check
def ban(update, context: CallbackContext):
    # this function bans the user/channel from the chat and deletes the bad message
    query = update.callback_query
    # see in delete_messages what this returns
    data = query.data.split("_")
    # we need these two to restrict the user/channel later
    bad_user_id = int(data[4])
    chat_id = int(data[2])
    pm, already_deleted = _delete_messages(context, query, data, False)
    # if no error happened, already_deleted is False, so we are good to go
    if not already_deleted:
        # a channel will have a negative id, a user a positive one
        if bad_user_id < 0:
            context.bot.ban_chat_sender_chat(chat_id=chat_id, sender_chat_id=bad_user_id)
        else:
            context.bot.kick_chat_member(chat_id=chat_id, user_id=bad_user_id)
        # now we check if there are linked groups and if yes, we ban from there
        linked_groups = database.get_group_link(chat_id=chat_id)
        if linked_groups:
            # the two for loops do look a bit unnecessary, but its more effective than having to
            # do an if else each iteration
            if bad_user_id < 0:
                context.bot.ban_chat_sender_chat(chat_id=chat_id, sender_chat_id=bad_user_id)
            else:
                for group_id in linked_groups:
                    context.bot.kick_chat_member(chat_id=group_id, user_id=bad_user_id)
        # and tell the user that
        if bad_user_id < 0:
            query.answer(strings.BAN_CHANNEL, show_alert=True)
        else:
            query.answer(strings.BAN, show_alert=True)
    if pm:
        query.delete_message()
