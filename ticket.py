import re
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from typing import List, Tuple

import requests
from lxml import etree

from utils import log


@dataclass
class TicketInfo:
    link: str = ''
    can_purchase: bool = False
    ticket_ids: List[str] = field(default_factory=list)
    ticket_count: int = 0
    need_purchase: bool = True


class TicketTools:
    def __init__(self, username: str, password: str):
        # urls
        self._base = 'http://city.qingdaonews.com/qingdao/laoshanculture'
        self._index = f'{self._base}/index'
        self._login = f'{self._base}/loginsub'
        self._order = f'{self._base}/myorder'
        self._remove = f'{self._base}/delorder'
        self._purchase = f'{self._base}/getticket'

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
        """
        :return: login status
        """
        try:
            r = self._session.post(self._login, data={
                'IdNumber': self._username,
                'PassWord': self._password
            })
            return r.json()['code'] == 0
        except Exception as e:
            log('登录', e)
            return False

    def update_links(self) -> date:
        act_date = date(2020, 1, 1)
        try:
            page, do = 1, True
            while do:
                r = requests.get(f'{self._index}/page/{page}')
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
                            info = self._my_orders[cinema][price]
                            info.link = item.xpath('.//a[@class="jianzheng_remai_case_title"]/@href')[0]
                            info.can_purchase = len(item.xpath('.//i')) != 0
                        else:
                            # wrong activity time, break
                            do = False
                # next page
                page += 1
        finally:
            return act_date

    def update_orders(self, act_date: date) -> None:
        """
        get orders, need login
        :param act_date: activity date
        """
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
                r = self._session.get(f'{self._order}/page/{page}')
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
                        info.need_purchase = info.ticket_count >= 2
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
            r = self._session.post(self._purchase, data)
            msg = r.json()['message']
            log('抢票', msg)
            return '抢票成功' in msg
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
                        r = self._session.post(self._remove, data={'QzId': tid})
                        code = r.text[1:-1]
                        log('删除', f'{cinema} {price} {msg[code] if code in msg else code}')
        except Exception as e:
            log('删除', e)

    def show_orders(self) -> None:
        print(f'{"[我的订单]":24s}\t|', end='')
        for cinema in self._my_orders:
            for price in self._my_orders[cinema]:
                print(f'{price:3d} ', end='|')
            break
        print()

        for cinema in self._my_orders:
            print(cinema)
            print(f'{" ":24s}\t|', end='')
            for price in self._my_orders[cinema]:
                print(f'{len(self._my_orders[cinema][price].ticket_ids):3d} ', end='|')
            print()

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
