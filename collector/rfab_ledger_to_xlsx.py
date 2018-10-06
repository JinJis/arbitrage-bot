import logging
import os

from openpyxl import load_workbook
from openpyxl.styles import Font
from openpyxl.workbook.workbook import Workbook
from openpyxl.worksheet.worksheet import Worksheet

from config.global_conf import Global
from config.shared_mongo_client import SharedMongoClient


class RFABLedgerXLSX:
    DEFAULT_DIR = os.path.dirname(__file__) + "/rfab_ledger_excel/"
    BASE_LEDGER_DIR = DEFAULT_DIR + "base_rfab_ledger.xlsx"
    FIRST_ROW = 11
    CRITERIA_COLUMN = {
        "time": "B",
        "mode_status": "C",
        "brief_profit": {
            "total_krw_earned": "C5",
            "total_coin_loss": "C6",
            "agg_yield": "C7"
        },
        "mm1": {
            "krw": "D",
            "coin": "E"
        },
        "mm2": {
            "krw": "F",
            "coin": "G"
        },
        "total": {
            "krw": "H",
            "coin": "I"
        },
        "yield": {
            "krw_earned": "J",
            "coin_loss": "K",
            "yield": "L",
            "agg_yield": "M"
        }
    }

    def __init__(self, target_currency: str, mm1_name: str, mm2_name: str,
                 start_time: int, end_time: int, is_test: bool):
        self.mm1_name = mm1_name
        self.mm2_name = mm2_name
        self.target_currency = target_currency

        self.start_time = start_time
        self.end_time = end_time

        if is_test:
            self.rfab_ledger_col = SharedMongoClient.get_test_streamer_db()["rfab_ledger"]
        else:
            self.rfab_ledger_col \
                = SharedMongoClient.get_streamer_db(target_currency, mm1_name, mm2_name)["rfab_ledger"]

        try:
            self.file_dir = self.DEFAULT_DIR + '%s_%s_%s.xlsx' % (self.target_currency, self.mm1_name, self.mm2_name)

            # set workbook
            self.target_wb: Workbook = load_workbook(self.file_dir)

            # set worksheet
            self.ledger_ws: Worksheet = self.target_wb["ledger"]
            self.transfer_ws: Worksheet = self.target_wb["transfer"]
            self.invest_ws: Worksheet = self.target_wb["investment"]

        except FileNotFoundError:
            logging.error("Filed Not Found!! Now creating New RFAB ledger xlsx!")
            self.write_new_ledger()

    def run(self):
        if self.ledger_ws is None or self.transfer_ws is None or self.invest_ws is None:
            raise Exception("Could not read your RFAB ledger sheets.. please manually check!")

        # get latest mongo rfab_ledger cursor
        profit_ledger_cur = self.get_mongo_rfab_ledger_cursor(self.start_time, self.end_time)

        # write balance info to excel
        current_row = self.FIRST_ROW
        for ledger_data in profit_ledger_cur:
            self.write_balance_in_excel(current_row, ledger_data)
            current_row += 1

        # write function for yield and etc info
        last_row = current_row - 1
        self.write_function_in_excel(last_row=last_row)

        # save to existing file
        self.target_wb.save(self.file_dir)
        logging.warning("RFAB Ledger saved to Excel successfully!!")

    def write_new_ledger(self):
        self.target_wb: Workbook = load_workbook(self.BASE_LEDGER_DIR)
        self.ledger_ws: Worksheet = self.target_wb["ledger"]

        # after doing this, excel funxction will automatically change table names
        self.ledger_ws["C3"] = self.target_currency
        self.ledger_ws["D3"] = self.mm1_name
        self.ledger_ws["E3"] = self.mm2_name

        # save to new combination named file
        self.target_wb.save(self.DEFAULT_DIR + '%s_%s_%s.xlsx' % (self.target_currency, self.mm1_name, self.mm2_name))

        logging.warning("New RFAB Ledger Excel file created with targeted combination")

    def get_mongo_rfab_ledger_cursor(self, start_time: int, end_time: int):
        # sort rfab_ledger of MongoDB by target combination
        mongo_rfab_ledger_cur = self.rfab_ledger_col.find({
            "time": {
                "$gte": start_time,
                "$lte": end_time
            }}).sort([("time", 1)])

        if mongo_rfab_ledger_cur is not None:
            return mongo_rfab_ledger_cur
        else:
            raise Exception("Nothing queried in MongoDB..Please manually check!")

    def write_balance_in_excel(self, target_row: int, ledger_data: dict):

        # write time
        self.ledger_ws[self.CRITERIA_COLUMN["time"] + str(target_row)].value = Global.convert_epoch_to_local_datetime(
            ledger_data["time"], timezone="kr")

        # write mode_status
        self.ledger_ws[self.CRITERIA_COLUMN["mode_status"] + str(target_row)].value = ledger_data["mode_status"]

        # write balance
        for key1 in ["mm1", "mm2", "total"]:
            for key2 in ["krw", "coin"]:
                self.ledger_ws[self.CRITERIA_COLUMN[key1][key2] + str(target_row)].value = ledger_data[key1][key2]

    def write_function_in_excel(self, last_row: int):

        for target_row in range(self.FIRST_ROW + 1, last_row + 1):  # + 1 for first row to skip

            # this will universally be used in =IF(cell="settelement") function
            logic_test_cell = self.CRITERIA_COLUMN["mode_status"] + str(target_row)

            # function(1): krw_earned, coin loss
            for target_colmn, currency_key in zip(["krw_earned", "coin_loss"], ["krw", "coin"]):
                self.ledger_ws[self.CRITERIA_COLUMN["yield"][target_colmn] + str(target_row)].value = \
                    '=IF(%s="settlement", %s-%s, "")' % (
                        logic_test_cell,
                        self.CRITERIA_COLUMN["total"][currency_key] + str(target_row),
                        self.CRITERIA_COLUMN["total"][currency_key] + str(target_row - 1))

            # function(2): calc yield %
            yield_cell = self.ledger_ws[self.CRITERIA_COLUMN["yield"]["yield"] + str(target_row)]
            yield_cell.value = '=IF(%s="settlement", %s/%s, "")' % (
                logic_test_cell,
                self.CRITERIA_COLUMN["yield"]["krw_earned"] + str(target_row),
                self.CRITERIA_COLUMN["total"]["krw"] + str(target_row - 1))
            # format to percentage
            yield_cell.number_format = '0.0000%'

            # FIXME: 여기 엄밀하게 바꿔야함... 일단 다 더하는걸로
            # function(3): calc agg. yield
            agg_yield_cell = self.ledger_ws[self.CRITERIA_COLUMN["yield"]["agg_yield"] + str(target_row)]
            agg_yield_cell.value = '=IF(%s="settlement", SUM(%s:%s), "")' % (
                logic_test_cell,
                "$" + self.CRITERIA_COLUMN["yield"]["yield"] + "$" + str(self.FIRST_ROW),
                self.CRITERIA_COLUMN["yield"]["yield"] + str(target_row))
            # format to percentage
            agg_yield_cell.number_format = '0.0000%'
            # make it bold
            agg_yield_cell.font = Font(bold=True)

        # function(4): # write brief profit status
        for column, key in zip(["total_krw_earned", "total_coin_loss"], ["krw_earned", "coin_loss"]):
            self.ledger_ws[self.CRITERIA_COLUMN["brief_profit"][column]].value = \
                '=SUM(%s:%s)' % (
                    self.CRITERIA_COLUMN["yield"][key] + str(self.FIRST_ROW),
                    self.CRITERIA_COLUMN["yield"][key] + str(last_row))

        # write agg. yield
        self.ledger_ws[self.CRITERIA_COLUMN["brief_profit"]["agg_yield"]].value = \
            '=%s' % self.CRITERIA_COLUMN["yield"]["agg_yield"] + str(last_row)
