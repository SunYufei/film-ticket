from copy import deepcopy
from datetime import date, datetime, timedelta
from typing import Tuple

import requests
from bs4 import BeautifulSoup

# link
BASE = 'http://city.qingdaonews.com/qingdao/laoshanculture/'
INDEX = BASE + 'index'
LOGIN = BASE + 'loginsub'
ORDER = BASE + 'myorder'
REMOVE = BASE + 'delorder'
PURCHASE = BASE + 'getticket'

# session
session = requests.Session()

# cinema table template
cinema_table = {
    '利群华艺国际影院金鼎广场店': {
        5: None,
        8: None,
        11: None
    },
    '中影国际影城大拇指广场店': {
        5: None,
        8: None,
        11: None
    }
}


def show_dict(d: dict, head: str) -> None:
    print(f'{head:20s}\t|  5 |  8 | 11 |')
    for cinema in d:
        print(f'{cinema:15s}\t', end='|')
        for price in d[cinema]:
            if isinstance(d[cinema][price], list):
                print(f'{len(d[cinema][price]):3d} ', end='|')
            elif isinstance(d[cinema][price], str) or d[cinema][price]:
                print(f'  √ ', end='|')
            elif d[cinema][price] is None or not d[cinema][price]:
                print(f'  × ', end='|')
        print()


def parse_title(title: str) -> Tuple[bool, str, int]:
    if '元观影活动' in title:
        start = title.index('(')
        end = title.index(')')
        cinema = title[start + 1:end]
        start = title.index(']')
        end = title.index('元')
        price = int(title[start + 1:end])
        return True, cinema, price
    else:
        return False, '', 0


def rest_tickets() -> Tuple[date, dict]:
    def get_date(link: str) -> date:
        resp = session.get(link)
        bs = BeautifulSoup(resp.text, 'lxml')
        return datetime.strptime(bs.select('div.xw_detail_date')[0].text,
                                 '%Y-%m-%d %H:%M:%S').date()

    # return values
    act_date = date(2020, 1, 1)
    links = deepcopy(cinema_table)

    try:
        page = 1
        count = 0
        flag = True
        while flag:
            r = session.get(f'{INDEX}/page/{page}')
            soup = BeautifulSoup(r.text, 'lxml')

            for item in soup.select('div.jianzheng_remai_case'):
                a = item.find('a', {'class': 'jianzheng_remai_case_title'})
                is_film, cinema, price = parse_title(a.text)
                if is_film:
                    time = get_date(a['href'])
                    if time - act_date >= timedelta(0):
                        act_date = time

                        button = item.find('a', {'class': 'zhuangtai'})
                        links[cinema][price] = a['href'] if button.find('i') else None

                        count = count + 1
                        if count >= len(cinema_table.keys()) * 3:
                            flag = False
                    else:
                        flag = False

            page = page + 1
    finally:
        return act_date, links


def login(username: str, password: str) -> Tuple[bool, str]:
    try:
        data = {'IdNumber': username, 'PassWord': password}
        # post login page
        r = session.post(LOGIN, data)
        if r.status_code == 200:
            resp = eval(r.text)
            code = resp['code']
            message = resp['message']
            return (True, message) if code == 0 else (False, message)
        else:
            raise ConnectionError
    except ConnectionError:
        return False, '连接失败'


def get_orders(act_date: date) -> Tuple[dict, bool]:
    # return values
    orders = deepcopy(cinema_table)
    for c in orders:
        for p in orders[c]:
            orders[c][p] = []

    count = 0

    try:
        page = 1
        flag = True
        while flag:
            r = session.get(f'{ORDER}/page/{page}')
            soup = BeautifulSoup(r.text, 'lxml')

            items = soup.select('div.jianzheng_remai_case')

            flag = len(items) > 0
            for item in items:
                title = item.find('a').text
                is_film, cinema, price = parse_title(title)

                # if order is about film ticket
                if is_film:
                    # get activity time
                    time = item.find('div', {'class': 'jianzheng_remai_case_detailp'}).text
                    time = datetime.strptime(time[5:], '%Y-%m-%d %H:%M:%S').date()

                    # check activity time
                    if time - act_date == timedelta(0):
                        button = item.find('input')
                        orders[cinema][price].append(button['onclick'][5:-2] if button else '')
                    else:
                        # wrong activity time, break
                        flag = False

            page = page + 1
    finally:
        for cinema in orders:
            for price in orders[cinema]:
                if isinstance(orders[cinema][price], list):
                    count += len(orders[cinema][price])
        return orders, count != 6


def get_ticket(url: str) -> str:
    data = {
        'activityid': '',
        'activityname': '',
        'idnumber': '',
        'realname': '',
        'type2': '',
        'current_url': url
    }

    try:
        r = session.get(url)
        soup = BeautifulSoup(r.text, 'lxml')
        for item in soup.find_all('input', {'type': 'text'}):
            if item['name'] in data:
                data[item['name']] = item['value']
        r = session.post(PURCHASE, data)
        message = eval(r.text)['message']
        return message
    except ConnectionError:
        return '连接失败'


def remove(tid: str) -> str:
    msg = {'1': '活动已过期', '2': '删除失败', '3': '删除成功', '200': '服务器错误'}
    try:
        r = session.post(REMOVE, data={'QzId': tid})
        return msg[r.text[1:-1]]
    except ConnectionError:
        return '连接失败'
