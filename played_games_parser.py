#!/usr/bin/env python
# -*- coding: utf-8 -*-

__author__ = 'ipetrash'


from collections import defaultdict
from enum import Enum
import fnmatch
import time

from common import get_logger
logger = get_logger('played_games_parser')

# Регулярка вытаскивает выражения вида: 1, 2, 3 или 1-3, или римские цифры: III, IV
import re
PARSE_GAME_NAME_PATTERN = re.compile(r'(\d+(, ?\d+)+)|(\d+ *?- *?\d+)|([MDCLXVI]+(, ?[MDCLXVI]+)+)',
                                     flags=re.IGNORECASE)


def parse_game_name(game_name):
    """
    Функция принимает название игры и пытается разобрать его, после возвращает список названий.
    Т.к. в названии игры может находиться указание ее частей, то функция разберет их.

    Пример:
        "Resident Evil 4, 5, 6" станет:
            ["Resident Evil 4", "Resident Evil 5", "Resident Evil 6"]

        "Resident Evil 1-3" станет:
            ["Resident Evil", "Resident Evil 2", "Resident Evil 3"]

    """

    match = PARSE_GAME_NAME_PATTERN.search(game_name)
    if match is None:
        return [game_name]

    seq_str = match.group(0)

    # "Resident Evil 4, 5, 6" -> "Resident Evil"
    # For not valid "Trollface Quest 1-7-8" -> "Trollface Quest"
    index = game_name.index(seq_str)
    base_name = game_name[:index].strip()

    seq_str = seq_str.replace(' ', '')

    if ',' in seq_str:
        # '1,2,3' -> ['1', '2', '3']
        seq = seq_str.split(',')

    elif '-' in seq_str:
        seq = seq_str.split('-')

        # ['1', '7'] -> [1, 7]
        seq = list(map(int, seq))

        # [1, 7] -> ['1', '2', '3', '4', '5', '6', '7']
        seq = list(map(str, range(seq[0], seq[1] + 1)))

    else:
        logger.warning('Unknown seq str = "{}".'.format(seq_str))
        return [game_name]

    # Сразу проверяем номер игры в серии и если она первая, то не добавляем в названии ее номер
    return [base_name if num == '1' else base_name + " " + num for num in seq]


class Parser:
    """Класс парсера. Содержит словарь платформ и объект неопределенных игр."""

    class CategoryEnum(Enum):
        """Перечисление видов категории."""

        # Четыре ниже используется для идентификации игр и платформ
        # OTHER -- только для идентифакации игр, т.к. у неопределенных игр нет категорий
        FINISHED_GAME = 0
        NOT_FINISHED_GAME = 1
        FINISHED_WATCHED = 2
        NOT_FINISHED_WATCHED = 3
        OTHER = 4

        def __str__(self):
            return '{}'.format(self.name)

        def __repr__(self):
            return self.__str__()

    class Game:
        """Класс игры. Содержит название игры и категорию, в которую игра входит."""

        def __init__(self, name=None, category=None):
            self.name = name
            self.category = category

        @property
        def category_kind(self):
            return self.category.kind if self.category is not None else None

        def __str__(self):
            return 'Game "{}" ({})'.format(self.name, self.category_kind)

        def __repr__(self):
            return self.__str__()

    class Category:
        """Класс категории. Содержит список игр, входящих в данную категорию.
        Итерируемый класс, в цикле возвращает игры.

        """

        def __init__(self, kind=None, platform=None):
            self.kind = kind
            self.platform = platform

        @property
        def game_list(self):
            return self.platform.get_game_list(self.kind)

        def sort_game_list(self, key=lambda x: x.name, reverse=False):
            self.game_list.sort(key=key, reverse=reverse)

        @property
        def count(self):
            """Свойство возвращает количество игр в категории."""

            return len(self.game_list)

        def add(self, name):
            self.platform.add_game(name, self)

        def __iter__(self):
            return self.game_list.__iter__()

        def next(self):
            return self.game_list.next()

        def __str__(self):
            return 'Category {} ({})'.format(self.kind, self.count)

        def __repr__(self):
            return self.__str__()

    class Platform:
        """Класс платформы. Содержит название, словарь категорий платформы и список
        всех игр платформы.

        """

        def __init__(self, name=None):
            self.name = name
            self.categories = dict()

            # Ключом словаря будет вид категории, а значением список игр
            self._game_list_by_category_kind = defaultdict(list)

            # Используется для проверки дублирующихся в категории игр
            # Ключом словаря будет кортеж имени игры и категории, а значением объект игры -- Parser.Game
            self._game_name_dict = dict()

        def get_game_list(self, category_kind):
            return self._game_list_by_category_kind[category_kind]

        def add_game(self, game_name, category):
            """Добавление игры в указанную категорию."""

            # Если игра с такой категории в списке всех игр уже есть
            if (game_name, category.kind) in self._game_name_dict:
                logger.warn('Предотвращено добавление дубликата игры "{}" в категорию {}.'.format(
                    game_name, category.kind))
                return

            game = Parser.Game(game_name, category)

            self.get_game_list(category.kind).append(game)
            self._game_name_dict[(game_name, category.kind)] = game

        @property
        def count_games(self):
            return len(self.game_list)

        @property
        def count_categories(self):
            return len(self.categories)

        @property
        def game_list(self):
            """Нередактируемый список всех игр на платформе."""

            return frozenset(self._game_name_dict.values())

        def get(self, kind_category):
            """Получение категории по перечислению. Если категории нет, она будет создана."""

            if kind_category not in self.categories:
                category = Parser.Category(kind_category, self)
                self.categories[kind_category] = category
                return category

            return self.categories[kind_category]

        def __str__(self):
            return 'Platform {}. Games: {}. Categories: {}.'.format(self.name, self.count_games, self.count_categories)

        def __repr__(self):
            return self.__str__()

    class Other:
        """Класс неопределенных игр. Содержит словарь платформ."""

        def __init__(self):
            self.platforms = dict()

        @property
        def count_games(self):
            return sum([p.count_games for p in self.platforms.values()])

        @property
        def count_platforms(self):
            return len(self.platforms)

        def add_game(self, name_platform, name_game):
            # Получаем платформу, создаем категорию и добавляем в нее игру
            self.get(name_platform).get(Parser.CategoryEnum.OTHER).add(name_game)

        def get(self, name_platform):
            """Функция возращает ссылку на объект Платформа. Если платформа с таким именем
            не существует, она будет будет создана.

            """

            if name_platform not in self.platforms:
                platform = Parser.Platform(name_platform)
                self.platforms[name_platform] = platform
                return platform

            return self.platforms[name_platform]

        def __str__(self):
            return 'Other. Platforms: {}. Games: {}. '.format(self.count_platforms, self.count_categories)

        def __repr__(self):
            return self.__str__()

    ALL_ATTRIBUTES_GAMES = ' -@'

    def __init__(self):
        self.platforms = dict()
        self.other = Parser.Other()

    @property
    def games(self):
        """Получение списка всех найденных игр."""

        all_games = list()
        for p in list(self.platforms.values()) + list(self.other.platforms.values()):
            all_games.extend(p.game_list)

        return frozenset(all_games)

    @property
    def count_games(self):
        return len(self.games)

    @property
    def count_platforms(self):
        return len(self.platforms)

    def get(self, name_platform):
        """Функция возращает ссылку на объект Платформа. Если платформа с таким именем
        не существует, она будет будет создана.

        """

        if name_platform not in self.platforms:
            platform = Parser.Platform(name_platform)
            self.platforms[name_platform] = platform
            return platform

        return self.platforms[name_platform]

    @staticmethod
    def delete_empty_platforms(platforms):
        # Удаляем пустые платформы
        platform_on_delete = set()
        for k, v in platforms.items():
            if v.count_games == 0:
                platform_on_delete.add(k)

        for name in platform_on_delete:
            del platforms[name]

    def parse(self, text, filter_exp='', parse_game_name_on_sequence=True, sort_game=False, sort_reverse=False,
              show_only_categories=(CategoryEnum.FINISHED_GAME,
                                    CategoryEnum.NOT_FINISHED_GAME,
                                    CategoryEnum.FINISHED_WATCHED,
                                    CategoryEnum.NOT_FINISHED_WATCHED,
                                    CategoryEnum.OTHER)):
        """Функция парсит строку игр.

        Args:
            text (str): строка с играми
            filter_exp (str): wildcard выражение фильтрации игр
            parse_game_name_on_sequence (bool): параметр определяет нужно ли в названиии
                игры искать указание ее частей. Например,
                "Resident Evil 4, 5, 6" станет:
                Resident Evil 4
                Resident Evil 5
                Resident Evil 6

                "Resident Evil 1-3" станет:
                Resident Evil 1
                Resident Evil 2
                Resident Evil 3

            sort_game (bool): сортировка игр
            sort_reverse (bool): направление сортировки
            show_only_categories (list): фильтр по категориям
        """

        logger.debug('Start parsing')
        t = time.clock()

        logger.debug('filter_exp="{}".'.format(filter_exp))

        # Для возможности поиска просто по словам:
        if not filter_exp.endswith('*'):
            filter_exp += '*'
            logger.debug('Change filter_exp="{}".'.format(filter_exp))

        self.platforms.clear()
        self.other.platforms.clear()

        name_platform = None

        # Проходим в текст построчно
        for line in text.split('\n'):
            line = line.rstrip()
            if not line:
                continue

            # Определим игровую платформу: ПК, консоли и т.п.
            if (line[0] not in Parser.ALL_ATTRIBUTES_GAMES
                and line[1] not in Parser.ALL_ATTRIBUTES_GAMES) and line.endswith(':'):
                # Имя платформы без двоеточия на конце
                name_platform = line[0: len(line) - 1]
                platform_item = self.get(name_platform)
                continue

            if name_platform:
                # Первые 2 символа -- тэг игры: пройденная, не пройденная, просмотренная
                attributes = line[0:2]

                # Третий символ и до конца строки -- имя игры
                game_name = line[2:]
                game_name_list = parse_game_name(game_name) if parse_game_name_on_sequence else [game_name]

                for game_name in game_name_list:
                    # Фильтруем игры
                    if not fnmatch.fnmatch(game_name, filter_exp):
                        continue

                    # Проверим на неизвестные атрибуты
                    unknown_attributes = str(attributes)
                    for c in Parser.ALL_ATTRIBUTES_GAMES:
                        unknown_attributes = unknown_attributes.replace(c, '')

                    # Если строка не пуста, значит в ней есть неизвестные символы
                    if unknown_attributes:
                        # Добавляем, если нет, к неопределенным играм узел платформы или получаем платформу
                        logger.warning('Обнаружен неизвестный атрибут: {}, игра: {}, платформа: {}.'.format(
                            unknown_attributes, line, name_platform))

                        if Parser.CategoryEnum.OTHER in show_only_categories:
                            self.other.add_game(name_platform, line)
                        continue

                    is_finished_watched = attributes == '@ ' or attributes == ' @'
                    is_not_finished_watched = attributes == '@-' or attributes == '-@'

                    is_finished_game = attributes == '  '
                    is_not_finished_game = attributes == '- ' or attributes == ' -'

                    def add_game(category, game_name):
                        # Фильтруем по типу категории
                        if category in show_only_categories:
                            platform_item.get(category).add(game_name)

                    if is_finished_game:
                        add_game(Parser.CategoryEnum.FINISHED_GAME, game_name)
                    elif is_not_finished_game:
                        add_game(Parser.CategoryEnum.NOT_FINISHED_GAME, game_name)
                    elif is_finished_watched:
                        add_game(Parser.CategoryEnum.FINISHED_WATCHED, game_name)
                    elif is_not_finished_watched:
                        add_game(Parser.CategoryEnum.NOT_FINISHED_WATCHED, game_name)
                    else:
                        if Parser.CategoryEnum.OTHER in show_only_categories:
                            logger.warning('Неопределенная игра {}, платформа: {}.'.format(line, name_platform))
                            self.other.add_game(name_platform, game_name)

        Parser.delete_empty_platforms(self.platforms)
        Parser.delete_empty_platforms(self.other.platforms)

        if sort_game:
            # который был заполнен при парсинге и производный от него -- отсортированный
            # Сортировка игр
            for platform in self.platforms.values():
                for category in platform.categories.values():
                    category.sort_game_list(reverse=sort_reverse)

            for platform in self.other.platforms.values():
                for category in platform.categories.values():
                    category.sort_game_list(reverse=sort_reverse)

        logger.debug('Finish parsing. Elapsed time: {:.3f} sec.'.format(time.clock() - t))

    @property
    def sorted_platforms(self, reverse=True):
        """Возвращает отсортированный список кортежей (имя_платформы, платформа).
        Сортируется по количеству игр в платформе.

        """

        return sorted(self.platforms.items(), key=lambda x: x[1].count_games, reverse=reverse)


if __name__ == '__main__':
    text = open('gistfile1.txt', encoding='utf8').read()

    p = Parser()
    p.parse(text)

    indent = ' ' * 2

    print()
    print('Games ({})'.format(p.count_games))
    print('Platforms ({}):'.format(p.count_platforms))
    for k, v in p.sorted_platforms:
        print('{}{}({}):'.format(indent, k, v.count_games))

        for kind, category in v.categories.items():
            print('{}{}({}):'.format(indent * 2, kind, category.count))

            for game in category:
                print(indent * 3, game.name)

            print()

    print()
    print('Other ({}/{}):'.format(p.other.count_platforms, p.other.count_games))
    for k, v in p.other.platforms.items():
        print('{}{}({}):'.format(indent, k, v.count_games))

        for category in v.categories.values():
            for game in category:
                print(indent * 2 + game.name)
