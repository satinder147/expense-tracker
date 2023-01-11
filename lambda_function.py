import os
import re
import email
import imaplib
from datetime import  datetime

import gkeepapi
import pandas as pd

credit_card_payment_string_re = re.compile(r'Thank you for using your HDFC Bank Credit Card ending [^\<]*')
debit_Card_payment_string_re = re.compile(r'Rs.*Your UPI transaction reference number is')
axis_credit_card_string_re = re.compile(r'Thank you for using your Card no. XX9244 for [\s\S]*credit')

def search_note_in_keeps(keep_object, title):
    gnotes = keep_object.find(func=lambda x: x.title == title)
    try:
        note = next(gnotes)
        return note
    except StopIteration:
        return None


def format_text_in_required_format(data_df):
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

def add_payment_info_to_google_keeps(keep_object, text, note_title):
    already_existing_note = search_note_in_keeps(keep_object, note_title)
    if already_existing_note:
        print("already existing")
        already_existing_note.delete()
    gnote = keep_object.createNote(note_title, text)
    gnote.pinned = True
    keep_object.sync()

def format_debit_card_payments(message):
    for i in debit_Card_payment_string_re.finditer(message):
        x, y = i.span()
        message = message[x:y].strip()
        tokens = message.split(' ')
        amount = float('.'.join(tokens[0].split('.')[1:]))
        vendor = tokens[9]
        date_str = tokens[11]
        card_no = tokens[6]
        card_no, amount, vendor, date_str = \
            card_no.split('*')[-1], amount, vendor.split('@')[0][:15], datetime.strptime(date_str.split('.')[0], '%d-%m-%y')
        print(card_no, amount, vendor, date_str)
        return card_no, amount, vendor, date_str
    return None, None, None, None


def format_credit_card_payments(email_body):
    for i in credit_card_payment_string_re.finditer(email_body):
        x, y = i.span()
        message = email_body[x:y].strip()
        tokens = message.split(' ')
        card_no, cost = tokens[10], tokens[13]
        vendor = ""
        p = 15
        while tokens[p]!='on':
            vendor += tokens[p]
            break
        date_str = tokens[-2] + ' ' + tokens[-1][:-1]
        print(card_no, cost, vendor, date_str, sep=' ')
        return int(card_no), float(cost), vendor, datetime.strptime(date_str, '%d-%m-%Y %H:%M:%S')
    return None, None, None, None

def get_month_start():
    date = datetime.today().replace(day=1).date()
    date = datetime.strftime(date, '%d-%b-%Y')
    return date
    

def get_card_payments(mail, search_string, format_funtion):
    _, selected_mails = mail.search(None, None, search_string)
    print("Total messages" , len(selected_mails[0].split()))
    mapping = {'card_no': [], 'cost': [], 'vendor': [], 'time': []}
    
    for num in selected_mails[0].split():
        _, data = mail.fetch(num , '(RFC822)')
        _, bytes_data = data[0]

        email_message = email.message_from_bytes(bytes_data)

        for part in email_message.walk():
            if part.get_content_type()=="text/plain" or part.get_content_type()=="text/html":
                message = part.get_payload(decode=True)
                message = message.decode()
                card_no, cost, vendor, date = format_funtion(message)
                mapping['card_no'].append(card_no)
                mapping['cost'].append(cost)
                mapping['vendor'].append(vendor)
                mapping['time'].append(date)
                break
    return mapping

def format_axis_bank_credit_card_payments(message):
    for i in axis_credit_card_string_re.finditer(message):
        x, y = i.span()
        message = message[x:y].strip()
        message = message.replace('\n', ' ')    
        message = message.replace('\r', '')    
        tokens = message.split(' ')
        
        card_no, cost = tokens[7], tokens[10]
        vendor = []
        p = 12

        while tokens[p]!='on':
           vendor.append(tokens[p])
           p=p+1
        vendor = ' '.join(vendor)
        date_str = tokens[-5] + ' ' + tokens[-4][:-1]
        print(card_no, cost, vendor, date_str, sep=' ')
        return card_no, float(cost), vendor, datetime.strptime(date_str, '%d-%m-%y %H:%M:%S')
    return None, None, None, None

def lambda_handler(*args):
    username = os.getenv('username')
    app_password = os.getenv('app_password')
    start_date = get_month_start()
    current_month = '-'.join(start_date.split('-')[1:])
    gmail_host= 'imap.gmail.com'    
    mail = imaplib.IMAP4_SSL(gmail_host)
    mail.login(username, app_password)
    mail.select("INBOX")
    search_string_credit_card = '((SENTSINCE "{}") (HEADER Subject "Alert : Update on your HDFC Bank Credit Card"))'.format(start_date)
    mapping1 = get_card_payments(mail, search_string_credit_card, format_credit_card_payments)
    search_string_debit_card = '((SENTSINCE "{}") (HEADER Subject "View: Account update for your HDFC Bank A/c"))'.format(start_date)
    mapping2 = get_card_payments(mail, search_string_debit_card, format_debit_card_payments)
    search_string_axis_bank_credit_card = '((SENTSINCE "{}") (HEADER Subject "Transaction alert on Axis Bank Credit Card no. XX9244"))'.format(start_date)
    mapping3 = get_card_payments(mail, search_string_axis_bank_credit_card, format_axis_bank_credit_card_payments)
    df = pd.concat([pd.DataFrame(mapping1), pd.DataFrame(mapping2), pd.DataFrame(mapping3)]).reset_index(drop=True)
    df = df[~df['card_no'].isna()].reset_index(drop=True)
    text = format_text_in_required_format(df)
    keep_object = gkeepapi.Keep()
    keep_object.login(username, app_password)
    
    add_payment_info_to_google_keeps(keep_object, text, current_month)


"""
TODO
fetch emails only after the latest date
how to do this automatically after every email. 
"""
lambda_handler()
