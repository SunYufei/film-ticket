import argparse
from datetime import timedelta
from time import sleep

from ticket import Ticket
from utils import utc_now

# args
parser = argparse.ArgumentParser()
parser.add_argument('-u', '--username', type=str)
parser.add_argument('-p', '--password', type=str)
args = parser.parse_args()

username = args.username
password = args.password

# start time
start_time = utc_now()

# ticket instance
instance = Ticket(username, password)
do = instance.login()

while do and utc_now() - start_time < timedelta(hours=1):
    do = instance.run()
    sleep(10)
