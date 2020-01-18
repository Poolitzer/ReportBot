# used for admins which are off
class Admin:
    def __init__(self, id=False, until=False, rotation=False, days=None, groups=None):
        if groups is None:
            groups = {}
        if days is None:
            days = {"mon": False, "tue": False, "wed": False, "thu": False, "fri": False, "sat": False, "sun": False}
        self.id = id
        # time until the admin doesn't want to receive notifications
        # can be directly set with timeout or indirectly with timeoff
        # is stored like 00:00
        self.until = until
        # we set this to True when the until date is after 00:00, so we skip the current rotation
        self.rotation = rotation
        # every day is a dictionary with the key groups and a list of all the group_ids for that day, the key when,
        # which is a float (so pymongo can do the filtering for us), and until, which is the normal string. Both
        # 24 hours
        self.days = days
        # this will be a dictionary, mapping the dictionary id to the type (PM, mention or off [lol]) where the user
        # is off to. only set when until is set
        self.groups = groups
