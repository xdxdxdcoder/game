import sys
import random
import math
import os
import pygame

# Импорты, которые работают и при запуске файла напрямую, и при запуске как пакет bd_curs
try:
    from characters import Warrior, Mage, Archer, Healer
    from boss import Boss
    from items import HealthPotion, ManaPotion, DamagePotion
    from effects import PoisonEffect, StrengthBuffEffect, RegenerationEffect
    import db as db_module
except ImportError:  # пакетный импорт
    from .characters import Warrior, Mage, Archer, Healer
    from .boss import Boss
    from .items import HealthPotion, ManaPotion, DamagePotion
    from .effects import PoisonEffect, StrengthBuffEffect, RegenerationEffect
    from . import db as db_module

# Окно поменьше по высоте, чтобы кнопки не перекрывались доком
WIDTH, HEIGHT = 1400, 600
FPS = 60

WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
RED = (200, 60, 60)
GREEN = (60, 200, 60)
BLUE = (60, 120, 220)
GRAY = (40, 40, 40)
LIGHT_GRAY = (80, 80, 80)
YELLOW = (240, 210, 90)

ASSETS_DIR = os.path.join(os.path.dirname(__file__), "assets")


def load_sprite(filename, size=None):
    """Пробуем загрузить спрайт из папки assets, иначе возвращаем None."""
    path = os.path.join(ASSETS_DIR, filename)
    try:
        image = pygame.image.load(path).convert_alpha()
        if size:
            image = pygame.transform.smoothscale(image, size)
        return image
    except Exception:
        return None


class SpriteSheet:
    """Нарезка спрайт-листа на кадры и выдача кадров по индексу/времени."""

    def __init__(self, surface, columns, rows, scale_to=None):
        self.columns = columns
        self.rows = rows
        self.frames = []
        frame_w = surface.get_width() // columns
        frame_h = surface.get_height() // rows

        for row in range(rows):
            for col in range(columns):
                rect = pygame.Rect(col * frame_w, row * frame_h, frame_w, frame_h)
                frame = surface.subsurface(rect).copy()
                if scale_to is not None:
                    frame = pygame.transform.smoothscale(frame, scale_to)
                self.frames.append(frame)

    def get_frame(self, indices, t, speed=10.0):
        if not indices or not self.frames:
            return None
        idx = int(t * speed) % len(indices)
        frame_idx = indices[idx]
        # Проверяем, что индекс в пределах границ
        if frame_idx < 0 or frame_idx >= len(self.frames):
            return None
        return self.frames[frame_idx]


class Button:
    def __init__(self, rect, text, font, callback, bg_color=LIGHT_GRAY, text_color=WHITE):
        self.rect = pygame.Rect(rect)
        self.text = text
        self.font = font
        self.callback = callback
        self.bg_color = bg_color
        self.text_color = text_color

    def draw(self, surface):
        pygame.draw.rect(surface, self.bg_color, self.rect, border_radius=6)
        label = self.font.render(self.text, True, self.text_color)
        label_rect = label.get_rect(center=self.rect.center)
        surface.blit(label, label_rect)

    def handle_event(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.rect.collidepoint(event.pos):
                self.callback()


class PygameBattle:
    """
    Визуальная оболочка над существующей боевой логикой.
    Не меняет сами классы персонажей, а только управляет ходами и отрисовкой.
    """

    def __init__(self, screen, font, small_font):
        self.screen = screen
        self.font = font
        self.small_font = small_font
        self.hud_font = pygame.font.SysFont("verdana", 18)
        self.tiny_font = pygame.font.SysFont("verdana", 14)

        # Плавная анимация снарядов
        self.projectiles = []
        # Летающие числа урона/лечения
        self.float_texts = []
        # Анимации атаки персонажей
        self.attack_animations = {}  # {character: {"time": 0.0, "duration": 0.5}}
        # Эффекты критических ударов
        self.crit_effects = []  # {"x": int, "y": int, "time": float, "life": float}
        # Экранный shake
        self.screen_shake = {"intensity": 0.0, "time": 0.0}
        # Фаза босса (False = первая фаза, True = вторая фаза)
        self.boss_phase2 = False
        # Флаги для отслеживания проигранных звуков окончания боя
        self.victory_sound_played = False
        self.defeat_sound_played = False

        # Флаг, чтобы в БД записывался только один результат боя
        self._db_result_saved = False

        # Краткие описания умений героев (для подсказки на экране)
        self.skill_descriptions = {
            "Воин": "Боевой крик: усиливает урон всей команды на 3 хода (25 MP).",
            "Маг": "Магия яда: урон и отравление босса на 3 хода (20 MP).",
            "Лучник": "Мощный выстрел: увеличенный урон боссу (25 MP).",
            "Лекарь": "Молитва исцеления: массовое лечение (25 MP).",
        }

        # Инициализируем команду и босса
        self.warrior = Warrior("Волк")
        self.mage = Mage("Пудж")
        self.archer = Archer("Стив")
        self.healer = Healer("Целитель")
        self.heroes = [self.warrior, self.mage, self.archer, self.healer]

        self.boss = Boss("Дракон")

        # Ссылки друг на друга, чтобы работали умения и предметы
        for h in self.heroes:
            h.heroes = self.heroes
            h.boss = self.boss
        self.boss.heroes = self.heroes

        # Начальные предметы как в текстовой версии
        for hero in self.heroes:
            hero.inventory.add_item(HealthPotion(), 2)
            hero.inventory.add_item(ManaPotion(), 1)
            hero.inventory.add_item(DamagePotion(), 1)
        self.boss.inventory.add_item(HealthPotion(), 3)

        self.current_hero_index = 0
        self.state = "player_turn"  # player_turn, boss_turn, choose_item, battle_over
        self.round = 1
        # Кто уже сходил в этом раунде (для корректного хода босса)
        self.heroes_played_this_round = set()

        self.log_lines = []
        self.max_log_lines = 10

        # Кнопки действий (под логом, но с запасом сверху от края экрана)
        btn_w = 260
        btn_h = 56
        btn_y = HEIGHT - btn_h - 20
        gap = 20
        btn_count = 4
        start_x = (WIDTH - (btn_w * btn_count + gap * (btn_count - 1))) // 2

        self.buttons = [
            # Обычная атака
            Button(
                (start_x, btn_y, btn_w, btn_h),
                "Атаковать",
                self.font,
                self.on_attack_clicked,
                bg_color=BLUE,
            ),
            # Особая способность героя
            Button(
                (start_x + (btn_w + gap), btn_y, btn_w, btn_h),
                "Способность",
                self.font,
                self.on_skill_clicked,
                bg_color=(120, 60, 180),
            ),
            # Инвентарь
            Button(
                (start_x + (btn_w + gap) * 2, btn_y, btn_w, btn_h),
                "Инвентарь",
                self.font,
                self.on_item_clicked,
                bg_color=YELLOW,
                text_color=BLACK,
            ),
            # Пропуск хода
            Button(
                (start_x + (btn_w + gap) * 3, btn_y, btn_w, btn_h),
                "Пропустить ход",
                self.font,
                self.on_skip_clicked,
                bg_color=LIGHT_GRAY,
            ),
        ]

        # Область лога (справа снизу, максимально длинная по горизонтали,
        # но относительно невысокая, чтобы не забирать много места по вертикали)
        self.log_height = 70
        # Лог растягиваем почти до правого края, оставляя небольшой отступ
        self.log_rect = pygame.Rect(WIDTH - 670, btn_y - self.log_height - 10, 650, self.log_height)

        # Модальное окно выбора предмета
        self.item_buttons = []
        self.build_item_buttons()

        self.add_log("ПАТИ ПРОТИВ БОССА")
        self.add_log("Нажмите кнопки внизу, чтобы управлять героями.")

        # Позиции "моделек" персонажей на сцене (как в 2D‑платформере)
        ground_y = HEIGHT - 240
        spacing_x = 180
        start_x = 220
        self.hero_positions = {
            self.warrior: (start_x + 0 * spacing_x, ground_y),
            self.mage: (start_x + 1 * spacing_x, ground_y),
            self.archer: (start_x + 2 * spacing_x, ground_y),
            self.healer: (start_x + 3 * spacing_x, ground_y),
        }
        self.boss_position = (WIDTH - 260, ground_y - 40)

        # Спрайты и анимации (если пользователь положит картинки в папку assets)
        self.hero_anim = {}

        def make_indices(cols, row_from, row_to, col_from, col_to):
            res = []
            for r in range(row_from, row_to + 1):
                for c in range(col_from, col_to + 1):
                    res.append(r * cols + c)
            return res

        # Воин: 10x10
        warrior_img = load_sprite("warrior.png")
        if warrior_img:
            sheet = SpriteSheet(warrior_img, columns=10, rows=10, scale_to=(96, 96))
            idle = make_indices(10, 0, 0, 0, 5)  # первая строка, первые 6 кадров
            attack = make_indices(10, 4, 4, 0, 5)  # строка 4 (атака вправо)
            death = make_indices(10, 9, 9, 0, 9)  # последняя строка
            self.hero_anim["Воин"] = {"sheet": sheet, "idle": idle, "attack": attack, "death": death}

        # Маг, Лучник, Лекарь: 10x5, последние 4 колонки всех 5 строк — смерть
        for role, filename, attack_row in [("Маг", "mage.png", 3), ("Лучник", "archer.png", 2),
                                           ("Лекарь", "healer.png", 3)]:
            img = load_sprite(filename)
            if img:
                sheet = SpriteSheet(img, columns=10, rows=5, scale_to=(96, 96))
                idle = make_indices(10, 0, 0, 0, 5)
                attack = make_indices(10, attack_row, attack_row, 0, 3)  # кадры атаки
                death = make_indices(10, 0, 4, 6, 9)
                self.hero_anim[role] = {"sheet": sheet, "idle": idle, "attack": attack, "death": death}

        boss_img = load_sprite("boss_dragon.png")
        self.boss_anim = None
        if boss_img:
            sheet = SpriteSheet(boss_img, columns=8, rows=3, scale_to=(260, 180))
            idle = make_indices(8, 0, 0, 0, 7)
            death = make_indices(8, 2, 2, 0, 7)
            self.boss_anim = {"sheet": sheet, "idle": idle, "death": death}

        # Время для простой анимации покачивания
        self.time = 0.0

        # Инициализация звуков (если файлы есть)
        pygame.mixer.init(frequency=22050, size=-16, channels=2, buffer=512)
        self.sounds = {}
        sound_files = {
            "attack": "attack.wav",
            "crit": "crit.wav",
            "boss_hit": "boss_hit.wav",
            "hero_hit": "hero_hit.wav",
            "victory": "victory.wav",
            "defeat": "defeat.wav"
        }
        for name, filename in sound_files.items():
            path = os.path.join(ASSETS_DIR, filename)
            if os.path.exists(path):
                try:
                    self.sounds[name] = pygame.mixer.Sound(path)
                except:
                    pass

    # ---------- ЛОГИКА БОЯ ----------

    def add_log(self, text):
        self.log_lines.append(text)
        if len(self.log_lines) > self.max_log_lines:
            self.log_lines = self.log_lines[-self.max_log_lines:]

    @property
    def alive_heroes(self):
        return [h for h in self.heroes if h.is_alive]

    def get_current_hero(self):
        if not self.alive_heroes:
            return None
        # Проверяем границы индекса
        if self.current_hero_index < 0 or self.current_hero_index >= len(self.heroes):
            # Исправляем индекс
            self.current_hero_index = 0
        # Сместить индекс на живого героя
        hero = self.heroes[self.current_hero_index]
        if not hero.is_alive:
            # Найти первого живого
            for i, h in enumerate(self.heroes):
                if h.is_alive:
                    self.current_hero_index = i
                    hero = h
                    break
        return hero

    def next_hero_turn(self):
        """
        Переходим к следующему герою.
        Когда все живые герои сходили в текущем раунде – ход переходит боссу.
        """
        # Проверяем поражение перед переходом к следующему герою
        self.check_battle_end()
        if self.state == "battle_over":
            return

        # Список живых героев, которые ещё не ходили в этом раунде
        remaining = [h for h in self.heroes if h.is_alive and h not in self.heroes_played_this_round]

        if remaining:
            # Берём первого из оставшихся и делаем его текущим
            next_hero = remaining[0]
            for i, h in enumerate(self.heroes):
                if h is next_hero:
                    self.current_hero_index = i
                    break
            self.state = "player_turn"
            return  # Важно: выходим, чтобы не выполнить код ниже

        # Все живые герои сходили — ход босса
        # Проверяем поражение еще раз перед ходом босса
        self.check_battle_end()
        if self.state == "battle_over":
            return

        self.heroes_played_this_round.clear()
        self.state = "boss_turn"

    def check_battle_end(self):
        # Проверяем победу
        if not self.boss.is_alive:
            if self.state != "battle_over":
                self.state = "battle_over"
                self.add_log("ПОБЕДА! Босс повержен!")
                # Сохраняем результат боя в БД (если настроено подключение)
                self._save_battle_result_to_db("victory")
            # Проигрываем звук победы только один раз
            if not self.victory_sound_played and "victory" in self.sounds:
                try:
                    # Останавливаем остальные звуки, чтобы победный звук был слышен
                    pygame.mixer.stop()
                    self.sounds["victory"].play()
                    self.victory_sound_played = True
                except Exception as e:
                    print(f"Ошибка воспроизведения звука победы: {e}")

        # Проверяем поражение - более надежная проверка
        alive_count = sum(1 for h in self.heroes if h.is_alive)
        if alive_count == 0:
            # Устанавливаем состояние поражения
            if self.state != "battle_over":
                self.state = "battle_over"
                self.add_log("ПОРАЖЕНИЕ... Босс одолел героев")
                # Сохранение результата поражения
                self._save_battle_result_to_db("defeat")

            # Проигрываем звук поражения - проверяем каждый раз, но проигрываем только один раз
            if not self.defeat_sound_played:
                if "defeat" in self.sounds:
                    try:
                        # Останавливаем все звуки перед проигрыванием звука поражения
                        pygame.mixer.stop()
                        self.sounds["defeat"].play()
                        self.defeat_sound_played = True
                    except Exception as e:
                        print(f"Ошибка воспроизведения звука поражения: {e}")
                        # Даже если была ошибка, помечаем как проигранный, чтобы не пытаться снова
                        self.defeat_sound_played = True
                else:
                    # Если звука нет, все равно помечаем как проигранный
                    print("Звук defeat.wav не найден!")
                    self.defeat_sound_played = True

    def _save_battle_result_to_db(self, result: str):
        """
        Пытается сохранить результат боя в удалённую БД.
        Ошибки подключения выводятся в консоль, но игру не ломают.
        """
        if self._db_result_saved:
            return

        # Подстраховка: проверяем, что модуль БД действительно есть
        if db_module is None:
            return

        try:
            # На всякий случай инициализируем таблицу (CREATE TABLE IF NOT EXISTS ...)
            db_module.init_db()
            db_module.save_battle_result(
                result=result,
                boss_name=getattr(self.boss, "name", "Босс"),
                round_count=self.round,
                heroes=self.heroes,
            )
            self._db_result_saved = True
            print(f"Результат боя сохранён в БД: {result}")
        except Exception as e:
            # Для учебного проекта достаточно вывести ошибку в консоль
            print(f"Не удалось сохранить результат боя в БД: {e}")

    def hero_attack(self):
        hero = self.get_current_hero()
        if hero is None:
            return

        # Запускаем анимацию атаки
        self.attack_animations[hero] = {"time": 0.0, "duration": 0.4}

        damage = hero.attack(self.boss)
        # Крит, если урон значительно выше среднего
        is_crit = damage >= 50 or random.random() < 0.15  # 15% шанс крита

        # Звук атаки
        if "attack" in self.sounds:
            self.sounds["attack"].play()
        if is_crit and "crit" in self.sounds:
            self.sounds["crit"].play()

        log_msg = f"{hero.name} атакует {self.boss.name} и наносит {damage} урона!"
        if is_crit:
            log_msg += " КРИТ!"
            # Эффект критического удара
            bx, by = self.get_model_pos(self.boss)
            self.crit_effects.append({
                "x": bx,
                "y": by - 40,
                "time": 0.0,
                "life": 0.6
            })
            # Экранный shake
            self.screen_shake = {"intensity": 3.0, "time": 0.2}

        self.add_log(log_msg)
        # Анимация выстрела героя по боссу
        if self.boss is not None:
            self.spawn_projectile(from_char=hero, to_char=self.boss, color=GREEN)
            # Летающий урон над боссом
            bx, by = self.get_model_pos(self.boss)
            float_color = (255, 255, 0) if is_crit else (255, 180, 100)
            size_mult = 1.5 if is_crit else 1.0
            self.add_float_text(bx, by - 60, f"-{damage}", float_color, size_mult=size_mult)

        # Проверяем фазу босса
        self.check_boss_phase()

        # Отмечаем, что герой сходил в этом раунде
        self.heroes_played_this_round.add(hero)
        self.check_battle_end()
        if self.state != "battle_over":
            self.next_hero_turn()
            if self.state == "boss_turn":
                self.boss_turn()

    def _skill_warrior_battle_cry(self, hero):
        """Воин: боевой крик — усиливает урон всей команды на несколько ходов."""
        mp_cost = 25
        if not hasattr(hero, "mp") or hero.mp < mp_cost:
            self.add_log(f"{hero.name} пытается использовать БОЕВОЙ КРИК, но не хватает маны.")
            return False

        hero.mp -= mp_cost
        self.add_log(f"{hero.name} использует БОЕВОЙ КРИК! Вся команда получает усиление урона.")
        for ally in self.heroes:
            if ally.is_alive:
                ally.add_effect(StrengthBuffEffect(duration=3, damage_bonus=10))
                ax, ay = self.get_model_pos(ally)
                self.add_float_text(ax, ay - 70, "Усиление", (255, 230, 120), size_mult=0.9)
        # Лёгкий вибро‑эффект
        self.screen_shake = {"intensity": 2.0, "time": 0.15}
        return True

    def _skill_mage_poison_magic(self, hero):
        """Маг: магия яда — урон и отравление босса."""
        mp_cost = 20
        if not hasattr(hero, "mp") or hero.mp < mp_cost:
            self.add_log(f"{hero.name} не хватает маны для магии яда.")
            return False
        if not self.boss or not self.boss.is_alive:
            return False

        hero.mp -= mp_cost
        poison = PoisonEffect(duration=3, damage_per_turn=10)
        self.boss.add_effect(poison)

        damage = random.randint(25, 35)
        actual_damage = self.boss.take_damage(damage)
        self.add_log(
            f"{hero.name} использует МАГИЮ ЯДА! {self.boss.name} получает {actual_damage} урона и отравляется."
        )

        # Визуальный эффект: фиолетовый снаряд и число урона
        self.spawn_projectile(from_char=hero, to_char=self.boss, color=(170, 80, 220))
        bx, by = self.get_model_pos(self.boss)
        self.add_float_text(bx, by - 70, f"-{actual_damage}", (200, 160, 255), size_mult=1.1)
        return True

    def _skill_archer_stun_shot(self, hero):
        """Лучник: мощный выстрел — наносит увеличенный урон боссу."""
        mp_cost = 25
        # У лучника может не быть маны, поэтому добавляем её при первом использовании
        if not hasattr(hero, "mp"):
            hero.mp = 40
            hero.max_mp = 40
        if hero.mp < mp_cost:
            self.add_log(f"{hero.name} не хватает маны для мощного выстрела.")
            return False
        if not self.boss or not self.boss.is_alive:
            return False

        hero.mp -= mp_cost
        damage = random.randint(hero.damage + 5, hero.damage + 20)
        actual_damage = self.boss.take_damage(damage)

        msg = f"{hero.name} выпускает МОЩНЫЙ ВЫСТРЕЛ и наносит {actual_damage} урона."
        self.add_log(msg)

        # Визуальный эффект: яркий жёлтый снаряд
        self.spawn_projectile(from_char=hero, to_char=self.boss, color=(255, 230, 120))
        bx, by = self.get_model_pos(self.boss)
        self.add_float_text(bx, by - 70, f"-{actual_damage}", (255, 220, 120), size_mult=1.1)
        return True

    def _skill_healer_mass_heal(self, hero):
        """Лекарь: массовое лечение, регенерация и частичное очищение дебаффов."""
        mp_cost = 25
        if not hasattr(hero, "mp") or hero.mp < mp_cost:
            self.add_log(f"{hero.name} не хватает маны для молитвы исцеления.")
            return False

        hero.mp -= mp_cost
        any_healed = False
        for ally in self.heroes:
            if ally.is_alive:
                old_hp = ally.hp
                heal_amount = random.randint(20, 35)
                ally.hp = min(ally.max_hp, ally.hp + heal_amount)
                actual_heal = ally.hp - old_hp
                if actual_heal > 0:
                    any_healed = True
                    ax, ay = self.get_model_pos(ally)
                    self.add_float_text(ax, ay - 70, f"+{actual_heal}", (140, 230, 160), size_mult=1.0)
                    # Краткая регенерация
                    ally.add_effect(RegenerationEffect(duration=2, heal_per_turn=6))

                # Частичное очищение негативных эффектов (яд, оглушение)
                to_remove = []
                for eff in getattr(ally, "effects", []):
                    name = getattr(eff, "name", "")
                    if name in ("Отравление", "Оглушение"):
                        to_remove.append(eff)
                for eff in to_remove:
                    ally.remove_effect(eff)
                    ax, ay = self.get_model_pos(ally)
                    self.add_float_text(ax, ay - 95, "ОЧИЩЕН", (200, 240, 255), size_mult=0.8)

        if any_healed:
            self.add_log(f"{hero.name} произносит МОЛИТВУ ИСЦЕЛЕНИЯ! Команда восстанавливает силы и очищается.")
        else:
            self.add_log(f"{hero.name} пытается исцелить союзников, но лечить пока некого.")
        return any_healed

    def hero_use_skill(self):
        """Активирует особую способность текущего героя."""
        hero = self.get_current_hero()
        if hero is None or not hero.is_alive:
            return

        role = getattr(hero, "role", "")
        used = False

        if role == "Воин":
            used = self._skill_warrior_battle_cry(hero)
        elif role == "Маг":
            used = self._skill_mage_poison_magic(hero)
        elif role == "Лучник":
            used = self._skill_archer_stun_shot(hero)
        elif role == "Лекарь":
            used = self._skill_healer_mass_heal(hero)
        else:
            self.add_log(f"У {hero.name} нет особых умений.")
            return

        # Если умение не сработало (например, не хватило маны) — ход не тратим
        if not used:
            return

        # Анимация атаки/каста для способности
        self.attack_animations[hero] = {"time": 0.0, "duration": 0.5}

        # Отмечаем, что герой сходил в этом раунде
        self.heroes_played_this_round.add(hero)

        # Проверяем смену фазы босса и окончание боя
        self.check_boss_phase()
        self.check_battle_end()
        if self.state != "battle_over":
            self.next_hero_turn()
            if self.state == "boss_turn":
                self.boss_turn()

    def hero_use_item(self, item_name):
        hero = self.get_current_hero()
        if hero is None:
            return
        result = hero.use_item(item_name)
        self.add_log(result)
        self.heroes_played_this_round.add(hero)
        self.check_battle_end()
        if self.state != "battle_over":
            self.next_hero_turn()
            if self.state == "boss_turn":
                self.boss_turn()

    def hero_skip(self):
        hero = self.get_current_hero()
        if hero is None:
            return
        self.add_log(f"{hero.name} пропускает ход.")
        self.heroes_played_this_round.add(hero)
        self.next_hero_turn()
        if self.state == "boss_turn":
            self.boss_turn()

    def boss_turn(self):
        if not self.boss.is_alive:
            return

        self.add_log(f"--- Ход босса {self.boss.name} ---")

        # Выбор действия (похоже на текстовую версию)
        if self.boss_phase2:
            action_weights = {"attack": 0.4, "skill": 0.5, "item": 0.1}
        else:
            action_weights = {"attack": 0.5, "skill": 0.3, "item": 0.2}

        actions = []
        weights = []
        for action_name, weight in action_weights.items():
            if action_name == "item" and not (
                    hasattr(self.boss, 'inventory') and self.boss.inventory and self.boss.inventory.items):
                continue
            actions.append(action_name)
            weights.append(weight)

        if not actions:
            actions = ["attack"]
            weights = [1.0]

        action = random.choices(actions, weights=weights)[0]

        if action == "attack":
            alive = [h for h in self.heroes if h.is_alive]
            if alive:
                target = random.choice(alive)
                if target is not None:
                    damage = self.boss.attack(target)
                    self.add_log(f"{self.boss.name} атакует {target.name} и наносит {damage} урона!")
                    # Звук попадания по герою
                    if "hero_hit" in self.sounds:
                        try:
                            self.sounds["hero_hit"].play()
                        except:
                            pass

                    # Анимация выстрела босса по герою
                    self.spawn_projectile(from_char=self.boss, to_char=target, color=RED)
                    tx, ty = self.get_model_pos(target)
                    self.add_float_text(tx, ty - 60, f"-{damage}", (255, 80, 80))
        elif action == "skill":
            result = self.boss.use_skill()
            self.add_log(str(result))
            # Проверяем, был ли нанесен урон скиллом (stomp_attack наносит урон всем)
            # Если в результате есть "урон" или "Общий урон", значит был нанесен урон
            if result and ("урон" in str(result) or "Общий" in str(result)):
                # Проигрываем звук попадания для скиллов, наносящих урон
                if "hero_hit" in self.sounds:
                    try:
                        self.sounds["hero_hit"].play()
                    except:
                        pass
        elif action == "item":
            item_name = random.choice(list(self.boss.inventory.items.keys()))
            if item_name:
                result = self.boss.use_item(item_name)
                self.add_log(str(result))

        self.check_battle_end()

        if self.state != "battle_over":
            # Новый раунд начинается с героев
            self.heroes_played_this_round.clear()  # Очищаем список сходивших героев
            self.state = "player_turn"
            # смещаем индекс на первого живого героя
            for i, h in enumerate(self.heroes):
                if h.is_alive:
                    self.current_hero_index = i
                    break
            self.round += 1

    # ---------- КНОПКИ / СОБЫТИЯ ----------

    def on_attack_clicked(self):
        if self.state != "player_turn":
            return
        self.hero_attack()

    def on_skill_clicked(self):
        if self.state != "player_turn":
            return
        self.hero_use_skill()

    def on_item_clicked(self):
        if self.state != "player_turn":
            return
        hero = self.get_current_hero()
        if hero and hero.inventory.items:
            self.build_item_buttons()
            self.state = "choose_item"
        else:
            self.add_log("Инвентарь пуст!")

    def on_skip_clicked(self):
        if self.state != "player_turn":
            return
        self.hero_skip()

    def build_item_buttons(self):
        """Создаём кнопки выбора предмета для текущего героя."""
        self.item_buttons = []
        hero = self.get_current_hero()
        if hero is None:
            return

        items = list(hero.inventory.items.items())  # [(name, data), ...]
        if not items:
            return

        modal_width = 360
        modal_height = 60 + 40 * len(items)
        modal_x = (WIDTH - modal_width) // 2
        modal_y = (HEIGHT - modal_height) // 2

        self.item_modal_rect = pygame.Rect(modal_x, modal_y, modal_width, modal_height)

        x = modal_x + 20
        y = modal_y + 40
        w = modal_width - 40
        h = 32

        for item_name, data in items:
            def make_callback(name=item_name):
                return lambda: self.select_item(name)

            btn = Button((x, y, w, h), f"{item_name} x{data['quantity']}", self.small_font,
                         make_callback(), bg_color=BLUE)
            self.item_buttons.append(btn)
            y += h + 8

    def select_item(self, item_name):
        if self.state != "choose_item":
            return
        self.hero_use_item(item_name)
        self.build_item_buttons()

    def handle_event(self, event):
        if event.type == pygame.QUIT:
            pygame.quit()
            sys.exit()

        if self.state == "battle_over":
            if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                pygame.quit()
                sys.exit()
            return

        if self.state == "choose_item":
            for btn in self.item_buttons:
                btn.handle_event(event)
            # Правый клик/ESC закрывает окно без выбора
            if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                self.state = "player_turn"
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 3:
                self.state = "player_turn"
        else:
            for btn in self.buttons:
                btn.handle_event(event)

    # ---------- ОТРИСОВКА ----------

    def get_model_pos(self, char):
        if char is None:
            return (0, 0)
        if char is self.boss:
            return self.boss_position
        return self.hero_positions.get(char, (0, 0))

    def spawn_projectile(self, from_char, to_char, color):
        start_x, start_y = self.get_model_pos(from_char)
        end_x, end_y = self.get_model_pos(to_char)
        # Проверяем, что позиции валидны (не (0, 0) если персонаж не найден)
        if (start_x, start_y) == (0, 0) and from_char not in self.hero_positions and from_char != self.boss:
            return
        if (end_x, end_y) == (0, 0) and to_char not in self.hero_positions and to_char != self.boss:
            return
        role = getattr(from_char, "role", "")
        if role == "Маг":
            p_type = "orb"
            size = 8
        elif role == "Лучник":
            p_type = "arrow"
            size = 5
        elif role == "Лекарь":
            p_type = "heal"
            size = 7
        else:
            p_type = "bolt"
            size = 6

        projectile = {
            "start": (start_x, start_y),
            "end": (end_x, end_y),
            "color": color,
            "type": p_type,
            "size": size,
            "progress": 0.0,
            "duration": 0.8,  # секунды
        }
        self.projectiles.append(projectile)

    def update(self, dt):
        """Обновление анимаций."""
        self.time += dt

        # Проверяем окончание боя каждый кадр (на случай, если герои умирают от эффектов)
        if self.state != "battle_over":
            self.check_battle_end()

        # Обновление анимаций атаки
        anim_remove = []
        for char, anim in self.attack_animations.items():
            anim["time"] += dt
            if anim["time"] >= anim["duration"]:
                anim_remove.append(char)
        for char in anim_remove:
            if char in self.attack_animations:
                del self.attack_animations[char]

        # Обновление эффектов критических ударов
        crit_remove = []
        for crit in self.crit_effects:
            crit["time"] += dt
            if crit["time"] >= crit["life"]:
                crit_remove.append(crit)
        for crit in crit_remove:
            if crit in self.crit_effects:
                self.crit_effects.remove(crit)

        # Обновление экранного shake
        if self.screen_shake["time"] > 0:
            self.screen_shake["time"] -= dt
            if self.screen_shake["time"] <= 0:
                self.screen_shake["intensity"] = 0.0

        to_remove = []
        for p in self.projectiles:
            if "duration" in p and p["duration"] > 0:
                p["progress"] += dt / p["duration"]
                if p["progress"] >= 1.0:
                    to_remove.append(p)
            else:
                # Если duration некорректный, удаляем снаряд
                to_remove.append(p)
        for p in to_remove:
            if p in self.projectiles:
                self.projectiles.remove(p)

        # Обновляем летающие тексты
        ft_remove = []
        for ft in self.float_texts:
            ft["time"] += dt
            ft["y"] -= 30 * dt
            if ft["time"] >= ft["life"]:
                ft_remove.append(ft)
        for ft in ft_remove:
            if ft in self.float_texts:
                self.float_texts.remove(ft)

    def add_float_text(self, x, y, text, color, size_mult=1.0):
        self.float_texts.append({
            "x": x,
            "y": y,
            "text": text,
            "color": color,
            "time": 0.0,
            "life": 0.9,
            "size_mult": size_mult
        })

    def check_boss_phase(self):
        """Проверяет, нужно ли перейти во вторую фазу босса"""
        if not self.boss_phase2 and self.boss.hp <= self.boss.max_hp * 0.5:
            self.boss_phase2 = True
            self.add_log("⚠️ БОСС ВХОДИТ ВО ВТОРУЮ ФАЗУ! ⚠️")
            self.add_log("Босс становится сильнее и агрессивнее!")
            # Усиление босса
            self.boss.damage = int(self.boss.damage * 1.3)
            # Экранный shake при смене фазы
            self.screen_shake = {"intensity": 5.0, "time": 0.4}

    def draw_hp_bar(self, x, y, w, h, current, maximum, color=GREEN):
        pygame.draw.rect(self.screen, GRAY, (x, y, w, h), border_radius=4)
        if maximum > 0 and current > 0:
            pct = max(0.0, min(1.0, current / maximum))
            # Градиент цвета здоровья: зелёный -> жёлтый -> красный
            if pct > 0.6:
                bar_color = (int(60 + (1 - pct) * 80), 200, 60)
            elif pct > 0.3:
                bar_color = (220, 180, 60)
            else:
                bar_color = (220, 70, 60)
            pygame.draw.rect(self.screen, bar_color, (x, y, int(w * pct), h), border_radius=4)

    def _render_trimmed(self, text, font, max_width, color=WHITE):
        if not text:
            return None
        display = text
        suffix = ""
        while display and font.render(display + suffix, True, color).get_width() > max_width:
            display = display[:-1]
            suffix = "…"
        if not display:
            return None
        return font.render(display + suffix, True, color)

    def draw_character_card(self, char, rect, is_current=False):
        if char is None:
            return
        # Фон HUD с легкой прозрачностью и цветом в зависимости от состояния
        is_alive = getattr(char, 'is_alive', False)
        if is_alive:
            bg_color = (70, 70, 70)
        else:
            bg_color = (110, 30, 30)
        pygame.draw.rect(self.screen, bg_color, rect, border_radius=10)
        if is_current and is_alive and self.state in ("player_turn", "choose_item"):
            pygame.draw.rect(self.screen, YELLOW, rect, width=3, border_radius=10)

        padding = 10
        text_x = rect.x + padding
        y = rect.y + padding

        max_name_width = rect.width - 2 * padding
        role = getattr(char, 'role', 'Персонаж')
        name = getattr(char, 'name', 'Неизвестно')
        name_text = self._render_trimmed(f"{role} {name}", self.hud_font, max_name_width)
        if name_text:
            self.screen.blit(name_text, (text_x, y))
            y += name_text.get_height() + 4

        # HP
        hp = getattr(char, 'hp', 0)
        max_hp = getattr(char, 'max_hp', 1)
        hp_text = self.tiny_font.render(f"HP: {hp}/{max_hp}", True, WHITE)
        self.screen.blit(hp_text, (text_x, y))
        y += hp_text.get_height() + 2

        # MP (если есть у персонажа) — показываем только текущее значение, отдельной строкой
        mp = getattr(char, 'mp', None)
        if mp is not None:
            mp_label = f"MP: {mp}"
            mp_text = self._render_trimmed(mp_label, self.tiny_font, rect.width - 2 * padding)
            if mp_text:
                self.screen.blit(mp_text, (text_x, y))
                y += mp_text.get_height() + 2

        # Полоска HP под текстом
        self.draw_hp_bar(text_x, y, rect.width - 2 * padding, 10, hp, max_hp)
        y += 14

        # Эффекты кратко (каждый эффект на новой строке, размещаем после HP)
        # Для босса эффекты не отображаем
        role = getattr(char, 'role', '')
        if role != "Босс":
            effects = getattr(char, 'effects', [])
            if effects:
                max_width = rect.width - 2 * padding
                line_height = self.tiny_font.get_height() + 2
                for eff in effects:
                    if eff is not None:
                        eff_str = f"{getattr(eff, 'name', 'Эффект')}({getattr(eff, 'duration', 0)})"
                        eff_surf = self._render_trimmed(eff_str, self.tiny_font, max_width)
                        if eff_surf:
                            # Размещаем эффекты после полоски HP с отступом, каждый на новой строке
                            self.screen.blit(eff_surf, (text_x, y))
                            y += line_height

        if not char.is_alive:
            status = self.tiny_font.render("МЁРТВ", True, (255, 180, 180))
            self.screen.blit(status, (text_x, y))

    def draw_log(self):
        # Лог над панелью действий, текст всегда внутри рамки
        log_rect = self.log_rect
        pygame.draw.rect(self.screen, (25, 25, 25), log_rect, border_radius=8)
        pygame.draw.rect(self.screen, LIGHT_GRAY, log_rect, width=2, border_radius=8)

        if not self.log_lines:
            return

        # Показываем только последнее сообщение, разбивая его по словам на несколько строк
        text = self.log_lines[-1]
        line_height = self.small_font.get_height() + 4
        max_lines = (log_rect.height - 20) // line_height
        max_line_width = log_rect.width - 24  # Отступы слева и справа (по 12px с каждой стороны)

        words = text.split(" ")
        lines = []
        current = ""
        for word in words:
            candidate = (current + " " + word).strip() if current else word
            surf = self.small_font.render(candidate, True, WHITE)
            if surf.get_width() <= max_line_width:
                current = candidate
            else:
                if current:
                    lines.append(current)
                current = word
        if current:
            lines.append(current)

        # Если строк больше, чем влезает по высоте, показываем только первые
        lines = lines[:max_lines]

        y = log_rect.y + 10
        for text_line in lines:
            surf = self.small_font.render(text_line, True, WHITE)
            self.screen.blit(surf, (log_rect.x + 12, y))
            y += line_height
            if y + line_height > log_rect.y + log_rect.height - 10:
                break

    def draw_round_info(self):
        text = self.font.render(f"Раунд {self.round}", True, WHITE)
        rect = text.get_rect()
        # Размещаем справа, с отступом от правого края
        self.screen.blit(text, (WIDTH - rect.width - 20, 24))

        hero = self.get_current_hero()
        if self.state == "player_turn" and hero:
            info = self.small_font.render(f"Ход героя: {hero.name}", True, WHITE)
            info_rect = info.get_rect(center=(WIDTH // 2, 50))
            self.screen.blit(info, info_rect.topleft)
        elif self.state == "boss_turn":
            info = self.small_font.render(f"Ход босса: {self.boss.name}", True, WHITE)
            info_rect = info.get_rect(center=(WIDTH // 2, 50))
            self.screen.blit(info, info_rect.topleft)
        elif self.state == "battle_over":
            info = self.small_font.render("Бой завершён. Нажмите ESC для выхода.", True, WHITE)
            info_rect = info.get_rect(center=(WIDTH // 2, 50))
            self.screen.blit(info, info_rect.topleft)

    def draw_item_modal(self):
        if self.state != "choose_item":
            return
        # затемнение фона
        overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 150))
        self.screen.blit(overlay, (0, 0))

        pygame.draw.rect(self.screen, (30, 30, 30), self.item_modal_rect, border_radius=10)
        pygame.draw.rect(self.screen, YELLOW, self.item_modal_rect, width=2, border_radius=10)

        title = self.font.render("Выберите предмет", True, WHITE)
        self.screen.blit(title, (self.item_modal_rect.x + 20, self.item_modal_rect.y + 10))

        for btn in self.item_buttons:
            btn.draw(self.screen)

    def draw(self):
        # Экранный shake
        shake_x = 0
        shake_y = 0
        if self.screen_shake["intensity"] > 0:
            shake_x = random.randint(-int(self.screen_shake["intensity"]), int(self.screen_shake["intensity"]))
            shake_y = random.randint(-int(self.screen_shake["intensity"]), int(self.screen_shake["intensity"]))

        # Используем основную поверхность (shake применяется через offset при blit)
        temp_surface = self.screen
        temp_surface.fill((10, 20, 70))

        # Красочный фон: градиентное небо, солнце, горы, трава и земля
        # простейший вертикальный "градиент"
        for i in range(80):
            c = 10 + i
            pygame.draw.rect(self.screen, (c, c + 20, 120 + i),
                             (0, i * (HEIGHT // 160), WIDTH, HEIGHT // 160))
        # солнце
        pygame.draw.circle(self.screen, (255, 230, 150), (120, 80), 30)
        # горы
        pygame.draw.polygon(self.screen, (40, 60, 110),
                            [(200, HEIGHT - 260), (420, 140), (640, HEIGHT - 260)])
        pygame.draw.polygon(self.screen, (30, 50, 100),
                            [(520, HEIGHT - 260), (820, 120), (1120, HEIGHT - 260)])
        pygame.draw.rect(self.screen, (30, 110, 55), (0, HEIGHT - 220, WIDTH, 40))  # трава
        pygame.draw.rect(self.screen, (55, 38, 22), (0, HEIGHT - 180, WIDTH, 200))  # земля

        # 2D‑модельки героев (спрайты из assets или детализированные человечки)
        for idx, (hero, (hx, hy)) in enumerate(self.hero_positions.items()):
            alive_color = {
                "Воин": (200, 70, 70),
                "Маг": (90, 70, 200),
                "Лучник": (60, 160, 80),
                "Лекарь": (200, 200, 80),
            }.get(hero.role, (120, 200, 255))
            color = alive_color if hero.is_alive else (90, 90, 90)

            # лёгкая анимация покачивания по синусу
            bob = int(4 * math.sin(self.time * 2 + idx))
            hy_anim = hy + bob

            anim_cfg = self.hero_anim.get(hero.role)
            if anim_cfg:
                sheet = anim_cfg.get("sheet")
                if sheet is None:
                    anim_cfg = None  # Пропускаем если нет sheet
                elif hero.is_alive:
                    # Проверяем, есть ли активная анимация атаки
                    if hero in self.attack_animations:
                        anim = self.attack_animations[hero]
                        if "attack" in anim_cfg and anim_cfg["attack"]:
                            # Показываем анимацию атаки
                            indices = anim_cfg["attack"]
                            frame = sheet.get_frame(indices, anim["time"], speed=15.0)
                        elif "idle" in anim_cfg and anim_cfg["idle"]:
                            # Если нет кадров атаки, используем idle
                            indices = anim_cfg["idle"]
                            frame = sheet.get_frame(indices, self.time, speed=8.0)
                        else:
                            frame = None
                    elif "idle" in anim_cfg and anim_cfg["idle"]:
                        indices = anim_cfg["idle"]
                        frame = sheet.get_frame(indices, self.time, speed=8.0)
                    else:
                        frame = None
                else:
                    # Для мёртвого героя показываем последний кадр анимации смерти
                    if sheet and hasattr(sheet, 'frames'):
                        death_indices = anim_cfg.get("death", [])
                        if death_indices and len(sheet.frames) > 0:
                            last_idx = death_indices[-1]
                            if 0 <= last_idx < len(sheet.frames):
                                frame = sheet.frames[last_idx]
                            else:
                                frame = None
                        else:
                            frame = None
                    else:
                        frame = None
                if frame:
                    rect = frame.get_rect(midbottom=(hx, hy_anim + 20))
                    temp_surface.blit(frame, rect)
            else:
                # ноги
                pygame.draw.rect(self.screen, (30, 30, 30), (hx - 10, hy_anim + 18, 8, 26))
                pygame.draw.rect(self.screen, (30, 30, 30), (hx + 2, hy_anim + 18, 8, 26))
                # тень под ногами
                pygame.draw.ellipse(self.screen, (20, 20, 20), (hx - 18, hy_anim + 42, 36, 10))
                # туловище
                pygame.draw.rect(self.screen, color, (hx - 18, hy_anim - 4, 36, 40), border_radius=10)
                # пояс
                pygame.draw.rect(self.screen, (30, 30, 30), (hx - 18, hy_anim + 8, 36, 4))
                # плечи
                pygame.draw.circle(self.screen, color, (hx - 18, hy_anim + 4), 8)
                pygame.draw.circle(self.screen, color, (hx + 18, hy_anim + 4), 8)
                # руки
                pygame.draw.rect(self.screen, (240, 220, 200), (hx - 30, hy_anim + 2, 12, 18), border_radius=4)
                pygame.draw.rect(self.screen, (240, 220, 200), (hx + 18, hy_anim + 2, 12, 18), border_radius=4)
                # голова
                pygame.draw.circle(self.screen, (240, 220, 200), (hx, hy_anim - 30), 16)
                # волосы
                pygame.draw.arc(self.screen, (80, 60, 40), (hx - 18, hy_anim - 48, 36, 24), 3.4, 6.1, 3)
                # глаза
                pygame.draw.circle(self.screen, (20, 20, 20), (hx - 5, hy_anim - 30), 2)
                pygame.draw.circle(self.screen, (20, 20, 20), (hx + 5, hy_anim - 30), 2)
                # рот
                pygame.draw.arc(self.screen, (150, 80, 80), (hx - 6, hy_anim - 24, 12, 6), 3.5, 5.8, 2)

            # Оружие в зависимости от роли (только для резервных рисованных моделей,
            # для спрайтов оружие уже нарисовано в самих спрайтах)
            if not anim_cfg:
                if hero.role == "Воин":
                    # щит и меч
                    pygame.draw.circle(self.screen, (120, 80, 40), (hx - 32, hy + 6), 14)
                    pygame.draw.circle(self.screen, (200, 190, 150), (hx - 32, hy + 6), 8, 2)
                    pygame.draw.rect(self.screen, (200, 200, 210), (hx + 20, hy - 6, 8, 36))
                    pygame.draw.rect(self.screen, (220, 220, 230), (hx + 20, hy - 12, 32, 8))
                elif hero.role == "Маг":
                    # посох с кристаллом и ореол магии
                    pygame.draw.rect(self.screen, (120, 80, 40), (hx + 26, hy - 16, 5, 38))
                    pygame.draw.circle(self.screen, (120, 210, 255), (hx + 28, hy - 20), 8)
                    pygame.draw.circle(self.screen, (80, 160, 230), (hx + 28, hy - 20), 12, 2)
                    pygame.draw.circle(self.screen, (150, 90, 200), (hx + 28, hy - 20), 16, 1)
                elif hero.role == "Лучник":
                    # лук и тетива
                    pygame.draw.arc(self.screen, (170, 130, 70),
                                    (hx + 12, hy - 18, 22, 36), 3.4, 8.1, 3)
                    pygame.draw.line(self.screen, (230, 230, 230), (hx + 14, hy - 4), (hx + 30, hy + 16), 2)
                    # стрела
                    pygame.draw.line(self.screen, (230, 230, 230), (hx + 18, hy + 4), (hx + 34, hy + 12), 2)
                    pygame.draw.polygon(self.screen, (230, 230, 230),
                                        [(hx + 34, hy + 12), (hx + 30, hy + 8), (hx + 30, hy + 16)])
                    # колчан
                    pygame.draw.rect(self.screen, (120, 70, 30), (hx - 30, hy - 4, 10, 28))
                elif hero.role == "Лекарь":
                    # книга и посох‑крест
                    pygame.draw.rect(self.screen, (230, 230, 240), (hx + 18, hy - 4, 22, 16))
                    pygame.draw.line(self.screen, (200, 60, 60), (hx + 20, hy + 3), (hx + 34, hy + 3), 2)
                    pygame.draw.line(self.screen, (200, 60, 60), (hx + 27, hy - 3), (hx + 27, hy + 9), 2)
                    pygame.draw.rect(self.screen, (220, 220, 220), (hx - 34, hy - 2, 6, 26))
                    pygame.draw.rect(self.screen, (200, 200, 200), (hx - 36, hy - 6, 10, 6))

        # Моделька босса (спрайт из assets или детализированный дракон)
        bx, by = self.boss_position
        if self.boss_anim:
            sheet = self.boss_anim.get("sheet")
            if sheet is None:
                self.boss_anim = None  # Пропускаем если нет sheet
            elif self.boss.is_alive:
                indices = self.boss_anim.get("idle", [])
                if indices:
                    frame = sheet.get_frame(indices, self.time, speed=6.0)
                else:
                    frame = None
            else:
                # Для мёртвого босса показываем последний кадр анимации смерти
                if sheet and hasattr(sheet, 'frames'):
                    death_indices = self.boss_anim.get("death", [])
                    if death_indices and len(sheet.frames) > 0:
                        last_idx = death_indices[-1]
                        if 0 <= last_idx < len(sheet.frames):
                            frame = sheet.frames[last_idx]
                        else:
                            frame = None
                    else:
                        frame = None
                else:
                    frame = None
            if frame:
                # Разворачиваем босса в сторону героев
                frame = pygame.transform.flip(frame, True, False)
                rect = frame.get_rect(midbottom=(bx, by + 40))
                self.screen.blit(frame, rect)
        else:
            boss_color = (180, 40, 40) if self.boss.is_alive else (90, 40, 40)
            darker = (120, 25, 25)
            highlight = (220, 110, 110)
            # тело
            pygame.draw.ellipse(self.screen, boss_color, (bx - 100, by - 50, 200, 110))
            pygame.draw.ellipse(self.screen, highlight, (bx - 70, by - 20, 120, 60))
            # спинные шипы
            for i in range(5):
                spike_x = bx - 30 - i * 30
                pygame.draw.polygon(self.screen, (230, 200, 140),
                                    [(spike_x, by - 10), (spike_x - 12, by - 60), (spike_x + 12, by - 15)])
            # хвост
            pygame.draw.polygon(self.screen, boss_color,
                                [(bx - 100, by + 10), (bx - 170, by + 50), (bx - 90, by + 60)])
            pygame.draw.circle(self.screen, darker, (bx - 170, by + 50), 10)
            # крыло
            pygame.draw.polygon(self.screen, (150, 30, 30),
                                [(bx - 10, by - 10), (bx + 80, by - 110), (bx + 120, by - 20)])
            pygame.draw.lines(self.screen, darker, False,
                              [(bx + 10, by - 20), (bx + 70, by - 70), (bx + 110, by - 20)], 3)
            # голова
            pygame.draw.circle(self.screen, boss_color, (bx + 70, by - 20), 36)
            pygame.draw.circle(self.screen, highlight, (bx + 70, by - 15), 24)
            # глаз
            pygame.draw.circle(self.screen, (250, 250, 250), (bx + 84, by - 28), 10)
            pygame.draw.circle(self.screen, (40, 0, 0), (bx + 86, by - 28), 4)
            # пасть
            pygame.draw.rect(self.screen, (120, 10, 10), (bx + 54, by - 6, 42, 12))
            pygame.draw.polygon(self.screen, (240, 240, 240),
                                [(bx + 60, by - 6), (bx + 66, by + 6), (bx + 72, by - 6)])
            # рога
            pygame.draw.polygon(self.screen, (230, 200, 140),
                                [(bx + 52, by - 48), (bx + 40, by - 86), (bx + 60, by - 50)])
            pygame.draw.polygon(self.screen, (230, 200, 140),
                                [(bx + 90, by - 48), (bx + 104, by - 84), (bx + 116, by - 46)])

        # Снаряды (выстрелы)
        for p in self.projectiles:
            sx, sy = p["start"]
            ex, ey = p["end"]
            t = max(0.0, min(1.0, p["progress"]))
            x = sx + (ex - sx) * t
            y = sy + (ey - sy) * t
            p_type = p.get("type", "bolt")
            size = p.get("size", 6)
            color = p["color"]
            if p_type == "orb":
                pygame.draw.circle(self.screen, color, (int(x), int(y)), size)
                pygame.draw.circle(self.screen, (200, 255, 255), (int(x), int(y)), size + 3, 1)
            elif p_type == "arrow":
                pygame.draw.line(self.screen, color, (int(x - size), int(y)),
                                 (int(x + size), int(y)), 3)
                pygame.draw.polygon(self.screen, color,
                                    [(int(x + size), int(y)),
                                     (int(x + size - 4), int(y - 3)),
                                     (int(x + size - 4), int(y + 3))])
            elif p_type == "heal":
                pygame.draw.circle(self.screen, (220, 255, 220), (int(x), int(y)), size + 2)
                pygame.draw.line(self.screen, (120, 220, 120),
                                 (int(x - size // 2), int(y)),
                                 (int(x + size // 2), int(y)), 2)
                pygame.draw.line(self.screen, (120, 220, 120),
                                 (int(x), int(y - size // 2)),
                                 (int(x), int(y + size // 2)), 2)
            else:
                pygame.draw.circle(self.screen, color, (int(x), int(y)), size)

        # Летающие числа урона/лечения
        for ft in self.float_texts:
            size_mult = ft.get("size_mult", 1.0)
            if size_mult > 1.0:
                # Для критических ударов используем больший шрифт
                crit_font = pygame.font.SysFont("verdana", int(18 * size_mult))
                surf = crit_font.render(ft["text"], True, ft["color"])
            else:
                surf = self.small_font.render(ft["text"], True, ft["color"])
            self.screen.blit(surf, (int(ft["x"] - surf.get_width() / 2), int(ft["y"])))

        # Эффекты критических ударов (вспышки)
        for crit in self.crit_effects:
            if "life" not in crit or crit["life"] <= 0:
                continue
            progress = crit["time"] / crit["life"]
            alpha = int(255 * (1.0 - progress))
            size = int(30 + 20 * progress)
            # Рисуем вспышку
            flash_surf = pygame.Surface((size * 2, size * 2), pygame.SRCALPHA)
            pygame.draw.circle(flash_surf, (255, 255, 0, alpha), (size, size), size)
            self.screen.blit(flash_surf, (crit["x"] - size, crit["y"] - size))

        # Прогресс-бар босса вверху экрана
        boss_bar_width = 600
        boss_bar_height = 30
        boss_bar_x = (WIDTH - boss_bar_width) // 2
        boss_bar_y = 10
        boss_bar_rect = pygame.Rect(boss_bar_x, boss_bar_y, boss_bar_width, boss_bar_height)

        # Фон прогресс-бара
        pygame.draw.rect(self.screen, (40, 40, 40), boss_bar_rect, border_radius=5)
        if self.boss.max_hp > 0:
            hp_pct = max(0.0, min(1.0, self.boss.hp / self.boss.max_hp))
            bar_color = GREEN if hp_pct > 0.5 else (YELLOW if hp_pct > 0.25 else RED)
            if self.boss_phase2:
                # Во второй фазе бар становится краснее
                bar_color = (255, 100, 100)
            fill_width = int(boss_bar_width * hp_pct)
            if fill_width > 0:
                pygame.draw.rect(self.screen, bar_color,
                                 (boss_bar_x, boss_bar_y, fill_width, boss_bar_height), border_radius=5)

        # Текст с HP босса
        boss_hp_text = self.small_font.render(f"{self.boss.name}: {self.boss.hp}/{self.boss.max_hp}", True, WHITE)
        text_rect = boss_hp_text.get_rect(center=boss_bar_rect.center)
        self.screen.blit(boss_hp_text, text_rect.topleft)

        # Индикатор фазы
        if self.boss_phase2:
            phase_text = self.tiny_font.render("ФАЗА 2", True, (255, 100, 100))
            self.screen.blit(phase_text, (boss_bar_x + boss_bar_width - 60, boss_bar_y + 5))

        # HUD: компактные карточки заметно выше персонажей, раздельные
        card_w = 180
        card_h = 75  # Увеличена высота для размещения всех элементов без налезания
        offset_y = 240
        card_gap = 15  # Отступ между карточками для визуального разделения
        for idx, (hero, (hx, hy)) in enumerate(self.hero_positions.items()):
            # Добавляем небольшой сдвиг для визуального разделения
            x_offset = (idx - 1.5) * card_gap
            rect = pygame.Rect(hx - card_w // 2 + x_offset, hy - offset_y, card_w, card_h)
            is_current = (hero == self.get_current_hero())
            self.draw_character_card(hero, rect, is_current=is_current)

        # Босс: карточка над моделькой, отдельно справа
        bx, by = self.boss_position
        boss_rect = pygame.Rect(bx - card_w // 2, by - offset_y - 10, card_w, card_h)
        self.draw_character_card(self.boss, boss_rect, is_current=(self.state == "boss_turn"))

        # Лог и раунд
        self.draw_round_info()

        # Подсказка по способности текущего героя (в левом нижнем углу)
        self.draw_skill_hint()

        # Кнопки действий
        if self.state in ("player_turn", "choose_item"):
            for btn in self.buttons:
                btn.draw(self.screen)

        # Лог поверх кнопок внизу справа
        self.draw_log()

        # Модальное окно предметов
        self.draw_item_modal()

    def draw_skill_hint(self):
        """Отдельное окошко с кратким описанием способности текущего героя."""
        if self.state not in ("player_turn", "choose_item"):
            return

        hero = self.get_current_hero()
        if hero is None or not hero.is_alive:
            return

        role = getattr(hero, "role", "")
        desc = self.skill_descriptions.get(role)
        if not desc:
            return

        # Окошко слева, в нижней части экрана, между персонажами и кнопками,
        # чтобы ничего не загораживать и при этом хорошо читаться
        box_width = 520
        box_height = 110
        box_x = 20
        # Располагаем чуть выше кнопок, но ниже персонажей
        box_y = HEIGHT - box_height - 90
        rect = pygame.Rect(box_x, box_y, box_width, box_height)

        pygame.draw.rect(self.screen, (25, 25, 25), rect, border_radius=8)
        pygame.draw.rect(self.screen, LIGHT_GRAY, rect, width=2, border_radius=8)

        # Заголовок
        title = self.small_font.render("Способность", True, WHITE)
        self.screen.blit(title, (rect.x + 10, rect.y + 6))

        # Имя героя
        name_surf = self.tiny_font.render(f"{hero.role} {hero.name}", True, WHITE)
        self.screen.blit(name_surf, (rect.x + 10, rect.y + 6 + title.get_height() + 2))

        # Краткое описание (обрезаем по ширине)
        max_width = rect.width - 20
        desc_surf = self._render_trimmed(desc, self.tiny_font, max_width)
        if desc_surf:
            self.screen.blit(desc_surf, (rect.x + 10, rect.y + rect.height - desc_surf.get_height() - 8))


def run_game():
    pygame.init()
    pygame.display.set_caption("Пати против босса")
    screen = pygame.display.set_mode((WIDTH, HEIGHT))

    # Более крупный и контрастный шрифт для удобства чтения
    font = pygame.font.SysFont("verdana", 24)
    small_font = pygame.font.SysFont("verdana", 18)

    clock = pygame.time.Clock()
    battle = PygameBattle(screen, font, small_font)

    running = True
    while running:
        dt = clock.tick(FPS) / 1000.0

        for event in pygame.event.get():
            battle.handle_event(event)

        battle.update(dt)
        battle.draw()
        pygame.display.flip()


if __name__ == "__main__":
    run_game()




