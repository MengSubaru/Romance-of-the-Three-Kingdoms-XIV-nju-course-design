from dataclasses import dataclass, field
from typing import Optional, List, Tuple
import random
import math

MAX_SOLDIERS = 1000 

@dataclass
class Faction:

    name: str # 势力名称
    ruler: "General"
    cities: List["City"] = field(default_factory=list)  # 拥有的城市
    generals: List["General"] = field(default_factory=list)  # 拥有的武将
    
    def add_general(self, general: "General"):
        """添加武将"""
        if general not in self.generals:
            self.generals.append(general)
            general.faction = self
    
    def remove_general(self, general: "General"):
        """移除武将"""
        if general in self.generals:
            self.generals.remove(general)
            general.faction = None
    
    def add_city(self, city: "City"):
        """添加城池"""
        if city not in self.cities:
            self.cities.append(city)
            city.owner = self
    
    def remove_city(self, city: "City"):
        """失去城池"""
        if city in self.cities:
            self.cities.remove(city)
            city.owner = None

@dataclass
class General:
    """
    武将类+
    - name: 武将姓名
    - leadership: 统率（影响军队整体战斗力）[0,100]
    - martial: 武力（影响单挑和募兵数量）[0,100]
    - intellect: 智力（影响商业开发效果）[0,100]
    - politics: 政治（影响农业开发效果）[0,100]
    - loyalty: 忠义（0~1），越高越难劝降 [0,1]
    - _greed: 隐藏贪婪（0.0 ~ 1.0 范围推荐，影响所需俸禄）[0,1]
    - faction: 所属势力 (Faction 或 None)
    - army: 每个武将带的士兵数(不超过MAX_SOLDIERS)
    """
    name: str
    leadership: int
    martial: int
    intellect: int
    politics: int

    loyalty: float  # 忠义（0~1），越高越难劝降

    _greed: float = field(default_factory=lambda: round(random.uniform(0.05, 0.3), 3))  # 隐藏
    
    faction:   Optional[Faction] = None # 所属势力

    army: int = 0 # 每个武将带的士兵数(不超过MAX_SOLDIERS)

    def monthly_salary(self, min_salary: float = 50.0, max_salary: float = 100.0) -> float:
        """
        根据贪婪属性计算固定区间内的俸禄：
        贪婪=0 → 50
        贪婪=1 → 100
        """
        return min_salary + (max_salary - min_salary) * self._greed

@dataclass
class City:
    """
    城池类
    - food: 粮草（粮草库存）
    - gold: 金钱（库存）
    - officer_commerce: 商业开发官 (General 或 None)
    - officer_agriculture: 农业开发官 (General 或 None)
    """

    name: str  # 城市名称
    food: int  # 粮草数量
    gold: int  # 金钱数量
    owner: Faction # 城池归属势力
    generals: List["General"] = field(default_factory=list)  # 城中驻守的武将

    # 城市开发度进度（0~500）
    commerce_progress: float = 0.0  # 商业开发进度
    agriculture_progress: float = 0.0  # 农业开发进度
    progress_per_level: float = 100.0  # 每100进度视为1级
    max_progress: float = 500.0  # 最高5级（5×100）

    # 城市基础收入
    base_commerce_income: int = 100  # 基础商业收入（金）
    base_agriculture_income: int = 1000  # 基础农业收入（粮）

    # 官员
    officer_commerce: Optional[General] = None
    officer_agriculture: Optional[General] = None
    
    wild_generals: List["General"] = field(default_factory=list)
    prisoners: List[Tuple["General", int]] = field(default_factory=list)  # (武将, 被关押回合数)

    neighbors: list["City"] = field(default_factory=list)

    def monthly_update(self):
        """每月城市更新：收入、支出、开发、募兵"""
        logs = []
        logs.append(f"\n=== {self.name} 城市月度更新 ===")
        #print(f"\n=== {self.name} 城市月度更新 ===")

        monthly_income = 0

        # ---- 商业收入 ----
        commerce_level = int(self.commerce_progress // self.progress_per_level)
        commerce_income = self.base_commerce_income + commerce_level * 100
        monthly_income += commerce_income
        logs.append(f"商业开发 {commerce_level}级 -> 收入 {commerce_income} 金")
        #print(f"商业开发 {commerce_level}级 -> 收入 {commerce_income} 金")

        # ---- 农业收入（粮草）----
        agriculture_level = int(self.agriculture_progress // self.progress_per_level)
        food_income = self.base_agriculture_income + agriculture_level * 1000
        logs.append(f"农业开发 {agriculture_level}级 -> 收入 {food_income} 粮草")
        #print(f"农业开发 {agriculture_level}级 -> 收入 {food_income} 粮草")

        # ---- 计算城中武将招募士兵和开发农商业的工资 ----

        total_salary = 0
        for officer in self.generals:
            if officer.army < MAX_SOLDIERS: #士兵未满，本回合需要募兵
                recruit_ratio = (MAX_SOLDIERS - officer.army) / MAX_SOLDIERS  # 保留小数
                total_salary += round(officer.monthly_salary() * recruit_ratio)
            
        # 商农业开发额外耗钱
        if self.officer_agriculture is not None: 
            total_salary += self.officer_agriculture.monthly_salary()
        
        if self.officer_commerce is not None:
            total_salary += self.officer_commerce.monthly_salary()

        #print(f"官员总俸禄需求: {total_salary} 金")
        logs.append(f"官员总俸禄需求: {total_salary} 金")

        # ---- 粮草结算 ----
        self.food += food_income

        # 士兵口粮消耗
        food_res = self.food
 
        for officer in self.generals:
            if food_res >= officer.army: # 粮草够吃
                food_res -= officer.army
            else: # 粮草不够吃
                shortage = officer.army - food_res
                lost_soldiers = int(shortage / 2)  # 逃兵数量
                food_res = 0
                officer.army = max(0, officer.army - lost_soldiers)
        
                #print(f" {self.name} 粮草不足！{officer.name} 军出现士兵逃亡")
                logs.append(f" {self.name} 粮草不足！{officer.name} 军出现士兵逃亡 {lost_soldiers} 人")
        
        self.food = food_res

        # ---- 收入结算 ----
        self.gold += monthly_income

        # ---- 支付工资逻辑 ----
        gold_before_salary = self.gold

        if self.officer_commerce and self.gold >= self.officer_commerce.monthly_salary(): # 存在商业官员并且资金够其开发商业
            self.gold -= self.officer_commerce.monthly_salary()
            inc = self.officer_commerce.intellect / 10.0
            self.commerce_progress = min(self.commerce_progress + inc, self.max_progress)
            #print(f"商业开发 +{inc:.1f}（总进度 {self.commerce_progress:.1f}/{self.max_progress}）")
            logs.append(f"商业开发 +{inc:.1f}（总进度 {self.commerce_progress:.1f}/{self.max_progress}）")

        if self.officer_agriculture and self.gold >= self.officer_agriculture.monthly_salary(): # 存在农业官员并且资金够其开发农业
            self.gold -= self.officer_agriculture.monthly_salary()
            inc = self.officer_agriculture.politics / 10.0
            self.agriculture_progress = min(self.agriculture_progress + inc, self.max_progress)
            #print(f"农业开发 +{inc:.1f}（总进度 {self.agriculture_progress:.1f}/{self.max_progress}）")
            logs.append(f"农业开发 +{inc:.1f}（总进度 {self.agriculture_progress:.1f}/{self.max_progress}）")

        for general in self.generals:
            if general.army < MAX_SOLDIERS:
                recruit_salary = general.monthly_salary() / MAX_SOLDIERS # 该武将招募一名士兵所需金钱数，保留小数

                num_recruit = min(MAX_SOLDIERS - general.army, int(self.gold // recruit_salary)) # 实际可招募的士兵数

                general.army += num_recruit

                self.gold = max(0, self.gold - int(num_recruit * recruit_salary)) # 避免小于0 

        #print(f"结算前金 {gold_before_salary} -> 结算后金 {self.gold}")
        logs.append(f"结算前金 {gold_before_salary} -> 结算后金 {self.gold}")
        return "\n".join(logs)

    def explore(self) -> str:
        """
        玩家或AI在城市内进行“探索”行动。
        - 40% 概率发现在野武将（若有）
        - 15% 概率获得金币
        - 15% 概率获得粮草
        - 30% 概率一无所获
        """
        # ========= 探索逻辑 =========

        roll = random.random()
        if roll < 0.4 :     
            return " 搜索了许久，一无所获……"
        elif roll < 0.6:
            gold_found = random.randint(150, 300)
            self.gold += gold_found
            return f" 发现了被遗弃的军资，获得 {gold_found} 金。"
        elif roll < 0.8:
            food_found = random.randint(200, 400)
            self.food += food_found
            return f" 找到隐藏的粮仓，获得 {food_found} 粮草。"
        elif self.wild_generals:
            general = random.choice(self.wild_generals)
            self.wild_generals.remove(general)

            self.owner.add_general(general)

            self.generals.append(general)
            return f" 发现在野武将 {general.name}！成功将其招入麾下！"
        else:
            roll = random.random()
            if roll < 0.5:
                gold_found = random.randint(150, 300)
                self.gold += gold_found
                return f" 发现了被遗弃的军资，获得 {gold_found} 金。"
            else:
                food_found = random.randint(200, 400)
                self.food += food_found
                return f" 找到隐藏的粮仓，获得 {food_found} 粮草。"
    
    def update_prisoners(self):
        """每回合更新：仅判断逃脱"""
        logs = []

        new_prisoners = []
        for general, turns in self.prisoners:          
            escape_prob = 0.01 * turns  # 每回合逃脱概率略微上升, 刚抓到的第一回合无法逃脱
            turns += 1

            if general.faction is None: # 如果关押的武将没有所属势力则不再逃脱；
                new_prisoners.append((general, turns))
                continue

            if random.random() < escape_prob:
                #print(f" {general.name} 从 {self.name} 逃脱！")
                logs.append(f" {general.name} 从 {self.name} 逃脱！")

                # === 新逻辑：只向该武将原势力的随机城池逃亡 ===
                if general.faction and general.faction.cities:
                    dest = random.choice(general.faction.cities)
                    dest.generals.append(general)
                    #print(f" {general.name} 趁乱逃回 {dest.name}")
                    logs.append(f" {general.name} 趁乱逃回 {dest.name}")
                else:
                    assert(0), "武将没有势力时应该无处可逃"

            else:
                new_prisoners.append((general, turns))
        self.prisoners = new_prisoners
        return "\n".join(logs) if logs else "无逃脱事件"

    def persuade_prisoner(self, target_general: "General"):
        """劝降逻辑：劝降特定武将"""

        if target_general.faction is None or target_general.faction == self.owner: # 该武将没有所属势力或者本身就是自己势力的人
            print(f" {target_general.name} 被成功劝降，加入 {self.owner.name} 势力！")
            self.generals.append(target_general)

            
            self.owner.add_general(target_general)

            # 从囚犯列表中移除
            self.prisoners = [(g, t) for g, t in self.prisoners if g != target_general]
            return True

        # 查找该武将在囚犯列表中的关押时间
        turns = next((t for g, t in self.prisoners if g == target_general), None)
        if turns is None:
            assert(0), f"{target_general.name} 不在 {self.name} 的囚犯列表中。"
            return False

        # 劝降成功率与被劝武将忠义以及关押回合数相关

        # 忠义基础项（忠义越高越难）
        base_prob = 1.0 - target_general.loyalty

        # 综合成功率
        success_prob = min(1.0, base_prob + 0.01 * turns)

        print(f"尝试劝降 {target_general.name}（关押 {turns} 回合，成功率约 {success_prob*100:.1f}%）...")

        if random.random() < success_prob:
            print(f" {target_general.name} 被成功劝降，加入 {self.owner.name} 势力！")
            target_general.faction.remove_general(target_general)

            self.generals.append(target_general)
            
            self.owner.add_general(target_general)

            # 从囚犯列表中移除
            self.prisoners = [(g, t) for g, t in self.prisoners if g != target_general]
            return True
        else:
            print(f" {target_general.name} 拒绝了劝降。")
            return False

    def remove_general(self, g: "General"): 
        #从该城市移除该武将
        if g in self.generals:
            self.generals.remove(g)

        if self.officer_agriculture and self.officer_agriculture == g: # g是城市的农业官员
            self.officer_agriculture = None
        
        if self.officer_commerce and self.officer_commerce == g: # g是城市的商业官员
            self.officer_commerce = None
      
def run_away(general: "General", city: "City"): # 武将逃跑逻辑
    if len(general.faction.cities) <= 1: # 最后一座城
        if general != general.faction.ruler and random.random() < 0.1: # 如果不是主公就有10%概率逃跑下野
            general.faction.remove_general(general)
            city.remove_general(general) # 下野到被攻击的城市中
            city.wild_generals.append(general)
    else: # 逃亡其他城池
        cities_wo_enemy = general.faction.cities.copy()
        if city in cities_wo_enemy:
            cities_wo_enemy.remove(city)

        dest = random.choice(cities_wo_enemy)
        city.remove_general(general)
        dest.generals.append(general)

@dataclass
class Army:
    """
    军队类
    - formation: 阵型（投石阵 / 锋矢阵 / 方圆阵）
    - general: 主将 (General)
    - soldiers: 士兵数
    """
    formation: str
    general: General

    soldiers: int
    bonus: float = 0 # 战前单挑获胜时军队获得额外增益 [0, 1]

    # ==== 动态属性 ====
    @property
    def attack(self) -> float:
        """计算军队攻击力：统率+士气+阵型系数"""
        base = self.general.leadership * 1.5 + self.soldiers / 200
        morale_factor = 1 + self.bonus  # 增益影响
        formation_bonus = {
            "投石阵": 1.2,
            "锋矢阵": 1.5,
            "方圆阵": 0.7,
        }.get(self.formation, 1.0)
        return base * morale_factor * formation_bonus

    @property
    def defense(self) -> float:
        """计算军队防御力"""
        base = self.general.leadership + self.soldiers / 300
        morale_factor = 1 + self.bonus
        formation_bonus = {
            "投石阵": 1.0,
            "锋矢阵": 0.7,
            "方圆阵": 1.3,
        }.get(self.formation, 1.0)
        return base * morale_factor * formation_bonus

    # ==== 战斗逻辑 ====
    def duel(self, enemy: "Army"):
        """
        主将单挑逻辑（强化版）：
        - 触发概率取决于武力差、智力差与阵型；
        - self武力越高越容易触发；
        - enemy智力越高越不容易触发；
        - 锋矢阵额外提高单挑概率；
        - 由self发起单挑；
        """
        result = ""

        # 计算武力与智力差
        diff_martial = self.general.martial - enemy.general.martial
        diff_intel = enemy.general.intellect - self.general.intellect

        # sigmoid 映射函数
        def sigmoid(x):
            return 1 / (1 + math.exp(-x))

        # 阵型修正系数
        formation_bonus = 0.0
        if getattr(self, "formation", None) == "锋矢阵":
            formation_bonus += 0.15  # 提高15%的触发率
        if getattr(enemy, "formation", None) == "锋矢阵":
            formation_bonus += 0.15  # 敌方锋矢阵也稍微影响整体对抗气氛

        # 基础触发分数：武力差正向影响，智力差负向影响
        trigger_score = 0.1 * diff_martial - 0.08 * diff_intel + formation_bonus

        # 计算触发概率
        trigger_chance = sigmoid(trigger_score)

        # 是否触发
        if random.random() > trigger_chance:
            return "本回合未触发单挑"

        #print(f"{self.general.name} 向 {enemy.general.name} 发起单挑！")
        result+= f"{self.general.name} 向 {enemy.general.name} 发起单挑！\n"

        # 单挑胜负判定（只看武力+随机波动）
        atk_self = self.general.martial + random.uniform(-10, 10)
        atk_enemy = enemy.general.martial + random.uniform(-10, 10)

        if atk_self > atk_enemy:
            self.bonus = random.uniform(0, 0.2)
            #result = f"{self.general.name} 单挑胜利！{enemy.general.name} 军受挫。"
            result+= f"{self.general.name} 单挑胜利！{enemy.general.name} 军受挫。"
        else:
            enemy.bonus = random.uniform(0, 0.2)
            #result = f"{enemy.general.name} 单挑胜利！{self.general.name} 军受挫。"
            result+= f"{enemy.general.name} 单挑胜利！{self.general.name} 军受挫。"

        return result

    def attack_enemy(self, enemy: "Army"):
        """军队对抗逻辑：攻防计算 + 阵型克制 + 士气疲劳"""
        # === 1. 基础攻防计算 ===
        # 我方对敌方的效能
        attack_true = self.attack * (1 + self.bonus)

        eff_self = attack_true / (attack_true + enemy.defense + 1e-6)

        # 随机微扰，避免完全确定性

        # 伤亡计算
        enemy_loss = int(eff_self * self.soldiers * random.uniform(0.1, 0.2))

        # 确保至少产生小量消耗（避免完全无伤害的僵持）
        if enemy_loss <= 0 and self.soldiers > 0:
            enemy_loss = 10

        enemy_loss = min(enemy_loss, enemy.soldiers)  # 伤亡不能超过现有士兵数

        # 4) 应用基础伤亡
        enemy.soldiers = max(0, enemy.soldiers - enemy_loss)

        result = f"{self.general.name} 发动攻击：{enemy.general.name} 军损失 {enemy_loss} 人。"

        # === 3. 阵型克制修正 ===
        formation_bonus = ""
        if self.formation == "锋矢阵":
            if enemy.formation == "投石阵": # 我方克制敌方
                extra_loss = int(enemy.soldiers * 0.05)

                # 确保至少产生小量消耗（避免完全无伤害的僵持）
                if extra_loss <= 0 and enemy.soldiers > 0:
                    extra_loss = 10

                extra_loss = min(extra_loss, enemy.soldiers)
                enemy.soldiers = max(0, enemy.soldiers - extra_loss)
                formation_bonus = f"{self.general.name}军阵型克制{enemy.general.name}军！锋矢阵突袭成功，额外对{enemy.general.name}军造成{extra_loss}人损失。"
                
        elif self.formation == "投石阵":
            if enemy.formation == "方圆阵": # 我方克制敌方
                extra_loss = int(enemy.soldiers * 0.05)

                # 确保至少产生小量消耗（避免完全无伤害的僵持）
                if extra_loss <= 0 and enemy.soldiers > 0:
                    extra_loss = 10
                extra_loss = min(extra_loss, enemy.soldiers)
                enemy.soldiers = max(0, enemy.soldiers - extra_loss)
                formation_bonus = f"{self.general.name}军投石阵远攻奏效，{enemy.general.name}军阵脚不稳，额外损失 {extra_loss} 人。"

        elif self.formation == "方圆阵":
            if enemy.formation == "锋矢阵": # 我方克制敌方
                extra_loss = int(enemy.soldiers * 0.05)

                # 确保至少产生小量消耗（避免完全无伤害的僵持）
                if extra_loss <= 0 and enemy.soldiers > 0:
                    extra_loss = 10
                extra_loss = min(extra_loss, enemy.soldiers)
                enemy.soldiers = max(0, enemy.soldiers - extra_loss)
                formation_bonus = f"{self.general.name}军方圆阵防御得当，{enemy.general.name}军不仅无法突破反而额外损失 {extra_loss} 人。"

        capture_prob = 0.2 # 主将战败被俘概率
        # === 5. 士兵耗尽：判定被俘或败走 ===
        captur_flag = False
        collapse_info = ""

        if enemy.soldiers <= 0: # 我军获胜
            if random.random() < capture_prob and enemy.general != enemy.general.faction.ruler:
                collapse_info = f"{enemy.general.name} 全军覆没，被 {self.general.name} 擒获！"
                captur_flag = True # 敌将被俘
            else:
                collapse_info = f"{enemy.general.name} 全军覆没，败将遁逃！"

        result_flag = {
            "win": enemy.soldiers <= 0, # 为真代表攻军获胜，反之进入守军的防守
            "capture": captur_flag, # 敌将是否被俘，只有win=True时才看这个变量
            "battle_log": f"{result}\n{formation_bonus}",
            "capture_log": collapse_info
        }
        return result_flag