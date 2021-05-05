import html

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, ChatMember
from telegram.error import Unauthorized, BadRequest
from telegram.utils.helpers import mention_html

import strings
import utils
from database import database
from objects import Group


def chat_member_update(update, context):
    status_change = update.chat_member.difference().get("status")

    if status_change is None:
        return

    old_status, new_status = status_change

    # luckily, we need not to worry about creator change, they can only change an admin to a creator, who then gets
    # an admin themselves

    if old_status == ChatMember.ADMINISTRATOR and new_status in [
        ChatMember.LEFT,
        ChatMember.KICKED,
        ChatMember.RESTRICTED,
    ]:
        database.remove_group_admin(
            update.effective_chat.id, update.chat_member.new_chat_member.user.id
        )
        # this makes sure the admin cant change any settings anymore
        context.dispatcher.user_data[update.chat_member.new_chat_member.user.id].clear()
    elif (
        old_status
        in [
            ChatMember.LEFT,
            ChatMember.KICKED,
            ChatMember.RESTRICTED,
        ]
        and new_status == ChatMember.ADMINISTRATOR
    ):
        database.add_group_admins(
            update.effective_chat.id, [update.chat_member.new_chat_member.user.id]
        )


def my_chat_member_update(update, _):

    if update.effective_chat.type not in ["group", "supergroup"]:
        # we only care if we were added or removed from a group
        return

    status_change = update.my_chat_member.difference().get("status")

    if status_change is None:
        return

    old_status, new_status = status_change

    if new_status in [
        ChatMember.LEFT,
        ChatMember.KICKED,
    ]:
        database.remove_group(update.effective_chat.id)
    elif new_status in [ChatMember.ADMINISTRATOR, ChatMember.MEMBER]:
        chat = update.effective_chat
        database.add_group(
            Group(
                chat.id,
                html.escape(chat.title),
                [x.user.id for x in chat.get_administrators()],
            )
        )


def report(update, context):
    # this function takes care of reports send into the group
    # this takes the actual report out of the potential longer message, so we can use it later
    report_string = str(context.matches[0].group(0)).strip()
    chat_id = update.effective_chat.id
    # check if the report is in code or pre tags, in which case we ignore it (we nerds ;P)
    for k, v in update.effective_message.parse_entities(["code", "pre"]).items():
        # we use in here in case more then our trigger is in the code tags
        # if the value of one of the code messages is the report string, this is true
        if report_string in v:
            return
    # we need to check if the group only wants one kind of report
    if report_string.startswith("@admin"):
        proceed = database.group_mention(chat_id, "admin")
    # we can use else, since the regex filter takes the actual filtering out of our hands, which is neat
    else:
        proceed = database.group_mention(chat_id, "report")
    if not proceed:
        # this happens when the report way is not handled based on the group settings
        return
    # message will be used to reply to. its either the message the report replies to, if they did, or the report itself
    if update.effective_message.reply_to_message:
        message = update.effective_message.reply_to_message
        # this button list gets attached if administration mode is on
        if proceed.administration:
            buttons = [
                InlineKeyboardButton("Ignore", callback_data="report_ignore"),
                InlineKeyboardButton("Delete", callback_data="report_del"),
                InlineKeyboardButton("Restrict", callback_data="report_restrict"),
                InlineKeyboardButton("Ban", callback_data="report_ban"),
            ]
            # this for loop adds chat, user and message id information to each query so it doesn't matter where someone
            # presses it the bot can still take appropriate actions
            for button in buttons:
                button.callback_data += (
                    f"_{chat_id}_{message.message_id}_{message.from_user.id}_"
                    f"{update.effective_message.message_id}"
                )
            buttons = utils.build_menu(buttons, 2)
        else:
            # the buttons are an empty lists since we can pass this to telegram and they wont add buttons but wont
            # complain about it either
            buttons = [[]]
    else:
        message = update.effective_message
        # see above
        buttons = [[]]
    # all members in .group needs to be mentioned
    if isinstance(proceed.group, list):
        # this generates a string, which appears empty on telegram clients, but in fact is all mentions after another
        mention_string = "".join([mention_html(i, "\u200D") for i in proceed.group])
        # we use reply_text so we reply to the message
        m = message.reply_text(
            mention_string + strings.REPORT,
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup(buttons),
            allow_sending_without_reply=True,
        )
        # if this message has buttons we have to add the message id to our cache so we can delete it when the report
        # gets solved
        if m.reply_markup:
            # first time we add a message to the cache, so we have to add the chat to the cache dict
            if chat_id not in context.bot_data:
                context.bot_data[chat_id] = {message.message_id: [m.message_id]}
            # the chat exists already, but not this report, so we add it
            elif message.message_id not in context.bot_data[chat_id]:
                context.bot_data[chat_id][message.message_id] = [m.message_id]
            # the report exists already, so someone else reports it, we add it to the list
            else:
                context.bot_data[chat_id][message.message_id].append(m.message_id)
    if proceed.pm:
        title = update.effective_chat.title
        # if the reported chat has a username, we create a link to the group, otherwise the name must be enough
        if update.effective_chat.username:
            title = (
                f'<a href="https://t.me/{update.effective_chat.username}">{title}</a>'
            )
        else:
            title = f"<b>{title}</b>"
        # if the message has a direct link to it, we insert it as the first button here
        if message.link:
            buttons.insert(0, [InlineKeyboardButton("Message", url=message.link)])
        # now we iterate through all admins in pm and send them a private message
        for user_id in proceed.pm:
            try:
                context.bot.send_message(
                    user_id,
                    strings.PM.format(title),
                    parse_mode="HTML",
                    reply_markup=InlineKeyboardMarkup(buttons),
                )
            except Unauthorized or BadRequest:
                # if they blocked the bot we put them in off
                database.insert_group_mention(chat_id, proceed.group, "o", user_id)


def reload_admins(update, context):
    admin_ids = [x.user.id for x in update.effective_chat.get_administrators()]
    known_admins = database.get_group_admins(update.effective_chat.id)
    new_admins = []
    for admin_id in admin_ids:
        if admin_id not in known_admins:
            new_admins.append(admin_id)
        else:
            known_admins.remove(admin_id)
    if known_admins:
        for id_to_remove in known_admins:
            database.remove_group_admin(
                update.effective_chat.id, id_to_remove
            )
            # this makes sure the admin cant change any settings anymore
            context.dispatcher.user_data[id_to_remove].clear()
    if new_admins:
        database.add_group_admins(update.effective_chat.id, new_admins)
    update.effective_message.reply_text(strings.ADMIN_RELOAD)


def update_title(update, _):
    message = update.effective_message
    old_id = message.migrate_from_chat_id
    new_id = update.effective_chat.id
    database.insert_group_id(old_id, new_id)


def update_id(update, _):
    database.insert_group_title(update.effective_chat.id, update.new_chat_title)
