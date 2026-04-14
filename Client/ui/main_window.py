# -*- coding: utf-8 -*-
"""主窗口"""

import logging
import time
import struct

from PyQt5.QtWidgets import (QMainWindow, QWidget, QHBoxLayout, QSplitter,
                             QVBoxLayout, QMessageBox)
from PyQt5.QtCore import Qt, QTimer

from .serial_panel import SerialPanel
from .param_panel import ParamPanel
from .chart_panel import ChartPanel
from .log_panel import LogPanel
from .slider_config_dialog import SliderConfigDialog
from protocol.handler import ProtocolHandler
from protocol.constants import PARAMS, get_param_type, get_param_name
from utils.config_manager import ConfigManager


logger = logging.getLogger(__name__)


class MainWindow(QMainWindow):
    """主窗口"""

    # 反馈参数ID列表 (用于轮询采集)
    FEEDBACK_PARAM_IDS = [0x60, 0x61, 0x62, 0x63, 0x64, 0x65, 0x66]

    def __init__(self):
        super().__init__()
        self.protocol_handler = None
        self.feedback_values = {}  # 存储最新的反馈值
        self.poll_timer = None
        self.current_poll_index = 0

        # 配置管理器
        self.config_manager = ConfigManager()

        self._init_ui()
        self._init_protocol()
        self._init_timers()
        self._load_config()

    def _init_ui(self):
        """初始化UI"""
        self.setWindowTitle("STM32 FOC 电机控制器客户端")
        self.setGeometry(100, 100, 1400, 800)

        # 中央widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        # 主布局
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(5, 5, 5, 5)
        main_layout.setSpacing(5)

        # 串口面板
        self.serial_panel = SerialPanel()
        self.serial_panel.connection_changed.connect(self._on_connection_changed)
        self.serial_panel.btn_config.clicked.connect(self._on_open_slider_config)
        main_layout.addWidget(self.serial_panel)

        # 加载滑动条范围和步长配置
        self.slider_ranges = self.config_manager.get_all_slider_ranges()
        self.slider_steps = self.config_manager.get_all_slider_steps()

        # 创建分割器 (左右分栏)
        splitter = QSplitter(Qt.Horizontal)

        # 左侧: 参数面板 (60%)
        self.param_panel = ParamPanel(slider_ranges=self.slider_ranges,
                                    slider_steps=self.slider_steps)
        self.param_panel.read_requested.connect(self._on_read_requested)
        self.param_panel.write_requested.connect(self._on_write_requested)
        self.param_panel.set_params_enabled(False)  # 初始状态禁用
        splitter.addWidget(self.param_panel)

        # 右侧: 图表面板 (40%)
        self.chart_panel = ChartPanel()
        splitter.addWidget(self.chart_panel)

        # 设置分割比例 60:40
        splitter.setStretchFactor(0, 60)
        splitter.setStretchFactor(1, 40)

        main_layout.addWidget(splitter, stretch=1)

        # 日志面板
        self.log_panel = LogPanel()
        main_layout.addWidget(self.log_panel)

    def _init_protocol(self):
        """初始化协议处理器"""
        self.protocol_handler = ProtocolHandler()
        self.protocol_handler.set_feedback_callback(self._on_feedback_received)

    def _init_timers(self):
        """初始化定时器"""
        # 轮询定时器 (用于采集反馈数据)
        self.poll_timer = QTimer()
        self.poll_timer.timeout.connect(self._poll_feedback)

    def _load_config(self):
        """加载配置"""
        # 恢复串口设置
        saved_port = self.config_manager.get_serial_port()
        saved_baudrate = self.config_manager.get_baudrate()
        if saved_port:
            # 设置到serial_panel
            index = self.serial_panel.port_combo.findData(saved_port)
            if index >= 0:
                self.serial_panel.port_combo.setCurrentIndex(index)
        if saved_baudrate:
            index = self.serial_panel.baud_combo.findText(str(saved_baudrate))
            if index >= 0:
                self.serial_panel.baud_combo.setCurrentIndex(index)

    def _on_connection_changed(self, is_connected):
        """连接状态改变"""
        if is_connected:
            self.protocol_handler.set_serial_port(self.serial_panel.get_serial_port())
            self.log_panel.append_info_log("串口连接成功")
            # 保存串口设置
            self.config_manager.set_serial_port(self.serial_panel.port_combo.currentData())
            self.config_manager.set_baudrate(int(self.serial_panel.baud_combo.currentText()))
            self.config_manager.save()
            # 加载保存的参数值到界面
            self._load_saved_params()
        else:
            self._stop_polling()
            self.log_panel.append_info_log("串口已断开")

        # 更新参数面板控件状态
        self.param_panel.set_params_enabled(is_connected)

    def _load_saved_params(self):
        """加载保存的参数值到界面"""
        saved_params = self.config_manager.get_all_params()
        for param_id, value in saved_params.items():
            # 只更新非只读参数
            from protocol.constants import is_readonly
            if not is_readonly(param_id):
                self.param_panel.update_param_value(param_id, value)

    def _on_open_slider_config(self):
        """打开滑动条配置对话框"""
        dialog = SliderConfigDialog(self.config_manager, self)
        if dialog.exec_():
            # 保存并更新
            self.slider_ranges = self.config_manager.get_all_slider_ranges()
            self.slider_steps = self.config_manager.get_all_slider_steps()
            self.param_panel.update_slider_configs(self.slider_ranges, self.slider_steps)
            self.log_panel.append_info_log("滑动条范围和步长配置已保存")

    def _on_read_requested(self, param_id):
        """读取参数请求"""
        if not self.serial_panel.is_connected():
            self.log_panel.append_error_log("串口未连接")
            return

        frame = self.protocol_handler.build_read_frame(param_id)
        self.serial_panel.write_data(frame)
        self.log_panel.append_send_log(frame)

        # 等待响应
        self._wait_for_response(param_id, timeout=2.0)

    def _on_write_requested(self, param_id, value):
        """写入参数请求"""
        if not self.serial_panel.is_connected():
            self.log_panel.append_error_log("串口未连接")
            return

        data_type = get_param_type(param_id)
        if not data_type:
            self.log_panel.append_error_log(f"未知参数ID: 0x{param_id:02X}")
            return

        frame = self.protocol_handler.build_write_frame(param_id, value, data_type)
        self.serial_panel.write_data(frame)
        self.log_panel.append_send_log(frame)
        # 设置参数不等待响应
        # 保存参数值到配置
        self.config_manager.set_param(param_id, value)
        self.config_manager.save()

    def _wait_for_response(self, param_id, timeout=2.0, is_write=False):
        """等待响应"""
        start_time = time.time()

        while time.time() - start_time < timeout:
            raw_frame = self.serial_panel.read_data(20)
            if not raw_frame or len(raw_frame) < 20:
                time.sleep(0.01)
                continue

            self.log_panel.append_receive_log(raw_frame)

            result = self.protocol_handler.parse_frame(raw_frame)
            if result['success'] and result['param_id'] == param_id:
                self._handle_response(result)
                return

            # 继续等待正确响应
            time.sleep(0.01)

        self.log_panel.append_error_log(f"参数 0x{param_id:02X} 响应超时")

    def _handle_response(self, result):
        """处理响应"""
        param_id = result['param_id']
        value = result['value']

        # 更新参数显示
        self.param_panel.update_param_value(param_id, value)

        # 如果是反馈参数，更新存储值
        if 0x60 <= param_id <= 0x68:
            param_name = get_param_name(param_id)
            self.feedback_values[param_id] = value

    def _on_feedback_received(self, param_id, value):
        """收到反馈数据"""
        self.feedback_values[param_id] = value
        self.param_panel.update_param_value(param_id, value)

        # 如果正在采集，更新图表数据
        if self.chart_panel.is_collecting:
            self._update_chart_data()

    def _update_chart_data(self):
        """更新图表数据"""
        feedback_data = {
            'motor_speed': self.feedback_values.get(0x64),  # 电机转速
            'current_d': self.feedback_values.get(0x62),    # D轴电流
            'current_q': self.feedback_values.get(0x63),    # Q轴电流
            'motor_angle': self.feedback_values.get(0x65),  # 电机角度
            'current_u': self.feedback_values.get(0x60),    # U相电流
            'current_v': self.feedback_values.get(0x61),    # V相电流
        }

        # 过滤掉None值
        feedback_data = {k: v for k, v in feedback_data.items() if v is not None}

        if feedback_data:
            self.chart_panel.append_data(time.time(), feedback_data)

    def _start_polling(self):
        """开始轮询"""
        self.poll_timer.start(100)  # 100ms 轮询

    def _stop_polling(self):
        """停止轮询"""
        self.poll_timer.stop()

    def _poll_feedback(self):
        """轮询反馈参数"""
        if not self.serial_panel.is_connected():
            return

        # 轮询反馈参数
        param_id = self.FEEDBACK_PARAM_IDS[self.current_poll_index]
        self.current_poll_index = (self.current_poll_index + 1) % len(self.FEEDBACK_PARAM_IDS)

        frame = self.protocol_handler.build_read_frame(param_id)
        self.serial_panel.write_data(frame)

    def closeEvent(self, event):
        """关闭窗口事件"""
        self._stop_polling()
        self.serial_panel.get_serial_port().close()
        self.config_manager.save()
        event.accept()
