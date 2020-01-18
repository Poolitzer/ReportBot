# used for storing settings/information of a group
class Group:
    def __init__(self, id, title, admins, admin=True, report=True, reply=True, pm=None, off=None):
        if off is None:
            off = []
        if pm is None:
            pm = []
        self.id = id
        # name of group
        self.title = title
        # list of admin, reload with command
        self.admins = admins
        # @admin triggers
        self.admin = admin
        # /report triggers
        self.report = report
        # replies in group
        self.reply = reply
        # used for admins who want a PM
        self.pm = pm
        # used for admins who are off, either for a timeframe or for the next x hours
        self.off = off
