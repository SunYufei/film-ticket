import argparse
from datetime import timedelta
from time import sleep

from ticket import Ticket
from utils import utc_now

# args
parser = argparse.ArgumentParser()
parser.add_argument('-u', '--username', type=str)
parser.add_argument('-p', '--password', type=str)
parser.add_argument('-m', '--max-run-time', type=int, default=60)
args = parser.parse_args()

username = args.username
password = args.password
max_run_time = args.max_run_time

# start time
start_time = utc_now()

# ticket instance
instance = Ticket(username, password)
do = instance.login()
print(f'[登录] 登录{"成功" if do else "失败"}')

while do and utc_now() - start_time < timedelta(hours=max_run_time):
    do = instance.run()
    sleep(10)
