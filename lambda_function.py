import os
import email
from datetime import  datetime

import pandas as pd

from boto_utils import BotoUtils
from google_keep_utils import GoogleKeepUtils
from extractors import Axis9244, HdfcUpi, Hdfc0578

def get_transactions(email_folder):
    paths = list(map(lambda x: os.path.join(email_folder, x), os.listdir(email_folder)))
    mapping = {'card_no': [], 'cost': [], 'vendor': [], 'time': []}
    extractors = [
        Hdfc0578(),
        HdfcUpi(),
        Axis9244()
    ]
    for path in paths:
        with open(path, 'rb') as f:
            mail = f.read()
            mail_message = email.message_from_bytes(mail)
            message = ""
            for part in mail_message.walk():
                if part.get_content_type()=="text/plain" or part.get_content_type()=="text/html":
                    mes = part.get_payload(decode=True)
                    mes = mes.decode('ISO 8859-1')
                    message += mes

            resp = None
            for extractor in extractors:
                try:
                    resp = extractor.extract_information_from_mail(message)
                    # one of the transaction extractor will succeed in extracting the information.
                    break
                except Exception as e:
                    pass
            if resp:
                for col in resp:
                    mapping[col].append(resp[col])
    df = pd.DataFrame(mapping).reset_index(drop=True)
    return df

def lambda_handler(*args):
    email_folder = 'emails'
    s3_bucket = 'satinder-bank-emails'
    username = os.getenv('username')
    app_password = os.getenv('app_password')
    start_time = datetime.today().replace(day=1)
    current_month = str(datetime.strftime(start_time, '%B-%Y'))
    BotoUtils(s3_bucket, email_folder).get_emails(start_time)
    df = get_transactions(email_folder)
    df = df[~df['card_no'].isna()].reset_index(drop=True)
    # email for a transaction in last month was received this month
    df = df[df['time'] >= start_time]
    print(df.sort_values(by='time'))
    google_keep_utils = GoogleKeepUtils(username, app_password)
    google_keep_utils.register(df, current_month)

if __name__ == "__main__":
    lambda_handler()
