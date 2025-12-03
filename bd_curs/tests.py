import unittest
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from core import Character
from characters import Warrior, Mage, Healer, Archer
from boss import Boss
from effects import PoisonEffect, ShieldEffect, StrengthBuffEffect
from items import HealthPotion, ManaPotion, DamagePotion, Inventory
from battle import Battle


class TestCharacter(unittest.TestCase):

    def setUp(self):
        self.character = Character("Тест", 100, 20)
        self.target = Character("Цель", 100, 15)

    def test_character_creation(self):
        self.assertEqual(self.character.name, "Тест")
        self.assertEqual(self.character.hp, 100)
        self.assertEqual(self.character.damage, 20)
        self.assertTrue(self.character.is_alive)

    def test_character_attack(self):
        initial_hp = self.target.hp
        damage = self.character.attack(self.target)
        self.assertLess(self.target.hp, initial_hp)
        self.assertEqual(damage, initial_hp - self.target.hp)

    def test_character_death(self):
        self.character.hp = 0
        self.assertFalse(self.character.is_alive)

    def test_effect_application(self):
        poison = PoisonEffect(duration=3, damage_per_turn=5)
        self.character.add_effect(poison)
        self.assertIn(poison, self.character.effects)
        self.assertEqual(len(self.character.effects), 1)

    def test_effect_removal(self):
        poison = PoisonEffect(duration=3, damage_per_turn=5)
        self.character.add_effect(poison)
        self.character.remove_effect(poison)
        self.assertNotIn(poison, self.character.effects)


class TestWarrior(unittest.TestCase):

    def setUp(self):
        self.warrior = Warrior("Тестовый воин")
        self.target = Character("Цель", 100, 15)

    def test_warrior_creation(self):
        self.assertEqual(self.warrior.role, "Воин")
        self.assertEqual(self.warrior.hp, 150)
        self.assertEqual(self.warrior.damage, 30)
        self.assertTrue(hasattr(self.warrior, 'mp'))


class TestMage(unittest.TestCase):

    def setUp(self):
        self.mage = Mage("Тестовый маг")
        self.target = Character("Цель", 100, 15)

    def test_mage_creation(self):
        self.assertEqual(self.mage.role, "Маг")
        self.assertEqual(self.mage.hp, 80)
        self.assertEqual(self.mage.damage, 40)
        self.assertEqual(self.mage.mp, 100)


class TestBoss(unittest.TestCase):

    def setUp(self):
        self.boss = Boss("Тестовый босс")
        self.hero = Character("Герой", 100, 20)

    def test_boss_creation(self):
        self.assertEqual(self.boss.role, "Босс")
        self.assertEqual(self.boss.hp, 400)
        self.assertTrue(hasattr(self.boss, 'mp'))

    def test_boss_skills(self):
        # Создаем мок-героев для тестирования навыков
        self.boss.heroes = [self.hero]

        # Тестируем использование навыка
        result = self.boss.use_skill()
        self.assertIsInstance(result, str)
        self.assertGreater(len(result), 0)


class TestEffects(unittest.TestCase):

    def setUp(self):
        self.character = Character("Тест", 100, 20)

    def test_poison_effect(self):
        poison = PoisonEffect(duration=2, damage_per_turn=10)
        self.character.add_effect(poison)

        initial_hp = self.character.hp
        poison.on_turn(self.character)
        self.assertLess(self.character.hp, initial_hp)

    def test_shield_effect(self):
        shield = ShieldEffect(duration=2, shield_amount=20)
        self.character.add_effect(shield)

        damage = 15
        absorbed_damage = shield.absorb_damage(damage)
        self.assertEqual(absorbed_damage, 0)
        self.assertEqual(shield.remaining_shield, 5)

    def test_strength_buff_effect(self):
        buff = StrengthBuffEffect(duration=2, damage_bonus=10)
        initial_damage = self.character.damage

        buff.on_apply(self.character)
        self.assertEqual(self.character.damage, initial_damage + 10)

        buff.on_remove(self.character)
        self.assertEqual(self.character.damage, initial_damage)


class TestItems(unittest.TestCase):

    def setUp(self):
        self.character = Character("Тест", 100, 20)
        self.character.max_hp = 100

    def test_health_potion(self):
        potion = HealthPotion()
        self.character.hp = 50

        result = potion.use(self.character)
        self.assertGreater(self.character.hp, 50)
        self.assertIn("восстанавливает", result.lower())

    def test_damage_potion(self):
        potion = DamagePotion()
        initial_effects_count = len(self.character.effects)

        result = potion.use(self.character)
        self.assertGreater(len(self.character.effects), initial_effects_count)
        self.assertIn("урон увеличен", result.lower())


class TestInventory(unittest.TestCase):
    class TestInventory(unittest.TestCase):

        def setUp(self):
            self.inventory = Inventory()
            self.potion = HealthPotion()

        def test_add_item(self):
            self.inventory.add_item(self.potion, 2)
            self.assertTrue(self.inventory.has_item("Зелье здоровья"))
            self.assertEqual(self.inventory.get_quantity("Зелье здоровья"), 2)  # Исправлено

        def test_remove_item(self):
            self.inventory.add_item(self.potion, 2)
            self.inventory.remove_item("Зелье здоровья", 1)
            self.assertEqual(self.inventory.get_quantity("Зелье здоровья"), 1)  # Исправлено

            self.inventory.remove_item("Зелье здоровья", 1)
            self.assertFalse(self.inventory.has_item("Зелье здоровья"))


class TestBattle(unittest.TestCase):

    def setUp(self):
        self.warrior = Warrior("Воин")
        self.mage = Mage("Маг")
        self.boss = Boss("Босс")
        self.heroes = [self.warrior, self.mage]

    def test_battle_creation(self):
        battle = Battle(self.heroes, self.boss)
        self.assertEqual(len(battle.heroes), 2)
        self.assertEqual(battle.boss, self.boss)

    def test_battle_over_condition(self):
        battle = Battle(self.heroes, self.boss)

        # Изначально бой не должен быть окончен
        self.assertFalse(battle.is_battle_over())

        # Убиваем всех героев
        for hero in self.heroes:
            hero.hp = 0
        self.assertTrue(battle.is_battle_over())

        # Проверяем победителя - исправленная строка
        winner = battle.get_winner()
        self.assertEqual(winner, "Босс")

    def test_battle_winner_heroes(self):
        battle = Battle(self.heroes, self.boss)

        # Убиваем босса
        self.boss.hp = 0
        self.assertTrue(battle.is_battle_over())

        # Проверяем победителя
        winner = battle.get_winner()
        self.assertEqual(winner, "Герои")


if __name__ == '__main__':
    # Запуск тестов с подробным выводом
    unittest.main(verbosity=2)