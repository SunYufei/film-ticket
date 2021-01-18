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

    act_date, links = tools.rest_tickets()
    log('最新活动', act_date)

    orders = my_orders(act_date)
    print_orders(orders)

    if now.hour >= 23:
        # delete all tickets at every 11pm
        tools.remove_all()
        break
    else:
        count = 0
        for cinema in links:
            for price in links[cinema]:
                link = links[cinema][price]
                if len(orders[cinema][price] != 2):
                    need_purchase = tools.purchase(link)
                    log('抢票', f'{cinema} {price} {"抢票结束" if not need_purchase else "仍需抢票"}')
                    if not need_purchase:
                        count += 1
        if count >= tools.max_type_count():
            break

    sleep(10)
