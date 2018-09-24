import logging
from pymongo.database import Database
from pymongo.collection import Collection
from config.shared_mongo_client import SharedMongoClient


class User:

    def __init__(self):
        self.user_db: Database = SharedMongoClient.get_user_db()

    def create_new_account(self):
        _user_id = str(input("Type ID: "))
        self.id_validation(_user_id)

        # create mongo collection in User database by its ID
        user_col: Collection = self.user_db.create_collection(_user_id)

        # create basic data structure and save their ObjectId to user collection

    def id_validation(self, user_id: str):
        if user_id in self.user_db.list_collection_names():
            logging.error("That User ID already exists.. Please try another ID!")
            return self.create_new_account()
        logging.warning("ID created! - %s" % user_id)

