import logging
from pymongo.database import Database
from pymongo.collection import Collection
from config.shared_mongo_client import SharedMongoClient
from .config import UserCreation, RFABValidation


class UserManager:

    def __init__(self):

        self.rfab_db: Database = SharedMongoClient.get_rfab_db()
        self.user_col: Collection = self.rfab_db["user"]
        self.streamer_col: Collection = self.rfab_db["streamer"]
        self.history_col: Collection = self.rfab_db["history"]

    def create_new_account(self):
        while True:
            _user_id = str(input("Type ID: "))
            if self.user_col.find_one({'user_id': _user_id}):
                logging.error("User ID already exists.. Please try another ID!")
                continue
            if len(_user_id) < 5:
                logging.error("User ID should be more or equal than 5 letters")
                continue
            break

        # in case same id exists in streamer collection
        if self.streamer_col.find_one({'user_id': _user_id}) or self.history_col.find_one({'user_id': _user_id}):
            raise Exception("User already exists in Streamer or History collection.. please inspect MongoDB to fix")

        # create user
        user_data_config = UserCreation(_user_id)
        self.user_col.insert_one(user_data_config.USER_COL_DICT)
        logging.warning("ID created! - %s" % _user_id)

        # create new streamer col at Mongo
        self.streamer_col.insert_one(user_data_config.STREAMER_COL_DICT)
        self.history_col.insert_one(user_data_config.HISTORY_COL_DICT)

        logging.warning("User created Successfully!!")

    def general_user_validation(self, _user_id: str):
        user_count = self.user_col.find({'user_id': _user_id}).count()
        streamer_count = self.streamer_col.find({'user_id': _user_id}).count()
        history_count = self.streamer_col.find({'user_id': _user_id}).count()

        # check ID
        if user_count == 0:
            raise Exception("ID you provided does not exist.. Create account first")
        if user_count > 1:
            raise Exception("There are more than two same IDs in User DB.. Manually check and make modification")

        # check streamer
        if streamer_count == 0:
            raise Exception("Your ID exists in User DB but not in streamer..Plz manually check")
        if streamer_count > 1:
            raise Exception("There are more than two same IDs in Streamer DB.. Manually check and make modification")

        # check histroy
        if history_count == 0:
            raise Exception("Your ID exists in User DB & streamer but not in history..Plz manually check")
        if history_count > 1:
            raise Exception("There are more than two same IDs in History DB.. Manually check and make modification")

        logging.info("General User Validation passed")

    def validation_before_rfab(self, _user_id: str, target_currency: str, mm1_name: str, mm2_name: str):

        # first, run general validation
        self.general_user_validation(_user_id=_user_id)

        combi_name = "%s-%s-%s" % (target_currency, mm1_name, mm2_name)

        # check if injected combination exists in Balance tracker & Trade commander
        self.streamer_col.find_one_and_update({
            'user_id': _user_id
        }, {
            "$set": {
                "balance_tracker.%s" % combi_name: RFABValidation.BALANCE_TRACKER_DICT,
                "trade_commander.%s" % combi_name: RFABValidation.TRADE_COMMANDER_DICT,
                "success_trade_recorder.%s" % combi_name: RFABValidation.SUCCESS_TRADE_RECORDER,
                "failed_trade_recorder.%s" % combi_name: RFABValidation.FAILED_TRADE_RECORDER
            }}, upsert=True)

        logging.info("DB is Ready for RFAB to launch")

    def find_user_and_update_streamer(self, user_id: str, query_dict: dict):
        self.streamer_col.find_one_and_update({'user_id': user_id}, {
            "$set": query_dict
        })
