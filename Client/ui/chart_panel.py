# -*- coding: utf-8 -*-
"""图表面板"""

from PyQt5.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QCheckBox, QPushButton, QGroupBox, QLabel
from PyQt5.QtCore import Qt, pyqtSignal, QTimer
import time

import pyqtgraph as pg
import numpy as np

from data.data_collector import DataCollector


class ChartPanel(QWidget):
    """图表面板 - 实时曲线显示"""

    # 信号: 采集状态改变 (is_collecting)
    collection_changed = pyqtSignal(bool)

    def __init__(self, parent=None):
        super().__init__(parent)

        self.data_collector = DataCollector(max_points=1000)
        self.is_collecting = False

        # 反馈数据缓存（用于定时刷新）
        self._feedback_cache = {}

        # 曲线配置
        self.curve_colors = {
            'motor_speed': '#FFFF00',  # 黄色
            'current_d': '#FF0000',   # 红色
            'current_q': '#0000FF',    # 蓝色
            'motor_angle': '#00FF00',  # 绿色
            'current_u': '#00FFFF',    # 青色
            'current_v': '#FF00FF',    # 紫色
        }

        self.curve_names = {
            'motor_speed': '电机转速',
            'current_d': 'D轴电流',
            'current_q': 'Q轴电流',
            'motor_angle': '电机角度',
            'current_u': 'U相电流',
            'current_v': 'V相电流',
        }

        self.checkboxes = {}
        self.curves = {}

        self._init_ui()

    def _init_ui(self):
        """初始化UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)

        # 实时曲线图表
        chart_group = QGroupBox("实时曲线")
        chart_layout = QVBoxLayout(chart_group)

        # 创建 DateAxisItem 作为 X 轴，用于显示标准时间
        date_axis = pg.DateAxisItem(orientation='bottom')
        
        # 创建PlotWidget
        self.plot_widget = pg.PlotWidget(axisItems={'bottom': date_axis})
        self.plot_widget.setBackground('#1E1E1E')
        self.plot_widget.showGrid(x=True, y=True, alpha=0.3)

        # 设置Y轴标签
        self.plot_widget.setLabel('left', '数值')
        self.plot_widget.setLabel('bottom', '时间')

        # 设置曲线
        default_visible = ['motor_speed', 'current_d', 'current_q']
        for key, color in self.curve_colors.items():
            pen = pg.mkPen(color=color, width=1)
            curve = self.plot_widget.plot(pen=pen)
            curve.setVisible(key in default_visible)
            self.curves[key] = curve

        chart_layout.addWidget(self.plot_widget)

        layout.addWidget(chart_group)

        # 曲线选择区域
        selector_group = QGroupBox("曲线选择")
        selector_layout = QHBoxLayout(selector_group)

        # 创建复选框
        for key, name in self.curve_names.items():
            # 颜色方块
            color_box = QLabel()
            color_box.setFixedSize(15, 15)
            color_box.setStyleSheet(f"background-color: {self.curve_colors[key]}; border: 1px solid #555;")
            selector_layout.addWidget(color_box)

            cb = QCheckBox(name)
            cb.setChecked(key in default_visible)
            cb.stateChanged.connect(lambda state, k=key: self._on_curve_toggled(k, state))
            self.checkboxes[key] = cb
            selector_layout.addWidget(cb)

        selector_layout.addStretch()

        # 控制按钮
        self.btn_start = QPushButton("开始采集")
        self.btn_start.clicked.connect(self._on_start_clicked)
        selector_layout.addWidget(self.btn_start)

        self.btn_stop = QPushButton("停止采集")
        self.btn_stop.setEnabled(False)
        self.btn_stop.clicked.connect(self._on_stop_clicked)
        selector_layout.addWidget(self.btn_stop)

        self.btn_clear = QPushButton("清空")
        self.btn_clear.clicked.connect(self._on_clear_clicked)
        selector_layout.addWidget(self.btn_clear)

        layout.addWidget(selector_group)

        # 定时器用于更新图表
        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self._update_plot)

    def _on_curve_toggled(self, key, state):
        """曲线复选框状态改变"""
        visible = state == Qt.Checked
        self.curves[key].setVisible(visible)

    def _on_start_clicked(self):
        """开始采集按钮点击"""
        self.is_collecting = True
        self.data_collector.clear()
        self.data_collector.set_start_time(None)  # 重置起始时间
        self._feedback_cache = {}  # 清空缓存
        self.btn_start.setEnabled(False)
        self.btn_stop.setEnabled(True)
        # 禁用曲线选择复选框
        for cb in self.checkboxes.values():
            cb.setEnabled(False)
        # 根据勾选的曲线数量计算刷新间隔
        checked_count = sum(1 for cb in self.checkboxes.values() if cb.isChecked())
        interval = checked_count * 30
        self.update_timer.start(interval)  # 启动图表刷新定时器
        self.collection_changed.emit(True)

    def _on_stop_clicked(self):
        """停止采集按钮点击"""
        self.is_collecting = False
        self.update_timer.stop()
        self.btn_start.setEnabled(True)
        self.btn_stop.setEnabled(False)
        # 启用曲线选择复选框
        for cb in self.checkboxes.values():
            cb.setEnabled(True)
        self.collection_changed.emit(False)

    def _on_clear_clicked(self):
        """清空按钮点击"""
        self.data_collector.clear()
        for curve in self.curves.values():
            curve.setData([], [])

    def _update_plot(self):
        """更新图表（定时器调用）"""
        if not self.is_collecting:
            return

        if not self._feedback_cache:
            return

        # 设置起始时间
        if self.data_collector._start_time is None:
            self.data_collector.set_start_time(time.time())

        # 将缓存数据添加到采集器
        self.data_collector.append(time.time(), self._feedback_cache)

        # 获取数据并更新图表 (使用绝对时间戳以支持 DateAxisItem)
        timestamps, data_dict = self.data_collector.get_all_data(absolute=True)

        if not timestamps:
            return

        for key, curve in self.curves.items():
            if key in data_dict and data_dict[key]:
                # 过滤掉None值，避免pyqtgraph的np.isfinite报错
                data = data_dict[key]
                filtered_ts = []
                filtered_data = []
                for t, v in zip(timestamps, data):
                    if v is not None:
                        filtered_ts.append(t)
                        filtered_data.append(v)
                if filtered_data:
                    curve.setData(filtered_ts, filtered_data)

    def append_data(self, feedback_data):
        """添加数据点到缓存

        Args:
            feedback_data: 反馈数据字典
        """
        # 更新缓存中的数据
        for key, value in feedback_data.items():
            # 仅记录勾选且存在的参数
            if key in self.checkboxes and self.checkboxes[key].isChecked():
                self._feedback_cache[key] = value

    def start_collection(self):
        """开始采集"""
        self._on_start_clicked()

    def stop_collection(self):
        """停止采集"""
        self._on_stop_clicked()

    def get_data_collector(self):
        """获取数据采集器"""
        return self.data_collector
