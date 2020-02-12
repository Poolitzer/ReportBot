from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.error import Unauthorized
from telegram.utils.helpers import mention_html

import strings
from database import database
from objects import Group


def added(update, context):
    if context.bot.id not in [x.id for x in update.effective_message.new_chat_members]:
        return
    update.effective_message.reply_text(strings.ADDED)
    chat = update.effective_chat
    database.add_group(Group(chat.id, chat.title, [x.user.id for x in chat.get_administrators()]))


def report(update, context):
    report_string = str(context.matches[0].group(0)).strip()
    chat_id = update.effective_chat.id
    # check if the report is in code or pre tags, in which case we ignore it (we nerds ;P)
    for k, v in update.effective_message.parse_entities(["code", "pre"]).items():
        # we use in here in case more then our trigger is in the code tags
        if report_string in v:
            return
    if report_string.startswith("@admin"):
        proceed = database.group_mention(chat_id, "admin")
    # we can use else, since the regex filter takes the actual filtering out of our hands, which is neat
    else:
        proceed = database.group_mention(chat_id, "report")
    if not proceed:
        return
    if update.effective_message.reply_to_message:
        message = update.effective_message.reply_to_message
    else:
        message = update.effective_message
    if isinstance(proceed.group, list):
        mention_string = "".join([mention_html(i, u'\u200D') for i in proceed.group])
        message.reply_text(mention_string + strings.REPORT, parse_mode="HTML")
    if proceed.pm:
        title = update.effective_chat.title
        if update.effective_chat.username:
            title = f"<a href=\"https://t.me/{update.effective_chat.username}\">{title}</a>"
        else:
            title = f"<b>{title}</b>"
        button = [[InlineKeyboardButton("Message", url=message.link)]]
        for user_id in proceed.pm:
            try:
                context.bot.send_message(user_id, strings.PM.format(title), parse_mode="HTML",
                                         reply_markup=InlineKeyboardMarkup(button))
            except Unauthorized:
                database.insert_group_mention(chat_id, proceed.group, "o", user_id)


def reload_admins(update, _):
    admin_ids = [x.user.id for x in update.effective_chat.get_administrators()]
    database.add_group_admins(update.effective_chat.id, admin_ids)
    update.effective_message.reply_text(strings.ADMIN_RELOAD)


def update_title(update, _):
    message = update.effective_message
    old_id = message.migrate_from_chat_id
    new_id = update.effective_chat.id
    database.insert_group_id(old_id, new_id)


def update_id(update, _):
    database.insert_group_title(update.effective_chat.id, update.new_chat_title)
