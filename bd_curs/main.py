import random

# Импорты, которые работают и при запуске напрямую, и как пакет bd_curs
try:
    from effects import Effect, PoisonEffect, ShieldEffect, StrengthBuffEffect
    from items import Inventory, HealthPotion, ManaPotion, DamagePotion
except ImportError:
    from .effects import Effect, PoisonEffect, ShieldEffect, StrengthBuffEffect
    from .items import Inventory, HealthPotion, ManaPotion, DamagePotion


class Character:
    def __init__(self, name, hp, damage, role="Персонаж"):
        self.name = name
        self.hp = hp
        self.max_hp = hp
        self.damage = damage
        self.base_damage = damage
        self.role = role
        self.effects = []
        self.inventory = Inventory()

    @property
    def is_alive(self):
        return self.hp > 0

    def add_effect(self, effect):
        self.effects.append(effect)
        effect.on_apply(self)
        print(f"{self.name} получает эффект: {effect.name}")

    def remove_effect(self, effect):
        if effect in self.effects:
            effect.on_remove(self)
            self.effects.remove(effect)

    def update_effects(self):
        for effect in self.effects[:]:
            effect.duration -= 1
            if effect.duration <= 0:
                self.remove_effect(effect)
            else:
                effect.on_turn(self)

    def calculate_damage(self):
        damage = self.base_damage
        for effect in self.effects:
            if hasattr(effect, 'damage_bonus'):
                damage += effect.damage_bonus
        return max(1, damage)

    def take_damage(self, damage):
        # Проверяем щиты
        actual_damage = damage
        for effect in self.effects:
            if isinstance(effect, ShieldEffect):
                actual_damage = effect.absorb_damage(actual_damage)
                if actual_damage <= 0:
                    break

        self.hp = max(0, self.hp - actual_damage)
        return actual_damage

    def attack(self, target):
        damage = random.randint(self.calculate_damage() - 5, self.calculate_damage() + 5)
        actual_damage = target.take_damage(damage)
        return actual_damage

    def use_item(self, item_name):
        if self.inventory.has_item(item_name):
            item = self.inventory.get_item(item_name)
            result = item.use(self)
            self.inventory.remove_item(item_name)
            return result
        return f"Предмет {item_name} не найден в инвентаре"

    def __str__(self):
        status = "ЖИВ" if self.is_alive else "МЕРТВ"
        effects_str = ", ".join([f"{eff.name}({eff.duration})" for eff in self.effects]) if self.effects else "нет"
        return f"{self.role} {self.name}: {status} HP: {self.hp}/{self.max_hp} | Эффекты: {effects_str}"


class Battle:
    def __init__(self, heroes, boss):
        self.heroes = heroes
        self.boss = boss
        self.round = 0

        for hero in heroes:
            hero.heroes = heroes
            hero.boss = boss
        boss.heroes = heroes

    def is_battle_over(self):
        heroes_alive = any(hero.is_alive for hero in self.heroes)
        boss_alive = self.boss.is_alive
        return not heroes_alive or not boss_alive

    def start_round(self):
        self.round += 1
        print(f"\n" + "=" * 60)
        print(f"РАУНД {self.round}")
        print("=" * 60)

        # Обновляем эффекты в начале раунда
        for hero in self.heroes:
            if hero.is_alive:
                hero.update_effects()
        if self.boss.is_alive:
            self.boss.update_effects()

        # Ходы героев
        for hero in self.heroes:
            if hero.is_alive and self.boss.is_alive:
                self.hero_turn(hero)

        # Ход босса
        if self.boss.is_alive:
            self.boss_turn()

        # Показать статус
        self.show_status()

    def hero_turn(self, hero):
        print(f"\n--- Ход {hero.name} ---")
        print("Доступные действия:")
        print("1. Атаковать")
        print("2. Использовать предмет")
        print("3. Пропустить ход")

        if any(isinstance(effect, PoisonEffect) for effect in hero.effects):
            print("ВНИМАНИЕ: Вы отравлены!")

        while True:
            choice = input("Выберите действие (1-3): ").strip()

            if choice == "1":
                damage = hero.attack(self.boss)
                print(f"{hero.name} атакует {self.boss.name} и наносит {damage} урона!")
                break
            elif choice == "2":
                self.use_item_menu(hero)
                break
            elif choice == "3":
                print(f"{hero.name} пропускает ход")
                break
            else:
                print("Неверный выбор. Попробуйте снова.")

    def use_item_menu(self, hero):
        print("\nИнвентарь:")
        hero.inventory.show()

        if not hero.inventory.items:
            print("Инвентарь пуст!")
            return

        item_names = list(hero.inventory.items.keys())
        for i, item_name in enumerate(item_names, 1):
            print(f"{i}. {item_name}")

        try:
            choice = int(input("Выберите предмет: ")) - 1
            if 0 <= choice < len(item_names):
                item_name = item_names[choice]
                result = hero.use_item(item_name)
                print(result)
            else:
                print("Неверный выбор")
        except ValueError:
            print("Введите число")

    def boss_turn(self):
        print(f"\n--- Ход {self.boss.name} ---")

        # Босс выбирает действие
        action = random.choice(["attack", "skill", "item"])

        if action == "attack" or not self.boss.inventory.items:
            alive_heroes = [hero for hero in self.heroes if hero.is_alive]
            if alive_heroes:
                target = random.choice(alive_heroes)
                damage = self.boss.attack(target)
                print(f"{self.boss.name} атакует {target.name} и наносит {damage} урона!")

        elif action == "skill":
            self.boss.use_skill()

        elif action == "item" and self.boss.inventory.items:
            item_name = random.choice(list(self.boss.inventory.items.keys()))
            result = self.boss.use_item(item_name)
            print(result)

    def show_status(self):
        print(f"\n--- Статус боя ---")
        print("Герои:")
        for hero in self.heroes:
            print(f"  {hero}")

        print(f"Босс: {self.boss}")


def main():
    # Импорт героев и босса так, чтобы работало и при запуске файла напрямую, и как пакет
    try:
        from characters import Warrior, Mage, Archer, Healer
        from boss import Boss
    except ImportError:
        from .characters import Warrior, Mage, Archer, Healer
        from .boss import Boss

    print("ПАТИ ПРОТИВ БОССА")
    print("=" * 60)

    # Создаем команду
    warrior = Warrior("Волк")
    mage = Mage("Пудж")
    archer = Archer("Стив")
    healer = Healer("Целитель")

    heroes = [warrior, mage, archer, healer]

    # Создаем босса
    boss = Boss("Дракон")

    # Даем начальные предметы
    for hero in heroes:
        hero.inventory.add_item(HealthPotion(), 2)
        hero.inventory.add_item(ManaPotion(), 1)
        hero.inventory.add_item(DamagePotion(), 1)

    boss.inventory.add_item(HealthPotion(), 3)

    print("Наша команда:")
    for hero in heroes:
        print(f"  {hero}")
        hero.inventory.show()
        print()

    print(f"Противник: {boss}")

    # Создаем бой
    battle = Battle(heroes, boss)

    print("\nНАЧАЛО БИТВЫ!")
    input("Нажмите Enter чтобы начать...")

    # Игровой цикл
    while not battle.is_battle_over():
        battle.start_round()
        if not battle.is_battle_over():
            input("\nНажмите Enter для следующего раунда...")

    # Результаты
    print(f"\n" + "=" * 60)
    if not boss.is_alive:
        print("ПОБЕДА! Босс повержен!")
    else:
        print("ПОРАЖЕНИЕ... Босс одолел героев")

    print("\nФинальный статус:")
    battle.show_status()


if __name__ == "__main__":
    main()