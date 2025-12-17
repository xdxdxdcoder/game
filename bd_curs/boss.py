# Импорт Character, работающий и при запуске напрямую, и как пакет bd_curs
try:
    from main import Character
except ImportError:
    from .main import Character

import random

# Импорт эффектов так, чтобы работало и как скрипт, и как пакет
try:
    from effects import PoisonEffect, ShieldEffect, StunEffect
except ImportError:
    from .effects import PoisonEffect, ShieldEffect, StunEffect


class Boss(Character):
    def __init__(self, name):
        # Босс, сбалансированный под текущую пати: всё ещё опасный, но не «ваншотит» команду
        super().__init__(name, 1700, 70, "Босс")
        self.special_attack_cooldown = 0
        self.mp = 200
        self.max_mp = 200

    def use_skill(self):
        skills = [
            self.poison_breath,
            self.shield_wall,
            self.stomp_attack
        ]
        skill = random.choice(skills)
        return skill()

    def poison_breath(self):
        if self.mp >= 40:
            self.mp -= 40
            print(f"{self.name} использует Ядовитое дыхание!")
            for hero in self.heroes:
                if hero.is_alive:
                    # Чуть ослабленное отравление
                    poison = PoisonEffect(duration=4, damage_per_turn=15)
                    hero.add_effect(poison)
            return "Все герои отравлены!"
        return "Недостаточно маны для навыка!"

    def shield_wall(self):
        if self.mp >= 30:
            self.mp -= 30
            # Щит по‑прежнему полезен, но не такой мощный
            shield = ShieldEffect(duration=3, shield_amount=60)
            self.add_effect(shield)
            return f"{self.name} создает магический щит!"
        return "Недостаточно маны для навыка!"

    def stomp_attack(self):
        print(f"{self.name} использует Сокрушающий удар!")
        total_damage = 0
        for hero in self.heroes:
            if hero.is_alive:
                # Чуть сниженный урон
                damage = random.randint(35, 50)
                actual_damage = hero.take_damage(damage)
                total_damage += actual_damage

                # Оглушение по‑прежнему опасно, но реже и короче
                if random.random() < 0.4:
                    stun = StunEffect(duration=1)
                    hero.add_effect(stun)
                    print(f"  {hero.name} оглушен!")
                else:
                    print(f"  {hero.name} получает {actual_damage} урона!")

        return f"Общий урон: {total_damage}"

    def attack(self, target):
        if self.special_attack_cooldown <= 0 and random.random() < 0.3:
            return self.use_skill()
        else:
            if self.special_attack_cooldown > 0:
                self.special_attack_cooldown -= 1
            return super().attack(target)