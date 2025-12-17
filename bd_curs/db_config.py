"""
Конфигурация подключения к базе данных на Jino.


"""

import os
from pathlib import Path

try:
    # python-dotenv используется только для удобной загрузки .env (если установлена)
    from dotenv import load_dotenv  # type: ignore
except ImportError:  # библиотека не обязательна
    load_dotenv = None  # type: ignore


def _simple_load_env(path: Path) -> None:
    """
    Простейшая загрузка .env без сторонних библиотек.
    Формат строк: KEY=VALUE, строки с # игнорируются.
    """
    if not path.exists():
        return
    try:
        with path.open("r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                key, value = line.split("=", 1)
                key = key.strip()
                value = value.strip()
                # Не перезаписываем уже заданные в окружении значения
                os.environ.setdefault(key, value)
    except Exception:
        # В учебном проекте достаточно молча проигнорировать ошибку
        pass


# Корень проекта: папка, в которой находится каталог `bd_curs`
BASE_DIR = Path(__file__).resolve().parent.parent
PACKAGE_DIR = Path(__file__).resolve().parent

# Возможные пути к .env: в корне проекта или рядом с кодом
ENV_CANDIDATES = [
    BASE_DIR / ".env",
    PACKAGE_DIR / ".env",
]

for env_path in ENV_CANDIDATES:
    if load_dotenv is not None and env_path.exists():
        # Если есть python-dotenv — используем его
        load_dotenv(env_path)
        break
    else:
        # Иначе пробуем простую ручную загрузку
        _simple_load_env(env_path)


# Читаем настройки из окружения (после попытки загрузки .env)
DB_HOST = os.getenv("DB_HOST")
DB_PORT = int(os.getenv("DB_PORT", "3306"))
DB_NAME = os.getenv("DB_NAME")
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")


# Простая проверка: без этих параметров подключение к БД не имеет смысла
if not all([DB_HOST, DB_NAME, DB_USER, DB_PASSWORD]):
    raise RuntimeError(
        "Не заданы переменные окружения DB_HOST, DB_NAME, DB_USER, DB_PASSWORD. "
        "Создайте файл .env в корне проекта (или рядом с папкой bd_curs) "
        "или экспортируйте их в окружение."
    )
