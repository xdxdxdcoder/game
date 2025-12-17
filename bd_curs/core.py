import random
from abc import ABC, abstractmethod


class BoundedStat:
    """Дескриптор для валидации характеристик"""

    def __init__(self, min_val=0, max_val=1000):
        self.min_val = min_val
        self.max_val = max_val

    def __set_name__(self, owner, name):
        self.name = f"_{name}"

    def __get__(self, instance, owner):
        return instance.__dict__.get(self.name, self.min_val)

    def __set__(self, instance, value):
        instance.__dict__[self.name] = max(self.min_val, min(self.max_val, value))


class Human:
    """Базовый класс для всех персонажей"""

    def __init__(self, name, hp, damage, role="Персонаж"):
        self.name = name
        self.hp = hp
        self.max_hp = hp
        self.damage = damage
        self.role = role
        self.effects = []
        self.agility = 10  # Базовая ловкость для порядка ходов

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
        """Обновляем эффекты в начале хода"""
        for effect in self.effects[:]:
            effect.duration -= 1
            if effect.duration <= 0:
                self.remove_effect(effect)
            else:
                effect.on_turn(self)

    def take_damage(self, damage):
        """Получение урона с учетом эффектов"""
        actual_damage = damage
        for effect in self.effects:
            if hasattr(effect, 'absorb_damage'):
                actual_damage = effect.absorb_damage(actual_damage)
                if actual_damage <= 0:
                    break

        self.hp = max(0, self.hp - actual_damage)
        return actual_damage

    def attack(self, target):
        """Базовая атака"""
        damage = random.randint(self.damage - 5, self.damage + 5)
        actual_damage = target.take_damage(damage)
        return actual_damage

    def __str__(self):
        status = "ЖИВ" if self.is_alive else "МЕРТВ"
        effects_str = ", ".join([f"{eff.name}({eff.duration})" for eff in self.effects]) if self.effects else "нет"
        return f"{self.role} {self.name}: {status} HP: {self.hp}/{self.max_hp} | Эффекты: {effects_str}"


class Character(Human):
    """Класс персонажа игрока"""

    def __init__(self, name, hp, damage, role="Персонаж"):
        super().__init__(name, hp, damage, role)
        # Импорт с учётом запуска как пакета bd_curs
        try:
            from items import Inventory
        except ImportError:
            from .items import Inventory
        self.inventory = Inventory()

    def use_item(self, item_name):
        """Использование предмета из инвентаря"""
        if self.inventory.has_item(item_name):
            item = self.inventory.get_item(item_name)
            result = item.use(self)
            self.inventory.remove_item(item_name, 1)
            return result
        return f"Предмет {item_name} не найден в инвентаре"


class CritMixin:
    """Миксин для критического удара"""

    def __init__(self, crit_chance=0.2, crit_multiplier=2.0):
        self.crit_chance = crit_chance
        self.crit_multiplier = crit_multiplier

    def check_critical(self, damage):
        """Проверка критического удара"""
        if random.random() < self.crit_chance:
            critical_damage = int(damage * self.crit_multiplier)
            print("Критический удар!")
            return critical_damage
        return damage