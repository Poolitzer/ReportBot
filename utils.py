from datetime import datetime

from telegram import InlineKeyboardButton, InlineKeyboardMarkup

import strings


def build_menu(buttons, n_cols, header_buttons=None, footer_buttons=None):
    menu = [buttons[i:i + n_cols] for i in range(0, len(buttons), n_cols)]
    if header_buttons:
        menu.insert(0, [header_buttons])
    if footer_buttons:
        menu.append([footer_buttons])
    return menu


def group_setting_buttons(group, user_id):
    dynamic_strings = {"report": "", "reply": "", "mention": ""}
    if group.admin:
        if group.report:
            dynamic_strings["report"] = "Both"
        else:
            dynamic_strings["report"] = "@admin"
    else:
        dynamic_strings["report"] = "/report"
    if group.reply:
        dynamic_strings["reply"] = "✅"
    else:
        dynamic_strings["reply"] = "❌"
    if user_id in group.pm:
        dynamic_strings["mention"] = "PM"
    elif user_id in group.off:
        dynamic_strings["mention"] = "Off"
    elif user_id in group.admins:
        dynamic_strings["mention"] = "Mention"
    else:
        dynamic_strings["mention"] = "❔"
    buttons = [InlineKeyboardButton(strings.SETTINGS_BUTTONS[0] + dynamic_strings["report"],
                                    callback_data=strings.SETTINGS_BUTTONS_DATA[0]),
               InlineKeyboardButton(strings.SETTINGS_BUTTONS[1] + dynamic_strings["reply"],
                                    callback_data=strings.SETTINGS_BUTTONS_DATA[1]),
               InlineKeyboardButton(strings.SETTINGS_BUTTONS[2] + dynamic_strings["mention"],
                                    callback_data=strings.SETTINGS_BUTTONS_DATA[2]),
               InlineKeyboardButton(strings.SETTINGS_BUTTONS[3], callback_data=strings.SETTINGS_BUTTONS_DATA[3])]
    return build_menu(buttons, 2)


def edit(update, group):
    query = update.callback_query
    user_id = update.effective_user.id
    query.edit_message_reply_markup(InlineKeyboardMarkup(group_setting_buttons(group, user_id)))
    query.answer()


def ceil_dt(dt, delta):
    return dt + (datetime.min - dt) % delta


def group_id_generator(groups):
    group_string = ""
    for index, group in enumerate(groups):
        group_string += f"\n{index}: {group.title}"
    return group_string
