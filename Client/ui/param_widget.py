# -*- coding: utf-8 -*-
"""参数行组件"""

from PyQt5.QtWidgets import (QWidget, QHBoxLayout, QLabel, QLineEdit,
                             QPushButton, QSpinBox, QDoubleSpinBox)
from PyQt5.QtCore import pyqtSignal


class ParamWidget(QWidget):
    """参数行组件

    每个参数行组件包含:
    - label_name: 参数名称 (左侧固定宽度)
    - spin_box: 参数值输入框 (中间自适应)
    - btn_read: 读取按钮
    - btn_write: 设置按钮 (只读参数无此按钮)
    """

    read_clicked = pyqtSignal(int)  # param_id
    write_clicked = pyqtSignal(int, object)  # param_id, value

    def __init__(self, param_id, param_name, data_type, is_readonly=False, parent=None):
        super().__init__(parent)
        self.param_id = param_id
        self.param_name = param_name
        self.data_type = data_type
        self.is_readonly = is_readonly

        self._init_ui()

    def _init_ui(self):
        """初始化UI"""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(5, 2, 5, 2)
        layout.setSpacing(10)

        # 参数名称标签
        self.label_name = QLabel(self.param_name)
        self.label_name.setFixedWidth(140)
        layout.addWidget(self.label_name)

        # 特殊处理 float×3 类型 (显示 Kp, Ki, Kd)
        if self.data_type == 'float×3':
            self._init_float3_ui(layout)
        else:
            self._init_normal_ui(layout)

    def _init_normal_ui(self, layout):
        """初始化普通参数的UI"""
        # 根据类型选择不同的控件
        if self.data_type == 'int':
            self.spin_box = QSpinBox()
            self.spin_box.setFixedWidth(100)
            # 设置范围
            self.spin_box.setRange(-2147483648, 2147483647)
        else:  # float
            self.spin_box = QDoubleSpinBox()
            self.spin_box.setFixedWidth(100)
            # 设置范围和精度
            self.spin_box.setRange(-1e9, 1e9)
            self.spin_box.setDecimals(4)

        self.spin_box.setButtonSymbols(QSpinBox.NoButtons)
        layout.addWidget(self.spin_box)

        # 读取按钮
        self.btn_read = QPushButton("读取")
        self.btn_read.setFixedWidth(60)
        self.btn_read.clicked.connect(self._on_read_clicked)
        layout.addWidget(self.btn_read)

        # 设置按钮 (只读参数无此按钮)
        if not self.is_readonly:
            self.btn_write = QPushButton("设置")
            self.btn_write.setFixedWidth(60)
            self.btn_write.clicked.connect(self._on_write_clicked)
            layout.addWidget(self.btn_write)
        else:
            self.btn_write = None

        layout.addStretch()

    def _init_float3_ui(self, layout):
        """初始化 float×3 类型参数的UI"""
        # float×3 显示为 Kp[xxx] Ki[xxx] Kd[xxx] 格式
        self.kp_spin = QDoubleSpinBox()
        self.kp_spin.setFixedWidth(70)
        self.kp_spin.setRange(-1e9, 1e9)
        self.kp_spin.setDecimals(4)
        self.kp_spin.setButtonSymbols(QDoubleSpinBox.NoButtons)

        self.ki_spin = QDoubleSpinBox()
        self.ki_spin.setFixedWidth(70)
        self.ki_spin.setRange(-1e9, 1e9)
        self.ki_spin.setDecimals(4)
        self.ki_spin.setButtonSymbols(QDoubleSpinBox.NoButtons)

        self.kd_spin = QDoubleSpinBox()
        self.kd_spin.setFixedWidth(70)
        self.kd_spin.setRange(-1e9, 1e9)
        self.kd_spin.setDecimals(4)
        self.kd_spin.setButtonSymbols(QDoubleSpinBox.NoButtons)

        # 创建显示标签
        kp_label = QLabel("Kp")
        ki_label = QLabel(" Ki")
        kd_label = QLabel(" Kd")

        layout.addWidget(kp_label)
        layout.addWidget(self.kp_spin)
        layout.addWidget(ki_label)
        layout.addWidget(self.ki_spin)
        layout.addWidget(kd_label)
        layout.addWidget(self.kd_spin)

        # 读取按钮
        self.btn_read = QPushButton("读取")
        self.btn_read.setFixedWidth(60)
        self.btn_read.clicked.connect(self._on_read_clicked)
        layout.addWidget(self.btn_read)

        # 设置按钮 (只读参数无此按钮)
        if not self.is_readonly:
            self.btn_write = QPushButton("设置")
            self.btn_write.setFixedWidth(60)
            self.btn_write.clicked.connect(self._on_write_clicked)
            layout.addWidget(self.btn_write)
        else:
            self.btn_write = None

        layout.addStretch()

    def _on_read_clicked(self):
        """读取按钮点击"""
        self.read_clicked.emit(self.param_id)

    def _on_write_clicked(self):
        """设置按钮点击"""
        if self.data_type == 'float×3':
            kp = self.kp_spin.value()
            ki = self.ki_spin.value()
            kd = self.kd_spin.value()
            value = [kp, ki, kd]
        else:
            if self.data_type == 'int':
                value = self.spin_box.value()
            else:  # float
                value = self.spin_box.value()

        self.write_clicked.emit(self.param_id, value)

    def update_value(self, value):
        """更新参数值显示

        Args:
            value: 参数值
        """
        if self.data_type == 'float×3':
            if isinstance(value, (list, tuple)) and len(value) >= 3:
                self.kp_spin.setValue(value[0])
                self.ki_spin.setValue(value[1])
                self.kd_spin.setValue(value[2])
        else:
            self.spin_box.setValue(value)

    def get_value(self):
        """获取当前输入值"""
        if self.data_type == 'float×3':
            kp = self.kp_spin.value()
            ki = self.ki_spin.value()
            kd = self.kd_spin.value()
            return [kp, ki, kd]
        else:
            return self.spin_box.value()

    def set_enabled(self, enabled):
        """设置控件启用状态"""
        if self.data_type == 'float×3':
            self.kp_spin.setEnabled(enabled)
            self.ki_spin.setEnabled(enabled)
            self.kd_spin.setEnabled(enabled)
        else:
            self.spin_box.setEnabled(enabled)
        self.btn_read.setEnabled(enabled)
        if self.btn_write:
            self.btn_write.setEnabled(enabled)
