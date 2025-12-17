"""
Модуль для работы с базой данных (MySQL на Jino).

Использует библиотеку PyMySQL:
    pip install pymysql

Функции:
    - get_connection() — создать подключение;
    - init_db() — создать таблицы, если их ещё нет;
    - save_battle_result(...) — сохранить результат боя.
"""

from __future__ import annotations

import datetime
from typing import Iterable

import pymysql

# Импорт конфигурации БД так, чтобы модуль работал и как часть пакета bd_curs,
# и при запуске/импорте как обычный скрипт.
try:
    from . import db_config  # пакетный импорт: bd_curs.db_config
except ImportError:
    import db_config  # скриптовый импорт: просто db_config.py в той же папке


def get_connection():
    """Создаёт и возвращает подключение к БД."""
    return pymysql.connect(
        host=db_config.DB_HOST,
        port=db_config.DB_PORT,
        user=db_config.DB_USER,
        password=db_config.DB_PASSWORD,
        database=db_config.DB_NAME,
        charset="utf8mb4",
        autocommit=True,
        cursorclass=pymysql.cursors.DictCursor,
    )


def init_db():
    """Создаёт таблицу для результатов боёв, если её ещё нет."""
    create_sql = """
    CREATE TABLE IF NOT EXISTS battle_results (
        id INT AUTO_INCREMENT PRIMARY KEY,
        result ENUM('victory', 'defeat') NOT NULL,
        boss_name VARCHAR(100) NOT NULL,
        round_count INT NOT NULL,
        hero1_name VARCHAR(100),
        hero1_hp INT,
        hero2_name VARCHAR(100),
        hero2_hp INT,
        hero3_name VARCHAR(100),
        hero3_hp INT,
        hero4_name VARCHAR(100),
        hero4_hp INT,
        created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
    ) CHARACTER SET utf8mb4
    COLLATE utf8mb4_general_ci;
    """
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(create_sql)
    finally:
        conn.close()


def save_battle_result(
    result: str,
    boss_name: str,
    round_count: int,
    heroes: Iterable,
):
    """
    Сохранить результат боя.

    result: 'victory' или 'defeat'
    boss_name: имя босса ("Дракон")
    round_count: количество раундов в бою
    heroes: коллекция героев (ожидаются объекты с атрибутами .name и .hp)
    """
    # Берём максимум 4 героев, чтобы соответствовать структуре таблицы.
    heroes = list(heroes)[:4]
    names = [getattr(h, "name", None) for h in heroes]
    hps = [getattr(h, "hp", None) for h in heroes]

    # Дополняем до 4 значений
    while len(names) < 4:
        names.append(None)
        hps.append(None)

    sql = """
        INSERT INTO battle_results (
            result,
            boss_name,
            round_count,
            hero1_name, hero1_hp,
            hero2_name, hero2_hp,
            hero3_name, hero3_hp,
            hero4_name, hero4_hp,
            created_at
        ) VALUES (%s, %s, %s,
                  %s, %s,
                  %s, %s,
                  %s, %s,
                  %s, %s,
                  %s)
    """

    params = [
        result,
        boss_name,
        int(round_count),
        names[0],
        hps[0],
        names[1],
        hps[1],
        names[2],
        hps[2],
        names[3],
        hps[3],
        datetime.datetime.utcnow(),
    ]

    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(sql, params)
    finally:
        conn.close()


__all__ = ["get_connection", "init_db", "save_battle_result"]


