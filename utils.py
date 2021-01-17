import datetime
from copy import deepcopy
from typing import Tuple, Dict

import requests
from bs4 import BeautifulSoup

# Link
BASE = 'http://qdlsqp.cn/'
LOGIN = BASE + 'Login.aspx'
ORDER = BASE + 'MyOrder.aspx'
REMOVE = BASE + 'laoshan/OrdersDel.ashx'
PURCHASE = BASE + 'laoshan/CheckZuowei2.ashx'

# Session
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


def parse_title(title: str) -> Tuple[str, int]:
    start = title.index('(')
    end = title.index(')')
    cinema = title[start + 1:end]
    start = title.index(']')
    end = title.index('元')
    price = int(title[start + 1:end])
    return cinema, price


def get_view_state(soup: BeautifulSoup) -> Dict[str, str]:
    ret = {}
    for item in soup.select('input[type=hidden]'):
        ret[item['name']] = item['value']
    return ret


def login(username: str, password: str) -> Tuple[bool, str]:
    try:
        # get login page
        r = session.get(LOGIN)
        if r.status_code == 200:
            soup = BeautifulSoup(r.text, 'lxml')
            data = get_view_state(soup)
            data['__EVENTTARGET'] = 'LinkButton1'
            data['idnumber2'] = username
            data['password2'] = password

            # post login page
            r = session.post(LOGIN, data)
            if '用户名或密码错误' in r.text:
                return False, '用户名或密码错误'
            else:
                return True, '登录成功'
    except ConnectionError:
        return False, '连接失败'


def rest_tickets() -> Tuple[datetime.datetime, dict]:
    # return values
    deadline = datetime.datetime(2019, 1, 1)
    link = deepcopy(cinema_table)

    # view state
    data = {}

    try:
        page = 1
        count = 0
        flag = True
        while flag:
            if page == 1:
                r = session.get(BASE)
            else:
                data['__EVENTTARGET'] = 'AspNetPager1'
                data['__EVENTARGUMENT'] = str(page)
                r = session.post(BASE, data)

            soup = BeautifulSoup(r.text, 'lxml')
            if len(data) == 0:
                data = get_view_state(soup)

            for item in soup.select('div.neiye_line'):
                if '[电影惠民季]' in item.text[:10]:
                    right = item.find('div', {'class': 'neiye_line_right'})

                    ddl = right.find('div', {'class': 'xw_date'}).text
                    ddl = ddl[ddl.index('：') + 1:]
                    ddl = datetime.datetime.strptime(ddl, '%Y-%m-%d')

                    if ddl - deadline >= datetime.timedelta(0):
                        deadline = ddl

                        a = right.find('a', {'class': 'xw_title'})
                        cinema, price = parse_title(a.text)

                        left = item.find('div', {'class': 'neiye_line_left'})
                        link[cinema][price] = a['href'] if (left.find('i') is None) else None

                        count = count + 1
                        if count >= len(cinema_table.keys()) * 3:
                            flag = False
            page = page + 1
    finally:
        return deadline, link


def get_orders(deadline: datetime.datetime) -> dict:
    def parse_param(onclick: str) -> list:
        onclick = onclick[onclick.index('(') + 1:onclick.index(')')]
        onclick = onclick.replace("'", '')
        return onclick.split(',')

    ret = deepcopy(cinema_table)
    for cinema in ret:
        for price in ret[cinema]:
            ret[cinema][price] = []

    data = {}

    try:
        page = 1
        flag = True
        while flag:
            if page == 1:
                r = session.get(ORDER)
            else:
                data['__EVENTTARGET'] = 'AspNetPager1'
                data['__EVENTARGUMENT'] = str(page)
                r = session.post(ORDER, data)

            soup = BeautifulSoup(r.text, 'lxml')
            if len(data) == 0:
                data = get_view_state(soup)

            for item in soup.select('div.neiye_line'):
                if '[电影惠民季]' in item.text[:10]:
                    right = item.find('div', {'class': 'neiye_line_right'})

                    ddl = right.find('div', {'class': 'xw_date'}).text
                    ddl = ddl[ddl.index('：') + 1:]
                    ddl = datetime.datetime.strptime(ddl, '%Y-%m-%d')

                    if ddl - deadline == datetime.timedelta(0):
                        cinema, price = parse_title(right.find('div', {'class': 'xw_title'}).text)
                        button = right.find('input', {'type': 'button'})
                        ret[cinema][price].append(parse_param(button['onclick']))
                    else:
                        flag = False
            page = page + 1
    finally:
        return ret


def remove(params: list) -> Tuple[bool, str]:
    data = {
        'QzId': params[0],
        'IdNumber': params[1],
        'Time': params[2],
        'Type2': params[3]
    }
    try:
        r = session.post(REMOVE, data)
        if r.status_code == 200:
            ret = {
                '1': (False, '活动已过期'),
                '2': (False, '删除失败'),
                '3': (True, '删除成功'),
                '200': (False, '服务器错误')
            }
            if r.text in ret:
                return ret[r.text]
    except ConnectionError:
        return False, '连接失败'


def purchase(link: str) -> dict:
    url = BASE + link
    try:
        # get purchase link
        r = session.get(url)
        if r.status_code == 200:
            soup = BeautifulSoup(r.text, 'lxml')
            # get params
            data = {}
            for i in soup.select('input[type=text]'):
                if 'value' in i.attrs:
                    data[i['name']] = i['value']
                else:
                    data[i['name']] = ''
            # post purchase link
            r = session.post(PURCHASE, data)
            if r.status_code == 200:
                return eval(r.text)
    except ConnectionError:
        return {
            'code': '200',
            'message': '连接失败'
        }
