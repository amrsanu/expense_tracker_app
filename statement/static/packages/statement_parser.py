"""parser for all the banks to have common base"""

import io
import pandas as pd

from django.core.cache import cache

STATEMENT_FILES = "bank_statements"


def hdfc_bank(statement_file):
    """To format the HDFC bank statement"""

    statement_file_data = statement_file.read().decode()
    if (
        " Date     ,Narration                                                                                                                ,Value Dat,Debit Amount       ,Credit Amount      ,Chq/Ref Number   ,Closing Balance"
        in statement_file_data
    ):
        print("-------- ALL Good --------------------")
        statement_df = pd.read_csv(io.StringIO(statement_file_data))
        statement_df = statement_df.applymap(
            lambda x: x.strip() if isinstance(x, str) else x
        )
        statement_df = statement_df.rename(
            columns={col: col.strip() for col in statement_df.columns}
        )
        statement_df["Date"] = pd.to_datetime(statement_df["Date"], format="%d/%m/%y")
        statement_df["Date"] = statement_df["Date"].dt.strftime("%d-%m-%Y")
        statement_df.drop(columns="Value Dat", axis=1)

        # statement_df.set_index("Date", inplace=True)
        statement_df = statement_df.reset_index(drop=True)

    else:
        print("-------- ERROR --------------------")
        return None
    # statement_lines = raw_statement.split("\r\n")
    return statement_df


def icici_credit(statement_file):
    """To format the HDFC bank statement"""
    statement_file_data = statement_file.read().decode()
    print(statement_file_data)
    print(f"ICICI---------- {statement_file_data}")

    if "DATE,MODE,PARTICULARS,DEPOSITS,WITHDRAWALS,BALANCE" in statement_file_data:
        # if "Statement of Transactions in SavingsNumber" in statement_file_data:
        print("-------- ALL Good --------------------")
        start, end = 0, 0
        stmt_lines = statement_file_data.split("/r/n")
        for i, line in enumerate(stmt_lines):
            if "Statement of Transactions in SavingsNumber" in line:
                start = i + 1
                break
        stmt_lines = stmt_lines[start:]
        end = 0
        for i, line in enumerate(stmt_lines):
            end = i + 1
            if line.strip() == "":
                break
        stmt_lines = stmt_lines[:end]

        statement_file_data = " /r/n".join(stmt_lines)
        statement_df = pd.read_csv(io.StringIO(statement_file_data))
        statement_df.dropna(subset=["DATE"], inplace=True)
        print(statement_df.head())
        statement_df = statement_df.applymap(
            lambda x: x.strip() if isinstance(x, str) else x
        )
        statement_df = statement_df.rename(
            columns={col: col.strip().title() for col in statement_df.columns}
        )
        statement_df["Date"] = pd.to_datetime(statement_df["Date"], format="%d/%m/%y")
        statement_df["Date"] = statement_df["Date"].dt.strftime("%d-%m-%Y")

        statement_df["Narration"] = (
            statement_df["Mode"].fillna("")
            + " "
            + statement_df["Particulars"].fillna("")
        )
        statement_df = statement_df.drop(columns=["Mode", "Particulars"], axis=1)
        statement_df = statement_df.rename(
            columns={
                "Deposits": "Credit Amount",
                "Withdrawals": "Debit Amount",
                "Balance": "Closing Balance",
            }
        )
        statement_df["Chq/Ref Number"] = 0
        statement_df = statement_df.reindex(
            columns=[
                "Date",
                "Narration",
                "Debit Amount",
                "Credit Amount",
                "Chq/Ref Number",
                "Closing Balance",
            ]
        )
        print(statement_df.head())

    else:
        print("-------- ERROR --------------------")
        return None
    # statement_lines = raw_statement.split("\r\n")
    return statement_df


def parse_statement(bank, statement_file):
    """To redirect to the specific parse"""
    if bank == "HDFC":
        return hdfc_bank(statement_file)
    if bank == "ICICI":
        return icici_credit(statement_file)

    return None
