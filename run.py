import argparse
from datetime import timedelta
from time import sleep

from ticket import TicketTools
from utils import log, utc_now

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

# ticket tools
tools = TicketTools(username, password)

# login
do = tools.login()
log('登录', '成功' if do else '失败')

while do and utc_now() - start_time < timedelta(minutes=max_run_time):
    # get UTC+8 time
    now = utc_now()
    log('当前时间', now.date())

    act_date = tools.update_links()
    log('最新活动', act_date)

    tools.update_orders(act_date)
    tools.show_orders()

    if now.hour >= 23:
        # delete all tickets at every 11pm
        tools.remove_all()
        do = False
    else:
        do = tools.purchase_all()
        log('抢票', '仍需抢票' if do else '抢票结束')

    sleep(10)
