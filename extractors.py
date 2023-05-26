import re
from datetime import datetime
from abc import ABC, abstractmethod

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

