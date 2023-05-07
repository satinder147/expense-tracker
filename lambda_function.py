import os
import re
import email
import imaplib
from datetime import  datetime
from abc import ABC, abstractmethod

import gkeepapi
import pandas as pd


class CardMailFormatter(ABC):

    @staticmethod
    @abstractmethod
    def extract_vendor(mail):
        pass

    @staticmethod
    @abstractmethod
    def extract_cost(mail):
        pass

    @staticmethod
    @abstractmethod
    def extract_card_number(mail):
        pass

    @staticmethod
    @abstractmethod
    def extract_time(mail):
        pass

    def extract_information_from_mail(self, mail):
        """
        This function extracts transaction cost, transaction time, transaction vendor and transaction card
        number from the mail
        :param mail:
        :return: dict
        """
        return {
            'cost': self.extract_cost(mail), 'vendor': self.extract_vendor(mail),
            'card_no': self.extract_card_number(mail), 'time': self.extract_time(mail)
        }

class Axis9244(CardMailFormatter):
    @staticmethod
    def extract_vendor(mail):
        return re.search(r'at\s+(.*?)\s+on', mail).group(1)
    @staticmethod
    def extract_cost(mail):
        return float(re.search(r'INR\s+(\d+(\.\d+)?)', mail).group(1))

    @staticmethod
    def extract_time(mail):
        date_str = re.search(r'on (\d{2}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})', mail).group(1)
        return datetime.strptime(date_str, '%d-%m-%y %H:%M:%S')

    @staticmethod
    def extract_card_number(mail):
        return int(re.search(r'Card no\. (\w{2}\d{4})', mail).group(1).split('X')[-1])

class HdfcUpi(CardMailFormatter):
    @staticmethod
    def extract_vendor(mail):
        return re.search(r'VPA\s+(\S+)', mail).group(1)

    @staticmethod
    def extract_cost(mail):
        return float(re.search(r'Rs\.([\d.]+)\shas been debited', mail).group(1))

    @staticmethod
    def extract_time(mail):
        date_str = re.search(r'(\d{2}-\d{2}-\d{2})', mail).group(1)
        return datetime.strptime(date_str, '%d-%m-%y')

    @staticmethod
    def extract_card_number(mail):
        return re.search(r'\*\*(\d+)', mail).group(1)

class Hdfc0578(CardMailFormatter):
    @staticmethod
    def extract_vendor(mail):
        return re.search(r'at (\w+\s?\w+) on', mail).group(1)

    @staticmethod
    def extract_cost(mail):
        return float(re.search(r'Rs ([\d\.]+) at', mail).group(1))

    @staticmethod
    def extract_time(mail):
        date_str = re.search(r'on (\d{2}-\d{2}-\d{4} \d{2}:\d{2}:\d{2})', mail).group(1)
        return datetime.strptime(date_str, '%d-%m-%y %H:%M:%S')

    @staticmethod
    def extract_card_number(mail):
        return re.search(r'ending\s+(\d{4})', mail).group(1)
    

class GoogleKeepUtils:

    def __init__(self, username, app_password):
        self.keeps_object = gkeepapi.Keep()
        self.keeps_object.login(username, app_password)
    def search_note_in_keeps(self, title):
        notes = self.keeps_object.find(func=lambda x: x.title == title)
        try:
            note = next(notes)
            return note
        except StopIteration:
            return None

    def add_transactions_to_google_keeps(self, note_title, transactions):
        already_existing_note = self.search_note_in_keeps(note_title)
        if already_existing_note:
            print("Note already existing, Deleting...")
            already_existing_note.delete()
        gnote = self.keeps_object.createNote(note_title, transactions)
        gnote.pinned = True
        self.keeps_object.sync()

    @staticmethod
    def prepare_message_for_google_keeps(data_df):
        text = """"""
        data_df['date'] = data_df['time'].apply(lambda x: str(x.date()))
        data_df['vendor'] = data_df['vendor'].apply(lambda x: x.lower())
        data_df['vendor_length'] = data_df['vendor'].apply(lambda x: len(x))
        for group_name, group in data_df.groupby('date'):
            text += '- ' + group_name + '\n'
            for idx, (_, row) in enumerate(group.iterrows()):
                text += "    {0} RS {2:^5},  {1:>5}({3})".format('*', row['vendor'], str(int(row['cost'])).rjust(5, ' '), row['card_no']) + '\n'
            text+='\n'
        total_per_card = data_df.groupby('card_no')['cost'].sum().to_dict()
        for card_no, total in total_per_card.items():
            text+= 'card - {},  total - {}\n'.format(str(card_no), str(total))
        text +='total {} \n'.format(data_df['cost'].sum())
        return text

    def register(self, data_df, current_month):
        transactions = self.prepare_message_for_google_keeps(data_df)
        self.add_transactions_to_google_keeps(transactions, current_month)

def get_month_start():
    date = datetime.today().replace(day=1).date()
    date = datetime.strftime(date, '%d-%b-%Y')
    return date
    

def get_card_payments(mail, search_string, format_funtion):
    _, selected_mails = mail.search(None, None, search_string)
    mapping = {'card_no': [], 'cost': [], 'vendor': [], 'time': []}
    
    for num in selected_mails[0].split():
        bytes_data = mail.fetch(num , '(RFC822)')[1][0][1]
        email_message = email.message_from_bytes(bytes_data)
        for part in email_message.walk():
            if part.get_content_type()=="text/plain" or part.get_content_type()=="text/html":
                message = part.get_payload(decode=True)
                message = message.decode('ISO 8859-1')
                try:
                    response = format_funtion(message)
                    for col in ['cost', 'card_no', 'vendor', 'time']:
                        mapping[col].append(response[col])
                except Exception as e:
                    pass
                break
    return mapping



def lambda_handler():
    username = os.getenv('username')
    app_password = os.getenv('app_password')
    start_date = get_month_start()
    current_month = '-'.join(start_date.split('-')[1:])
    gmail_host= 'imap.gmail.com'    
    mail = imaplib.IMAP4_SSL(gmail_host)
    mail.login(username, app_password)
    mail.select("INBOX")
    email_search_strings_and_functions = [
        ('((SENTSINCE "{}") (HEADER Subject "Alert : Update on your HDFC Bank Credit Card"))'.format(start_date),
          Hdfc0578().extract_information_from_mail),
         ('((SENTSINCE "{}") (HEADER Subject "View: Account update for your HDFC Bank A/c"))'.format(start_date),
          HdfcUpi().extract_information_from_mail),
        ('((SENTSINCE "{}") (HEADER Subject "Transaction alert on Axis Bank Credit Card no. XX9244"))'.format(start_date),
         Axis9244().extract_information_from_mail)
    ]
    transactions = []
    for email_search_string, info_extractor_func in email_search_strings_and_functions:
        transactions.append(get_card_payments(mail, email_search_string, info_extractor_func))
    df = pd.concat(list(map(pd.DataFrame, transactions))).reset_index(drop=True)
    df = df[~df['card_no'].isna()].reset_index(drop=True)
    google_keep_utils = GoogleKeepUtils(username, app_password)
    google_keep_utils.register(df, current_month)


lambda_handler()
