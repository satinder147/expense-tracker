import os
import time
import boto3
import shutil
import datetime
import itertools
from concurrent.futures import ThreadPoolExecutor

class BotoUtils:
    def __init__(self, bucket_name, local_emails_folder):
        self.s3 = boto3.client('s3')
        self.bucket_name = bucket_name
        self.local_emails_folder = local_emails_folder

    @staticmethod
    def convert_to_ist(utc_time):
        """
        LastModified in boto3 response is UTC, convert that to IST and strip off timezone info from the datatime object
        """
        utc_offset = datetime.timedelta(hours=5, minutes=30)
        time_ist = utc_time + utc_offset
        return time_ist.replace(tzinfo=None)


    def get_all_objects_after_time(self, start_time):
        s3 = boto3.client('s3')
        response = s3.list_objects_v2(
            Bucket=self.bucket_name,
        )
        objects = response['Contents']
        print("got the objects")
        while response['IsTruncated']:
            response = s3.list_objects_v2(
                Bucket=self.bucket_name,
                ContinuationToken=response['NextContinuationToken']
            )
            objects.extend(response['Contents'])
        results = []
        for response in objects:
            if self.convert_to_ist(response['LastModified']) >= start_time:
                results.append(response)
        return results


    def download_object(self, inp):
        self.s3.download_file(*inp)

    def download_objects(self, object_keys):
        if os.path.exists(self.local_emails_folder):
            shutil.rmtree(self.local_emails_folder)
        os.makedirs(self.local_emails_folder)
        local_paths = list(map(lambda x: os.path.join(self.local_emails_folder, x), object_keys))
        tic = time.time()
        with ThreadPoolExecutor(max_workers=8) as executor:
            args = list(zip(itertools.repeat(self.bucket_name), object_keys, local_paths))
            executor.map(self.download_object, args)
        print("downloaded emails in {}".format(time.time() - tic))

    def get_emails(self, start_time):
        """
        Args:
            start_time(datetime object): In YYYY-MM-DD HH:MM:SS
        """
        objects = self.get_all_objects_after_time(start_time)
        self.download_objects([obj['Key'] for obj in objects])

if __name__ == '__main__':
    obj = BotoUtils('satinder-bank-emails', 'emails')
    start_time = '2023-05-01 00:00:00'
    obj.get_emails(start_time)
