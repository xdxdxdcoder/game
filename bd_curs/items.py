class Item:
    def __init__(self, name, description):
        self.name = name
        self.description = description

    def use(self, user):
        pass

    def __str__(self):
        return f"{self.name}: {self.description}"


class HealthPotion(Item):
    def __init__(self):
        super().__init__("Зелье здоровья", "Восстанавливает 50 HP")
        self.heal_amount = 50

    def use(self, user):
        if not user.is_alive:
            return f"{user.name} мертв и не может использовать зелье!"

        old_hp = user.hp
        user.hp = min(user.max_hp, user.hp + self.heal_amount)
        actual_heal = user.hp - old_hp

        return f"{user.name} использует {self.name}! Восстанавливает {actual_heal} HP!"


class ManaPotion(Item):
    def __init__(self):
        super().__init__("Зелье маны", "Восстанавливает 30 MP")
        self.mana_amount = 30

    def use(self, user):
        if not user.is_alive:
            return f"{user.name} мертв и не может использовать зелье!"

        # Для простоты считаем, что у всех есть MP
        if not hasattr(user, 'mp'):
            return f"{user.name} не использует ману!"

        old_mp = user.mp
        user.mp = min(user.max_mp, user.mp + self.mana_amount)
        actual_mana = user.mp - old_mp

        return f"{user.name} использует {self.name}! Восстанавливает {actual_mana} MP!"


class DamagePotion(Item):
    def __init__(self):
        super().__init__("Зелье ярости", "Увеличивает урон на 15 на 3 хода")

    def use(self, user):
        from effects import StrengthBuffEffect
        effect = StrengthBuffEffect(duration=3, damage_bonus=15)
        user.add_effect(effect)
        return f"{user.name} использует {self.name}! Урон увеличен на 15!"


class PoisonDart(Item):
    def __init__(self):
        super().__init__("Отравленный дротик", "Накладывает отравление на врага")

    def use(self, user):
        if hasattr(user, 'boss') and user.boss.is_alive:
            from effects import PoisonEffect
            effect = PoisonEffect(duration=3, damage_per_turn=8)
            user.boss.add_effect(effect)
            return f"{user.name} использует {self.name} на {user.boss.name}! {user.boss.name} отравлен!"
        return "Нет цели для использования!"


class Inventory:
    def __init__(self):
        self.items = {}

    def add_item(self, item, quantity=1):
        if item.name in self.items:
            self.items[item.name]['quantity'] += quantity
        else:
            self.items[item.name] = {
                'item': item,
                'quantity': quantity
            }

    def remove_item(self, item_name, quantity=1):
        if item_name in self.items:
            self.items[item_name]['quantity'] -= quantity
            if self.items[item_name]['quantity'] <= 0:
                del self.items[item_name]
            return True
        return False

    def get_item(self, item_name):
        return self.items.get(item_name, {}).get('item')

    def has_item(self, item_name):
        return item_name in self.items and self.items[item_name]['quantity'] > 0

    def get_quantity(self, item_name):
        """Получить количество конкретного предмета"""
        if item_name in self.items:
            return self.items[item_name]['quantity']
        return 0

    def show(self):
        if not self.items:
            print("  Инвентарь пуст")
            return

        for item_name, data in self.items.items():
            print(f"  {item_name}: {data['quantity']} шт. - {data['item'].description}")