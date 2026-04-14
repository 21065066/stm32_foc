# -*- coding: utf-8 -*-
"""滑动条范围配置对话框"""

from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel,
                             QSpinBox, QDoubleSpinBox, QPushButton, QGroupBox,
                             QScrollArea, QWidget)
from PyQt5.QtCore import Qt


class SliderRangeConfigWidget(QWidget):
    """单个滑动条范围配置控件"""

    SPIN_WIDTH = 80  # 统一样式框宽度

    def __init__(self, param_id, param_name, data_type, default_range=None,
                 default_step=None, parent=None):
        super().__init__(parent)
        self.param_id = param_id
        self.param_name = param_name
        self.data_type = data_type

        layout = QHBoxLayout(self)
        layout.setContentsMargins(5, 2, 5, 2)
        layout.setSpacing(5)

        # 参数名称 - 统一宽度
        name_label = QLabel(f"{param_name} (0x{param_id:02X})")
        name_label.setFixedWidth(170)
        layout.addWidget(name_label)

        # 最小值
        min_label = QLabel("最小:")
        min_label.setFixedWidth(30)
        layout.addWidget(min_label)

        if data_type == 'int':
            self.min_spin = QSpinBox()
            self.min_spin.setFixedWidth(self.SPIN_WIDTH)
            self.min_spin.setRange(-2147483648, 2147483647)
        else:
            self.min_spin = QDoubleSpinBox()
            self.min_spin.setFixedWidth(self.SPIN_WIDTH)
            self.min_spin.setRange(-1e9, 1e9)
            self.min_spin.setDecimals(4)

        if default_range:
            self.min_spin.setValue(default_range[0])
        layout.addWidget(self.min_spin)

        # 最大值
        max_label = QLabel("最大:")
        max_label.setFixedWidth(30)
        layout.addWidget(max_label)

        if data_type == 'int':
            self.max_spin = QSpinBox()
            self.max_spin.setFixedWidth(self.SPIN_WIDTH)
            self.max_spin.setRange(-2147483648, 2147483647)
        else:
            self.max_spin = QDoubleSpinBox()
            self.max_spin.setFixedWidth(self.SPIN_WIDTH)
            self.max_spin.setRange(-1e9, 1e9)
            self.max_spin.setDecimals(4)

        if default_range:
            self.max_spin.setValue(default_range[1])
        layout.addWidget(self.max_spin)

        # 步长
        step_label = QLabel("步长:")
        step_label.setFixedWidth(30)
        layout.addWidget(step_label)

        if data_type == 'int':
            self.step_spin = QSpinBox()
            self.step_spin.setFixedWidth(self.SPIN_WIDTH)
            self.step_spin.setRange(1, 2147483647)
            self.step_spin.setValue(default_step if default_step else 1)
        else:
            self.step_spin = QDoubleSpinBox()
            self.step_spin.setFixedWidth(self.SPIN_WIDTH)
            self.step_spin.setRange(0.0001, 1e9)
            self.step_spin.setDecimals(4)
            self.step_spin.setValue(default_step if default_step else 0.1)

        layout.addWidget(self.step_spin)
        layout.addStretch()

    def get_range(self):
        """获取范围"""
        return (self.min_spin.value(), self.max_spin.value())

    def get_step(self):
        """获取步长"""
        return self.step_spin.value()


class SliderConfigDialog(QDialog):
    """滑动条范围配置对话框"""

    # 默认步长配置
    DEFAULT_STEPS = {
        0x02: 0.01,     # 电流采样电阻
        0x03: 1.0,      # 运放放大倍数
        0x04: 0.1,      # 最大Q轴电流
        0x05: 0.1,      # ADC参考电压
        0x06: 100,      # PWM频率
        0x07: 10,       # 速度计算频率
        0x08: 1,        # ADC精度
        0x09: 0.1,      # 多圈周期
        0x42: 0.1,      # 目标角度
        0x43: 1.0,      # 目标速度
        0x44: 0.1,      # 目标转矩D轴
        0x45: 0.1,      # 目标转矩Q轴
    }

    def __init__(self, config_manager, parent=None):
        super().__init__(parent)
        self.config_manager = config_manager

        self.range_widgets = {}  # param_id -> SliderRangeConfigWidget

        self._init_ui()
        self._load_config()

    def _init_ui(self):
        """初始化UI"""
        self.setWindowTitle("滑动条范围配置")
        self.setMinimumSize(750, 500)

        layout = QVBoxLayout(self)

        # 创建滚动区域
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        content = QWidget()
        content_layout = QVBoxLayout(content)

        # 硬件参数组
        hw_group = QGroupBox("硬件参数")
        hw_layout = QVBoxLayout(hw_group)

        hw_params = [
            (0x02, "电流采样电阻(Ω)", "float"),
            (0x03, "运放放大倍数", "float"),
            (0x04, "最大Q轴电流(A)", "float"),
            (0x05, "ADC参考电压(V)", "float"),
            (0x06, "PWM频率(Hz)", "int"),
            (0x07, "速度计算频率(Hz)", "int"),
            (0x08, "ADC精度(bit)", "int"),
            (0x09, "多圈周期", "float"),
        ]

        for param_id, name, dtype in hw_params:
            widget = self._create_range_widget(param_id, name, dtype)
            hw_layout.addWidget(widget)
            self.range_widgets[param_id] = widget

        content_layout.addWidget(hw_group)

        # 目标值组
        target_group = QGroupBox("目标值")
        target_layout = QVBoxLayout(target_group)

        target_params = [
            (0x42, "目标角度(rad)", "float"),
            (0x43, "目标速度(rad/s)", "float"),
            (0x44, "目标转矩D轴", "float"),
            (0x45, "目标转矩Q轴", "float"),
        ]

        for param_id, name, dtype in target_params:
            widget = self._create_range_widget(param_id, name, dtype)
            target_layout.addWidget(widget)
            self.range_widgets[param_id] = widget

        content_layout.addWidget(target_group)

        content_layout.addStretch()

        scroll.setWidget(content)
        layout.addWidget(scroll)

        # 按钮区域
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        self.btn_save = QPushButton("保存")
        self.btn_save.clicked.connect(self._on_save)
        btn_layout.addWidget(self.btn_save)

        self.btn_cancel = QPushButton("取消")
        self.btn_cancel.clicked.connect(self.reject)
        btn_layout.addWidget(self.btn_cancel)

        self.btn_reset = QPushButton("重置")
        self.btn_reset.clicked.connect(self._on_reset)
        btn_layout.addWidget(self.btn_reset)

        layout.addLayout(btn_layout)

    def _create_range_widget(self, param_id, name, dtype):
        """创建范围配置控件"""
        # 从配置中获取已保存的范围，否则使用默认值
        saved_range = self.config_manager.get_slider_range(param_id)
        default_range = self._get_default_range(param_id) if not saved_range else saved_range

        # 获取步长
        saved_step = self.config_manager.get_slider_step(param_id)
        default_step = self.DEFAULT_STEPS.get(param_id, 1 if dtype == 'int' else 0.1)
        step = saved_step if saved_step is not None else default_step

        widget = SliderRangeConfigWidget(param_id, name, dtype, default_range, step)
        return widget

    def _get_default_range(self, param_id):
        """获取默认范围"""
        defaults = {
            0x02: (0, 1),       # 电流采样电阻
            0x03: (1, 100),     # 运放放大倍数
            0x04: (0, 10),      # 最大Q轴电流
            0x05: (0, 5),       # ADC参考电压
            0x06: (1000, 50000),# PWM频率
            0x07: (100, 5000),  # 速度计算频率
            0x08: (8, 16),     # ADC精度
            0x09: (0, 100),     # 多圈周期
            0x42: (-10, 10),   # 目标角度
            0x43: (0, 300),    # 目标速度
            0x44: (-5, 5),     # 目标转矩D轴
            0x45: (0, 5),      # 目标转矩Q轴
        }
        return defaults.get(param_id)

    def _load_config(self):
        """从配置加载"""
        saved_ranges = self.config_manager.get_all_slider_ranges()
        saved_steps = self.config_manager.get_all_slider_steps()

        for param_id, range_vals in saved_ranges.items():
            if param_id in self.range_widgets:
                widget = self.range_widgets[param_id]
                widget.min_spin.setValue(range_vals[0])
                widget.max_spin.setValue(range_vals[1])

        for param_id, step in saved_steps.items():
            if param_id in self.range_widgets:
                widget = self.range_widgets[param_id]
                widget.step_spin.setValue(step)

    def _on_save(self):
        """保存按钮点击"""
        for param_id, widget in self.range_widgets.items():
            min_val, max_val = widget.get_range()
            step = widget.get_step()
            self.config_manager.set_slider_range(param_id, min_val, max_val)
            self.config_manager.set_slider_step(param_id, step)
        self.config_manager.save()
        self.accept()

    def _on_reset(self):
        """重置按钮点击"""
        for param_id, widget in self.range_widgets.items():
            default = self._get_default_range(param_id)
            if default:
                widget.min_spin.setValue(default[0])
                widget.max_spin.setValue(default[1])
            # 重置步长
            default_step = self.DEFAULT_STEPS.get(param_id, 1)
            widget.step_spin.setValue(default_step)

    def get_updated_ranges(self):
        """获取更新后的范围配置"""
        return {param_id: widget.get_range()
                for param_id, widget in self.range_widgets.items()}
