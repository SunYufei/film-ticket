import re
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from typing import List, Tuple

import requests
from lxml import etree

from utils import log

# url
BASE = 'http://city.qingdaonews.com/qingdao/laoshanculture'
INDEX = f'{BASE}/index'
LOGIN = f'{BASE}/loginsub'
ORDER = f'{BASE}/myorder'
REMOVE = f'{BASE}/delorder'
PURCHASE = f'{BASE}/getticket'

# pattern
title_ptn = re.compile(r'<a href="(.*?)".*?>.*?(\d)元观影活动\((.*?)\)</a>')
date_ptn = re.compile(r'\d{4}-\d{2}-\d{2}')
no_ticket_ptn = re.compile(r'已抢光')
order_ptn = re.compile(r'')


@dataclass
class TicketInfo:
    link: str = ''
    can_purchase: bool = False
    ticket_ids: List[str] = field(default_factory=list)
    ticket_count: int = 0
    need_purchase: bool = True


class TicketTools:
    def __init__(self, username: str, password: str):
        # my orders
        self._my_orders = {
            '利群华艺国际影院金鼎广场店': {8: TicketInfo()},
            '中影国际影城大拇指广场店': {8: TicketInfo()}
        }

        # username, password
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
            log('登录', e)
            return False

    def update_links(self) -> date:
        act_date = date(2021, 1, 1)
        try:
            page, do = 1, True
            while do:
                r = requests.get(f'{INDEX}/page/{page}')
                for link, price, cinema in title_ptn.findall(r.text):
                    r = requests.get(link)
                    act = date_ptn.search(r.text).group()
                    act = datetime.strptime(act, '%Y-%m-%d').date()
                    if act - act_date >= timedelta(0):
                        act_date = act
                        info = self._my_orders[cinema][price]
                        info.link = link
                        info.can_purchase = len(no_ticket_ptn.findall(r.text)) == 0
                    else:
                        # wrong activity time, break
                        do = False
                # next page
                page += 1
        finally:
            return act_date

    def update_orders(self, act_date: date) -> None:
        # clear old data
        for cinema in self._my_orders:
            for price in self._my_orders[cinema]:
                info = self._my_orders[cinema][price]
                info.ticket_ids.clear()
                info.ticket_count = 0
                info.need_purchase = True

        # update new data
        try:
            page, do = 1, True
            while do:
                r = self._session.get(f'{ORDER}/page/{page}')
                html = etree.HTML(r.text)
                items = html.xpath('//div[@class="jianzheng_remai_case"]')
                do = len(items) > 0
                for item in items:
                    is_film, cinema, price = self._parse_title(item.xpath('.//a/text()')[0])
                    # if order is about film ticket
                    if is_film:
                        time = item.xpath('.//div[@class="jianzheng_remai_case_detailp"]/text()')[0]
                        time = datetime.strptime(time[5:], '%Y-%m-%d %H:%M:%S').date()
                        # check activity time
                        if time - act_date == timedelta(0):
                            button = item.xpath('.//input')
                            info = self._my_orders[cinema][price]
                            info.ticket_count += 1
                            if info.ticket_count >= 2:
                                info.need_purchase = False
                            if len(button) == 1:
                                info.ticket_ids.append(button[-1].xpath('@onclick')[0][5:-2])
                        else:
                            # wrong activity time, break
                            do = False
                # next page
                page += 1
        except Exception as e:
            log('我的订单', e)

    def purchase_all(self) -> bool:
        ret = False
        for cinema in self._my_orders:
            for price in self._my_orders[cinema]:
                info = self._my_orders[cinema][price]
                while info.need_purchase and info.can_purchase:
                    if self._purchase_one(info.link):
                        info.ticket_count += 1
                    info.need_purchase = info.ticket_count < 2
                ret = ret or info.need_purchase
        return ret

    def _purchase_one(self, url: str) -> bool:
        data = {
            'activityid': '',
            'activityname': '',
            'idnumber': '',
            'realname': '',
            'type2': '',
            'current_url': url
        }
        try:
            r = self._session.get(url)
            html = etree.HTML(r.text)
            for item in html.xpath('//input[@type="text"]'):
                name = item.xpath('@name')[0]
                if name in data:
                    data[name] = item.xpath('@value')[0]
            r = self._session.post(PURCHASE, data)
            msg = r.json()['message']
            log('抢票', msg)
            return '抢票成功' in msg or '只能' in msg
        except Exception as e:
            log('抢票', e)
            return False

    def remove_all(self) -> None:
        msg = {
            '1': '活动已过期',
            '2': '删除失败',
            '3': '删除成功',
            '200': '服务器错误'
        }
        try:
            for cinema in self._my_orders:
                for price in self._my_orders[cinema]:
                    for tid in self._my_orders[cinema][price].ticket_ids:
                        r = self._session.post(REMOVE, data={'QzId': tid})
                        code = r.text[1:-1]
                        log('删除', f'{cinema} {price} {msg[code] if code in msg else code}')
        except Exception as e:
            log('删除', e)

    def show_orders(self) -> None:
        log('我的订单', '')
        print('|'.join([' ' * 26, '票价', '已抢', '需抢', '可抢']))
        for cinema in self._my_orders:
            content = [cinema + ' ' * (28 - len(cinema) * 2)]
            for price in self._my_orders[cinema]:
                content.append(f'{price:3d} ')
                info = self._my_orders[cinema][price]
                content.append(f'{len(info.ticket_ids):3d} ')
                content.append(f' {"√" if info.need_purchase else "×"} ')
                content.append(f' {"√" if info.can_purchase else "×"} ')
                print('|'.join(content))

    @staticmethod
    def _parse_title(title: str) -> Tuple[bool, str, int]:
        """
        parse and check title
        :param title: title str
        :return: is_film, cinema, price
        """
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
