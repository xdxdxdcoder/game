import random

# Импорт эффектов так, чтобы модуль можно было запускать и как скрипт, и как часть пакета bd_curs
try:
    from effects import PoisonEffect, ShieldEffect, StrengthBuffEffect
except ImportError:
    from .effects import PoisonEffect, ShieldEffect, StrengthBuffEffect


class TurnOrder:
    """Итератор для определения порядка ходов на основе ловкости"""

    def __init__(self, participants):
        self.participants = sorted(
            participants,
            key=lambda x: getattr(x, 'agility', 10),
            reverse=True
        )
        self.index = 0

    def __iter__(self):
        return self

    def __next__(self):
        if self.index < len(self.participants):
            participant = self.participants[self.index]
            self.index += 1
            return participant
        raise StopIteration


class BattleLogger:
    """Контекстный менеджер для логирования боя"""

    def __init__(self, filename="battle_log.txt"):
        self.filename = filename
        self.log_file = None

    def __enter__(self):
        self.log_file = open(self.filename, 'w', encoding='utf-8')
        self.log_file.write("=== ЛОГ БОЯ ===\n")
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.log_file:
            self.log_file.close()

    def log(self, message):
        """Записать сообщение в лог"""
        print(message)
        if self.log_file:
            self.log_file.write(message + "\n")


class Battle:
    def __init__(self, heroes, boss):
        self.heroes = heroes
        self.boss = boss
        self.round = 0
        self.logger = BattleLogger()

        # Добавляем ссылки на бой для всех персонажей
        for hero in heroes:
            hero.heroes = heroes
            hero.boss = boss
            if not hasattr(hero, 'agility'):
                hero.agility = random.randint(10, 20)
        boss.heroes = heroes
        if not hasattr(boss, 'agility'):
            boss.agility = 15

    def is_battle_over(self):
        heroes_alive = any(hero.is_alive for hero in self.heroes)
        boss_alive = self.boss.is_alive
        return not heroes_alive or not boss_alive

    def get_winner(self):
        """Определить победителя боя"""
        if not self.boss.is_alive:
            return "Герои"
        elif not any(hero.is_alive for hero in self.heroes):
            return "Босс"
        return None

    def get_battle_stats(self):
        """Получить статистику боя"""
        return {
            "rounds": self.round,
            "boss_hp": self.boss.hp,
            "heroes_alive": sum(1 for hero in self.heroes if hero.is_alive),
            "winner": self.get_winner()
        }

    def start_round(self):
        self.round += 1

        with self.logger as log:
            log.log(f"\n" + "=" * 60)
            log.log(f"РАУНД {self.round}")
            log.log("=" * 60)

            # Обновляем эффекты в начале раунда
            for hero in self.heroes:
                if hero.is_alive:
                    hero.update_effects()
            if self.boss.is_alive:
                self.boss.update_effects()

            # Определяем порядок ходов
            all_participants = [h for h in self.heroes if h.is_alive]
            if self.boss.is_alive:
                all_participants.append(self.boss)

            turn_order = TurnOrder(all_participants)

            # Выполняем ходы в порядке инициативы
            for participant in turn_order:
                if not self.is_battle_over():
                    if participant == self.boss:
                        self.boss_turn(log)
                    else:
                        self.hero_turn(participant, log)

                if self.is_battle_over():
                    break

            # Показать статус
            self.show_status(log)

    def hero_turn(self, hero, log):
        log.log(f"\n--- Ход {hero.name} (Ловкость: {hero.agility}) ---")

        # Проверяем, не оглушен ли герой
        stun_effects = [eff for eff in hero.effects if eff.name == "Оглушение"]
        if stun_effects:
            log.log(f"{hero.name} оглушен и пропускает ход!")
            return

        log.log("Доступные действия:")
        log.log("1. Атаковать")
        log.log("2. Использовать предмет")

        # Показываем особые возможности классов
        if hasattr(hero, 'mp') and hero.mp >= 20:
            if hero.role == "Маг":
                log.log("3. Использовать магию яда (20 MP)")
            elif hero.role == "Лекарь":
                log.log("3. Исцелить союзника (25 MP)")

        log.log("4. Пропустить ход")

        # Показываем активные эффекты
        if hero.effects:
            effects_str = ", ".join([f"{eff.name}({eff.duration})" for eff in hero.effects])
            log.log(f"Активные эффекты: {effects_str}")

        while True:
            try:
                choice = input("Выберите действие: ").strip()

                if choice == "1":
                    damage = hero.attack(self.boss)
                    log.log(f"{hero.name} атакует {self.boss.name} и наносит {damage} урона!")
                    break

                elif choice == "2":
                    self.use_item_menu(hero, log)
                    break

                elif choice == "3":
                    if hasattr(hero, 'mp') and hero.mp >= 20:
                        if hero.role == "Маг":
                            try:
                                from effects import PoisonEffect
                            except ImportError:
                                from .effects import PoisonEffect
                            poison = PoisonEffect(duration=2, damage_per_turn=10)
                            self.boss.add_effect(poison)
                            hero.mp -= 20
                            damage = random.randint(25, 35)
                            actual_damage = self.boss.take_damage(damage)
                            log.log(
                                f"{hero.name} использует магию яда! Наносит {actual_damage} урона и отравляет {self.boss.name}!")
                            break
                        elif hero.role == "Лекарь":
                            self.heal_ally(hero, log)
                            break
                    log.log("Недостаточно маны или недоступно!")

                elif choice == "4":
                    log.log(f"{hero.name} пропускает ход")
                    break

                else:
                    log.log("Неверный выбор. Попробуйте снова.")
            except Exception as e:
                log.log(f"Ошибка: {e}")

    def heal_ally(self, healer, log):
        if healer.mp >= 25:
            healer.mp -= 25
            alive_allies = [h for h in self.heroes if h.is_alive and h != healer]
            if alive_allies:
                target = random.choice(alive_allies)
                heal_amount = random.randint(30, 45)
                old_hp = target.hp
                target.hp = min(target.max_hp, target.hp + heal_amount)
                actual_heal = target.hp - old_hp
                log.log(f"{healer.name} исцеляет {target.name} на {actual_heal} HP!")
            else:
                log.log("Нет живых союзников для лечения!")
        else:
            log.log("Недостаточно маны для исцеления!")

    def use_item_menu(self, hero, log):
        log.log("\nИнвентарь:")
        hero.inventory.show()

        if not hero.inventory.items:
            log.log("Инвентарь пуст!")
            return

        item_names = list(hero.inventory.items.keys())
        for i, item_name in enumerate(item_names, 1):
            log.log(f"{i}. {item_name}")

        try:
            choice = int(input("Выберите предмет: ")) - 1
            if 0 <= choice < len(item_names):
                item_name = item_names[choice]
                result = hero.use_item(item_name)
                log.log(result)
            else:
                log.log("Неверный выбор")
        except ValueError:
            log.log("Введите число")

    def boss_turn(self, log):
        log.log(f"\n--- Ход {self.boss.name} (Ловкость: {self.boss.agility}) ---")

        # Босс выбирает действие
        action_weights = {
            "attack": 0.5,
            "skill": 0.3,
            "item": 0.2
        }

        actions = []
        weights = []
        for action, weight in action_weights.items():
            if action == "item" and not self.boss.inventory.items:
                continue
            actions.append(action)
            weights.append(weight)

        if not actions:
            actions = ["attack"]
            weights = [1.0]

        action = random.choices(actions, weights=weights)[0]

        if action == "attack":
            alive_heroes = [hero for hero in self.heroes if hero.is_alive]
            if alive_heroes:
                target = random.choice(alive_heroes)
                damage = self.boss.attack(target)
                log.log(f"{self.boss.name} атакует {target.name} и наносит {damage} урона!")

        elif action == "skill":
            result = self.boss.use_skill()
            log.log(result)

        elif action == "item":
            item_names = list(self.boss.inventory.items.keys())
            if item_names:
                item_name = random.choice(item_names)
                result = self.boss.use_item(item_name)
                log.log(result)

    def show_status(self, log):
        log.log(f"\n--- Статус боя ---")
        log.log("Герои:")
        for hero in self.heroes:
            status = "ЖИВ" if hero.is_alive else "МЕРТВ"
            mp_info = f" MP: {hero.mp}/{hero.max_mp}" if hasattr(hero, 'mp') else ""
            effects_info = f" | Эффекты: {', '.join([f'{eff.name}({eff.duration})' for eff in hero.effects])}" if hero.effects else ""
            log.log(f"  {hero.role} {hero.name}: {status} HP: {hero.hp}/{hero.max_hp}{mp_info}{effects_info}")

        boss_mp_info = f" MP: {self.boss.mp}/{self.boss.max_mp}" if hasattr(self.boss, 'mp') else ""
        boss_effects_info = f" | Эффекты: {', '.join([f'{eff.name}({eff.duration})' for eff in self.boss.effects])}" if self.boss.effects else ""
        log.log(
            f"Босс {self.boss.name}: {'ЖИВ' if self.boss.is_alive else 'МЕРТВ'} HP: {self.boss.hp}/{self.boss.max_hp}{boss_mp_info}{boss_effects_info}")

        # Прогресс боя
        if self.boss.is_alive:
            boss_hp_percent = (self.boss.hp / self.boss.max_hp) * 100
            log.log(f"Оставшееся HP босса: {boss_hp_percent:.1f}%")

    def get_battle_stats(self):
        """Получить статистику боя"""
        return {
            "rounds": self.round,
            "boss_hp": self.boss.hp,
            "heroes_alive": sum(1 for hero in self.heroes if hero.is_alive),
            "winner": self.get_winner()
        }