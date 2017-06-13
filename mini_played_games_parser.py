#!/usr/bin/env python3
# -*- coding: utf-8 -*-

__author__ = 'ipetrash'


def parse_played_games(text: str) -> dict:
    """
    Функция для парсинга списка игр.

    """

    FINISHED_GAME = 'FINISHED_GAME'
    NOT_FINISHED_GAME = 'NOT_FINISHED_GAME'
    FINISHED_WATCHED = 'FINISHED_WATCHED'
    NOT_FINISHED_WATCHED = 'NOT_FINISHED_WATCHED'

    # Регулярка вытаскивает выражения вида: 1, 2, 3 или 1-3, или римские цифры: III, IV
    import re
    PARSE_GAME_NAME_PATTERN = re.compile(r'(\d+(, *?\d+)+)|(\d+ *?- *?\d+)|([MDCLXVI]+(, ?[MDCLXVI]+)+)',
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
            return [game_name]

        # Сразу проверяем номер игры в серии и если она первая, то не добавляем в названии ее номер
        return [base_name if num == '1' else base_name + " " + num for num in seq]

    from collections import OrderedDict
    platforms = OrderedDict()
    platform = None

    for line in text.splitlines():
        line = line.rstrip()
        if not line:
            continue

        if line[0] not in ' -@' and line[1] not in ' -@' and line.endswith(':'):
            platform_name = line[:-1]

            platform = OrderedDict()
            platform[FINISHED_GAME] = list()
            platform[NOT_FINISHED_GAME] = list()
            platform[FINISHED_WATCHED] = list()
            platform[NOT_FINISHED_WATCHED] = list()

            platforms[platform_name] = platform

            continue

        if not platform:
            continue

        flag = line[:2]
        games = parse_game_name(line[2:])

        if flag == '  ':
            platform[FINISHED_GAME] += games

        elif flag == ' -' or flag == '- ':
            platform[NOT_FINISHED_GAME] += games

        elif flag == ' @' or flag == '@ ':
            platform[FINISHED_WATCHED] += games

        elif flag == '@-' or flag == '-@':
            platform[NOT_FINISHED_WATCHED] += games

    return platforms


if __name__ == '__main__':
    text = open('gistfile1.txt', encoding='utf-8').read()
    platforms = parse_played_games(text)
    print(', '.join(platforms.keys()))

    import json
    json.dump(platforms, open('games.json', mode='w', encoding='utf-8'), ensure_ascii=False, indent=4)
