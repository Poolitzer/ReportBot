from pymongo import MongoClient, ReturnDocument, UpdateOne
import logging

from objects import Group, Admin


class Database:
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.logger.debug("Database init")
        self.db = MongoClient()
        self.db = self.db["reportbot"]
        self.logger.debug("database init done")

    def add_group(self, group):
        self.db["groups"].insert_one(group.__dict__)

    def insert_group_title(self, group_id, title):
        self.db["groups"].update_one({"id": group_id}, {"$set": {"title": title}})

    def insert_group_id(self, old_group_id, new_group_id):
        self.db["groups"].update_one({"id": old_group_id}, {"$set": {"id": new_group_id}})

    def get_groups(self):
        groups = self.db["groups"].find({}, {"_id": 0})
        return [Group(**group) for group in groups]

    def remove_group(self, group_id):
        group = self.db["groups"].find_one({"id": group_id})
        if group["linked_groups"]:
            for chat_id in group["linked_groups"]:
                self.db["groups"].find_one_and_update({"id": chat_id}, {"$pull": {"linked_groups": group_id}})
        self.db["groups"].delete_one({"id": group_id})

    def group_mention(self, group_id, what):
        class Return:
            def __init__(self, group):
                if group["reply"]:
                    to_mention_ids = [x for x in group["admins"] if x not in group["pm"] + group["off"]]
                    self.group = to_mention_ids
                else:
                    self.group = False
                self.pm = [x for x in group["pm"] if x not in group["off"]]
                self.administration = group["administration"]

        get = self.db["groups"].find_one({"id": group_id, what: {"$eq": True}})
        if get:
            return Return(get)
        return False

    def add_group_admins(self, chat_id, admin_ids):
        self.db["groups"].update_one({"id": chat_id}, {"$addToSet": {"admins": {"$each": admin_ids}}})

    def remove_group_admin(self, chat_id, admin_id):
        self.db["groups"].update_one({"id": chat_id}, {"$pull": {"admins": admin_id}})

    def get_groups_admin(self, admin_id):
        groups = self.db["groups"].find({"admins": admin_id}, {"_id": 0})
        return [Group(**group) for group in groups]

    def insert_group_report(self, chat_id, new_report):
        if new_report == "b":
            insert = [True, True]
        elif new_report == "a":
            insert = [True, False]
        else:
            insert = [False, True]
        group = self.db["groups"].find_one_and_update({"id": chat_id}, {"$set": {"admin": insert[0],
                                                                                 "report": insert[1]}},
                                                      {"_id": 0}, return_document=ReturnDocument.AFTER)
        return Group(**group)

    def insert_group_reply(self, chat_id, reply):
        # if reply is false, it means reply is true. Since reply is actually the people from the former mention group
        if isinstance(reply, list):
            group = self.db["groups"].find_one_and_update({"id": chat_id}, {"$set": {"reply": False},
                                                                            "$addToSet": {"pm": {"$each": reply}}},
                                                          {"_id": 0}, return_document=ReturnDocument.AFTER)
        else:
            group = self.db["groups"].find_one_and_update({"id": chat_id}, {"$set": {"reply": True}}, {"_id": 0},
                                                          return_document=ReturnDocument.AFTER)
        return Group(**group)

    def insert_group_mention(self, chat_id, reply, mention, user_id):
        if reply:
            if mention == "o":
                insert = ["pm", "off"]
            elif mention == "m":
                insert = ["off", "admins"]
            else:
                group = self.db["groups"].find_one_and_update({"id": chat_id}, {"$addToSet": {"pm": user_id}},
                                                              {"_id": 0}, return_document=ReturnDocument.AFTER)
                return Group(**group)
        else:
            if mention == "o":
                insert = ["pm", "off"]
            else:
                insert = ["off", "pm"]
        group = self.db["groups"].find_one_and_update({"id": chat_id},
                                                      {"$pull": {insert[0]: user_id},
                                                       "$addToSet": {insert[1]: user_id}}, {"_id": 0},
                                                      return_document=ReturnDocument.AFTER)
        return Group(**group)

    def insert_group_administration(self, chat_id, value):
        group = self.db["groups"].find_one_and_update({"id": chat_id}, {"$set": {"administration": value}}, {"_id": 0},
                                                      return_document=ReturnDocument.AFTER)
        return Group(**group)

    def insert_group_link(self, chat_id, to_link_id):
        group = self.db["groups"].find_one_and_update({"id": chat_id}, {"$addToSet": {"linked_groups": to_link_id}},
                                                      {"_id": 0}, return_document=ReturnDocument.AFTER)
        group2 = self.db["groups"].find_one_and_update({"id": to_link_id}, {"$addToSet": {"linked_groups": chat_id}},
                                                       {"_id": 0}, return_document=ReturnDocument.AFTER)
        return Group(**group), Group(**group2)

    def remove_group_link(self, chat_id, to_link_id):
        group = self.db["groups"].find_one_and_update({"id": chat_id}, {"$pull": {"linked_groups": to_link_id}},
                                                      {"_id": 0}, return_document=ReturnDocument.AFTER)
        group2 = self.db["groups"].find_one_and_update({"id": to_link_id}, {"$pull": {"linked_groups": chat_id}},
                                                       {"_id": 0}, return_document=ReturnDocument.AFTER)
        return Group(**group), Group(**group2)

    def get_group_link(self, chat_id):
        group = self.db["groups"].find_one({"id": chat_id})
        if group:
            return group["linked_groups"]
        return False

    def start_timeout(self, chat_ids, user_id):
        requests = []
        for chat_id in chat_ids:
            # we pull from PMs, just in case they are in there and to not screw around in our db
            requests.append(UpdateOne({"id": chat_id}, {"$addToSet": {"off": user_id}, "$pull": {"pm": user_id}}))
        self.db["groups"].bulk_write(requests)
    # WHEN FINISHING TIMES; SANITY CHECK FOR REPLY NEEDS TO BE INVOLVED

    def end_timeout(self, user_id, chats):
        for chat_id in chats:
            # that means the mention is a reply mention in group, so we need to make sure that reply exists
            if not chats[chat_id]:
                group = self.db["groups"].find_one({"id": chat_id})
                if group["reply"]:
                    self.db["groups"].update_one({"id": chat_id}, {"$pull": {"off": user_id}})
                    continue
            # that means he wants to switch from off to off, we dont have to do anything
            elif chats[chat_id] == "off":
                continue
            # if we reach this part of the code, its either a wanted PM or an unsuccessful reply, which means PM.
            self.db["groups"].update_one({"id": chat_id}, {"$pull": {"off": user_id}, "$addToSet": {"pm": user_id}})

    def insert_timeoff(self, admin):
        temp_admin = vars(admin)
        # making group_ids to strings in .groups
        for key in list(temp_admin["groups"].keys()):
            temp_admin["groups"][str(key)] = temp_admin["groups"][key]
            del temp_admin["groups"][key]
        # just in case someone is overwriting themselves
        self.db["admins"].delete_one({"id": admin.id})
        self.db["admins"].insert_one(temp_admin)

    def get_timeoff(self, day, time):
        admins = self.db["admins"].find({"days." + day.lower() + ".when": {"$lte": float(time)}}, {"_id": 0})
        # making keys to integers again
        actual_admins = []
        for admin in admins:
            for key in list(admin["groups"].keys()):
                admin["groups"][int(key)] = admin["groups"][key]
                del admin["groups"][key]
            actual_admins.append(admin)
        return [Admin(**admin) for admin in actual_admins]

    def delete_timeoff(self, admin_id):
        count = self.db["admins"].delete_one({"id": admin_id}).deleted_count
        if count < 1:
            return False
        return True


database = Database()
