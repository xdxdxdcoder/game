from main import Character
import random
from effects import PoisonEffect, ShieldEffect, StunEffect


class Boss(Character):
    def __init__(self, name):
        super().__init__(name, 400, 35, "Босс")
        self.special_attack_cooldown = 0
        self.mp = 150
        self.max_mp = 150

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
                    poison = PoisonEffect(duration=3, damage_per_turn=12)
                    hero.add_effect(poison)
            return "Все герои отравлены!"
        return "Недостаточно маны для навыка!"

    def shield_wall(self):
        if self.mp >= 30:
            self.mp -= 30
            shield = ShieldEffect(duration=3, shield_amount=50)
            self.add_effect(shield)
            return f"{self.name} создает магический щит!"
        return "Недостаточно маны для навыка!"

    def stomp_attack(self):
        print(f"{self.name} использует Сокрушающий удар!")
        total_damage = 0
        for hero in self.heroes:
            if hero.is_alive:
                damage = random.randint(20, 30)
                actual_damage = hero.take_damage(damage)
                total_damage += actual_damage

                # Шанс оглушить
                if random.random() < 0.3:
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