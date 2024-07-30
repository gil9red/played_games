#!/usr/bin/env python
# -*- coding: utf-8 -*-

__author__ = "ipetrash"


from io import StringIO
import json
import os
import time
import traceback
import sys

from urllib.request import urlopen
from urllib.parse import urljoin

from lxml import etree


try:
    from PyQt5.QtWidgets import *
    from PyQt5.QtCore import *
except:
    from PyQt4.QtGui import *
    from PyQt4.QtCore import *


from common import get_logger


logger = get_logger("played_games")


DEFAULT_URL = "https://gist.github.com/gil9red/2f80a34fb601cd685353"


def log_uncaught_exceptions(ex_cls, ex, tb):
    text = f"{ex_cls.__name__}: {ex}:\n"
    text += "".join(traceback.format_tb(tb))

    logger.error(text)
    QMessageBox.critical(None, "Error", text)
    quit()


sys.excepthook = log_uncaught_exceptions


def add_tree_widget_item_platform(platform):
    return QTreeWidgetItem([f"{platform.name} ({platform.count_games}):"])


def add_tree_widget_item_category(category):
    return QTreeWidgetItem(
        [f"{ENUM_CATEGORY_TITLE_DICT[category.kind]} ({category.count}):"]
    )


def add_tree_widget_item_game(game):
    return QTreeWidgetItem([game.name])


WINDOW_TITLE = "Played Games"
TREE_HEADER = "Games"
OTHER_GAME_TITLE = "Неопределенные игры"

CONFIG_FILE = "config"


from played_games_parser import Parser

ENUM_CATEGORY_TITLE_DICT = {
    Parser.CategoryEnum.FINISHED_GAME: "Пройденные",
    Parser.CategoryEnum.NOT_FINISHED_GAME: "Не закончено прохождение",
    Parser.CategoryEnum.FINISHED_WATCHED: "Просмотренные",
    Parser.CategoryEnum.NOT_FINISHED_WATCHED: "Не закончен просмотр",
}

# Последовательность добавления категорий в узел платформы
SEQ_ADDED_CATEGORIES = [
    Parser.CategoryEnum.FINISHED_GAME,
    Parser.CategoryEnum.NOT_FINISHED_GAME,
    Parser.CategoryEnum.FINISHED_WATCHED,
    Parser.CategoryEnum.NOT_FINISHED_WATCHED,
]


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle(WINDOW_TITLE)

        self.tree_games = QTreeWidget()

        self.line_edit_url = QLineEdit(DEFAULT_URL)
        self.button_refresh_by_url = QPushButton("&Refresh")
        self.button_refresh_by_url.clicked.connect(self.refresh_by_url)

        self.dock_widget_settings = QDockWidget("Settings")
        self.dock_widget_settings.setObjectName(self.dock_widget_settings.windowTitle())
        layout = QFormLayout()
        self.TEST_USING_FILE_GAMES = QCheckBox()
        self.PARSE_GAME_NAME_ON_SEQUENCE = QCheckBox()
        self.SORT_GAME = QCheckBox()
        self.SORT_REVERSE = QCheckBox()
        label_SORT_REVERSE = QLabel("SORT_REVERSE")
        self.SORT_GAME.toggled.connect(self.SORT_REVERSE.setVisible)
        self.SORT_GAME.toggled.connect(label_SORT_REVERSE.setVisible)

        self.TEST_USING_FILE_GAMES.setChecked(True)
        self.PARSE_GAME_NAME_ON_SEQUENCE.setChecked(True)
        self.SORT_GAME.setChecked(False)
        self.SORT_REVERSE.setChecked(False)

        self.SORT_REVERSE.setVisible(self.SORT_GAME.isChecked())
        label_SORT_REVERSE.setVisible(self.SORT_GAME.isChecked())

        layout.addRow("TEST_USING_FILE_GAMES", self.TEST_USING_FILE_GAMES)
        layout.addRow("PARSE_GAME_NAME_ON_SEQUENCE", self.PARSE_GAME_NAME_ON_SEQUENCE)
        layout.addRow("SORT_GAME", self.SORT_GAME)
        layout.addRow(label_SORT_REVERSE, self.SORT_REVERSE)

        # TODO: может в checkbox'ах показывать количество игр данных категорий
        self.check_FINISHED_GAME = QCheckBox(Parser.CategoryEnum.FINISHED_GAME.name)
        self.check_NOT_FINISHED_GAME = QCheckBox(
            Parser.CategoryEnum.NOT_FINISHED_GAME.name
        )
        self.check_FINISHED_WATCHED = QCheckBox(
            Parser.CategoryEnum.FINISHED_WATCHED.name
        )
        self.check_NOT_FINISHED_WATCHED = QCheckBox(
            Parser.CategoryEnum.NOT_FINISHED_WATCHED.name
        )
        self.check_OTHER = QCheckBox(Parser.CategoryEnum.OTHER.name)

        self.check_FINISHED_GAME.setChecked(True)
        self.check_NOT_FINISHED_GAME.setChecked(True)
        self.check_FINISHED_WATCHED.setChecked(True)
        self.check_NOT_FINISHED_WATCHED.setChecked(True)
        self.check_OTHER.setChecked(True)

        show_only_layout = QVBoxLayout()
        show_only_layout.addWidget(self.check_FINISHED_GAME)
        show_only_layout.addWidget(self.check_NOT_FINISHED_GAME)
        show_only_layout.addWidget(self.check_FINISHED_WATCHED)
        show_only_layout.addWidget(self.check_NOT_FINISHED_WATCHED)
        show_only_layout.addWidget(self.check_OTHER)

        show_only_group = QGroupBox("Show categories:")
        show_only_group.setLayout(show_only_layout)
        layout.addRow(show_only_group)

        widget = QWidget()
        widget.setLayout(layout)

        self.dock_widget_settings.setWidget(widget)
        self.dock_widget_settings.hide()
        self.addDockWidget(Qt.RightDockWidgetArea, self.dock_widget_settings)

        general_tool_bar = self.addToolBar("General")
        general_tool_bar.setObjectName(general_tool_bar.windowTitle())
        general_tool_bar.addAction(self.dock_widget_settings.toggleViewAction())

        layout = QHBoxLayout()
        layout.addWidget(self.line_edit_url)
        layout.addWidget(self.button_refresh_by_url)

        self.line_edit_filter = QLineEdit()
        self.line_edit_filter.setToolTip("Wildcard Filter")
        self.line_edit_filter.textEdited.connect(self.load_tree)

        filter_layout = QHBoxLayout()
        filter_layout.addWidget(QLabel("Filter:"))
        filter_layout.addWidget(self.line_edit_filter)

        main_layout = QVBoxLayout()
        main_layout.addLayout(layout)
        main_layout.addLayout(filter_layout)
        main_layout.addWidget(self.tree_games)

        central_widget = QWidget()
        central_widget.setLayout(main_layout)

        self.setCentralWidget(central_widget)

        self.parser = Parser()
        self.parse_content = None

        self.update_header_tree_and_window_title()

        self.read_settings()

    def refresh_by_url(self):
        logger.debug(
            f"TEST_USING_FILE_GAMES = {self.TEST_USING_FILE_GAMES.isChecked()}."
        )

        if self.TEST_USING_FILE_GAMES.isChecked():
            # TODO: для тестирования интерфейса
            test_file_name = "gistfile1.txt"

            logger.debug(f"Open and read {test_file_name} start.")
            with open(test_file_name, "r", encoding="utf8") as f:
                content_file = f.read()
            logger.debug(
                f"Finish open and read. Content file length = {len(content_file)}."
            )
        else:
            url = self.line_edit_url.text()

            # Проверяем, что если прописан путь до файла на компе, то его открываем, иначе считаем ссылкой и качаем
            if os.path.exists(url):
                with open(url, encoding="utf-8") as f:
                    content_file = f.read()

            else:
                # Теперь нужно получить url файла с последней ревизией
                logger.debug("Get url file last revision start.")
                t = time.perf_counter()

                try:
                    with urlopen(url) as f:
                        context = f.read().decode()

                        parser = etree.HTMLParser()
                        tree = etree.parse(StringIO(context), parser)

                        # Ищем первый файл с кнопкой Raw
                        rel_url = tree.xpath(
                            '//*[contains(@class, "file-actions")]/a/@href'
                        )[0]
                        logger.debug(f"Relative url = {rel_url}.")

                        url = urljoin(url, str(rel_url))
                        logger.debug(f"Full url = {url}.")

                    logger.debug(
                        f"Get url file last revision finish. Elapsed time: {time.perf_counter() - t:.3f} sec."
                    )

                    with urlopen(url) as f:
                        content_file = f.read().decode()

                except Exception as e:
                    text = "".join(traceback.format_exc())

                    logger.error(text)
                    QMessageBox.critical(None, "Error", text)

                    content_file = ""

        logger.debug("Read last content finish.")

        self.parse_content = content_file
        self.load_tree()

    def load_tree(self):
        logger.debug("Start build tree.")

        show_only_categories = list()
        if self.check_FINISHED_GAME.isChecked():
            show_only_categories.append(Parser.CategoryEnum.FINISHED_GAME)

        if self.check_NOT_FINISHED_GAME.isChecked():
            show_only_categories.append(Parser.CategoryEnum.NOT_FINISHED_GAME)

        if self.check_FINISHED_WATCHED.isChecked():
            show_only_categories.append(Parser.CategoryEnum.FINISHED_WATCHED)

        if self.check_NOT_FINISHED_WATCHED.isChecked():
            show_only_categories.append(Parser.CategoryEnum.NOT_FINISHED_WATCHED)

        if self.check_OTHER.isChecked():
            show_only_categories.append(Parser.CategoryEnum.OTHER)

        self.parser.parse(
            self.parse_content,
            self.line_edit_filter.text(),
            self.PARSE_GAME_NAME_ON_SEQUENCE.isChecked(),
            self.SORT_GAME.isChecked(),
            self.SORT_REVERSE.isChecked(),
            show_only_categories,
        )
        self.tree_games.clear()

        for k, v in self.parser.sorted_platforms:
            platform_item = add_tree_widget_item_platform(v)
            self.tree_games.addTopLevelItem(platform_item)

            for kind in SEQ_ADDED_CATEGORIES:
                if kind not in v.categories:
                    continue

                category = v.categories[kind]
                category_item = add_tree_widget_item_category(category)
                platform_item.addChild(category_item)

                for game in category:
                    game_item = add_tree_widget_item_game(game)
                    category_item.addChild(game_item)

        if self.parser.other.count_games > 0:
            other_item = QTreeWidgetItem(
                [f"{OTHER_GAME_TITLE} ({self.parser.other.count_games}):"]
            )
            self.tree_games.addTopLevelItem(other_item)

            for k, v in self.parser.other.platforms.items():
                platform_item = add_tree_widget_item_platform(v)
                other_item.addChild(platform_item)

                for category in v.categories.values():
                    for game in category:
                        game_item = add_tree_widget_item_game(game)
                        platform_item.addChild(game_item)

        self.tree_games.expandAll()
        self.update_header_tree_and_window_title()

    def update_header_tree_and_window_title(self):
        # Указываем в заголовке общее количество игр и при фильтр, количество игр, оставшихся после фильтрации
        self.tree_games.setHeaderLabel(f"{TREE_HEADER} ({self.parser.count_games})")

        # Обновление заголовка окна
        self.setWindowTitle(
            f"{WINDOW_TITLE}. Platforms: {self.parser.count_platforms}. Games: {self.parser.count_games}"
        )

    def read_settings(self):
        logger.debug(f"Start read_settings. CONFIG_FILE={CONFIG_FILE}.")

        try:
            with open(CONFIG_FILE, encoding="utf-8") as f:
                settings = json.load(f)

                self.TEST_USING_FILE_GAMES.setChecked(settings["TEST_USING_FILE_GAMES"])
                self.PARSE_GAME_NAME_ON_SEQUENCE.setChecked(
                    settings["PARSE_GAME_NAME_ON_SEQUENCE"]
                )
                self.SORT_GAME.setChecked(settings["SORT_GAME"])
                self.SORT_REVERSE.setChecked(settings["SORT_REVERSE"])

                self.check_FINISHED_GAME.setChecked(settings["check_FINISHED_GAME"])
                self.check_NOT_FINISHED_GAME.setChecked(
                    settings["check_NOT_FINISHED_GAME"]
                )
                self.check_FINISHED_WATCHED.setChecked(
                    settings["check_FINISHED_WATCHED"]
                )
                self.check_NOT_FINISHED_WATCHED.setChecked(
                    settings["check_NOT_FINISHED_WATCHED"]
                )
                self.check_OTHER.setChecked(settings["check_OTHER"])

                base64_state = settings["MainWindow_State"]
                state = QByteArray.fromBase64(base64_state.encode())
                self.restoreState(state)

                base64_geometry = settings["MainWindow_Geometry"]
                geometry = QByteArray.fromBase64(base64_geometry.encode())
                self.restoreGeometry(geometry)

        except Exception as e:
            logger.exception(e)
            logger.debug("Заполняю значения по умолчанию.")

            self.TEST_USING_FILE_GAMES.setChecked(True)
            self.PARSE_GAME_NAME_ON_SEQUENCE.setChecked(True)
            self.SORT_GAME.setChecked(False)
            self.SORT_REVERSE.setChecked(False)

            self.check_FINISHED_GAME.setChecked(True)
            self.check_NOT_FINISHED_GAME.setChecked(True)
            self.check_FINISHED_WATCHED.setChecked(True)
            self.check_NOT_FINISHED_WATCHED.setChecked(True)
            self.check_OTHER.setChecked(True)

        logger.debug("Finish read_settings.")

    def write_settings(self):
        logger.debug(f"Start write_settings. CONFIG_FILE={CONFIG_FILE}.")
        logger.debug("Build dict.")

        settings = {
            "TEST_USING_FILE_GAMES": self.TEST_USING_FILE_GAMES.isChecked(),
            "PARSE_GAME_NAME_ON_SEQUENCE": self.PARSE_GAME_NAME_ON_SEQUENCE.isChecked(),
            "SORT_GAME": self.SORT_GAME.isChecked(),
            "SORT_REVERSE": self.SORT_REVERSE.isChecked(),
            "check_FINISHED_GAME": self.check_FINISHED_GAME.isChecked(),
            "check_NOT_FINISHED_GAME": self.check_NOT_FINISHED_GAME.isChecked(),
            "check_FINISHED_WATCHED": self.check_FINISHED_WATCHED.isChecked(),
            "check_NOT_FINISHED_WATCHED": self.check_NOT_FINISHED_WATCHED.isChecked(),
            "check_OTHER": self.check_OTHER.isChecked(),
            "MainWindow_State": bytes(self.saveState().toBase64()).decode(),
            "MainWindow_Geometry": bytes(self.saveGeometry().toBase64()).decode(),
        }

        logger.debug("Write config.")

        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            str_json_obj = json.dumps(settings, sort_keys=True, indent=4)
            f.write(str_json_obj)

        logger.debug("Finish write_settings.")

    def closeEvent(self, event):
        self.write_settings()
        quit()


if __name__ == "__main__":
    app = QApplication(sys.argv)

    mw = MainWindow()
    mw.show()
    mw.refresh_by_url()

    sys.exit(app.exec_())
