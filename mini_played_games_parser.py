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
        short_name = game_name.replace(seq_str, '').strip()

        if ',' in seq_str:
            seq = seq_str.replace(' ', '').split(',')

        elif '-' in seq_str:
            seq = seq_str.replace(' ', '').split('-')
            if len(seq) == 2:
                seq = tuple(map(int, seq))
                seq = tuple(range(seq[0], seq[1] + 1))
        else:
            return [game_name]

        # Сразу проверяем номер игры в серии и если она первая, то не добавляем в названии ее номер
        return [short_name if str(num) == '1' else '{} {}'.format(short_name, num) for num in seq]

    from collections import OrderedDict
    platforms = OrderedDict()
    platform = None

    for line in text.splitlines():
        line = line.rstrip()

        if not line:
            continue

        flag_1, flag_2 = line[0], line[1]

        if flag_1 not in ' -@' and flag_2 not in ' -@' and line.endswith(':'):
            platform_name = line[:-1]

            platform = {
                FINISHED_GAME: list(),
                NOT_FINISHED_GAME: list(),
                FINISHED_WATCHED: list(),
                NOT_FINISHED_WATCHED: list(),
            }
            platforms[platform_name] = platform

            continue

        if not platform:
            continue

        flag = flag_1 + flag_2
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