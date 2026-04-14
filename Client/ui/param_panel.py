# -*- coding: utf-8 -*-
"""参数面板"""

from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QGroupBox,
                             QScrollArea, QLabel)
from PyQt5.QtCore import Qt, pyqtSignal

from .param_widget import ParamWidget
from protocol.constants import PARAMS


class ParamPanel(QWidget):
    """参数面板 - 包含所有参数组"""

    # 信号定义
    read_requested = pyqtSignal(int)      # 读取参数请求 (param_id)
    write_requested = pyqtSignal(int, object)  # 写入参数请求 (param_id, value)

    def __init__(self, slider_ranges=None, slider_steps=None, parent=None):
        """初始化参数面板

        Args:
            slider_ranges: dict, param_id -> (min, max) 滑动条范围配置
            slider_steps: dict, param_id -> step 滑动条步长配置
        """
        super().__init__(parent)
        self.param_widgets = {}  # param_id -> ParamWidget
        self.slider_ranges = slider_ranges or {}
        self.slider_steps = slider_steps or {}
        self._init_ui()

    def _init_ui(self):
        """初始化UI"""
        # 创建滚动区域
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        # 创建内容widget
        content = QWidget()
        layout = QVBoxLayout(content)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(10)

        # 添加各个参数组
        layout.addWidget(self._create_hardware_group())
        layout.addWidget(self._create_pid_group())
        layout.addWidget(self._create_target_group())
        layout.addWidget(self._create_feedback_group())

        layout.addStretch()

        scroll.setWidget(content)

        # 主布局
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.addWidget(scroll)

    def _create_hardware_group(self):
        """创建硬件参数组"""
        group = QGroupBox("硬件参数")
        layout = QVBoxLayout(group)
        layout.setContentsMargins(5, 10, 5, 5)

        # 硬件参数 ID: 0x01 - 0x09
        hw_params = [(0x01, "极对数", "int"),
                     (0x02, "电流采样电阻(Ω)", "float"),
                     (0x03, "运放放大倍数", "float"),
                     (0x04, "最大Q轴电流(A)", "float"),
                     (0x05, "ADC参考电压(V)", "float"),
                     (0x06, "PWM频率(Hz)", "int"),
                     (0x07, "速度计算频率(Hz)", "int"),
                     (0x08, "ADC精度(bit)", "int"),
                     (0x09, "多圈周期", "float")]

        for param_id, name, dtype in hw_params:
            slider_range = self.slider_ranges.get(param_id)
            slider_step = self.slider_steps.get(param_id)
            widget = ParamWidget(param_id, name, dtype, is_readonly=False,
                               slider_range=slider_range, slider_step=slider_step)
            widget.read_clicked.connect(self._on_read_clicked)
            widget.write_clicked.connect(self._on_write_clicked)
            layout.addWidget(widget)
            self.param_widgets[param_id] = widget

        return group

    def _create_pid_group(self):
        """创建PID参数组"""
        group = QGroupBox("PID参数")
        layout = QVBoxLayout(group)
        layout.setContentsMargins(5, 10, 5, 5)

        # PID参数 ID: 0x20 - 0x23
        pid_params = [(0x20, "Position PID", "float×3"),
                      (0x21, "Speed PID", "float×3"),
                      (0x22, "Torque D PID", "float×3"),
                      (0x23, "Torque Q PID", "float×3")]

        for param_id, name, dtype in pid_params:
            widget = ParamWidget(param_id, name, dtype, is_readonly=False)
            widget.read_clicked.connect(self._on_read_clicked)
            widget.write_clicked.connect(self._on_write_clicked)
            layout.addWidget(widget)
            self.param_widgets[param_id] = widget

        return group

    def _create_target_group(self):
        """创建目标值参数组"""
        group = QGroupBox("目标值")
        layout = QVBoxLayout(group)
        layout.setContentsMargins(5, 10, 5, 5)

        # 目标值 ID: 0x41 - 0x45
        target_params = [(0x41, "控制类型", "int"),
                         (0x42, "目标角度(rad)", "float"),
                         (0x43, "目标速度(rad/s)", "float"),
                         (0x44, "目标转矩D轴", "float"),
                         (0x45, "目标转矩Q轴", "float")]

        for param_id, name, dtype in target_params:
            slider_range = self.slider_ranges.get(param_id)
            slider_step = self.slider_steps.get(param_id)
            widget = ParamWidget(param_id, name, dtype, is_readonly=False,
                               slider_range=slider_range, slider_step=slider_step)
            widget.read_clicked.connect(self._on_read_clicked)
            widget.write_clicked.connect(self._on_write_clicked)
            layout.addWidget(widget)
            self.param_widgets[param_id] = widget

        return group

    def _create_feedback_group(self):
        """创建反馈值参数组 (只读)"""
        group = QGroupBox("反馈值 (只读)")
        layout = QVBoxLayout(group)
        layout.setContentsMargins(5, 10, 5, 5)

        # 反馈值 ID: 0x60 - 0x68
        feedback_params = [(0x60, "U相电流(A)", "float"),
                           (0x61, "V相电流(A)", "float"),
                           (0x62, "D轴电流(A)", "float"),
                           (0x63, "Q轴电流(A)", "float"),
                           (0x64, "电机转速(rad/s)", "float"),
                           (0x65, "电机多圈角度(rad)", "float"),
                           (0x66, "编码器角度(rad)", "float"),
                           (0x67, "编码器初始角度(rad)", "float"),
                           (0x68, "转子零位角度(rad)", "float")]

        for param_id, name, dtype in feedback_params:
            widget = ParamWidget(param_id, name, dtype, is_readonly=True)
            widget.read_clicked.connect(self._on_read_clicked)
            layout.addWidget(widget)
            self.param_widgets[param_id] = widget

        return group

    def _on_read_clicked(self, param_id):
        """读取按钮点击"""
        self.read_requested.emit(param_id)

    def _on_write_clicked(self, param_id, value):
        """写入按钮点击"""
        self.write_requested.emit(param_id, value)

    def update_param_value(self, param_id, value):
        """更新参数值显示

        Args:
            param_id: 参数ID
            value: 参数值
        """
        if param_id in self.param_widgets:
            self.param_widgets[param_id].update_value(value)

    def set_params_enabled(self, enabled):
        """设置所有参数控件的启用状态

        Args:
            enabled: 是否启用
        """
        for widget in self.param_widgets.values():
            widget.set_enabled(enabled)

    def get_param_widget(self, param_id):
        """获取指定参数ID的控件"""
        return self.param_widgets.get(param_id)

    def update_slider_configs(self, slider_ranges, slider_steps):
        """更新滑动条范围和步长

        Args:
            slider_ranges: dict, param_id -> (min, max)
            slider_steps: dict, param_id -> step
        """
        self.slider_ranges = slider_ranges
        self.slider_steps = slider_steps
        for param_id, widget in self.param_widgets.items():
            range_val = slider_ranges.get(param_id)
            step_val = slider_steps.get(param_id)
            if range_val is not None or step_val is not None:
                widget.update_slider_config(range_val, step_val)
