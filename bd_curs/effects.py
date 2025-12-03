class Effect:
    def __init__(self, name, duration):
        self.name = name
        self.duration = duration

    def on_apply(self, target):
        pass

    def on_remove(self, target):
        pass

    def on_turn(self, target):
        pass


class PoisonEffect(Effect):
    def __init__(self, duration=3, damage_per_turn=5):
        super().__init__("Отравление", duration)
        self.damage_per_turn = damage_per_turn

    def on_apply(self, target):
        print(f"{target.name} отравлен! Будет получать {self.damage_per_turn} урона за ход.")

    def on_turn(self, target):
        if target.is_alive:
            damage = target.take_damage(self.damage_per_turn)
            print(f"{target.name} получает {damage} урона от яда!")

    def on_remove(self, target):
        print(f"{target.name} больше не отравлен.")


class ShieldEffect(Effect):
    def __init__(self, duration=2, shield_amount=20):
        super().__init__("Щит", duration)
        self.shield_amount = shield_amount
        self.remaining_shield = shield_amount

    def on_apply(self, target):
        print(f"{target.name} получает щит на {self.shield_amount} урона!")

    def absorb_damage(self, damage):
        if self.remaining_shield >= damage:
            self.remaining_shield -= damage
            print(f"Щит поглощает {damage} урона!")
            return 0
        else:
            remaining_damage = damage - self.remaining_shield
            print(f"Щит поглощает {self.remaining_shield} урона!")
            self.remaining_shield = 0
            return remaining_damage

    def on_remove(self, target):
        print(f"Щит {target.name} исчезает.")


class StrengthBuffEffect(Effect):
    def __init__(self, duration=3, damage_bonus=10):
        super().__init__("Усиление силы", duration)
        self.damage_bonus = damage_bonus

    def on_apply(self, target):
        target.damage += self.damage_bonus
        print(f"{target.name} получает +{self.damage_bonus} к урону!")

    def on_remove(self, target):
        target.damage -= self.damage_bonus
        print(f"Эффект усиления силы у {target.name} заканчивается.")


class RegenerationEffect(Effect):
    def __init__(self, duration=3, heal_per_turn=10):
        super().__init__("Регенерация", duration)
        self.heal_per_turn = heal_per_turn

    def on_apply(self, target):
        print(f"{target.name} начинает регенерировать!")

    def on_turn(self, target):
        if target.is_alive:
            old_hp = target.hp
            target.hp = min(target.max_hp, target.hp + self.heal_per_turn)
            actual_heal = target.hp - old_hp
            if actual_heal > 0:
                print(f"{target.name} восстанавливает {actual_heal} HP от регенерации!")

    def on_remove(self, target):
        print(f"Регенерация {target.name} прекращается.")


class StunEffect(Effect):
    def __init__(self, duration=1):
        super().__init__("Оглушение", duration)
        self.stunned_this_turn = False

    def on_apply(self, target):
        print(f"{target.name} оглушен и пропускает ход!")
        self.stunned_this_turn = True

    def on_turn(self, target):
        if self.stunned_this_turn:
            print(f"{target.name} все еще оглушен!")
            self.stunned_this_turn = False

    def on_remove(self, target):
        print(f"{target.name} больше не оглушен.")