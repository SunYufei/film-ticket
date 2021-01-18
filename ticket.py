import re
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from typing import List, Tuple

import requests
from lxml import etree

from utils import log


@dataclass
class TicketInfo:
    price: int
    link: str = ''
    rest: bool = True
    tid: List[str] = field(default=[])
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
        self.my_orders = {
            '利群华艺国际影院金鼎广场店': (TicketInfo(price=8),),
            '中影国际影城大拇指广场店': (TicketInfo(price=8),)
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

    def rest_tickets(self) -> date:
        """
        update rest tickets
        """
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
                            for info in self.my_orders[cinema]:
                                if info.price == price:
                                    info.link = item.xpath('.//a[@class="jianzheng_remai_case_title"]/@href')[0]
                                    info.rest = len(item.xpath('.//i')) != 0
                                    break
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
        for cinema in self.my_orders:
            for info in self.my_orders[cinema]:
                info.tid.clear()
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
                            if len(button) == 1:
                                for info in self.my_orders[cinema]:
                                    if info.price == price:
                                        info.tid.append(button[-1].xpath('@onclick')[0][5:-2])
                                        if len(info.tid) == 2:
                                            info.need_purchase = False
                                        break
                        else:
                            # wrong activity time, break
                            do = False
                # next page
                page += 1
        except Exception as e:
            log('我的订单', e)

    def purchase(self, url: str) -> bool:
        """
        purchase, need login
        :param url: purchase url
        :return: need purchase
        """
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
            return r.json()['message'] != '每人只能抢2票'
        except Exception as e:
            log('抢票', e)
            return True

    def remove_all(self) -> None:
        """
        remove all tickets
        """
        msg = {
            '1': '活动已过期',
            '2': '删除失败',
            '3': '删除成功',
            '200': '服务器错误'
        }
        try:
            for cinema in self.my_orders:
                for info in self.my_orders[cinema]:
                    for tid in info.tid:
                        r = self._session.post(self._remove, data={'QzId': tid})
                        code = r.text[1:-1]
                        log('删除', f'{cinema} {info.price} {msg[code] if code in msg else code}')
        except Exception as e:
            log('删除', e)

    def max_type_count(self) -> int:
        count = 0
        for cinema in self.my_orders:
            count += len(self.my_orders[cinema])
        return count

    def show_orders(self) -> None:
        print(f'{"[我的订单]":24s}\t|', end='')
        for cinema in self.my_orders:
            for info in self.my_orders[cinema]:
                print(f'{info.price:3d} ', end='|')
            break
        print()

        for cinema in self.my_orders:
            print(cinema)
            print(f'{" ":24s}\t|', end='')
            for info in self.my_orders[cinema]:
                print(f'{len(info.tid):3d} ', end='|')
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
