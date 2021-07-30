ADDED = "Hello there, thanks for adding me to your group. I will report reports to the group admins. Admins can run " \
        "/settings with me in private to set me up and change how or if they want to get mentioned. By default, I " \
        "respond to @admin and /report, and will respond to this message in this group, and mention all admins in it"
REPORT = "Admins have been notified."
PM = "Hey there. There was a report in group {}."
ADMIN_RELOAD = "Admin list has been reloaded"
PRIVATE_START = "Hey there. I am TheReportBot, I help forwarding reports to the group admins. If you are not a group " \
                "admin, I am afraid I am of not much use to you in PM. If you are though, you can run /settings to " \
                "change settings for yourself and the groups you administer. Don't forget about /help either :)"
SETTINGS_COMMAND = "You want to change the settings of one of the groups you are admin in? Great, go right ahead. " \
                   "Pick the group below. If you don't see yours in there but are 100% sure you are an admin in this " \
                   "group (and that I am in it), send the command /reload_admins in the group, then send /settings " \
                   "here again."
SETTINGS_MESSAGE = "You are changing settings for the group {}.\nLet me explain what the buttons you see below " \
                   "mean:\n\n* <b>Report</b>: Which report triggers are used in the group. Its @admin and/or /report." \
                   "\n* <b>Reply</b>: If the bot replies to the report in the group or not.\n* <b>Mention</b>: How " \
                   "<i>you</i> are mentioned. Either mentioned in the reply message (for that, <b>Reply</b> needs to " \
                   "be activated), getting a PM from the bot with the direct link to the message or not at all.\n" \
                   "* <b>AdminMode</b>: Toggling administration mode. To learn what it does, look at /help\n" \
                   "* <b>Linked groups</b>: (For AdminMode) You can link groups to each other. If you ban or restrict" \
                   " an report through me, I'm gonna do that action in all linked groups to the one the report came " \
                   "from\n" \
                   "* <b>Back:</b> Get back to the group selection"
# the code adds the current setting to this string
SETTINGS_BUTTONS = ["Report: ", "Reply: ", "Mention: ", "AdminMode: ", "Linked groups", "Back"]
# every string starts with set in order to pattern it out
SETTINGS_BUTTONS_DATA = ["set_report", "set_reply", "set_mention", "set_administration", "set_link", "set_back"]
EXPIRED = "Hey, im sorry to inform you, but apparently I have been restarted and lost all information. Please run " \
          "/settings again, I am sorry :("
REPLY_WARNING = "Warning: When you change this, every admin who previously got mentioned will receive PMs. Are you " \
                "sure? Then press the button again."
TIMEOUT_COMMAND = "Hey. You want to take a timeout, fair enough. For more information about this, run /help. " \
                  "Otherwise the syntax is <code>group_ids time_in_24_hours</code>, which could look like this: " \
                  "<code>1,2,3 00:00</code>. Important part: No space between the ids. You can alternatively use " \
                  "all, that would look like this: <code>all 12:00</code>. Every group has its own id:<code>{}</code>" \
                  "\nP.S.: The server runs on UTC, which means it's currently {}"
TIMEOUT_WHITESPACE = "So that didn't work out, you missed the space between the ids and the time. Try again :)"
TIMEOUT_INDEX = "Either wrong id or screwed up with commas/whitespace there maybe?"
TIMEOUT_DATE = "I have 0 idea, but you really messed up the time. I mean, come on. Its a 24 hours format.-."
TIMEOUT_SUCCEED = "Hey, I added you to the timeout list. Keep in mind that changing how you are mentioned now will " \
                  "be reset once the timeout runs out, so, just don't do it, okay? Spares us trouble"
TIMEOFF_COMMAND = "Okay, a timeoff. If you want more information about this command, run /help. The syntax is\n<code>" \
                  "Weekday_in_three_letters group_ids time\nNext_weekday...</code>\nwhich could look like this:\n" \
                  "<code>Mon group_id1,group_id2,group_id3 00:00,13:00\nTue group_id1,group_id3 08:00,12:00\nFri all " \
                  "00:00,24:00</code>\nNo spaces between the ids or the time. Every group has its own id:<code>{}" \
                  "</code>\nP.S.: The server runs on UTC, which means it's currently {}"
TIMEOFF_WHITESPACE = "Im sorry, but you messed up the spaces in paragraph {}"
TIMEOFF_INDEX = "You have a wrong id in paragraph {}. Or you messed up with spaces."
TIMEOFF_DATE = "You screwed up the time in paragraph {}. Either that or you have a problem with whitespaces."
TIMEOFF_DAY = "You messed up the day in paragraph {}. Im gonna give the to you one more time: Mon, Tue, Wed, Thu, " \
              "Fri, Sat, Sun. There you go."
TIMEOFF_SUCCEED = "Great, you were added to the timeoff list. In case you want to get off it, send /timeoff_del or " \
                  "make a new timeoff aktion, which will override the existing one."
TIMEOFF_DELETE_SUCCESS = "You are removed from the timeoff list"
TIMEOFF_DELETE_FAIL = "You are are not on the timeoff list, therefore you aren't removed..."
PRIVATE_HELP = "Hey, this a message trying to tell you how I work.\n/settings - gives you a list of groups which you " \
               "are admin in, which you then can change their settings for\n/reload_admin - in groups, you can force " \
               "me to refresh the admin list. I do this every 24 hours on my own, but its helpful if you just added " \
               "a new (or removed a bad) one\n\n<b>AdminMode</b> or administration mode in long, is a mode you can " \
               "activate in the settings for each group. If a report of a user replies to a message, it adds buttons " \
               "to the reports the bot generates, either in PM of the admins and/or in the message it sends in the " \
               "group. With these buttons you can\n* Ignore the report\n* Delete the message\n* Restrict the user for" \
               " two weeks and delete the message\n* Ban the user and delete the message\nIf you want a custom time " \
               "instead of the two weeks, PM @Poolitzer, he will add that. If the original message or mine in the " \
               "group (if I send one) get deleted, I will not ban or restrict the user and tell you that, since I " \
               "assume another admin already handled the report.\nOn a side note, the desktop client is known to " \
               "swallow these notifications since I almost directly delete the messages they are bound to. Nothing I " \
               "can do about, sorry.\n\n<b>Timout and timeoff in general</b> are overcomplex automatic mute options. " \
               "During the time you give, they put your mention status on off in every half hour. Now to the actual " \
               "commands\n/timeout - you can take a timeout from being mentioned in your groups. This works like a " \
               "timer with a 24 hour format.\n/timeoff - you can set for every day in the week different times you " \
               "want to be off. Also supports different groups, but only one setting per day.\n/timeoff_del - " \
               "deletes you from the timeoff list"
ADMIN_RELOAD_PRIVATE = "In the group. I mean, come on dude."
ERROR = "Hey, an error happend. I notified my developer. If you think you can help him, PM @poolitzer. Thanks"
NOT_ADMIN = "In order to use this mode, you need to make me an admin with delete and ban rights."
IGNORE = "This report was successfully ignored by you"
DELETE = "The reported message was deleted, nothing happened to the sender."
REPORTED_ALREADY_DELETED = "The reported message was already deleted, another admin probably took action, I aborted " \
                           "mine!"
BOT_MESSAGE_ALREADY_DELETED = "My report message got deleted in the group, another admin probably took action, I " \
                              "aborted mine!"
RESTRICT = "The reported message was deleted and the sender restricted for two weeks."
BAN = "The reported message was deleted and the sender banned from the group!"
LINK_GROUP = "Hey. In this menu, you can link groups to each other which you are an admin in. This means that every " \
             "ban or restrict action I do in one group of the linked one I am going to do in all of the linked ones " \
             "as well.\n\nLinked to the group <b>{}</b> are these groups right now: {}. If you want to add another " \
             "one, pick one from below; if you want to unlink groups, pick it from down there as well. Back brings " \
             "you back."
LINK_GROUP_NO_ADMINISTRATION = "Sorry, in order to link me to this group, you need to activate administration mode in" \
                               "that one as well. This ensures I have appropriate admin rights in it."
NO_ADMIN = "Sorry, you have to be an admin to use this function."
# guy who discovered this and gets an own mention
NO_ADMIN_AM = "Arun Mani... fool me once, shame on you; fool me twice, ...nevermind. IT AINT GONNA HAPPEN."
