from copy import deepcopy

from PyQt5.QtWidgets import *

from v1.utils import cinema_table


class CinemaWidget(QWidget):
    def __init__(self):
        super().__init__()

        layout = QGridLayout()
        self.setLayout(layout)

        layout.addWidget(QLabel('利群华艺国际影院金鼎广场店：'), 1, 0)
        layout.addWidget(QLabel('中影国际影城大拇指广场店：'), 2, 0)
        layout.addWidget(QLabel('5元'), 0, 1)
        layout.addWidget(QLabel('8元'), 0, 2)
        layout.addWidget(QLabel('11元'), 0, 3)

        self.labels = deepcopy(cinema_table)

        for cinema in self.labels:
            for price in self.labels[cinema]:
                self.labels[cinema][price] = QLabel()

        for i, cinema in enumerate(self.labels):
            for j, price in enumerate(self.labels[cinema]):
                layout.addWidget(self.labels[cinema][price], i + 1, j + 1)

    def fresh(self, content: dict):
        for cinema in content:
            for price in content[cinema]:
                if isinstance(content[cinema][price], bool):
                    self.labels[cinema][price].setText('√' if content[cinema][price] else '×')
                elif isinstance(content[cinema][price], str):
                    self.labels[cinema][price].setText(content[cinema][price])
