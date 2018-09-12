import os
from openpyxl import load_workbook
from config.shared_mongo_client import SharedMongoClient


class RevLedgerCSV:
    DEFAULT_DIR = os.path.dirname(__file__) + "/rev_ledger_excel/"

    def __init__(self, target_coin: str, mm1_name: str, mm2_name: str):
        self.target_coin = target_coin
        self.mm1_name = mm1_name
        self.mm2_name = mm2_name
        self.rev_ledger_col = SharedMongoClient.get_streamer_db()["rev_ledger"]

    def read_existing_rev_ledger_xlsx(self):
        workbook = load_workbook(self.DEFAULT_DIR + '%s_%s_%s.xlsx'
                                 % (self.target_coin, self.mm1_name, self.mm2_name))
        working_sheet = workbook["ledger"]
        print(working_sheet)


SharedMongoClient.initialize(should_use_localhost_db=False)
RevLedgerCSV("xrp", "bithumb", "okcoin").read_existing_rev_ledger_xlsx()
