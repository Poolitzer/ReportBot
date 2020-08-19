import datetime
import logging

from telegram.ext import Updater, MessageHandler, Filters, CommandHandler, CallbackQueryHandler

import group
import private
from jobs import half_hourly, group_check
from tokens import TELEGRAM
from utils import ceil_dt

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.INFO, filename="log.log")


def main():
    updater = Updater(token=TELEGRAM, use_context=True, request_kwargs={'read_timeout': 10, 'connect_timeout': 10})
    dp = updater.dispatcher
    # group handlers
    dp.add_handler(MessageHandler(Filters.status_update.new_chat_members, group.added))
    # thanks to https://t.me/dotvhs, who likes regex (weird). test: https://regex101.com/r/h4oH0X/2
    dp.add_handler(MessageHandler(Filters.regex(r"(\s|^)(/report|@admins?)(\s|$)") & Filters.group, group.report))
    dp.add_handler(CommandHandler("reload_admins", group.reload_admins, Filters.group))
    # private handlers
    dp.add_handler(CommandHandler("start", private.start, Filters.private))
    dp.add_handler(CommandHandler("settings", private.settings, Filters.private))
    dp.add_handler(CallbackQueryHandler(private.select_group, pattern="settings"))
    dp.add_handler(CallbackQueryHandler(private.group_report, pattern="set_report"))
    dp.add_handler(CallbackQueryHandler(private.group_reply_confirmation, pattern="set_reply"))
    dp.add_handler(CallbackQueryHandler(private.group_mention, pattern="set_mention"))
    dp.add_handler(CallbackQueryHandler(private.back, pattern="set_back"))
    dp.add_handler(CommandHandler("timeout", private.timeout_command, Filters.private))
    dp.add_handler(CommandHandler("help", private.help_command, Filters.private))
    dp.add_handler(MessageHandler(Filters.private & Filters.text, private.timeout))
    dp.add_handler(CommandHandler("timeoff", private.timeoff_command, Filters.private))
    dp.add_handler(MessageHandler(Filters.private & Filters.text, private.timeoff), 1)
    dp.add_handler(CommandHandler("timeoff_del", private.timeoff_del, Filters.private))
    dp.add_error_handler(private.error_handler)
    # just for the sake of it (BLUE TEXT)
    dp.add_handler(CommandHandler("reload_admins", private.reload_admins, Filters.private))
    updater.start_polling()
    now = datetime.datetime.now()
    dt = ceil_dt(now, datetime.timedelta(minutes=30))
    # temporary fix
    td = dt - now
    updater.job_queue.run_repeating(half_hourly, 60*30, first=td.total_seconds(), name="half-hourly",
                                    context={"admins": {}, "date": now.strftime("%d.%m")})
    updater.job_queue.run_daily(group_check, datetime.time(12, 0, 0), name="Group check")
    updater.idle()


if __name__ == '__main__':
    main()
