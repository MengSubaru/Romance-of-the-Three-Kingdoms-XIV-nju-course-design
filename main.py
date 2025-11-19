# map_ui.py
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QLabel, QListWidget, QGraphicsView, QGraphicsScene, QGraphicsEllipseItem,
    QGraphicsLineItem, QGraphicsPixmapItem, QDialog, QFormLayout, QSpinBox,
    QDialogButtonBox, QMessageBox, QComboBox, QGraphicsSimpleTextItem, QTextEdit, QListWidgetItem
)
from PySide6.QtGui import QBrush, QColor, QPen, QPainter, QPixmap
from PySide6.QtCore import Qt, Signal, QObject
import random
import sys
import time

from dataclasses import dataclass, field
from typing import List, Tuple
import math
import json
import os

# ========== 导入你的游戏内核 ==========
# 假设你把之前那堆类保存为 attribute.py（或改成你实际模块名）
# 要求：City, Faction, General 至少存在并实现 explore(), persuade_prisoner(), attack_other_city() 等方法
try:
    from attribute import City, Faction, General, Army, run_away
except Exception as e:
    # 如果没有外部模块，提供一个非常小的替代实现以便演示 UI（你运行时请改为 import 你的模块）
    print("注意：未能导入 attribute.py，使用演示替代类（运行时请把 attribute.py 放在同目录并改 import）。", e)

    assert(0)
# ========== end fallback ==========

class BattleWindow(QDialog):
    """
    战斗展示窗口：
    - 左边：Army1（攻击方）武将头像 + 阵型 + 士兵
    - 右边：Army2（防守方）武将头像 + 阵型 + 士兵
    - 中间：战斗日志滚动显示
    """

    def __init__(self, army1, army2, parent=None):
        super().__init__(parent)

        self.army1 = army1
        self.army2 = army2
        self.battle_finished = False  # 标记战斗是否结束

        #self.setWindowTitle("战斗中……")
        self.resize(800, 500)

        # 禁用窗口关闭按钮
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowCloseButtonHint)

        main_layout = QVBoxLayout(self)

        # 战斗信息区域（水平布局）
        battle_layout = QHBoxLayout()

        # ===== 左侧军队信息 =====
        left_layout = QVBoxLayout()
        self.left_img = QLabel()
        self.left_img.setAlignment(Qt.AlignCenter)
        self._set_general_image(self.left_img, army1.general.name)
        left_layout.addWidget(self.left_img)

        self.left_info = QLabel(self._army_text(army1))
        self.left_info.setAlignment(Qt.AlignCenter)
        left_layout.addWidget(self.left_info)

        # ===== 中间日志区域 =====
        self.log_box = QTextEdit()
        self.log_box.setReadOnly(True)
        self.log_box.setStyleSheet("font-size:15px;")
        battle_layout.addLayout(left_layout, 2)
        battle_layout.addWidget(self.log_box, 4)

        # ===== 右侧军队信息 =====
        right_layout = QVBoxLayout()
        self.right_img = QLabel()
        self.right_img.setAlignment(Qt.AlignCenter)
        self._set_general_image(self.right_img, army2.general.name)
        right_layout.addWidget(self.right_img)

        self.right_info = QLabel(self._army_text(army2))
        self.right_info.setAlignment(Qt.AlignCenter)
        right_layout.addWidget(self.right_info)


        battle_layout.addLayout(right_layout, 2)
        
        main_layout.addLayout(battle_layout, 1)

        # ===== 底部关闭按钮 =====
        #self.close_btn = QPushButton("关闭战斗窗口")
        #self.close_btn.setEnabled(False)  # 初始禁用
        #self.close_btn.clicked.connect(self.close)
        #main_layout.addWidget(self.close_btn)

    # ==================
    # 工具函数
    # ==================
    def _set_general_image(self, label, general_name):
        """尝试加载头像，若失败用占位图"""
        path = f"image/{general_name}.jpg"   # ← 你原本的路径方式
        pix = QPixmap(path)
        if pix.isNull():
            pix = QPixmap(150, 200)
            pix.fill(Qt.gray)

        pix = pix.scaled(150, 200, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        label.setPixmap(pix)

    def _army_text(self, army):
        return (f"<b>{army.general.name}</b><br>"
                f"阵型：{army.formation}<br>"
                f"士兵：{army.soldiers}")

    # ==================
    # 供外界调用的接口
    # ==================
    def append_log(self, text):
        """外部调用此函数来追加战斗日志"""
        self.log_box.append(text)
        self.log_box.verticalScrollBar().setValue(
            self.log_box.verticalScrollBar().maximum()
        )

    def update_army_info(self):
        """更新双方军队状态，例如士兵变化后刷新"""
        self.left_info.setText(self._army_text(self.army1))
        self.right_info.setText(self._army_text(self.army2))
    def enable_close_button(self):
        """启用关闭按钮"""
        self.battle_finished = True
        #self.close_btn.setEnabled(True)
        # 重新启用窗口关闭按钮
        self.setWindowFlags(self.windowFlags() | Qt.WindowCloseButtonHint)
        self.show()  # 需要重新显示窗口以使标志更改生效
    
    def closeEvent(self, event):
        """重写关闭事件，战斗未结束时阻止关闭"""
        if not self.battle_finished:
            event.ignore()
            QMessageBox.warning(self, "战斗进行中", "战斗尚未结束，请等待战斗完成！")
        else:
            event.accept()

class SetOfficersDialog(QDialog):
    """设置官员对话框"""
    def __init__(self, city: City, parent=None):
        super().__init__(parent)
        self.city = city
        self.setWindowTitle(f"设置官员 - {city.name}")
        self.resize(500, 400)
        
        layout = QVBoxLayout(self)
        
        # 当前官员信息
        current_info = QLabel(
            f"当前官员：\n"
            f"农业开发：{city.officer_agriculture.name if city.officer_agriculture else '无'} (政治:{city.officer_agriculture.politics if city.officer_agriculture else 'N/A'})\n"
            f"商业开发：{city.officer_commerce.name if city.officer_commerce else '无'} (智力:{city.officer_commerce.intellect if city.officer_commerce else 'N/A'})"
        )
        layout.addWidget(current_info)
        
        # 农业官员选择
        agri_layout = QHBoxLayout()
        agri_layout.addWidget(QLabel("农业官员:"))
        self.agri_combo = QComboBox()
        self.agri_combo.addItem("无", None)
        
        # 按政治排序显示武将
        sorted_generals = sorted(city.generals, key=lambda g: g.politics, reverse=True)
        for general in sorted_generals:
            self.agri_combo.addItem(f"{general.name} (政治:{general.politics})", general)
        
        # 设置当前农业官员为选中项
        current_index = 0
        for i in range(self.agri_combo.count()):
            if self.agri_combo.itemData(i) == city.officer_agriculture:
                current_index = i
                break
        self.agri_combo.setCurrentIndex(current_index)
        
        agri_layout.addWidget(self.agri_combo)
        layout.addLayout(agri_layout)
        
        # 商业官员选择
        comm_layout = QHBoxLayout()
        comm_layout.addWidget(QLabel("商业官员:"))
        self.comm_combo = QComboBox()
        self.comm_combo.addItem("无", None)
        
        # 按智力排序显示武将
        sorted_generals = sorted(city.generals, key=lambda g: g.intellect, reverse=True)
        for general in sorted_generals:
            self.comm_combo.addItem(f"{general.name} (智力:{general.intellect})", general)
        
        # 设置当前商业官员为选中项
        current_index = 0
        for i in range(self.comm_combo.count()):
            if self.comm_combo.itemData(i) == city.officer_commerce:
                current_index = i
                break
        self.comm_combo.setCurrentIndex(current_index)
        
        comm_layout.addWidget(self.comm_combo)
        layout.addLayout(comm_layout)
        
        # 连接信号，当选择变化时检查冲突
        self.agri_combo.currentIndexChanged.connect(self.check_officer_conflict)
        self.comm_combo.currentIndexChanged.connect(self.check_officer_conflict)
        
        # 冲突提示
        self.conflict_label = QLabel("")
        self.conflict_label.setStyleSheet("color: red; font-weight: bold;")
        layout.addWidget(self.conflict_label)
        
        # 说明文字
        info_label = QLabel(
            "提示：\n"
            "- 农业官员效果取决于政治属性\n"
            "- 商业官员效果取决于智力属性\n"
            "- 一个武将不能同时担任两个职位\n"
            "- 取消设置官员请选择'无'"
        )
        info_label.setStyleSheet("color: gray; font-size: 12px;")
        layout.addWidget(info_label)
        
        # 按钮
        self.button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        self.button_box.accepted.connect(self.on_accept)
        self.button_box.rejected.connect(self.reject)
        layout.addWidget(self.button_box)
        
        # 初始检查冲突
        self.check_officer_conflict()
    
    def check_officer_conflict(self):
        """检查官员冲突"""
        agri_officer = self.agri_combo.currentData()
        comm_officer = self.comm_combo.currentData()
        
        # 检查是否同一个武将担任两个职位
        if agri_officer and comm_officer and agri_officer == comm_officer:
            self.conflict_label.setText("错误：同一个武将不能同时担任两个职位！")
            self.button_box.button(QDialogButtonBox.Ok).setEnabled(False)
        else:
            self.conflict_label.setText("")
            self.button_box.button(QDialogButtonBox.Ok).setEnabled(True)
    
    def on_accept(self):
        """接受前的验证"""
        agri_officer = self.agri_combo.currentData()
        comm_officer = self.comm_combo.currentData()
        
        # 再次检查冲突
        if agri_officer and comm_officer and agri_officer == comm_officer:
            QMessageBox.warning(self, "错误", "同一个武将不能同时担任两个职位！")
            return
        
        self.accept()
    
    def get_result(self):
        """返回选择的官员"""
        agri_officer = self.agri_combo.currentData()
        comm_officer = self.comm_combo.currentData()
        return agri_officer, comm_officer

class CityInfoWindow(QWidget):
    def __init__(self, city: City, is_player_city, world, parent=None):
        super().__init__(parent)

        self.city = city
        self.is_player_city = is_player_city
        self.world = world
        self.parent_window = parent   # 用于访问主窗口 world update 等
        self.setFixedSize(400, 400)

        layout = QVBoxLayout(self)

        # 标题
        title = QLabel(f"【{city.name}】 - {'我方' if is_player_city else '敌方'}")
        title.setStyleSheet("font-size:20px; font-weight:bold;")
        layout.addWidget(title)
        self.setWindowTitle(f"{city.name}")

        # ==== 城市基本信息 ====
        self.info_label = QLabel(self._city_info())
        self.info_label.setWordWrap(True)
        layout.addWidget(self.info_label)

        # ==== 按钮区域 ====
        self.btn_area = QVBoxLayout()
        layout.addLayout(self.btn_area)

        if is_player_city:
            self.add_action_buttons()
        
        # 无论敌我均可查看情报
        # 城市情报
        btn_intel = QPushButton("城市情报")
        btn_intel.clicked.connect(self.on_city_intel)
        self.btn_area.addWidget(btn_intel)
            

        # ==== 日志 ====
        self.log_label = QLabel("")
        self.log_label.setWordWrap(True)
        layout.addWidget(self.log_label)

    # ---------- 城市信息 ----------
    def _city_info(self):
        c = self.city
        gens = "、".join([g.name for g in c.generals]) or "无"
        pris = "、".join([g.name for g,_ in c.prisoners]) or "无"
        # 添加官员信息
        agri_officer = c.officer_agriculture.name if c.officer_agriculture else "无"
        comm_officer = c.officer_commerce.name if c.officer_commerce else "无"
        return (
            f"粮草：{c.food}  金钱：{c.gold}\n"
            f"武将：{gens}\n"
            f"囚犯：{pris}\n"
            f"农业官员：{agri_officer}\n"
            f"商业官员：{comm_officer}"
        )

    # ---------- 增加按钮 ----------
    def add_action_buttons(self):
        # 探索
        self.btn_explore = QPushButton("探索")
        self.btn_explore.clicked.connect(self.on_explore)
        self.btn_area.addWidget(self.btn_explore)

        # 劝降
        self.btn_persuade = QPushButton("劝降")
        self.btn_persuade.clicked.connect(self.on_persuade)
        self.btn_area.addWidget(self.btn_persuade)

        # 出兵（必须有敌方邻居）
        if self.exists_enemy_neighbor(self.city):
            self.btn_attack = QPushButton("出兵作战")
            self.btn_attack.clicked.connect(self.on_attack)
            self.btn_area.addWidget(self.btn_attack)

        # 运输
        self.btn_transfer = QPushButton("运输（粮/金）")
        self.btn_transfer.clicked.connect(self.on_transfer)
        self.btn_area.addWidget(self.btn_transfer)

         # ==== 新增：粮食买卖 ====
        self.btn_trade_food = QPushButton("买卖粮食")
        self.btn_trade_food.clicked.connect(self.on_trade_food)
        self.btn_area.addWidget(self.btn_trade_food)

        # ==== 新增：调遣武将 ====
        self.btn_transfer_general = QPushButton("调遣武将")
        self.btn_transfer_general.clicked.connect(self.on_transfer_general)
        self.btn_area.addWidget(self.btn_transfer_general)

        # ==== 新增：设置官员 ====
        self.btn_set_officers = QPushButton("设置官员")
        self.btn_set_officers.clicked.connect(self.on_set_officers)
        self.btn_area.addWidget(self.btn_set_officers)

        # 更新按钮状态
        self.update_buttons_state()

    def on_set_officers(self):
        """设置城市官员"""
        if not self.check_and_consume_action():
            return

        dlg = SetOfficersDialog(self.city, parent=self)
        if dlg.exec() == QDialog.Accepted:
            agri_officer, comm_officer = dlg.get_result()
            
            # 再次检查冲突（双重保险）
            if agri_officer and comm_officer and agri_officer == comm_officer:
                QMessageBox.warning(self, "错误", "同一个武将不能同时担任两个职位！")
                # 返还操作次数
                self.parent_window.actions_remaining += 1
                self.parent_window.update_turn_info()
                self.update_buttons_state()
                return
            
            # 设置农业官员
            old_agri = self.city.officer_agriculture
            if agri_officer:
                self.city.officer_agriculture = agri_officer
            else:
                self.city.officer_agriculture = None
                
            # 设置商业官员
            old_comm = self.city.officer_commerce
            if comm_officer:
                self.city.officer_commerce = comm_officer
            else:
                self.city.officer_commerce = None
            
            # 生成日志信息
            log_parts = []
            if old_agri != agri_officer:
                if agri_officer:
                    log_parts.append(f"农业官员设为 {agri_officer.name}")
                else:
                    log_parts.append("取消农业官员")
                    
            if old_comm != comm_officer:
                if comm_officer:
                    log_parts.append(f"商业官员设为 {comm_officer.name}")
                else:
                    log_parts.append("取消商业官员")
            
            if log_parts:
                self.log_label.setText("；".join(log_parts))
            else:
                self.log_label.setText("官员设置未变更")
                
            self.refresh()
            self.world_update()
        else:
            # 用户取消，返还操作次数
            self.parent_window.actions_remaining += 1
            self.parent_window.update_turn_info()
            self.update_buttons_state()

    def update_buttons_state(self):
        """根据剩余操作次数更新按钮状态"""
        can_act = self.parent_window.can_perform_action()
        
        self.btn_explore.setEnabled(can_act)
        self.btn_persuade.setEnabled(can_act)
        if self.exists_enemy_neighbor(self.city):
            self.btn_attack.setEnabled(can_act and self.exists_enemy_neighbor(self.city))
        self.btn_transfer.setEnabled(can_act)
        self.btn_trade_food.setEnabled(can_act)  # 新增
        self.btn_transfer_general.setEnabled(can_act)  # 新增
        self.btn_set_officers.setEnabled(can_act)  # 新增
        
        if not can_act:
            self.btn_explore.setToolTip("操作次数已用完，请结束回合")
            self.btn_persuade.setToolTip("操作次数已用完，请结束回合")
            if self.exists_enemy_neighbor(self.city):
                self.btn_attack.setToolTip("操作次数已用完，请结束回合")
            self.btn_transfer.setToolTip("操作次数已用完，请结束回合")
            self.btn_trade_food.setToolTip("操作次数已用完，请结束回合")  # 新增
            self.btn_transfer_general.setToolTip("操作次数已用完，请结束回合")  # 新增
            self.btn_set_officers.setToolTip("操作次数已用完，请结束回合")  # 新增
        else:
            self.btn_explore.setToolTip("")
            self.btn_persuade.setToolTip("")
            if self.exists_enemy_neighbor(self.city):
                self.btn_attack.setToolTip("")
            self.btn_transfer.setToolTip("")
            self.btn_trade_food.setToolTip("")  # 新增
            self.btn_transfer_general.setToolTip("")  # 新增
            self.btn_set_officers.setToolTip("")  # 新增

    def exists_enemy_neighbor(self, city):
        my_faction = city.owner
        return any(nb.owner != my_faction for nb in city.neighbors)

    def refresh(self):
        self.info_label.setText(self._city_info())

    def world_update(self):
        if self.parent_window:
            self.parent_window.on_world_update()

    def on_city_intel(self):
        dlg = CityIntelDialog(self.city, parent=self)
        dlg.exec()
        
    def check_and_consume_action(self):
        """检查并消耗操作次数，返回是否成功"""
        if self.parent_window.consume_action():
            self.update_buttons_state()
            return True
        else:
            QMessageBox.warning(self, "操作限制", "本回合操作次数已用完，请结束回合")
            return False
    
    def on_trade_food(self):
        """粮食买卖功能"""
        if not self.check_and_consume_action():
            return

        dlg = FoodTradeDialog(self.city, parent=self)
        if dlg.exec() == QDialog.Accepted:
            trade_type, amount = dlg.get_result()
            
            if trade_type == "buy":
                # 买粮食：1金钱买10粮食
                cost = amount
                food_gain = amount * 10
                
                if cost > self.city.gold:
                    QMessageBox.warning(self, "错误", "金钱不足")
                    # 返还操作次数
                    self.parent_window.actions_remaining += 1
                    self.parent_window.update_turn_info()
                    self.update_buttons_state()
                    return
                    
                self.city.gold -= cost
                self.city.food += food_gain
                self.log_label.setText(f"购买粮食：花费 {cost} 金钱，获得 {food_gain} 粮食")
                
            else:  # sell
                # 卖粮食：10粮食卖1金钱
                food_cost = amount * 10
                gold_gain = amount
                
                if food_cost > self.city.food:
                    QMessageBox.warning(self, "错误", "粮食不足")
                    # 返还操作次数
                    self.parent_window.actions_remaining += 1
                    self.parent_window.update_turn_info()
                    self.update_buttons_state()
                    return
                    
                self.city.food -= food_cost
                self.city.gold += gold_gain
                self.log_label.setText(f"出售粮食：出售 {food_cost} 粮食，获得 {gold_gain} 金钱")
            
            self.refresh()
            self.world_update()
        else:
            # 用户取消，返还操作次数
            self.parent_window.actions_remaining += 1
            self.parent_window.update_turn_info()
            self.update_buttons_state()


    def on_transfer_general(self):
        """调遣武将功能"""
        if not self.check_and_consume_action():
            return

        # 检查当前城市是否有可调遣的武将
        if not self.city.generals:
            QMessageBox.information(self, "提示", "当前城市没有可调遣的武将")
            # 返还操作次数
            self.parent_window.actions_remaining += 1
            self.parent_window.update_turn_info()
            self.update_buttons_state()
            return

        dlg = GeneralTransferDialog(self.city, self.parent_window.world_cities, parent=self)
        if dlg.exec() == QDialog.Accepted:
            generals, target_city = dlg.get_result()
            
            if generals and target_city:
                # 从当前城市移除选中的武将
                for general in generals:
                    self.city.remove_general(general)
                    # 添加到目标城市
                    target_city.generals.append(general)
                
                general_names = "、".join([g.name for g in generals])
                self.log_label.setText(f"调遣 {len(generals)} 名武将到 {target_city.name}：{general_names}")
                self.refresh()
                self.world_update()
            else:
                QMessageBox.warning(self, "提示", "请选择要调遣的武将和目标城市")
                # 返还操作次数
                self.parent_window.actions_remaining += 1
                self.parent_window.update_turn_info()
                self.update_buttons_state()
        else:
            # 用户取消，返还操作次数
            self.parent_window.actions_remaining += 1
            self.parent_window.update_turn_info()
            self.update_buttons_state()

    def on_explore(self):
        if not self.check_and_consume_action():
            return

        try:
            res = self.city.explore()
        except Exception as e:
            res = f"探索失败：{e}"
        self.log_label.setText(str(res))
        self.refresh()
        self.world_update()

    def on_persuade(self):
        if not self.check_and_consume_action():
            return

        if not self.city.prisoners:
            QMessageBox.information(self, "提示", "当前城市无囚犯")
            self.parent_window.actions_remaining += 1
            self.parent_window.update_turn_info()
            self.update_buttons_state()
            return

        # 弹出劝降窗口
        dlg = PrisonerDialog(self.city.prisoners, parent=self)
        if dlg.exec() == QDialog.Accepted:
            idx = dlg.list_widget.currentRow()
            if idx < 0:
                QMessageBox.warning(self, "提示", "未选择武将")
                # 返还操作次数
                self.parent_window.actions_remaining += 1
                self.parent_window.update_turn_info()
                self.update_buttons_state()
                return
            prisoner, _ = self.city.prisoners[idx]
            try:
                ok = self.city.persuade_prisoner(prisoner)
                bold_name = f"<b>{prisoner.name}</b>"
                msg = f"劝降成功, {bold_name} 加入 {self.city.owner.name}" if ok else f"劝降失败, {bold_name} 拒绝了你的请求"
            except Exception as e:
                msg = f"劝降失败：{e}"
            self.log_label.setText(msg)
            self.refresh()
            self.world_update()
        else:
            # 用户取消劝降，返还操作次数
            self.parent_window.actions_remaining += 1
            self.parent_window.update_turn_info()
            self.update_buttons_state()

    def simulate_attack(self, armies: list["General"], enemy: "City")-> bool:
        """
        这是 attack_other_city 的“可视化日志版”。
        完全保留你的双层循环逻辑，只是把所有 print 换成 logs.append。
        """
        fight_or_cancel = False # 是否进行战斗，如果进行过至少一轮战斗，则为True，后续即使撤军也消耗行动次数

        defend_armies = []

        tmp_copy = enemy.generals.copy()

        for general in tmp_copy:
            if general.army <= 0:
                run_away(general, enemy)
                self.parent_window.refresh_faction_panel()
            else:
                defend_armies.append(general)

        attack = True  # 攻军先手

        # ------------- 主战斗循环 -------------
        while armies and defend_armies:
            if attack:
                # 玩家选择阵型 + 武将
                # TODO: 以下窗口反复打开关闭的过程均在三级窗口层次进行
                # 玩家选择阵型
                while True:
                    # 玩家取消阵型选择 → 重新选择武将
                    dlg = ArmySelectDialog(armies, single_mode=True)
                    if dlg.exec() != QDialog.Accepted or not dlg.get_selected():
                        # 玩家在武将界面也取消 → 退出整个战斗
                        msg = "作战已取消。部队撤回城市。"
                        self.parent_window.log_list.addItem(msg)
                        self.log_label.setText(msg)
                        self.parent_window.refresh_faction_panel()
                        return fight_or_cancel
                    atk_general = dlg.get_selected()[0]

                    # 玩家选择阵型
                    f_dlg = FormationSelectDialog(self, "请选择你的阵型")
                    ret = f_dlg.exec()

                    if ret == QDialog.Accepted:
                        formation_atk = f_dlg.get_formation()
                        fight_or_cancel = True
                        break  # 正常进入战斗

                # 敌人由玩家选择
                while True:
                    dlg = ArmySelectDialog(defend_armies, single_mode=True)   # 每次重新创建
                    ret = dlg.exec()
                    selected = dlg.get_selected()

                    if ret == QDialog.Accepted and selected:
                        dfd_general = selected[0]
                        fight_or_cancel = True
                        break  # 成功选择

                    QMessageBox.warning(self, "提示", "必须选择一名敌方武将迎战！")
                formation_dfd = random.choice(["锋矢阵", "方圆阵", "投石阵"])
            else:
                # TODO: 以下窗口反复打开关闭的过程均在三级窗口层次进行
                # 守方选择阵型随机
                atk_general = max(defend_armies, key=lambda g: g.leadership)

                formation_atk = random.choice(["锋矢阵", "方圆阵", "投石阵"])
                
                dfd_general = min(armies, key=lambda g: g.leadership)
                # 玩家选择阵型
                while True:
                    fdlg = FormationSelectDialog(self, f"{atk_general.name}军向{dfd_general.name}发起挑战！请选择阵型迎战！")
                    ret = fdlg.exec()
                    if ret == QDialog.Accepted:
                        formation_dfd = fdlg.get_formation()
                        fight_or_cancel = True
                        break
                    else:
                        QMessageBox.warning(self, "提示", "敌方来袭，必须选择阵型迎战！")
                
            msg = f"{atk_general.name}军 向 {dfd_general.name}军发起了对战"# TODO-finished: 在主窗口的def on_world_update(self)中显示“atk_general军 向 dfd_general军发起了对战”
            self.parent_window.log_list.addItem(msg)
            self.parent_window.refresh_faction_panel()

            Army1 = Army(formation_atk, atk_general, atk_general.army)
            Army2 = Army(formation_dfd, dfd_general, dfd_general.army)  

            
            battle_window = BattleWindow(Army1, Army2, parent=self)
            battle_window.setWindowTitle("战斗中……（请等待战斗结束）")
            
            # 添加关闭按钮（初始禁用）
            close_btn = QPushButton("关闭战斗窗口")
            close_btn.setEnabled(False)
            close_btn.clicked.connect(battle_window.close)
            
            # 将关闭按钮添加到战斗窗口布局
            battle_window.layout().addWidget(close_btn)
            
            battle_window.show()
            current_battle_window = battle_window
            # TODO-finished:此处打开一个战斗窗口，这个战斗窗口应该显示Army1和Army2的阵型和武将信息，并且两边是武将图像，中间有一个显示战斗日志的区域展示后面我标记的日志

            # 单挑
            to_duel = Army1
            if random.choice([True, False]):
                to_duel = Army2
            # 随机选择一方主动触发单挑
            duel_result = to_duel.duel(Army2 if to_duel == Army1 else Army1)           
            if duel_result != "本回合未触发单挑":
                # BattleWindow 日志
                current_battle_window.append_log(f"<b>【单挑】</b>{duel_result}")

                QApplication.processEvents()  # 确保UI更新
                time.sleep(1)  # 等待1秒

                item = QListWidgetItem()
                item.setText(f"【单挑】{duel_result}")

                # 设置加粗字体
                font = item.font()
                font.setBold(True)
                item.setFont(font)

                # 主窗口日志
                self.parent_window.log_list.addItem(item)
                self.parent_window.refresh_faction_panel() # TODO: 此处refresh需要吗？
                # 单挑日志同时显示在战斗窗口的日志区域和主窗口的def on_world_update(self)中

            # ------- 内层战斗循环 -------
            while Army1.soldiers > 0 and Army2.soldiers > 0:

                res1 = Army1.attack_enemy(Army2)
                #logs.append(res1["battle_log"]) 
                #TODO-finished res1["battle_log"]日志只显示在战斗窗口的日志区域,res1["capture_log"]日志同时显示在战斗窗口的日志区域和主窗口的def on_world_update(self)中

                # battle_log 仅 BattleWindow
                current_battle_window.append_log(res1["battle_log"])
                QApplication.processEvents()
                time.sleep(1)

                # capture_log 若存在，两个地方都显示
                if res1["capture_log"]: # TODO: 我的capture_log和这里的是否为空对应了吗？
                    current_battle_window.append_log(f"<b>{res1['capture_log']}</b>")
                    QApplication.processEvents()
                    time.sleep(1)
                    self.parent_window.log_list.addItem(res1["capture_log"])
                    self.refresh()
                current_battle_window.update_army_info()
                self.parent_window.refresh_faction_panel()
                QApplication.processEvents()

                if res1["win"]: # Army1获胜
                    atk_general.army = Army1.soldiers
                    dfd_general.army = 0
                    if res1["capture"]:
                        if attack:
                            enemy.remove_general(dfd_general)
                            self.city.prisoners.append((dfd_general, 0))   
                            self.refresh()
                        else:
                            self.city.remove_general(dfd_general)
                            enemy.prisoners.append((dfd_general, 0))
                    else:
                        if attack: # 攻军获胜,守军触发逃亡
                            run_away(dfd_general, enemy)
                            self.parent_window.refresh_faction_panel()
                        # 守军获胜，攻军逃亡回self.city即可
                    break

                # 轮到Army2反击
                res2 = Army2.attack_enemy(Army1)
                # res2["battle_log"]日志只显示在战斗窗口的日志区域,res2["capture_log"]日志同时显示在战斗窗口的日志区域和主窗口的def on_world_update(self)中

                current_battle_window.append_log(res2["battle_log"])
                QApplication.processEvents()
                time.sleep(1)

                if res2["capture_log"]:
                    current_battle_window.append_log(f"<b>{res2['capture_log']}</b>")
                    QApplication.processEvents()
                    time.sleep(1)
                    self.parent_window.log_list.addItem(res2["capture_log"])
                    self.refresh()

                current_battle_window.update_army_info()
                self.parent_window.refresh_faction_panel()
                QApplication.processEvents()

                if res2["win"]:# Army2获胜
                    dfd_general.army = Army2.soldiers
                    atk_general.army = 0
                    if res2["capture"]:
                        if attack:
                            self.city.remove_general(atk_general)
                            enemy.prisoners.append((atk_general, 0))
                        else:
                            enemy.remove_general(atk_general)
                            self.city.prisoners.append((atk_general, 0))
                            self.refresh()
                    else:
                        if not attack: # 攻军获胜,守军触发逃亡
                            run_away(atk_general, enemy)  
                            self.parent_window.refresh_faction_panel()
                            
                        # 攻军溃散时逃跑回self.city即可，无需逃亡其他城市 
                    break
            # ------- end 内层战斗循环 -------
            
            # 关闭战斗窗口，之前挑选出的一对武将的战斗结束
            # 当前这场战斗结束，关闭窗口
            # 当前这场战斗结束，启用关闭按钮
            close_btn.setEnabled(True)
            current_battle_window.setWindowTitle("战斗结束 - 请点击关闭按钮继续")
            # 当前这场战斗结束，启用关闭按钮
            current_battle_window.enable_close_button()
            #current_battle_window.close()

            # 等待用户关闭窗口
            while current_battle_window.isVisible():
                QApplication.processEvents()
                time.sleep(0.1)

            # ------- 外层循环剔除溃逃武将 -------
            if Army1.soldiers <= 0:
                if attack:
                    armies.remove(atk_general)
                else:
                    defend_armies.remove(atk_general)
            else:
                if Army2.soldiers > 0:
                    assert(0), "跳出内层循环时必然有一队士兵为0但是Army1不为0是Army2同时不为0"
                else: # Army2军队溃散
                    if attack:
                       defend_armies.remove(dfd_general)
                    else:
                        armies.remove(dfd_general) 

            self.refresh() # 刷新窗口，self的武将可能在战斗中落败被俘

            attack = not attack # 取反，下一轮由另一方先攻

        fight_or_cancel = True #设置为True避免出现守城武将为空，不战而胜但是返回值为False的情况

        # 战后总结
        if armies:
            if defend_armies:
                assert(0), "不可能两个攻城军和守城军同时不为空时中止战斗！"
            else: # 守城军消耗殆尽
                
                if len(enemy.owner.cities) <= 1: # 最后一城
                    if len(enemy.owner.cities) != 1:
                        assert(0), "势力所拥有的城池数小于等于0"
                    
                    to_remove_generals: list["General"] = []

                    for g in enemy.generals:
                        to_remove_generals.append(g)
                    
                    for g in to_remove_generals:
                        enemy.remove_general(g) # 从该城池移除该武将
                        self.city.prisoners.append((g, 0)) #加入监狱

                    to_remove_generals.clear()

                    for g in enemy.owner.generals:
                        to_remove_generals.append(g)

                    for g in to_remove_generals:
                        enemy.owner.remove_general(g)
                    
                    # TODO-finished: 在主窗口的def on_world_update(self)中显示“敌方势力 {enemy.owner.name} 被消灭！”
                    msg = f"敌方势力 {enemy.owner.name} 被消灭！"
                    self.parent_window.log_list.addItem(msg)           # 主窗口显示
                    self.log_label.setText(msg)                        # 二级窗口 CityInfoWindow 显示
                    self.parent_window.refresh_faction_panel()


                enemy.owner.remove_city(enemy)
                
                # 剩余攻城军进入enemy，self的势力占领新城，将所有官员设置为空
                for g in armies:
                    self.city.remove_general(g)
                    enemy.generals.append(g)
                    
                self.city.owner.add_city(enemy)
                enemy.officer_agriculture = None
                enemy.officer_commerce = None

                 # 更新城市颜色
                self.parent_window.update_city_color(enemy.name)

                msg = f"我方势力 {self.city.owner.name} 成功占领 {enemy.name}！"
                self.parent_window.log_list.addItem(msg)      # 主窗口日志
                self.log_label.setText(msg)                   # 当前城市信息窗口
                self.parent_window.refresh_faction_panel()

                self.refresh()# 刷新窗口，因为我方武将离开了原城市进入了enemy

                # === 新增：检查游戏是否结束 ===
                self.parent_window.check_game_over(conquered_city=enemy, conqueror=self.city.owner)

        else: # 攻城军耗尽
            if not defend_armies:
                assert(0), "攻城军和守城军无法同时为0！"
            else:
                msg = f"敌方势力 {enemy.owner.name} 成功防守 {enemy.name}！"
                self.parent_window.log_list.addItem(msg)     # 主窗口日志
                self.log_label.setText(msg)                  # 二级窗口显示
                self.parent_window.refresh_faction_panel()
                #TODO: 在主窗口和二级窗口显示敌方势力 {enemy.owner.name} 成功防守 {enemy.name}！

            # 如果攻城军耗尽，守城军依旧存在，攻城的将领要么在前面的逻辑被俘，要么已经逃回self，因此无需处理

        return fight_or_cancel# 无需返回日志，因为日志在运行过程中以及主窗口中已经显示出来了

    def on_attack(self):
        if not self.check_and_consume_action():
            return

        # TODO: 记主窗口为一级窗口，点击城市后打开的窗口为二级窗口，则选择出城作战的武将时打开三级窗口
        # Step1 选择我方出战武将
        tmp_list = [g for g in self.city.generals if g.army > 0]

        if not tmp_list:
            QMessageBox.warning(self, "提示", "没有可出战的武将")
            # 返还操作次数
            self.parent_window.actions_remaining += 1
            self.parent_window.update_turn_info()
            self.update_buttons_state()
            return

        dlg = ArmySelectDialog(tmp_list, self) #给出的选项应该在士兵数大于0的武将中选择
        if dlg.exec() != QDialog.Accepted:
            # 用户取消，返还操作次数
            self.parent_window.actions_remaining += 1
            self.parent_window.update_turn_info()
            self.update_buttons_state()
            return
        armies = dlg.get_selected()
        if not armies:
            QMessageBox.warning(self, "提示", "未选择武将")
            # 返还操作次数
            self.parent_window.actions_remaining += 1
            self.parent_window.update_turn_info()
            self.update_buttons_state()
            return

        #TODO: 选择完毕武将后选择要攻击的城市，此时关闭旧的三级窗口，打开新的三级窗口
        dlg2 = CitySelectDialog(self.city, self)
        if dlg2.exec() != QDialog.Accepted:
            # 用户取消，返还操作次数
            self.parent_window.actions_remaining += 1
            self.parent_window.update_turn_info()
            self.update_buttons_state()
            return
        enemy = dlg2.get_city()

        # Step3 使用 simulate_attack 运行战斗得到 logs
        if not self.simulate_attack(armies, enemy):# 用户在战斗过程中取消
            # 返还操作次数
            self.parent_window.actions_remaining += 1
            self.parent_window.update_turn_info()
            self.update_buttons_state()
            return

    def on_transfer(self):
        if not self.check_and_consume_action():
            return
        dlg = TransferDialog(self, self.city)
        if dlg.exec() == QDialog.Accepted:
            dest, food, gold = dlg.get_result()
            if food > self.city.food or gold > self.city.gold:
                QMessageBox.warning(self, "错误", "资源不足")
                # 返还操作次数
                self.parent_window.actions_remaining += 1
                self.parent_window.update_turn_info()
                self.update_buttons_state()
                return
            self.city.food -= food
            self.city.gold -= gold
            dest.food += food
            dest.gold += gold
            self.log_label.setText(f"向 {dest.name} 运输 粮{food} 金{gold}")
            self.refresh()
            self.world_update()
        else:
            # 用户取消运输，返还操作次数
            self.parent_window.actions_remaining += 1
            self.parent_window.update_turn_info()
            self.update_buttons_state()

class CityNodeSignals(QObject):
    """专门用于信号的辅助类"""
    city_clicked = Signal(object)  # 定义信号

class CityNode(QGraphicsEllipseItem):
    R = 80
    
    def __init__(self, city: City, x: float, y: float):
        super().__init__(-CityNode.R, -CityNode.R, CityNode.R*2, CityNode.R*2)
        self.city = city
        self.setPos(x, y)
        
        # 创建信号对象
        self.signals = CityNodeSignals()
        
        # 初始颜色设置
        self.update_color()
        
        self.setPen(QPen(Qt.black, 3))
        self.setFlag(QGraphicsEllipseItem.ItemIsSelectable, True)
        self.setFlag(QGraphicsEllipseItem.ItemIsFocusable, True)

        # 城市名称标签
        text = QGraphicsSimpleTextItem(city.name, self)
        font = text.font()
        font.setPointSize(24)
        font.setBold(True)
        text.setFont(font)
        br = text.boundingRect()
        text.setPos(-br.width()/2, -br.height()/2)
        text.setBrush(QBrush(Qt.white))
    
    def update_color(self):
        """根据城市所有者更新颜色"""
        if self.city.owner.name == "蜀":
            color = QColor(200, 50, 50, 220)    # 红色 - 蜀
        elif self.city.owner.name == "魏":
            color = QColor(50, 50, 200, 220)    # 蓝色 - 魏
        elif self.city.owner.name == "吴":
            color = QColor(50, 200, 50, 220)    # 绿色 - 吴
        else:
            color = QColor(150, 150, 150, 220)  # 灰色 - 其他
        
        self.setBrush(QBrush(color))
        self.update()  # 强制重绘
    
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.signals.city_clicked.emit(self.city)  # 使用 signals 对象发射信号
            event.accept()
        else:
            super().mousePressEvent(event)

class TransferDialog(QDialog):
    def __init__(self, parent, origin_city: City):
        super().__init__(parent)
        self.origin = origin_city
        self.setWindowTitle("运输 粮/金")
        layout = QFormLayout()

        # target choice
        mainwin = self.parent().parent()
        self.dest_combo = QComboBox()
         # 直接在下拉框中存储城市对象
        cities = [
            c for c in mainwin.world_cities
            if c != origin_city and c.owner == origin_city.owner
        ]

        for c in cities:
            self.dest_combo.addItem(c.name, c)  # 第二个参数是关联的数据
        layout.addRow("目标城市", self.dest_combo)

        self.food_spin = QSpinBox(); self.food_spin.setRange(0, origin_city.food)
        self.gold_spin = QSpinBox(); self.gold_spin.setRange(0, origin_city.gold)
        layout.addRow("粮草", self.food_spin)
        layout.addRow("金钱", self.gold_spin)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        self.setLayout(layout)

    def get_result(self):
        # 直接从下拉框获取关联的城市对象
        dest = self.dest_combo.currentData()
        if dest:
            return dest, self.food_spin.value(), self.gold_spin.value()
        return None, 0, 0

class ArmySelectDialog(QDialog):
    def __init__(self, armies, parent=None, single_mode=False):
        super().__init__(parent)
        self.armies = armies
        self.single_mode = single_mode
        self.setWindowTitle("选择武将")
        self.resize(400, 500)

        layout = QVBoxLayout(self)
        self.list = QListWidget()
        self.list.setSelectionMode(
            QListWidget.SingleSelection if single_mode else QListWidget.MultiSelection
        )

        for g in armies:
            item = QListWidgetItem(f"{g.name} | 统率:{g.leadership} 武力:{g.martial} 兵:{g.army}")
            item.setData(Qt.UserRole, g)
            self.list.addItem(item)

        layout.addWidget(self.list)

        btn = QPushButton("确定")
        btn.clicked.connect(self.accept)
        layout.addWidget(btn)

    def get_selected(self):
        items = self.list.selectedItems()
        if not items:
            return []
        if self.single_mode:
            return [items[0].data(Qt.UserRole)]
        return [i.data(Qt.UserRole) for i in items]

class CitySelectDialog(QDialog):
    def __init__(self, city: City, parent=None):
        super().__init__(parent)
        self.setWindowTitle("选择目标城市")

        layout = QVBoxLayout()
        self.list = QListWidget()
      
        # 直接保存可攻击城市的引用
        self.targets = [
            c for c in city.neighbors
            if c.owner != city.owner
        ]

        # 填入名称
        for c in self.targets:
            self.list.addItem(c.name)

        layout.addWidget(self.list)

        btns = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        btns.accepted.connect(self.accept)
        btns.rejected.connect(self.reject)
        layout.addWidget(btns)
        self.setLayout(layout)

    def get_city(self):
        idx = self.list.currentRow()
        if idx < 0:
            return None
        return self.targets[idx]

class FormationSelectDialog(QDialog):
    def __init__(self, parent=None, wintitle="选择阵型"):
        super().__init__(parent)
        self.setWindowTitle(wintitle)
        self.resize(300, 200)#设置选择阵型的窗口大小

        layout = QVBoxLayout(self)

        self.combo = QComboBox()
        self.combo.addItems(["锋矢阵", "方圆阵", "投石阵"])
        layout.addWidget(self.combo)

        btn = QPushButton("确定")
        btn.clicked.connect(self.accept)
        layout.addWidget(btn)

    def get_formation(self):
        return self.combo.currentText()

class FoodTradeDialog(QDialog):
    """粮食买卖对话框"""
    def __init__(self, city: City, parent=None):
        super().__init__(parent)
        self.city = city
        self.setWindowTitle("买卖粮食")
        self.resize(300, 200)
        
        layout = QVBoxLayout(self)
        
        # 当前资源显示
        info_label = QLabel(f"当前粮食: {city.food}\n当前金钱: {city.gold}")
        layout.addWidget(info_label)
        
        # 交易类型选择
        type_layout = QHBoxLayout()
        type_layout.addWidget(QLabel("交易类型:"))
        self.trade_type = QComboBox()
        self.trade_type.addItems(["购买粮食", "出售粮食"])
        self.trade_type.currentTextChanged.connect(self.update_info)
        type_layout.addWidget(self.trade_type)
        layout.addLayout(type_layout)
        
        # 交易数量
        amount_layout = QHBoxLayout()
        amount_layout.addWidget(QLabel("交易数量:"))
        self.amount_spin = QSpinBox()
        self.amount_spin.setRange(1, 10000)
        self.amount_spin.valueChanged.connect(self.update_info)
        amount_layout.addWidget(self.amount_spin)
        layout.addLayout(amount_layout)
        
        # 交易信息显示
        self.info_label = QLabel()
        layout.addWidget(self.info_label)
        
        # 按钮
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        
        self.update_info()
    
    def update_info(self):
        """更新交易信息显示"""
        trade_type = self.trade_type.currentText()
        amount = self.amount_spin.value()
        
        if trade_type == "购买粮食":
            cost = amount
            food_gain = amount * 10
            info_text = f"花费: {cost} 金钱\n获得: {food_gain} 粮食"
            # 检查是否买得起
            if cost > self.city.gold:
                info_text += f"\n金钱不足！"
        else:  # 出售粮食
            food_cost = amount * 10
            gold_gain = amount
            info_text = f"花费: {food_cost} 粮食\n获得: {gold_gain} 金钱"
            # 检查是否卖得起
            if food_cost > self.city.food:
                info_text += f"\n粮食不足！"
        
        self.info_label.setText(info_text)
    
    def get_result(self):
        """返回交易结果"""
        trade_type = "buy" if self.trade_type.currentText() == "购买粮食" else "sell"
        return trade_type, self.amount_spin.value()

class GeneralTransferDialog(QDialog):
    """武将调遣对话框 - 支持多选"""
    def __init__(self, current_city: City, all_cities: list[City], parent=None):
        super().__init__(parent)
        self.current_city = current_city
        self.all_cities = [c for c in all_cities if c != current_city and c.owner == current_city.owner]
        
        self.setWindowTitle("调遣武将")
        self.resize(500, 400)
        
        layout = QVBoxLayout(self)
        
        # 武将选择（多选）
        layout.addWidget(QLabel("选择要调遣的武将（可多选）:"))
        self.general_list = QListWidget()
        self.general_list.setSelectionMode(QListWidget.MultiSelection)  # 设置为多选模式
        
        for general in current_city.generals:
            item = QListWidgetItem(f"{general.name} (统率:{general.leadership} 武力:{general.martial} 兵力:{general.army})")
            item.setData(Qt.UserRole, general)
            self.general_list.addItem(item)
        
        layout.addWidget(self.general_list)
        
        # 目标城市选择
        layout.addWidget(QLabel("选择目标城市:"))
        self.city_combo = QComboBox()
        for city in self.all_cities:
            generals_count = len(city.generals)
            self.city_combo.addItem(f"{city.name} (现有武将:{generals_count})", city)
        layout.addWidget(self.city_combo)
        
        # 信息显示
        self.info_label = QLabel("请选择要调遣的武将和目标城市")
        self.info_label.setStyleSheet("color: blue;")
        layout.addWidget(self.info_label)
        
        # 连接信号，实时更新信息
        self.general_list.itemSelectionChanged.connect(self.update_info)
        self.city_combo.currentIndexChanged.connect(self.update_info)
        
        # 按钮
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        
        self.update_info()
    
    def update_info(self):
        """更新调遣信息显示"""
        selected_generals = self.get_selected_generals()
        target_city = self.city_combo.currentData()
        
        if not selected_generals:
            self.info_label.setText("请选择要调遣的武将")
            return
        
        if not target_city:
            self.info_label.setText("请选择目标城市")
            return
        
        general_names = "、".join([g.name for g in selected_generals])
        total_army = sum(g.army for g in selected_generals)
        
        self.info_label.setText(
            f"准备调遣 {len(selected_generals)} 名武将到 {target_city.name}：\n"
            f"{general_names}\n"
            f"总兵力：{total_army} 人"
        )
    
    def get_selected_generals(self):
        """获取选中的武将列表"""
        selected_generals = []
        for item in self.general_list.selectedItems():
            general = item.data(Qt.UserRole)
            if general:
                selected_generals.append(general)
        return selected_generals
    
    def get_result(self):
        """返回选择的武将列表和目标城市"""
        selected_generals = self.get_selected_generals()
        target_city = self.city_combo.currentData()
        return selected_generals, target_city     

class HoverImageWindow(QDialog):
    """ 悬停时出现的小头像窗口（无边框） """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(
            Qt.FramelessWindowHint |
            Qt.Tool |
            Qt.WindowStaysOnTopHint
        )
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.label = QLabel(self)
        self.label.setAlignment(Qt.AlignCenter)
        self.resize(180, 220)

    def show_image(self, pixmap: QPixmap):
        if pixmap is None or pixmap.isNull():
            return
        self.label.setPixmap(
            pixmap.scaled(
                self.width(), self.height(),
                Qt.KeepAspectRatio, Qt.SmoothTransformation
            )
        )
        self.show()

    def clear(self):
        # 清空并隐藏
        self.label.clear()
        self.hide()

class CityIntelDialog(QDialog):
    """
    城市情报窗口：
    - 左侧：武将属性列表
    - 鼠标悬停某项 → 右侧弹出 HoverImageWindow（使用已有类）
    """

    def __init__(self, city: City, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"{city.name} - 城市情报")
        self.resize(520, 380)

        self.city = city
        self.generals = city.generals

        # 记录悬浮窗口与上一个 item
        self.hover_window: HoverImageWindow | None = None
        self._last_item = None

        layout = QVBoxLayout(self)

        # ================= 武将列表 =================
        self.list_widget = QListWidget()
        self.list_widget.setMouseTracking(True)
        self.list_widget.leaveEvent = self._on_list_leave
        layout.addWidget(self.list_widget)

        for g in self.generals:
            text = (
                f"{g.name} | "
                f"统:{g.leadership} 武:{g.martial} 智:{g.intellect} "
                f"政:{g.politics} | 兵:{g.army}"
            )
            item = QListWidgetItem()
            item.setText(text)
            item.setData(Qt.UserRole, g)
            self.list_widget.addItem(item)

        # 用于捕获鼠标移动事件
        self.list_widget.mouseMoveEvent = self._on_mouse_move

        btn_box = QDialogButtonBox(QDialogButtonBox.Close)
        btn_box.rejected.connect(self.reject)
        layout.addWidget(btn_box)

    # ======================================================================
    # 鼠标移动：判断悬停项
    # ======================================================================
    def _on_mouse_move(self, event):
        # Qt6 写法兼容
        try:
            pos = event.position().toPoint()
        except:
            pos = event.pos()

        item = self.list_widget.itemAt(pos)
        if item is None:
            self._hide_hover()
            self._last_item = None
        else:
            if item != self._last_item:
                self._last_item = item
                self._show_hover(item)

        return QListWidget.mouseMoveEvent(self.list_widget, event)

    def _on_list_leave(self, event):
        self._hide_hover()
        self._last_item = None
        return super(QListWidget, self.list_widget).leaveEvent(event)

    # ======================================================================
    # 显示已有 HoverImageWindow
    # ======================================================================
    def _show_hover(self, item):
        g: General = item.data(Qt.UserRole)
        img_path = f"image/{g.name}.jpg"

        pix = QPixmap(img_path)
        if pix.isNull():
            self._hide_hover()
            return

        # 第一次：创建 HoverImageWindow
        if self.hover_window is None:
            self.hover_window = HoverImageWindow(self)

        # 设置图片
        self.hover_window.show_image(pix)

        # =========== 位置计算：放在右侧，不遮挡母窗口 ===========
        dialog_pos = self.mapToGlobal(self.rect().topLeft())
        x = dialog_pos.x() + self.width() + 10

        rect = self.list_widget.visualItemRect(item)
        global_item_top = self.list_widget.viewport().mapToGlobal(rect.topLeft())
        y = global_item_top.y()

        self.hover_window.move(x, y)
        self.hover_window.show()

    # ======================================================================
    # 隐藏头像窗口
    # ======================================================================
    def _hide_hover(self):
        if self.hover_window:
            self.hover_window.hide()

class PrisonerDialog(QDialog):
    """ 劝降窗口：文字列表为主，鼠标悬停时在旁边弹出无边框头像窗口 """
    def __init__(self, prisoners: List[Tuple["General", int]], parent=None):
        super().__init__(parent)
        self.setWindowTitle("劝降武将")
        self.resize(520, 360)

        self.prisoners = prisoners
        self._last_item = None
        self.hover_window = None

        main_layout = QVBoxLayout(self)

        # 列表：只展示文字信息（主角）
        self.list_widget = QListWidget()
        # 单选，并可通过键盘/鼠标选择
        self.list_widget.setSelectionMode(QListWidget.SingleSelection)
        self.list_widget.setMouseTracking(True)  # 让 mouseMoveEvent 生效
        for g, days in prisoners:
            item_text = (
                f"{g.name} | 统:{g.leadership} 武:{g.martial} 智:{g.intellect} "
                f"政:{g.politics} | 势力:{g.faction.name if g.faction else '无'} | 关押:{days} 回合"
            )
            self.list_widget.addItem(item_text)

        main_layout.addWidget(self.list_widget, 1)

        # 按钮栏（OK / Cancel）
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self._on_accept)
        buttons.rejected.connect(self.reject)
        main_layout.addWidget(buttons)

        # 连接事件：鼠标移动 -> 我们自定义处理；双击 -> 直接 accept
        self.list_widget.mouseMoveEvent = self._on_list_mouse_move  # 覆写以获取实时位置
        self.list_widget.leaveEvent = self._on_list_leave  # 鼠标离开列表区域时关闭头像
        self.list_widget.itemDoubleClicked.connect(self._on_double_click)

    # 鼠标在列表上移动时调用（覆写 mouseMoveEvent）
    def _on_list_mouse_move(self, event):
        # event.position() 返回 QPointF；转为 QPoint 供 itemAt() 使用
        try:
            pos = event.position().toPoint()
        except AttributeError:
            # 兼容旧版：如果没有 position() 方法，再尝试 pos()
            pos = event.pos()

        item = self.list_widget.itemAt(pos)
        if item is None:
            # 没有悬停到 item，隐藏窗口（仅在曾经显示时）
            self._hide_hover()
            self._last_item = None
        else:
            if item != self._last_item:
                # item 发生变化：显示新的图像
                self._last_item = item
                self._show_hover_for_item(item, pos)
            # 否则保持当前图像显示

        # 继续默认行为（保留内建 hover 效果等）
        QListWidget.mouseMoveEvent(self.list_widget, event)

    def _on_list_leave(self, event):
        # 鼠标离开整个列表区域，关闭头像
        self._last_item = None
        self._hide_hover()
        return super(QListWidget, self.list_widget).leaveEvent(event)

    def _on_double_click(self, item):
        # 双击即选择并确认
        row = self.list_widget.row(item)
        if row >= 0:
            self.list_widget.setCurrentRow(row)
            self._on_accept()

    def _on_accept(self):
        if self.list_widget.currentRow() < 0:
            QMessageBox.warning(self, "提示", "请先选择一个武将或双击选中武将")
            return
        self.accept()

    def _show_hover_for_item(self, item, pos):
        # 根据 item 文本解析出名字（你之前格式是 "名字 | ..."）
        name = item.text().split("|")[0].strip()
        image_path = f"image/{name}.jpg"  # 你约定的路径
        pix = QPixmap(image_path)
        if pix.isNull():
            # 没有图片时隐藏
            self._hide_hover()
            return

        if self.hover_window is None:
            self.hover_window = HoverImageWindow(self)

        # 显示图片
        self.hover_window.show_image(pix)

        # 将悬浮窗口放在劝降对话框右侧并对齐当前 item 行的垂直位置
        # 计算全局坐标：列表 viewport 上的 item 顶部坐标
        item_rect = self.list_widget.visualItemRect(item)
        # item_rect.topLeft() 是相对于 viewport 的坐标
        global_item_top = self.list_widget.viewport().mapToGlobal(item_rect.topLeft())
        dialog_global = self.mapToGlobal(self.rect().topLeft())
        x = dialog_global.x() + self.width() + 8  # 放在对话框右侧
        y = global_item_top.y()
        # 如果超出屏幕底部，可以向上微调（可选）
        self.hover_window.move(x, y)

    def _hide_hover(self):
        if self.hover_window:
            self.hover_window.clear()
            # 不销毁 hover_window，以免频繁创建销毁；若希望销毁以释放资源可调用 close()
            # self.hover_window.close()
            # self.hover_window = None

    # 在 dialog 关闭时确保清理
    def closeEvent(self, event):
        self._hide_hover()
        return super().closeEvent(event)

class MapView(QGraphicsView):
    def __init__(self, parent=None):
        super().__init__(parent)
        sc = QGraphicsScene(self)
        sc.parent = parent
        self.setScene(sc)
        
        self.setRenderHint(QPainter.Antialiasing)
        self.setRenderHint(QPainter.SmoothPixmapTransform)
        
        # 设置视图属性
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.setDragMode(QGraphicsView.ScrollHandDrag)  # 允许拖拽查看
        
        # 设置背景图片
        self.background_item = None
        self.set_background_image("image/三国地图.png")
    
    def set_background_image(self, image_path):
        """设置填满整个视图的地图背景图片"""
        pixmap = QPixmap(image_path)
        if not pixmap.isNull():
            # 清除之前的背景
            if self.background_item:
                self.scene().removeItem(self.background_item)
            
            # 设置场景矩形为图片大小
            self.scene().setSceneRect(0, 0, pixmap.width(), pixmap.height())
            
            # 创建背景图片项
            self.background_item = QGraphicsPixmapItem(pixmap)
            self.background_item.setPos(0, 0)
            self.background_item.setZValue(-1)  # 确保背景在最底层
            
            self.scene().addItem(self.background_item)
            
            # 初始适应视图
            self.fitInView(self.background_item, Qt.KeepAspectRatioByExpanding)
            
            print(f"地图背景图片加载成功: {image_path} - 尺寸: {pixmap.width()}x{pixmap.height()}")
        else:
            print(f"无法加载地图背景图片: {image_path}")
            # 设置默认背景
            self.scene().setBackgroundBrush(QBrush(QColor(200, 220, 240)))
    
    def resizeEvent(self, event):
        """当窗口大小改变时，重新调整视图"""
        super().resizeEvent(event)
        if self.background_item:
            self.fitInView(self.background_item, Qt.KeepAspectRatioByExpanding)
    
    def wheelEvent(self, event):
        """支持鼠标滚轮缩放"""
        zoom_in_factor = 1.25
        zoom_out_factor = 1 / zoom_in_factor
        
        # 保存当前鼠标位置的场景坐标
        old_pos = self.mapToScene(event.position().toPoint())
        
        # 缩放
        if event.angleDelta().y() > 0:
            zoom_factor = zoom_in_factor
        else:
            zoom_factor = zoom_out_factor
        
        self.scale(zoom_factor, zoom_factor)
        
        # 将鼠标位置调整回原来的场景坐标
        new_pos = self.mapToScene(event.position().toPoint())
        delta = new_pos - old_pos
        self.translate(delta.x(), delta.y())

class MainWindow(QMainWindow):
    def __init__(self, faction: Faction, world_cities: list[City], other_factions: list[Faction]):
        super().__init__()
        self.setWindowTitle("三国志 - 地图界面")
        self.faction = faction
        self.world_cities = world_cities
        self.info_window = None
        self.game_over = False

        self.other_factions = other_factions # 记录其他势力列表，供电脑回合使用

        self.player = faction
        self.world = world_cities

        # 添加回合操作计数器
        self.actions_remaining = 8  # 每回合剩余的操作次数
        self.actions_per_turn = 8  # 每回合允许的操作次数
        self.current_turn = 1  # 当前回合数

        central = QWidget()
        h = QHBoxLayout()
        central.setLayout(h)
        self.setCentralWidget(central)

        # 地图视图
        #self.map = MapView(parent=self)
        #h.addWidget(self.map, 3)
        # 地图视图
        self.map = MapView(parent=self)
        h.addWidget(self.map, 3)

        # 右侧面板：势力 / 日志
        right = QVBoxLayout()
        self.lbl_faction = QLabel()
        right.addWidget(self.lbl_faction)

        # 添加回合信息显示
        self.turn_info = QLabel()
        right.addWidget(self.turn_info)
        
        # 添加结束回合按钮
        self.end_turn_btn = QPushButton("结束回合")
        self.end_turn_btn.clicked.connect(self.on_end_turn)
        self.end_turn_btn.setStyleSheet("font-size: 16px; font-weight: bold; padding: 10px;")
        right.addWidget(self.end_turn_btn)
        
        self.log_list = QListWidget()
        right.addWidget(self.log_list, 1)
        h.addLayout(right, 1)

        self.scene = self.map.scene()

        #offset_x = -80    # 向左移动 80 像素
        #offset_y = -60    # 向上移动 60 像素

        # ====== 固定城市坐标（画成三角地图） ======
        # 之前的坐标
        old_positions = {
            # 蜀
            "益州": (-200, 100),
            "汉中": (-100, 0),
            "荆州": (-150, 200),

            # 魏
            "上庸": (0, -50),
            "许昌": (150, -20),
            "陈留": (250, 0),

            # 吴
            "柴桑": (200, 150),
            "吴": (300, 120),
            "会稽": (280, 200),
        }
        # 转换到新坐标
        fixed_positions = {}
        for city_name, (x_old, y_old) in old_positions.items():
            x_new = (x_old + 400) * (2364 / 800)
            y_new = (y_old + 300) * (1773 / 600)
            fixed_positions[city_name] = (x_new, y_new)

        # ====== 在地图中加入城市节点 ======
        self.city_nodes = {}
        for city in world_cities:
            pos = fixed_positions.get(city.name, (1182, 886))
            node = CityNode(city, pos[0], pos[1])
            self.scene.addItem(node)
            self.city_nodes[city.name] = node
            
            # 连接信号到槽
            node.signals.city_clicked.connect(self.on_city_clicked)
            
            node.setAcceptHoverEvents(True)

        # ====== 按你的三条路径连线 ======

        edges = [
            # 路径1
            ("益州", "汉中"),
            ("汉中", "上庸"),
            ("上庸", "许昌"),

            # 路径2
            ("许昌", "陈留"),
            ("陈留", "柴桑"),
            ("柴桑", "吴"),

            # 路径3
            ("吴", "会稽"),
            ("会稽", "荆州"),
            ("荆州", "益州"),
        ]

        for a, b in edges:
            if a in self.city_nodes and b in self.city_nodes:
                n1 = self.city_nodes[a]
                n2 = self.city_nodes[b]

                self.add_connection(n1, n2)
                #line = QGraphicsLineItem(n1.pos().x(), n1.pos().y(), n2.pos().x(), n2.pos().y())
                #line.setPen(QPen(Qt.black, 2))
                #self.scene.addItem(line)


        self.refresh_faction_panel()
        self.update_turn_info()

    def update_turn_info(self):
        """更新回合信息显示"""
        self.turn_info.setText(
            f"第 {self.current_turn} 回合\n"
            f"剩余操作次数: {self.actions_remaining}/{self.actions_per_turn}"
        )
        
        # 根据剩余操作次数更新按钮状态
        if self.actions_remaining <= 0:
            self.turn_info.setStyleSheet("color: red; font-weight: bold;")
        else:
            self.turn_info.setStyleSheet("color: black;")

    def check_game_over(self, conquered_city: City = None, conqueror: Faction = None):
        """检查游戏是否结束"""
        if self.game_over:
            return
            
        # 如果玩家统一了所有势力
        player_faction = self.faction
        all_factions = [self.faction] + self.other_factions
        
        # 检查是否所有城市都属于玩家
        all_cities_belong_to_player = all(city.owner == player_faction for city in self.world_cities)
        
        if all_cities_belong_to_player:
            self.show_victory_dialog()
            return
        
        # 检查玩家是否失去所有城市
        if not player_faction.cities:
            self.show_defeat_dialog()
            return
        
        # 检查特定征服事件
        if conquered_city and conqueror:
            # 如果玩家征服了最后一个敌方城市
            if conqueror == player_faction:
                # 检查是否还有其他敌方势力存在
                remaining_enemies = [f for f in self.other_factions if f.cities]
                if not remaining_enemies:
                    self.show_victory_dialog()
                    return
            
            # 如果电脑征服了玩家的最后一个城市
            elif conquered_city.owner == player_faction and len(player_faction.cities) == 1:
                # 这个城市即将被征服，玩家将失去所有城市
                self.show_defeat_dialog()
                return

    def show_victory_dialog(self):
        """显示胜利对话框"""
        self.game_over = True
        dialog = GameOverDialog(
            "一统中原", 
            "恭喜你！\n你已统一天下，成就霸业！\n万民归心，四海升平！", 
            is_victory=True,
            parent=self
        )
        dialog.exec()

    def show_defeat_dialog(self):
        """显示失败对话框"""
        self.game_over = True
        dialog = GameOverDialog(
            "势力覆灭", 
            "你的势力已经覆灭！\n霸业未成，壮志未酬...\n愿来世再图大业！", 
            is_victory=False,
            parent=self
        )
        dialog.exec()

    def update_city_color(self, city_name: str):
        """更新指定城市的颜色"""
        if city_name in self.city_nodes:
            node = self.city_nodes[city_name]
            node.update_color()
    
    def update_all_city_colors(self):
        """更新所有城市的颜色"""
        for city_name, node in self.city_nodes.items():
            node.update_color()

    def on_end_turn(self):
        """结束当前回合，开始电脑操作"""
        if self.actions_remaining > 0:
            reply = QMessageBox.question(
                self, 
                "确认结束回合", 
                f"你还有 {self.actions_remaining} 次操作未使用，确定要结束回合吗？",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )
            if reply == QMessageBox.No:
                return
        
        # 执行电脑回合逻辑
        self.execute_computer_turn()
        
        # 重置玩家操作次数
        self.actions_remaining = self.actions_per_turn
        self.current_turn += 1
        self.update_turn_info()

        # 确保所有城市颜色正确显示
        self.update_all_city_colors()

        # 更新所有城市状态（月度更新）
        player_city_logs = []
        for city in self.world_cities:
            # 月度更新
            monthly_log = city.monthly_update()
            if city.owner == self.player:
                player_city_logs.append(monthly_log)
            
            # 更新监狱
            prisoner_log = city.update_prisoners()
            if prisoner_log != "无逃脱事件":
                player_city_logs.append(prisoner_log)

        # 显示玩家城市的更新日志
        if player_city_logs:
            for log in player_city_logs:
                for line in log.split('\n'):
                    if line.strip():
                        self.log_list.addItem(line)
        
        self.log_list.addItem(f"=== 第 {self.current_turn} 回合开始 ===")
        self.refresh_faction_panel()

    def execute_computer_turn(self):
        """执行电脑势力的回合操作"""
        self.log_list.addItem("=== 电脑势力行动开始 ===")
        
        # 电脑也有操作次数限制（每个势力独立）
        computer_actions_per_faction = self.actions_per_turn
        
        # 按照势力顺序执行
        for faction in self.other_factions:
            if not faction.cities:  # 势力已灭亡
                continue
                
            actions_remaining = computer_actions_per_faction
            self.log_list.addItem(f"--- {faction.name}势力行动 ---")
            
            # 第零阶段：劝降囚犯（高优先级）
            if actions_remaining > 0:
                actions_remaining = self.execute_computer_persuade_prisoners(faction, actions_remaining)

             # 第一阶段：内部管理（设置官员、买卖粮食、调遣武将）
            if actions_remaining > 0:
                actions_remaining = self.execute_computer_internal_management(faction, actions_remaining)

            # 第二阶段：内部资源调配（粮草运输）
            if actions_remaining > 0:
                actions_remaining = self.execute_computer_resource_management(faction, actions_remaining)
            
            # 第二阶段：军事行动（攻击玩家）
            if actions_remaining > 0:
                actions_remaining = self.execute_computer_military_actions(faction, actions_remaining)


            if actions_remaining > 0: #还有多余行动力时随机挑选城市进行探索
                while actions_remaining > 0:
                    actions_remaining -= 1
                    random_city = random.choice(faction.cities)
                    random_city.explore()
            
            self.log_list.addItem(f"--- {faction.name}势力行动结束 ---")

    def execute_computer_persuade_prisoners(self, faction: Faction, actions_remaining):
        """电脑劝降囚犯逻辑"""
        # 收集所有有囚犯的城市
        cities_with_prisoners: list[City] = []
        
        for city in faction.cities:
            if city.prisoners:
                cities_with_prisoners.append(city)
        
        if not cities_with_prisoners:
            return actions_remaining
        
        # 按城市重要性排序（城池数量少的势力更急需武将）
        cities_with_prisoners.sort(key=lambda c: len(faction.cities))
        
        for city in cities_with_prisoners:
            if actions_remaining <= 0:
                break
            
            for prisoner, _ in city.prisoners:
                if actions_remaining <= 0:
                    break
                if city.persuade_prisoner(prisoner):
                    self.refresh_faction_panel()
                actions_remaining -= 1
        
        return actions_remaining

    def execute_computer_set_officers(self, city: City):
        """电脑设置官员逻辑"""
        if not city.generals:
            return False
        
        changed = False
        # 只有一个武将的情况
        if len(city.generals) == 1:
            single_general = city.generals[0]
            
            intell = single_general.intellect
            polit = single_general.politics

            if intell >= polit: #该武将适合开发商业
                if city.officer_commerce:
                    if city.officer_commerce != single_general:
                        assert(0), "城市只有一个武将,且城市的商业开发官员有人担任，但是两者不是一人，出现问题！"
                else:
                    city.officer_commerce = single_general
                    changed = True
            else: #该武将适合开发农业
                if city.officer_agriculture:
                    if city.officer_agriculture != single_general:
                        assert(0), "城市只有一个武将,且城市的农业业开发官员有人担任，但是两者不是一人，出现问题！"
                else:
                    city.officer_agriculture = single_general
                    changed = True
                
            return changed

        # 不止一个武将
        # 找出政治最高的武将作为农业官员候选人
        best_agri = max(city.generals, key=lambda g: g.politics)
        
        # 找出智力最高的武将作为商业官员候选人
        best_comm = max(city.generals, key=lambda g: g.intellect)
        
        # 避免同一个武将担任两个职位
        if best_agri == best_comm:
            # 如果同一个武将，选择次优的
            other_generals = [g for g in city.generals if g != best_agri]
            if other_generals:
                second_best_comm = max(other_generals, key=lambda g: g.intellect)
                best_comm = second_best_comm
        
        # 设置农业官员（如果比当前的好或者当前没有）
        if (not city.officer_agriculture or 
            best_agri.politics > city.officer_agriculture.politics):
            city.officer_agriculture = best_agri
            changed = True
        
        # 设置商业官员（如果比当前的好或者当前没有）
        if (not city.officer_commerce or 
            best_comm.intellect > city.officer_commerce.intellect):
            city.officer_commerce = best_comm
            changed = True
        
        return changed
    
    def execute_computer_transfer_generals(self, faction: Faction, actions_remaining):
        """电脑调遣武将逻辑 - 优化版"""
        # 找出需要增援的城市（边境城市或兵力不足的城市）
        reinforcement_needed = []
        
        for city in faction.cities:
            # 检查是否是边境城市（有敌方邻居）
            is_border_city = any(neighbor.owner != faction for neighbor in city.neighbors)
            
            # 计算城市总兵力
            total_army = sum(g.army for g in city.generals)
            
            # 如果是边境城市且兵力不足，需要增援
            if is_border_city and total_army < 2000:
                reinforcement_needed.append((city, total_army))
        
        if not reinforcement_needed:
            return actions_remaining
        
        # 按兵力需求排序（兵力越少的越需要增援）
        reinforcement_needed.sort(key=lambda x: x[1])
        
        # 找出有富余兵力的城市（内陆城市或兵力充足的城市）
        donor_cities = []
        
        for city in faction.cities:
            # 检查是否是内陆城市（没有敌方邻居）
            is_inland = all(neighbor.owner == faction for neighbor in city.neighbors)
            
            total_army = sum(g.army for g in city.generals)
            
            # 如果是内陆城市且兵力充足，可以作为捐赠城市
            if is_inland and total_army > 1500 and len(city.generals) > 1:
                donor_cities.append((city, total_army))
        
        if not donor_cities:
            return actions_remaining
        
        # 按兵力富余程度排序
        donor_cities.sort(key=lambda x: x[1], reverse=True)
        
        # 为需要增援的城市调遣武将（一次可以调遣多名）
        for target_city, target_army in reinforcement_needed:
            if actions_remaining <= 0:
                break
                
            # 计算需要的增援兵力
            needed_army = 2000 - target_army
            
            # 从捐赠城市选择武将调遣
            for donor_city, donor_army in donor_cities:
                if actions_remaining <= 0:
                    break
                    
                if donor_army <= 1000:  # 捐赠城市兵力不足
                    continue
                    
                # 选择要调遣的武将（选择兵力适中的，避免调走主力）
                available_generals = [g for g in donor_city.generals if g.army > 0]
                if len(available_generals) <= 1:  # 至少要保留1名武将
                    continue
                    
                # 按兵力排序，选择中间力量的武将（不调最强的，也不调最弱的）
                sorted_generals = sorted(available_generals, key=lambda g: g.army)
                transfer_candidates = []
                
                # 尝试选择1-3名武将进行调遣
                if len(sorted_generals) >= 4:
                    transfer_candidates = sorted_generals[1:3]  # 选择第2、3名
                elif len(sorted_generals) >= 3:
                    transfer_candidates = [sorted_generals[1]]  # 选择第2名
                else:
                    transfer_candidates = [sorted_generals[0]]  # 选择最弱的
                
                if transfer_candidates:
                    # 执行调遣
                    for general in transfer_candidates:
                        donor_city.remove_general(general)
                        target_city.generals.append(general)
                    
                    general_names = "、".join([g.name for g in transfer_candidates])
                    self.log_list.addItem(f"{faction.name}势力从{donor_city.name}调遣{len(transfer_candidates)}名武将到{target_city.name}：{general_names}")
                    actions_remaining -= 1
                    
                    # 更新捐赠城市兵力
                    donor_army = sum(g.army for g in donor_city.generals)
                    if donor_army <= 1000:
                        break
        
        return actions_remaining

    def execute_computer_trade_food(self, city: City):
        """电脑买卖粮食逻辑 - 优化版"""
        # 计算粮食需求（每个士兵每回合消耗1粮食）
        army_food_consumption = sum(g.army for g in city.generals)
        
        # 计算官员维护费用（假设每个官员需要一定金钱维护）
        officer_maintenance = 0
        if city.officer_agriculture:
            officer_maintenance += city.officer_agriculture.monthly_salary()  # 农业官员维护费
        if city.officer_commerce:
            officer_maintenance += city.officer_commerce.monthly_salary()  # 商业官员维护费
        
        # 计算开发所需的最低金钱（官员维护 + 缓冲）
        development_min_gold = officer_maintenance + 100
        
        # 情况1：买粮食（当粮食不足且有钱留给开发时）
        if city.food < army_food_consumption:
            # 计算缺粮数量
            food_deficit = army_food_consumption - city.food
            
            # 计算可以用于买粮食的最大金钱（要保留开发所需金钱）
            available_gold_for_food = max(0, city.gold - development_min_gold)
            
            if available_gold_for_food > 0:
                # 买足够的粮食来满足军队消耗（至少买缺粮部分）
                buy_amount = min(food_deficit // 10 + 1, available_gold_for_food)
                
                if buy_amount > 0:
                    cost = buy_amount
                    food_gain = buy_amount * 10
                    
                    city.gold -= cost
                    city.food += food_gain
                    self.log_list.addItem(f"{city.owner.name}势力在{city.name}购买粮食：花费{cost}金钱，获得{food_gain}粮食（解决缺粮问题）")
                    return True
        
        # 情况2：卖粮食（当粮食过剩且金钱不足支付开发时）
        elif city.food > army_food_consumption * 3:  # 粮食是军队消耗的3倍以上
            if city.gold < development_min_gold:
                # 计算可以卖的粮食数量（保留军队3回合的消耗）
                food_surplus = city.food - army_food_consumption * 3
                max_sell_food = min(food_surplus, 2000)  # 每次最多卖2000粮食
                
                if max_sell_food >= 10:  # 至少能卖1单位（10粮食）
                    # 计算需要卖多少粮食来获得足够的开发资金
                    gold_needed = development_min_gold - city.gold
                    sell_units = min(gold_needed, max_sell_food // 10)
                    
                    if sell_units > 0:
                        food_cost = sell_units * 10
                        gold_gain = sell_units
                        
                        city.food -= food_cost
                        city.gold += gold_gain
                        self.log_list.addItem(f"{city.owner.name}势力在{city.name}出售粮食：出售{food_cost}粮食，获得{gold_gain}金钱（用于开发资金）")
                        return True
        
        # 情况3：战略性卖粮（当粮食极其过剩时）
        elif city.food > army_food_consumption * 5 and city.food > 5000:
            # 即使金钱充足，也卖一些过剩粮食换取更多资金
            food_surplus = city.food - army_food_consumption * 3  # 保留3倍消耗
            max_sell_units = min(food_surplus // 10, 300)  # 最多卖300单位
            
            if max_sell_units > 0:
                sell_units = max_sell_units // 2  # 卖一半的过剩粮食
                food_cost = sell_units * 10
                gold_gain = sell_units
                
                city.food -= food_cost
                city.gold += gold_gain
                self.log_list.addItem(f"{city.owner.name}势力在{city.name}出售过剩粮食：出售{food_cost}粮食，获得{gold_gain}金钱")
                return True
        
        # 情况4：紧急买粮（当粮食严重不足且可能饿死士兵时）
        elif city.food < army_food_consumption // 2:  # 粮食不足军队消耗的一半
            # 即使金钱紧张也要买粮
            emergency_buy_amount = min((army_food_consumption - city.food) // 10 + 1, city.gold)
            
            if emergency_buy_amount > 0:
                cost = emergency_buy_amount
                food_gain = emergency_buy_amount * 10
                
                city.gold -= cost
                city.food += food_gain
                self.log_list.addItem(f"{city.owner.name}势力在{city.name}紧急购买粮食：花费{cost}金钱，获得{food_gain}粮食（避免军队缺粮）")
                return True
        
        return False

    def execute_computer_internal_management(self, faction: Faction, actions_remaining):
        """执行电脑内部管理（设置官员、买卖粮食、调遣武将）"""
        # 1. 首先设置官员（每个城市最多消耗1次行动）
        if actions_remaining > 0:
            for city in faction.cities:
                if actions_remaining <= 0:
                    break
                if self.execute_computer_set_officers(city):
                    actions_remaining -= 1
                    self.log_list.addItem(f"{faction.name}势力在{city.name}设置了官员")
        
        # 2. 买卖粮食（根据资源状况决定）
        if actions_remaining > 0:
            for city in faction.cities:
                if actions_remaining <= 0:
                    break
                if self.execute_computer_trade_food(city):
                    actions_remaining -= 1
        
        # 3. 调遣武将（优化兵力分布）
        if actions_remaining > 0:
            actions_remaining = self.execute_computer_transfer_generals(faction, actions_remaining)
        
        return actions_remaining

    def execute_computer_resource_management(self, faction, actions_remaining):
        """执行电脑资源管理（粮草运输）"""
        # 找出需要粮草的城市（粮草少于需求-500）
        needy_cities = []

        for city in faction.cities:
            needy_food = 0
            for general in city.generals:
                needy_food += general.army
            if city.food < needy_food - 500:
                needy_cities.append(city)
        
        if not needy_cities:
            return actions_remaining
        
        # 找出有富余粮草的城市（粮草多于需求+500）
        donor_cities = []

        for city in faction.cities:
            needy_food = 0
            for general in city.generals:
                needy_food += general.army
            if city.food > needy_food + 500:
                donor_cities.append(city)
        
        if not donor_cities:
            return actions_remaining
        
        # 为每个需要粮草的城市寻找最近的捐赠城市
        for needy_city in needy_cities:
            if actions_remaining <= 0:
                break
                
            # 寻找最近的捐赠城市（简化：随机选择）
            if donor_cities:
                donor_city = random.choice(donor_cities)
                transfer_amount = min(500, donor_city.food - 500, 1000 - needy_city.food)
                
                if transfer_amount > 0:
                    donor_city.food -= transfer_amount
                    needy_city.food += transfer_amount
                    self.log_list.addItem(f"{faction.name}势力从{donor_city.name}向{needy_city.name}运输{transfer_amount}粮草")
                    actions_remaining -= 1
                    
                    # 如果捐赠城市粮草不足了，从列表中移除
                    needy_food = 0
                    for general in donor_city.generals:
                        needy_food += general.army
                    if donor_city.food <= needy_food + 500: # 不再富余
                        donor_cities.remove(donor_city)
        
        return actions_remaining

    def execute_computer_military_actions(self, faction: Faction, actions_remaining):
        """执行电脑军事行动（攻击玩家）"""
        # 收集所有可以攻击敌方城市的电脑城市
        attackable_cities: list[Tuple[City,City]] = []
        for city in faction.cities:
            # 检查是否有相邻的非faction城市
            player_neighbors = [neighbor for neighbor in city.neighbors if neighbor.owner != faction]
            if player_neighbors and any(g.army > 800 for g in city.generals):
                for player_targets in player_neighbors:
                    attackable_cities.append((city, player_targets))
        
        if not attackable_cities:
            return actions_remaining
        
        # 随机打乱攻击顺序
        random.shuffle(attackable_cities)
        
        for attack_city, player_targets in attackable_cities:
            if actions_remaining <= 0:
                break
                
            if random.random() > 0.5:
                # 50% 概率选择不攻击，保存行动次数
                continue
            
            # 选择出战武将（选择兵力大于800的）
            available_generals = [g for g in attack_city.generals if g.army > 800]
            if available_generals:
                # 电脑可以选择多个武将攻击（最多3个）
                max_attackers = min(3, len(available_generals))
                attacking_generals = sorted(available_generals, key=lambda g: g.army, reverse=True)[:max_attackers]
                
                self.log_list.addItem(f"{faction.name}势力从{attack_city.name}向{player_targets.name}发动攻击！")
                
                # 执行电脑攻击
                self.execute_computer_attack(attack_city, attacking_generals, player_targets)
                
                # 无论攻击是否成功都消耗行动次数
                actions_remaining -= 1
        
        return actions_remaining

    def execute_computer_attack(self, origin_city, armies, target_city):
        """执行电脑攻击（会触发战斗界面）"""
        # 创建战斗管理对象来执行战斗
        battle_manager = ComputerBattleManager(self, origin_city, armies, target_city)

        # 战斗结束后更新城市颜色
        self.update_city_color(target_city.name)
        return battle_manager.execute_battle()

    def consume_action(self):
        """消耗一次操作次数"""
        if self.actions_remaining > 0:
            self.actions_remaining -= 1
            self.update_turn_info()
            return True
        return False
    
    def can_perform_action(self):
        """检查是否还可以执行操作"""
        return self.actions_remaining > 0

    def add_connection(self, node1: CityNode, node2: CityNode):
        x1, y1 = node1.pos().x(), node1.pos().y()
        x2, y2 = node2.pos().x(), node2.pos().y()

        dx = x2 - x1
        dy = y2 - y1

        dist = math.hypot(dx, dy)
        if dist == 0:
            return  # 避免除零

        # 圆半径
        R = CityNode.R

        # 方向单位向量
        ux = dx / dist
        uy = dy / dist

        # 起点：从 node1 中心沿方向移动 R
        sx = x1 + ux * R
        sy = y1 + uy * R

        # 终点：从 node2 中心沿反方向移动 R
        ex = x2 - ux * R
        ey = y2 - uy * R

        line = QGraphicsLineItem(sx, sy, ex, ey)
        pen = QPen(QColor(120, 120, 120), 8)  # 进一步加粗连接线
        line.setPen(pen)
        self.scene.addItem(line)

    def on_city_clicked(self, city: City):
        # 已有的弹窗如果存在，先关闭
        if self.info_window:
            self.info_window.close()

        is_player_city = (city.owner == self.player)

        # 创建城市信息窗口（传入是否是玩家城市）
        self.info_window = CityInfoWindow(city, is_player_city, self.world, parent=self)
        self.info_window.setWindowFlag(Qt.Window)
        self.info_window.show()

    def on_world_update(self):
        # 当世界状态有变更时（例如城市粮金变化、武将变化），更新侧面板和日志
        self.refresh_faction_panel()
        # 将基本信息写进日志
        #self.log_list.addItem("世界状态更新；(示例)")

    def refresh_faction_panel(self):
        f = self.faction
        info = f"势力：{f.name}\n主公：{f.ruler.name}\n城池：{', '.join([c.name for c in f.cities])}\n武将：{', '.join([g.name for g in f.generals])}"
        self.lbl_faction.setText(info)

class ComputerBattleManager:
    """电脑战斗管理器"""
    def __init__(self, main_window, origin_city: City, armies: list[General], target_city: City):
        self.main_window = main_window
        self.origin_city = origin_city
        self.armies = armies
        self.target_city = target_city
        self.faction = origin_city.owner
        self.player = target_city.owner == main_window.player # 目标城市是否为玩家所有,如果是则为True
    
    def execute_battle(self):
        """执行战斗"""
        defend_armies: list[General] = []

        tmp_copy = self.target_city.generals.copy()
        for general in tmp_copy:
            if general.army <= 0:
                run_away(general, self.target_city)
                self.main_window.refresh_faction_panel()
            else:
                defend_armies.append(general)
        
        attack = True  # 攻军先手

        # ------------- 主战斗循环 -------------
        while self.armies and defend_armies:
            if attack:
                # 电脑选择出阵武将以及阵型
                atk_general = max(self.armies, key=lambda g: g.leadership)

                formation_atk = random.choice(["锋矢阵", "方圆阵", "投石阵"])

                dfd_general = min(defend_armies, key=lambda g: g.leadership) # 电脑选择对方迎战的武将

                if self.player: # 攻打玩家城市，由玩家选择阵型
                    # 玩家选择阵型
                    while True:
                        fdlg = FormationSelectDialog(self.main_window, wintitle= f"{atk_general.name}军向{dfd_general.name}军发起挑战,请选择阵型迎战")
                        ret = fdlg.exec()
                        if ret == QDialog.Accepted:
                            formation_dfd = fdlg.get_formation()
                            break
                        else:
                            QMessageBox.warning(self.main_window, "提示", "敌方来袭，必须选择阵型迎战！")
                else:
                    formation_dfd = random.choice(["锋矢阵", "方圆阵", "投石阵"])
            else:
                if self.player: # 玩家城市被攻打，由玩家选择出阵武将和阵型
                    # 玩家选择出阵武将
                    while True:
                        adlg = ArmySelectDialog(defend_armies, parent=self.main_window, single_mode=True)
                        ret = adlg.exec()
                        selected = adlg.get_selected()
                        if ret == QDialog.Accepted and selected:
                            atk_general = selected[0]
                            break
                        else:
                            QMessageBox.warning(self.main_window, "提示", "敌方来袭，必须选择武将迎战！")
                    
                    # 玩家选择阵型
                    while True:
                        fdlg = FormationSelectDialog(self.main_window, wintitle="请选择阵型出战")
                        ret = fdlg.exec()
                        if ret == QDialog.Accepted:
                            formation_atk = fdlg.get_formation()
                            break
                        else:
                            QMessageBox.warning(self.main_window, "提示", "敌方来袭，必须选择阵型迎战！")
                    
                    # 由玩家选择敌方接受挑战的武将
                    while True:
                        ddlg = ArmySelectDialog(self.armies, parent=self.main_window, single_mode=True)
                        ret = ddlg.exec()
                        selected = ddlg.get_selected()
                        if ret == QDialog.Accepted and selected:
                            dfd_general = selected[0]
                            break
                        else:
                            QMessageBox.warning(self.main_window, "提示", "敌方来袭，必须选择武将迎战！")
                else:
                    atk_general = max(defend_armies, key=lambda g: g.leadership)
                    formation_atk = random.choice(["锋矢阵", "方圆阵", "投石阵"])
                    dfd_general = min(self.armies, key=lambda g: g.leadership)
                    #dfd_general = max(self.armies, key=lambda g: g.leadership)

                formation_dfd = random.choice(["锋矢阵", "方圆阵", "投石阵"])
                
            msg = f"{atk_general.name}军 向 {dfd_general.name}军发起了对战"# TODO-finished: 在主窗口的def on_world_update(self)中显示“atk_general军 向 dfd_general军发起了对战”
            self.main_window.log_list.addItem(msg)
            self.main_window.refresh_faction_panel()

            Army1 = Army(formation_atk, atk_general, atk_general.army)
            Army2 = Army(formation_dfd, dfd_general, dfd_general.army)  

            if self.player: # 如果玩家参与战斗，显示战斗窗口
                battle_window = BattleWindow(Army1, Army2, parent=self.main_window)
                battle_window.setWindowTitle("战斗中……（请等待战斗结束）")
                
                # 添加关闭按钮（初始禁用）
                close_btn = QPushButton("关闭战斗窗口")
                close_btn.setEnabled(False)
                close_btn.clicked.connect(battle_window.close)
                
                # 将关闭按钮添加到战斗窗口布局
                battle_window.layout().addWidget(close_btn)
                
                battle_window.show()
                current_battle_window = battle_window
                # TODO-finished:此处打开一个战斗窗口，这个战斗窗口应该显示Army1和Army2的阵型和武将信息，并且两边是武将图像，中间有一个显示战斗日志的区域展示后面我标记的日志

                # 单挑
                to_duel = Army1
                if random.choice([True, False]):
                    to_duel = Army2
                # 随机选择一方主动触发单挑
                duel_result = to_duel.duel(Army2 if to_duel == Army1 else Army1)           
                if duel_result != "本回合未触发单挑":
                    # BattleWindow 日志
                    current_battle_window.append_log(f"<b>【单挑】</b>{duel_result}")

                    QApplication.processEvents()  # 确保UI更新
                    time.sleep(1)  # 等待1秒

                    item = QListWidgetItem()
                    item.setText(f"【单挑】{duel_result}")

                    # 设置加粗字体
                    font = item.font()
                    font.setBold(True)
                    item.setFont(font)

                    # 主窗口日志
                    self.main_window.log_list.addItem(item)
                    self.main_window.refresh_faction_panel() # TODO: 此处refresh需要吗？
                    # 单挑日志同时显示在战斗窗口的日志区域和主窗口的def on_world_update(self)中

                # ------- 内层战斗循环 -------
                while Army1.soldiers > 0 and Army2.soldiers > 0:

                    res1 = Army1.attack_enemy(Army2)
                    #logs.append(res1["battle_log"]) 
                    #TODO-finished res1["battle_log"]日志只显示在战斗窗口的日志区域,res1["capture_log"]日志同时显示在战斗窗口的日志区域和主窗口的def on_world_update(self)中

                    # battle_log 仅 BattleWindow
                    current_battle_window.append_log(res1["battle_log"])
                    QApplication.processEvents()
                    time.sleep(1)

                    # capture_log 若存在，两个地方都显示
                    if res1["capture_log"]: # TODO: 我的capture_log和这里的是否为空对应了吗？
                        current_battle_window.append_log(f"<b>{res1['capture_log']}</b>")
                        QApplication.processEvents()
                        time.sleep(1)
                        self.main_window.log_list.addItem(res1["capture_log"])
                    current_battle_window.update_army_info()
                    self.main_window.refresh_faction_panel()
                    QApplication.processEvents()

                    if res1["win"]: # Army1获胜
                        atk_general.army = Army1.soldiers
                        dfd_general.army = 0
                        if res1["capture"]:
                            if attack:
                                self.target_city.remove_general(dfd_general)
                                self.origin_city.prisoners.append((dfd_general, 0))   
                            else:
                                self.origin_city.remove_general(dfd_general)
                                self.target_city.prisoners.append((dfd_general, 0))
                        else:
                            if attack: # 攻军获胜,守军触发逃亡
                                run_away(dfd_general, self.target_city)
                                self.main_window.refresh_faction_panel()
                            # 守军获胜，攻军逃亡回self.city即可
                        break

                    # 轮到Army2反击
                    res2 = Army2.attack_enemy(Army1)
                    # res2["battle_log"]日志只显示在战斗窗口的日志区域,res2["capture_log"]日志同时显示在战斗窗口的日志区域和主窗口的def on_world_update(self)中

                    current_battle_window.append_log(res2["battle_log"])
                    QApplication.processEvents()
                    time.sleep(1)

                    if res2["capture_log"]:
                        current_battle_window.append_log(f"<b>{res2['capture_log']}</b>")
                        QApplication.processEvents()
                        time.sleep(1)
                        self.main_window.log_list.addItem(res2["capture_log"])

                    current_battle_window.update_army_info()
                    self.main_window.refresh_faction_panel()
                    QApplication.processEvents()

                    if res2["win"]:# Army2获胜
                        dfd_general.army = Army2.soldiers
                        atk_general.army = 0
                        if res2["capture"]:
                            if attack:
                                self.origin_city.remove_general(atk_general)
                                self.target_city.prisoners.append((atk_general, 0))
                            else:
                                self.target_city.remove_general(atk_general)
                                self.origin_city.prisoners.append((atk_general, 0))
                        else:
                            if not attack: # 攻军获胜,守军触发逃亡
                                run_away(atk_general, self.target_city)   
                                self.main_window.refresh_faction_panel()
                            # 攻军溃散时逃跑回self.city即可，无需逃亡其他城市 
                        break
                # ------- end 内层战斗循环 -------
                
                # 关闭战斗窗口，之前挑选出的一对武将的战斗结束
                # 当前这场战斗结束，关闭窗口
                # 当前这场战斗结束，启用关闭按钮
                close_btn.setEnabled(True)
                current_battle_window.setWindowTitle("战斗结束 - 请点击关闭按钮继续")
                # 当前这场战斗结束，启用关闭按钮
                current_battle_window.enable_close_button()
                #current_battle_window.close()

                # 等待用户关闭窗口
                while current_battle_window.isVisible():
                    QApplication.processEvents()
                    time.sleep(0.1)
            else:
                # 单挑
                to_duel = Army1
                if random.choice([True, False]):
                    to_duel = Army2
                # 随机选择一方主动触发单挑
                to_duel.duel(Army2 if to_duel == Army1 else Army1)           

                # ------- 内层战斗循环 -------
                while Army1.soldiers > 0 and Army2.soldiers > 0:
                    res1 = Army1.attack_enemy(Army2)

                    # capture_log 若存在，两个地方都显示
                    if res1["capture_log"]:
                        self.main_window.log_list.addItem(res1["capture_log"])

                    self.main_window.refresh_faction_panel()

                    if res1["win"]: # Army1获胜
                        atk_general.army = Army1.soldiers
                        dfd_general.army = 0
                        if res1["capture"]:
                            if attack:
                                self.target_city.remove_general(dfd_general)
                                self.origin_city.prisoners.append((dfd_general, 0))   
                            else:
                                self.origin_city.remove_general(dfd_general)
                                self.target_city.prisoners.append((dfd_general, 0))
                        else:
                            if attack: # 攻军获胜,守军触发逃亡
                                run_away(dfd_general, self.target_city)
                                self.main_window.refresh_faction_panel()
                            # 守军获胜，攻军逃亡回self.city即可
                        break

                    # 轮到Army2反击
                    res2 = Army2.attack_enemy(Army1)

                    if res2["capture_log"]:
                        self.main_window.log_list.addItem(res2["capture_log"])

                    self.main_window.refresh_faction_panel()

                    if res2["win"]:# Army2获胜
                        dfd_general.army = Army2.soldiers
                        atk_general.army = 0
                        if res2["capture"]:
                            if attack:
                                self.origin_city.remove_general(atk_general)
                                self.target_city.prisoners.append((atk_general, 0))
                            else:
                                self.target_city.remove_general(atk_general)
                                self.origin_city.prisoners.append((atk_general, 0))
                        else:
                            if not attack: # 攻军获胜,守军触发逃亡
                                run_away(atk_general, self.target_city)   
                                self.main_window.refresh_faction_panel()
                            # 攻军溃散时逃跑回self.city即可，无需逃亡其他城市 
                        break
                # ------- end 内层战斗循环 -------
                
            # ------- 外层循环剔除溃逃武将 -------
            if Army1.soldiers <= 0:
                if attack:
                    self.armies.remove(atk_general)
                else:
                    defend_armies.remove(atk_general)
            else:
                if Army2.soldiers > 0:
                    assert(0), "跳出内层循环时必然有一队士兵为0但是Army1不为0是Army2同时不为0"
                else: # Army2军队溃散
                    if attack:
                       defend_armies.remove(dfd_general)
                    else:
                        self.armies.remove(dfd_general) 

            attack = not attack # 取反，下一轮由另一方先攻

        # 战后总结
        if self.armies:
            if defend_armies:
                assert(0), "不可能两个攻城军和守城军同时不为空时中止战斗！"
            else: # 守城军消耗殆尽
                if len(self.target_city.owner.cities) <= 1: # 最后一城
                    if len(self.target_city.owner.cities) != 1:
                        assert(0), "势力所拥有的城池数小于等于0"
                    
                    to_remove_generals: list["General"] = []

                    for g in self.target_city.generals:
                        to_remove_generals.append(g)
                    
                    for g in to_remove_generals:
                        self.target_city.remove_general(g) # 从该城池移除该武将
                        self.origin_city.prisoners.append((g, 0)) #加入监狱

                    to_remove_generals.clear()

                    for g in self.target_city.owner.generals:
                        to_remove_generals.append(g)

                    for g in to_remove_generals:
                        self.target_city.owner.remove_general(g)
                    
                    # TODO-finished: 在主窗口的def on_world_update(self)中显示“敌方势力 {enemy.owner.name} 被消灭！”
                    msg = f"敌方势力 {self.target_city.owner.name} 被消灭！"
                    self.main_window.log_list.addItem(msg)           # 主窗口显示
                    self.main_window.refresh_faction_panel()

                self.target_city.owner.remove_city(self.target_city)
                
                # 剩余攻城军进入enemy，self的势力占领新城，将所有官员设置为空
                for g in self.armies:
                    self.origin_city.remove_general(g)
                    self.target_city.generals.append(g)
                    
                self.origin_city.owner.add_city(self.target_city)
                self.target_city.officer_agriculture = None
                self.target_city.officer_commerce = None

                # 更新城市颜色
                self.main_window.update_city_color(self.target_city.name)

                msg = f"势力 {self.origin_city.owner.name} 成功占领 {self.target_city.name}！"
                self.main_window.log_list.addItem(msg)      # 主窗口日志
                self.main_window.refresh_faction_panel()
                # === 新增：检查游戏是否结束 ===
                self.main_window.check_game_over(conquered_city=self.target_city, conqueror=self.origin_city.owner)

        else: # 攻城军耗尽
            if not defend_armies:
                assert(0), "攻城军和守城军无法同时为0！"
            else:
                msg = f"势力 {self.target_city.owner.name} 成功防守 {self.target_city.name}！"
                self.main_window.log_list.addItem(msg)     # 主窗口日志
                self.main_window.refresh_faction_panel()
                #TODO: 在主窗口和二级窗口显示敌方势力 {enemy.owner.name} 成功防守 {enemy.name}！

            # 如果攻城军耗尽，守城军依旧存在，攻城的将领要么在前面的逻辑被俘，要么已经逃回self，因此无需处理

        return # 无需返回日志，因为日志在运行过程中以及主窗口中已经显示出来了

class VictoryDialog(QDialog):
    """胜利对话框"""
    def __init__(self, message, parent=None):
        super().__init__(parent)
        self.setWindowTitle("游戏结束")
        self.setFixedSize(400, 200)
        
        layout = QVBoxLayout(self)
        
        # 图标和消息
        icon_label = QLabel()
        icon_label.setPixmap(QPixmap("image/victory.png").scaled(64, 64, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        icon_label.setAlignment(Qt.AlignCenter)
        
        message_label = QLabel(message)
        message_label.setAlignment(Qt.AlignCenter)
        message_label.setStyleSheet("font-size: 18px; font-weight: bold; color: green;")
        
        layout.addWidget(icon_label)
        layout.addWidget(message_label)
        
        # 按钮
        btn_box = QDialogButtonBox(QDialogButtonBox.Ok)
        btn_box.accepted.connect(self.accept)
        layout.addWidget(btn_box)
        
        self.setStyleSheet("""
            QDialog {
                background-color: #f0fff0;
                border: 2px solid #4CAF50;
            }
        """)

class DefeatDialog(QDialog):
    """失败对话框"""
    def __init__(self, message, parent=None):
        super().__init__(parent)
        self.setWindowTitle("游戏结束")
        self.setFixedSize(400, 200)
        
        layout = QVBoxLayout(self)
        
        # 图标和消息
        icon_label = QLabel()
        icon_label.setPixmap(QPixmap("image/defeat.png").scaled(64, 64, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        icon_label.setAlignment(Qt.AlignCenter)
        
        message_label = QLabel(message)
        message_label.setAlignment(Qt.AlignCenter)
        message_label.setStyleSheet("font-size: 18px; font-weight: bold; color: red;")
        
        layout.addWidget(icon_label)
        layout.addWidget(message_label)
        
        # 按钮
        btn_box = QDialogButtonBox(QDialogButtonBox.Ok)
        btn_box.accepted.connect(self.close_game)
        layout.addWidget(btn_box)
        
        self.setStyleSheet("""
            QDialog {
                background-color: #fff0f0;
                border: 2px solid #F44336;
            }
        """)
    
    def close_game(self):
        """关闭游戏"""
        self.accept()
        QApplication.quit()

class GameOverDialog(QDialog):
    """通用游戏结束对话框"""
    def __init__(self, title, message, is_victory=True, parent=None):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setFixedSize(450, 250)
        self.is_victory = is_victory
        
        layout = QVBoxLayout(self)
        
        # 图标
        icon_label = QLabel()
        if is_victory:
            icon_label.setPixmap(QPixmap("image/victory.png").scaled(80, 80, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        else:
            icon_label.setPixmap(QPixmap("image/defeat.png").scaled(80, 80, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        icon_label.setAlignment(Qt.AlignCenter)
        
        # 消息
        message_label = QLabel(message)
        message_label.setAlignment(Qt.AlignCenter)
        message_label.setStyleSheet(f"font-size: 20px; font-weight: bold; color: {'green' if is_victory else 'red'};")
        message_label.setWordWrap(True)
        
        layout.addWidget(icon_label)
        layout.addWidget(message_label)
        
        # 按钮区域
        button_layout = QHBoxLayout()
        
        if is_victory:
            continue_btn = QPushButton("继续游玩")
            continue_btn.clicked.connect(self.accept)
            continue_btn.setStyleSheet("font-size: 14px; padding: 8px;")
            
            quit_btn = QPushButton("退出游戏")
            quit_btn.clicked.connect(self.close_game)
            quit_btn.setStyleSheet("font-size: 14px; padding: 8px;")
            
            button_layout.addWidget(continue_btn)
            button_layout.addWidget(quit_btn)
        else:
            quit_btn = QPushButton("退出游戏")
            quit_btn.clicked.connect(self.close_game)
            quit_btn.setStyleSheet("font-size: 14px; padding: 8px;")
            button_layout.addWidget(quit_btn)
        
        layout.addLayout(button_layout)
        
        # 样式
        if is_victory:
            self.setStyleSheet("""
                QDialog {
                    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                                            stop:0 #e8f5e8, stop:1 #c8e6c9);
                    border: 3px solid #4CAF50;
                    border-radius: 10px;
                }
                QPushButton {
                    background-color: #4CAF50;
                    color: white;
                    border: none;
                    border-radius: 5px;
                    padding: 8px 16px;
                    font-weight: bold;
                }
                QPushButton:hover {
                    background-color: #45a049;
                }
            """)
        else:
            self.setStyleSheet("""
                QDialog {
                    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                                            stop:0 #ffebee, stop:1 #ffcdd2);
                    border: 3px solid #F44336;
                    border-radius: 10px;
                }
                QPushButton {
                    background-color: #F44336;
                    color: white;
                    border: none;
                    border-radius: 5px;
                    padding: 8px 16px;
                    font-weight: bold;
                }
                QPushButton:hover {
                    background-color: #d32f2f;
                }
            """)
    
    def close_game(self):
        """关闭游戏"""
        self.accept()
        QApplication.quit()

def load_generals_from_json(file_path="generals.json"):
    """从JSON文件加载武将数据"""
    if not os.path.exists(file_path):
        print(f"错误：找不到文件 {file_path}")
        return None
    
    with open(file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    return data

def create_general_from_data(gen_data):
    """从字典数据创建General对象"""
    return General(
        name=gen_data["name"],
        leadership=gen_data["leadership"],
        martial=gen_data["martial"],
        intellect=gen_data["intellect"],
        politics=gen_data["politics"],
        loyalty=gen_data["loyalty"],
        _greed=gen_data.get("greed", 0.3)  # 默认贪婪值
    )

def initialize_game_from_data(data):
    """从加载的数据初始化游戏"""
    factions = {}
    wild_generals = []
    
    # 创建在野武将
    for wild_data in data["wild_generals"]:
        wild_generals.append(create_general_from_data(wild_data))
    
    # 创建势力
    for faction_name, faction_data in data["factions"].items():
        # 创建君主
        ruler = create_general_from_data(faction_data["ruler"])
        
        # 创建势力
        faction = Faction(faction_name, ruler)
        
        # 添加武将到势力
        for gen_data in faction_data["generals"]:
            general = create_general_from_data(gen_data)
            faction.add_general(general)
        
        factions[faction_name] = faction
    
    return factions, wild_generals

if __name__ == "__main__":
    app = QApplication(sys.argv)

    # 从JSON文件加载数据
    data = load_generals_from_json("generals.json")
    if not data:
        print("无法加载武将数据，使用默认数据")
        # 这里可以保留原来的硬编码数据作为备用
        sys.exit(1)
    
    # 初始化游戏
    factions, wild_generals = initialize_game_from_data(data)
    
    shu = factions["蜀"]
    wei = factions["魏"] 
    wu = factions["吴"]
    
    # ======================
    # 创建城市并分配武将
    # ======================
    
    # 蜀国城市
    yizhou = City("益州", food=1200, gold=900, owner=shu)
    hanzhong = City("汉中", food=900, gold=700, owner=shu)
    jingzhou = City("荆州", food=1000, gold=800, owner=shu)
    
    # 分配蜀国武将到城市（前4个）
    shu_generals = [g for g in shu.generals if g != shu.ruler]
    yizhou.generals.extend([shu.ruler, shu_generals[0], shu_generals[1]])  # 刘备、诸葛亮、关羽
    hanzhong.generals.extend([shu_generals[2], shu_generals[3], shu_generals[6], shu_generals[7]])  # 张飞、赵云
    jingzhou.generals.extend([shu_generals[4], shu_generals[5], shu_generals[8], shu_generals[9]])  # 马超、黄忠
    
    # 魏国城市
    shangyong = City("上庸", food=900, gold=700, owner=wei)
    chenliu = City("陈留", food=1100, gold=1000, owner=wei)
    xuchang = City("许昌", food=1300, gold=1200, owner=wei)
    
    # 分配魏国武将到城市
    wei_generals = [g for g in wei.generals if g != wei.ruler]
    shangyong.generals.extend([wei_generals[0], wei_generals[1], wei_generals[6], wei_generals[7]])  # 司马懿、夏侯惇
    chenliu.generals.extend([wei_generals[2], wei_generals[3], wei_generals[8], wei_generals[9]])  # 夏侯渊、张辽
    xuchang.generals.extend([wei.ruler, wei_generals[4], wei_generals[5]])  # 曹操、徐晃、张郃
    
    # 吴国城市
    wucheng = City("吴", food=1100, gold=900, owner=wu)
    kuaiji = City("会稽", food=950, gold=850, owner=wu)
    chaisang = City("柴桑", food=1000, gold=900, owner=wu)
    
    # 分配吴国武将到城市
    wu_generals = [g for g in wu.generals if g != wu.ruler]
    wucheng.generals.extend([wu.ruler, wu_generals[0], wu_generals[1]])  # 孙权、周瑜、吕蒙
    kuaiji.generals.extend([wu_generals[2], wu_generals[3], wu_generals[6], wu_generals[7]])  # 陆逊、甘宁
    chaisang.generals.extend([wu_generals[4], wu_generals[5], wu_generals[8], wu_generals[9]])  # 太史慈、黄盖
    
    # 添加城市到势力
    for city in [yizhou, hanzhong, jingzhou]:
        shu.add_city(city)
    for city in [shangyong, chenliu, xuchang]:
        wei.add_city(city)
    for city in [wucheng, kuaiji, chaisang]:
        wu.add_city(city)
    
    # 分配在野武将到随机城市
    for wild_general in wild_generals:
        random_city = random.choice([yizhou, hanzhong, jingzhou, shangyong, chenliu, xuchang, wucheng, kuaiji, chaisang])
        random_city.wild_generals.append(wild_general)
    
    # ======================
    # 设置城市连接关系
    # ======================
    yizhou.neighbors = [hanzhong, jingzhou]
    hanzhong.neighbors = [yizhou, shangyong]
    jingzhou.neighbors = [yizhou, kuaiji]
    kuaiji.neighbors = [jingzhou, wucheng]
    wucheng.neighbors = [kuaiji, chaisang]
    chaisang.neighbors = [wucheng, chenliu]
    chenliu.neighbors = [chaisang, xuchang]
    xuchang.neighbors = [chenliu, shangyong]
    shangyong.neighbors = [xuchang, hanzhong]
    
    # 设置初始兵力
    for faction in [shu, wei, wu]:
        for general in faction.generals:
            if general.faction == wei:
                continue
            if general.martial >= 80:  # 武力高的武将初始兵力多
                general.army = random.randint(800, 1000)
            else:
                general.army = random.randint(500, 800)
    
    # ======================
    # 世界城市列表
    # ======================
    world = [yizhou, hanzhong, jingzhou, shangyong, chenliu, xuchang, wucheng, kuaiji, chaisang]
    
    shu.add_general(shu.ruler)
    wei.add_general(wei.ruler)
    wu.add_general(wu.ruler)
    

    # 打开主界面（玩家暂定为蜀）
    main = MainWindow(shu, world, [wei, wu])
    main.resize(1200, 800)
    main.show()
    sys.exit(app.exec())
