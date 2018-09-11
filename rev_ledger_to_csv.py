import os
import csv
from collector.csv_writer import CsvWriter
from config.shared_mongo_client import SharedMongoClient


class RevLedgerCSV:
    DEFAULT_DIR = os.path.dirname(__file__) + "/rev_ledger_csv/"

    def __init__(self, target_coin: str, mm1_name: str, mm2_name: str):
        self.mm1_name = mm1_name
        self.mm2_name = mm2_name
        self.target_coin = target_coin
        self.rev_ledger_col = SharedMongoClient.get_streamer_db()["rev_ledger"]

    def write_new_rev_ledger_csv(self):
        with open(self.DEFAULT_DIR + '[%s-%s-%s].csv'
                  % (self.target_coin, self.mm1_name, self.mm2_name), 'w') as csvfile:
            ledger_writer = csv.writer(csvfile)
            ledger_writer.writerow(['status'] * 10 + ['Baked Beans'])
            ledger_writer.writerow(['Spam', 'Lovely Spam', 'Wonderful Spam'])

        csvfile.close()

    def read_latest_rev_ledger_db(self, file_name: str):
        with open(self.DEFAULT_DIR + file_name, 'r') as csvfile:
            rev_ledger_reader = csv.reader(csvfile)
