import argparse
import time
from v2.utils import login, rest_tickets, get_orders, show_dict, get_ticket

parser = argparse.ArgumentParser()
parser.add_argument('-u', '--username', type=str, default='')
parser.add_argument('-p', '--password', type=str, default='')
args = parser.parse_args()

username = args.username
password = args.password

# login
code, msg = login(username, password)
print(f'[登录]\t{msg}')

# login successful
while code:
    # get latest activity date
    act_date, tickets = rest_tickets()
    print(f'[最新活动]\t{act_date}')

    # get orders
    orders, code = get_orders(act_date)
    show_dict(orders, '[我的订单]')

    for cinema in orders:
        for price in orders[cinema]:
            for _ in range(2 - len(orders[cinema][price])):
                print(f'[抢票] {cinema} {price}元', end='\t')
                if tickets[cinema][price]:
                    msg = get_ticket(tickets[cinema][price])
                    print(msg)
                else:
                    print('无票')

    time.sleep(10)
