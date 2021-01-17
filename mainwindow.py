import datetime
from copy import deepcopy
from threading import Thread

from PyQt5.QtCore import *
from PyQt5.QtWidgets import *

from v1.cinema_widget import CinemaWidget
from v1.utils import login, rest_tickets, get_orders, remove, cinema_table, purchase

link = {}
order = {}


class MainWindow(QWidget):
    msg_signal = pyqtSignal(str)

    def show_message(self, msg: str):
        QMessageBox.information(self, '提示信息', msg, QMessageBox.Ok, QMessageBox.Ok)

    order_signal = pyqtSignal()

    def get_my_orders(self):
        def fun(deadline: str, order_widget: CinemaWidget):
            global order

            deadline = datetime.datetime.strptime(deadline, '%Y-%m-%d')
            order = get_orders(deadline)

            content = deepcopy(order)
            for cinema in content:
                for price in content[cinema]:
                    content[cinema][price] = str(len(content[cinema][price]))
            order_widget.fresh(content)

        Thread(target=fun, args=(self.edit_deadline.text(), self.orders)).start()

    purchase_signal = pyqtSignal()

    def purchase_ticket(self):
        def fun(msg_signal: pyqtSignal, order_signal: pyqtSignal):
            for c in link:
                for p in link[c]:
                    if link[c][p] is not None:
                        code, msg = purchase(link[c][p])
                        if code == '1':
                            msg_signal.emit(msg)
                            return
                        # successful
                        elif code == '0':
                            msg_signal.emit('抢到一张{0}的{1}元观影票'.format(c, p))
                            order_signal.emit()

        count = 0
        for cinema in order:
            for price in order[cinema]:
                count = count + len(order[cinema][price])
        if count < len(cinema_table) * 2:
            Thread(target=fun, args=(self.msg_signal, self.order_signal)).start()

    def __init__(self):
        super().__init__()

        # window
        self.setWindowTitle('文化崂山抢票')
        self.setWindowFlags(Qt.WindowMinimizeButtonHint | Qt.WindowCloseButtonHint)

        # signal
        self.msg_signal.connect(self.show_message)
        self.order_signal.connect(self.get_my_orders)
        self.purchase_signal.connect(self.purchase_ticket)

        # main layout
        layout = QVBoxLayout()
        layout.setSizeConstraint(QLayout.SetFixedSize)
        self.setLayout(layout)

        # group monitor
        group_monitor = QGroupBox('余票监控')
        layout.addWidget(group_monitor)

        v_box_monitor = QVBoxLayout()
        group_monitor.setLayout(v_box_monitor)

        form_monitor = QFormLayout()
        v_box_monitor.addLayout(form_monitor)

        self.edit_deadline = QLineEdit()
        self.edit_deadline.setReadOnly(True)
        self.edit_deadline.setAlignment(Qt.AlignCenter)
        form_monitor.addRow('截止日期：', self.edit_deadline)

        self.rest_widget = CinemaWidget()
        v_box_monitor.addWidget(self.rest_widget)

        timer = QTimer(self)
        timer.timeout.connect(self.timer_rest_ticket_timeout)
        timer.start(10000)
        self.timer_rest_ticket_timeout()

        # group login
        group_login = QGroupBox()
        layout.addWidget(group_login)

        v_box_login = QVBoxLayout()
        group_login.setLayout(v_box_login)

        form_login = QFormLayout()
        v_box_login.addLayout(form_login)

        self.edit_username = QLineEdit()
        # self.edit_username.setEchoMode(QLineEdit.Password)
        form_login.addRow('用户名：', self.edit_username)

        self.edit_password = QLineEdit()
        self.edit_password.setEchoMode(QLineEdit.Password)
        form_login.addRow('密码：', self.edit_password)

        self.btn_login = QPushButton('登录')
        self.btn_login.clicked.connect(self.btn_login_clicked)
        v_box_login.addWidget(self.btn_login)

        # group order
        self.group_order = QGroupBox('我的订单')
        self.group_order.setVisible(False)
        layout.addWidget(self.group_order)

        v_box_order = QVBoxLayout()
        self.group_order.setLayout(v_box_order)

        self.orders = CinemaWidget()
        v_box_order.addWidget(self.orders)

        self.btn_remove = QPushButton('全部删除')
        self.btn_remove.clicked.connect(self.btn_remove_clicked)
        v_box_order.addWidget(self.btn_remove)

    def btn_login_clicked(self):
        if self.btn_login.text() == '登录':
            code, msg = login(self.edit_username.text(), self.edit_password.text())
            self.msg_signal.emit(msg)

            if code:
                self.btn_login.setText('切换用户')
                self.edit_username.setEnabled(False)
                self.edit_password.setEnabled(False)
                self.group_order.setVisible(True)
                # get orders
                self.order_signal.emit()
                return

        self.btn_login.setText('登录')
        self.edit_username.setEnabled(True)
        self.edit_password.setEnabled(True)
        self.edit_username.setText('')
        self.edit_password.setText('')
        self.group_order.setVisible(False)

    def timer_rest_ticket_timeout(self):
        def fun(edit_deadline: QLineEdit, rest_widget: CinemaWidget,
                purchase_signal: pyqtSignal):
            global link

            deadline, link = rest_tickets()
            edit_deadline.setText(deadline.strftime('%Y-%m-%d'))
            content = deepcopy(link)
            for cinema in content:
                for price in content[cinema]:
                    content[cinema][price] = (content[cinema][price] is not None)
            rest_widget.fresh(content)
            purchase_signal.emit()

        Thread(target=fun, args=(self.edit_deadline, self.rest_widget,
                                 self.purchase_signal)).start()

    def btn_remove_clicked(self):
        def fun(order_signal: pyqtSignal):
            global order

            for cinema in order:
                for price in order[cinema]:
                    for param in order[cinema][price]:
                        code, _ = remove(param)
                        if code:
                            order[cinema][price].remove(param)

            order_signal.emit()

        Thread(target=fun, args=(self.order_signal,)).start()
