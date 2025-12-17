# Импорты, которые работают и при запуске напрямую, и при запуске как пакет bd_curs
try:
    from core import Character, CritMixin
except ImportError:
    from .core import Character, CritMixin
import random


class Warrior(Character, CritMixin):
    def __init__(self, name):
        super().__init__(name, 150, 30, "Воин")
        self.mp = 50
        self.max_mp = 50
        self.agility = 12
        CritMixin.__init__(self, crit_chance=0.25, crit_multiplier=2.0)


class Mage(Character):
    def __init__(self, name):
        super().__init__(name, 80, 40, "Маг")
        self.mp = 100
        self.max_mp = 100
        self.agility = 15

    def attack(self, target):
        # Маг может использовать магическую атаку
        if self.mp >= 15 and random.random() < 0.6:
            self.mp -= 15
            try:
                from effects import PoisonEffect
            except ImportError:
                from .effects import PoisonEffect
            poison = PoisonEffect(duration=3, damage_per_turn=8)
            target.add_effect(poison)
            damage = random.randint(20, 30)
            actual_damage = target.take_damage(damage)
            print(f"{self.name} использует ЯДОВИТЫЙ ШАР! Наносит {actual_damage} урона и отравляет {target.name}!")
            return actual_damage
        return super().attack(target)


class Archer(Character, CritMixin):
    def __init__(self, name):
        super().__init__(name, 100, 28, "Лучник")
        self.mp = 40
        self.max_mp = 40
        self.agility = 25
        CritMixin.__init__(self, crit_chance=0.35, crit_multiplier=2.2)


class Healer(Character):
    def __init__(self, name):
        super().__init__(name, 90, 15, "Лекарь")
        self.mp = 80
        self.max_mp = 80
        self.agility = 14

    def attack(self, target):
        # Лекарь предпочитает лечить
        if self.mp >= 20 and random.random() < 0.7:
            self.mp -= 20
            alive_allies = [h for h in self.heroes if h.is_alive]
            if alive_allies:
                heal_target = random.choice(alive_allies)
                heal_amount = random.randint(25, 40)
                old_hp = heal_target.hp
                heal_target.hp = min(heal_target.max_hp, heal_target.hp + heal_amount)
                actual_heal = heal_target.hp - old_hp
                print(f"{self.name} лечит {heal_target.name} на {actual_heal} HP!")
                return 0
        return super().attack(target)