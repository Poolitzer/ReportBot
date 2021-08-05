import datetime
import logging

from telegram import (
    Update,
    BotCommand,
    BotCommandScopeAllChatAdministrators,
    BotCommandScopeAllPrivateChats,
)
from telegram.ext import (
    Updater,
    MessageHandler,
    Filters,
    CommandHandler,
    CallbackQueryHandler,
    ChatMemberHandler,
    ConversationHandler,
)

import group
import private
import report_callback
from jobs import half_hourly, backup_job
from tokens import TELEGRAM
from utils import ceil_dt

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
    filename="log.log",
)
aps_logger = logging.getLogger("apscheduler")
aps_logger.setLevel(logging.WARNING)


def main():
    updater = Updater(
        token=TELEGRAM,
        use_context=True,
        request_kwargs={"read_timeout": 10, "connect_timeout": 10},
    )
    dp = updater.dispatcher
    # group handlers
    dp.add_handler(
        ChatMemberHandler(group.chat_member_update, ChatMemberHandler.CHAT_MEMBER)
    )
    dp.add_handler(
        ChatMemberHandler(group.my_chat_member_update, ChatMemberHandler.MY_CHAT_MEMBER)
    )
    # thanks to https://t.me/dotvhs and https://t.me/twitface, both of them like regex (weird).
    # test: https://regex101.com/r/Amrm07/1
    dp.add_handler(
        MessageHandler(
            Filters.regex(r"^/report\b|(^|\s)@admin[a-z_]{0,27}\b")
            & Filters.chat_type.groups,
            group.report,
        )
    )
    dp.add_handler(
        CommandHandler("reload_admins", group.reload_admins, Filters.chat_type.groups)
    )
    dp.add_handler(
        MessageHandler(Filters.status_update.new_chat_title, group.update_title)
    )
    dp.add_handler(MessageHandler(Filters.status_update.migrate, group.update_id))

    # this is the administration mode where the bot can kick and restrict members
    dp.add_handler(
        CallbackQueryHandler(report_callback.ignore, pattern="report_ignore")
    )
    dp.add_handler(CallbackQueryHandler(report_callback.delete, pattern="report_del"))
    dp.add_handler(
        CallbackQueryHandler(report_callback.restrict, pattern="report_restrict")
    )
    dp.add_handler(CallbackQueryHandler(report_callback.ban, pattern="report_ban"))
    dp.add_error_handler(private.error_handler)

    # private handlers, basic setup
    dp.add_handler(CommandHandler("start", private.start, Filters.chat_type.private))
    dp.add_handler(
        CommandHandler("settings", private.settings, Filters.chat_type.private)
    )
    dp.add_handler(
        CommandHandler("help", private.help_command, Filters.chat_type.private)
    )

    # private setting callbacks
    dp.add_handler(CallbackQueryHandler(private.select_group, pattern="settings"))
    dp.add_handler(CallbackQueryHandler(private.group_report, pattern="set_report"))
    dp.add_handler(
        CallbackQueryHandler(private.group_reply_confirmation, pattern="set_reply")
    )
    dp.add_handler(CallbackQueryHandler(private.group_mention, pattern="set_mention"))
    dp.add_handler(
        CallbackQueryHandler(private.group_administration, pattern="set_administration")
    )
    dp.add_handler(
        CallbackQueryHandler(private.group_link_back, pattern="set_linked_back")
    )
    dp.add_handler(CallbackQueryHandler(private.group_do_link, pattern="set_linked"))
    dp.add_handler(CallbackQueryHandler(private.group_link, pattern="set_link"))
    dp.add_handler(CallbackQueryHandler(private.back, pattern="set_back"))

    # private timeout/timeoff convs
    timeout_conv = ConversationHandler(
        entry_points=[
            CommandHandler(
                "timeout", private.timeout_command, Filters.chat_type.private
            ),
        ],
        states={
            private.TIMEOUT_REPLY: [
                MessageHandler(
                    Filters.text & (~Filters.command),
                    private.timeout,
                )
            ]
        },
        fallbacks=[CommandHandler("cancel", private.cancel)],
    )
    dp.add_handler(timeout_conv)
    timeoff_conv = ConversationHandler(
        entry_points=[
            CommandHandler(
                "timeoff", private.timeoff_command, Filters.chat_type.private
            )
        ],
        states={
            private.TIMEOFF_REPLY: [
                MessageHandler(
                    Filters.text & (~Filters.command),
                    private.timeoff,
                )
            ]
        },
        fallbacks=[CommandHandler("cancel", private.cancel)],
    )

    dp.add_handler(timeoff_conv)
    dp.add_handler(
        CommandHandler("timeoff_del", private.timeoff_del, Filters.chat_type.private)
    )
    dp.add_handler(CommandHandler("cancel", private.cancel, Filters.chat_type.private))
    # just for the sake of it (BLUE TEXT), do not use it in private
    dp.add_handler(
        CommandHandler(
            "reload_admins", private.reload_admins, Filters.chat_type.private
        )
    )

    # registering to group member updates
    updater.start_polling(
        allowed_updates=[
            Update.MESSAGE,
            Update.CHAT_MEMBER,
            Update.MY_CHAT_MEMBER,
            Update.CALLBACK_QUERY,
        ]
    )
    now = datetime.datetime.now()
    dt = ceil_dt(now, datetime.timedelta(minutes=30))
    # temporary fix
    td = dt - now
    updater.job_queue.run_repeating(
        half_hourly,
        60 * 30,
        first=td.total_seconds(),
        name="half-hourly",
        context={"admins": {}, "date": now.strftime("%d.%m")},
    )
    updater.job_queue.run_daily(
        backup_job, datetime.time(12, 0, 0), name="Backup database"
    )
    # set private commands
    dp.bot.set_my_commands(
        [
            BotCommand("start", "Short greeting message"),
            BotCommand("settings", "change settings of administrated groups"),
            BotCommand("help", "Long help message"),
            BotCommand(
                "timeout",
                "set a timeout for some time between now and sometime in the next 24 hours",
            ),
            BotCommand(
                "timeoff", "Specifiy do not disturb times for each day of the week"
            ),
            BotCommand("timeoff_del", "Delete yourself from the timeoff list"),
            BotCommand("cancel", "Cancel the current action"),
        ],
        scope=BotCommandScopeAllPrivateChats(),
    )
    updater.idle()


if __name__ == "__main__":
    main()
