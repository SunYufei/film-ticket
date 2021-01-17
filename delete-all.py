import argparse
from v2.utils import login, rest_tickets, get_orders, remove

parser = argparse.ArgumentParser()
parser.add_argument('-u', '--username', type=str, default='')
parser.add_argument('-p', '--password', type=str, default='')
args = parser.parse_args()

username = args.username
password = args.password

# login
code, msg = login(username, password)
print(f'[Login]\t{msg}')

# if login successful
if code:
    # get activity time
    act_date, _ = rest_tickets()

    # get orders
    orders, _ = get_orders(act_date)

    # remove all tickets
    for cinema in orders:
        for price in orders[cinema]:
            for idx in orders[cinema][price]:
                if len(idx):
                    msg = remove(idx)
                    print(f'[Remove]\t{cinema} {price:2d} {msg}')
