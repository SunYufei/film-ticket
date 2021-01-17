import re
from collections import defaultdict
from datetime import date, datetime, timedelta
from typing import Tuple

import requests
from lxml import etree

# links
from utils import utc_now

BASE = 'http://city.qingdaonews.com/qingdao/laoshanculture'
INDEX = f'{BASE}/index'
LOGIN = f'{BASE}/loginsub'
ORDER = f'{BASE}/myorder'
REMOVE = f'{BASE}/delorder'
PURCHASE = f'{BASE}/getticket'

# cinema table template
ticket_types = {
    '利群华艺国际影院金鼎广场店': (8,),
    '中影国际影城大拇指广场店': (8,)
}


class Ticket:
    def __init__(self, username, password):
        self._username = username
        self._password = password
        # session
        self._session = requests.Session()

    def login(self) -> bool:
        try:
            r = self._session.post(LOGIN, data={
                'IdNumber': self._username,
                'PassWord': self._password
            })
            return r.json()['code'] == 0
        except Exception as e:
            print(f'[登录] {e}')
            return False

    def run(self) -> bool:
        # get UTC-8 time
        now = utc_now()
        print(f'[当前时间]\t{now.date()}')

        # rest tickets
        act_date, links = self._rest_tickets()
        print(f'[最新活动]\t{act_date}')

        # get orders
        orders = self._get_orders(act_date)
        print(f'{"[我的订单]":24s}\t|', end='')
        for cinema in ticket_types:
            for price in ticket_types[cinema]:
                print(f'{price:3d} ', end='|')
            break
        print()

        for cinema in orders:
            print(cinema)
            print(f'{" ":24s}\t|', end='')
            for price in orders[cinema]:
                print(f'{len(orders[cinema][price]):3d} ', end='|')
            print()

        if now.hour >= 23:
            # delete all at every 11pm
            for cinema in orders:
                for price in orders[cinema]:
                    for tid in orders[cinema][price]:
                        print(f'[删除]\t{cinema} {price} {self._remove(tid)}')
            return False
        else:
            ret = False
            for cinema in orders:
                for price in orders[cinema]:
                    if len(orders[cinema][price]) != 2:
                        need_purchase = self._purchase(links[cinema][price])
                        print(f'[抢票]\t{cinema} {price} {"抢票结束" if not need_purchase else "仍需抢票"}')
                        ret = ret or need_purchase
            return ret

    def _rest_tickets(self) -> Tuple[date, dict]:
        # return values
        act_date = date(2021, 1, 1)
        links = defaultdict(dict)
        for cinema in ticket_types:
            for price in ticket_types[cinema]:
                links[cinema][price] = None

        try:
            page, flag = 1, True
            while flag:
                r = requests.get(f'{INDEX}/page/{page}')
                html = etree.HTML(r.text)
                for item in html.xpath('//div[@class="jianzheng_remai_case"]'):
                    a = item.xpath('.//a[@class="jianzheng_remai_case_title"]')[0]
                    is_film, cinema, price = self._parse_title(a.xpath('text()')[0])
                    if is_film:
                        r = requests.get(a.xpath('@href')[0])
                        act = re.compile(r'\d{4}-\d{2}-\d{2}').search(r.text).group()
                        act = datetime.strptime(act, '%Y-%m-%d').date()
                        if act - act_date >= timedelta(0):
                            act_date = act
                            if len(item.xpath('.//i')) != 0:
                                links[cinema][price] = item.xpath('.//a[@class="jianzheng_remai_case_title"]/@href')[0]
                            else:
                                links[cinema][price] = None
                        else:
                            flag = False
                page += 1
        finally:
            return act_date, links

    @staticmethod
    def _parse_title(title: str) -> Tuple[bool, str, int]:
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

    def _get_orders(self, act_date: date) -> dict:
        orders = defaultdict(dict)
        for cinema in ticket_types:
            for price in ticket_types[cinema]:
                orders[cinema][price] = []

        try:
            page, flag = 1, True
            while flag:
                r = self._session.get(f'{ORDER}/page/{page}')
                html = etree.HTML(r.text)
                items = html.xpath('//div[@class="jianzheng_remai_case"]')
                flag = len(items) > 0
                for item in items:
                    is_film, cinema, price = self._parse_title(item.xpath('.//a/text()')[0])
                    # if order is about film ticket
                    if is_film:
                        time = item.xpath('.//div[@class="jianzheng_remai_case_detailp"]/text()')[0]
                        time = datetime.strptime(time[5:], '%Y-%m-%d %H:%M:%S').date()
                        # check activity time
                        if time - act_date == timedelta(0):
                            button = item.xpath('.//input')
                            if len(button) == 1:
                                orders[cinema][price].append(button[-1].xpath('@onclick')[0][5:-2])
                        else:
                            # wrong activity time, break
                            flag = False
                # next page
                page += 1
        finally:
            return orders

    def _purchase(self, url: str) -> bool:
        if not isinstance(url, str):
            return True
        data = {'activityid': '',
                'activityname': '',
                'idnumber': '',
                'realname': '',
                'type2': '',
                'current_url': url}
        try:
            r = self._session.get(url)
            html = etree.HTML(r.text)
            for item in html.xpath('//input[@type="text"]'):
                name = item.xpath('@name')[0]
                if name in data:
                    data[name] = item.xpath('@value')[0]
            while True:
                r = self._session.post(PURCHASE, data)
                if r.json()['message'] == '每人只能抢2票':
                    break
            return False
        except Exception as e:
            print(e)
            return True

    def _remove(self, tid: str) -> object:
        msg = {'1': '活动已过期', '2': '删除失败',
               '3': '删除成功', '200': '服务器错误'}
        try:
            r = self._session.post(REMOVE, data={'QzId': tid})
            code = r.text[1:-1]
            return msg[code] if code in msg else code
        except Exception as e:
            return e
