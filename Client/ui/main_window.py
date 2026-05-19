# -*- coding: utf-8 -*-
"""主窗口"""

import logging
import time
import struct

from PyQt5.QtWidgets import (QMainWindow, QWidget, QHBoxLayout, QSplitter,
                             QVBoxLayout, QMessageBox)
from PyQt5.QtCore import Qt, QThread, QTimer

from .serial_panel import SerialPanel
from .param_panel import ParamPanel
from .chart_panel import ChartPanel
from .log_panel import LogPanel
from .slider_config_dialog import SliderConfigDialog
from protocol.handler import ProtocolHandler
from protocol.constants import PARAMS, get_param_type, get_param_name
from utils.config_manager import ConfigManager
from utils.serial_reader import SerialReader


logger = logging.getLogger(__name__)


class MainWindow(QMainWindow):
    """主窗口"""

    def __init__(self):
        super().__init__()
        self.protocol_handler = None
        self.feedback_values = {}  # 存储最新的反馈值
        self._serial_reader = None
        self._reader_thread = None

        # 配置管理器
        self.config_manager = ConfigManager()

        self._init_ui()
        self._init_protocol()
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
            # 启动接收线程
            self._start_reader()
        else:
            self._stop_reader()
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

    def _start_reader(self):
        """启动接收线程"""
        if self._serial_reader is not None:
            return

        self._serial_reader = SerialReader(
            self.serial_panel.get_serial_port(),
            self.protocol_handler
        )
        self._reader_thread = QThread()
        self._serial_reader.moveToThread(self._reader_thread)

        # 连接接收线程信号
        self._serial_reader.frame_received.connect(self._on_reader_frame_received)
        self._serial_reader.param_updated.connect(self._on_reader_param_updated)
        self._serial_reader.data_line_received.connect(self.chart_panel.append_data)
        self._serial_reader.error_occurred.connect(self._on_reader_error)
        self._serial_reader.connection_lost.connect(self._on_reader_connection_lost)

        # 线程启动时执行读取循环
        self._reader_thread.started.connect(self._serial_reader.start_reader)

        self._reader_thread.start()

    def _stop_reader(self):
        """停止接收线程"""
        if self._serial_reader:
            self._serial_reader.stop_reader()
            self._serial_reader = None

        if self._reader_thread:
            self._reader_thread.quit()
            self._reader_thread.wait(1000)
            self._reader_thread = None

    def _on_reader_frame_received(self, frame):
        """接收线程收到完整帧"""
        self.log_panel.append_receive_log(bytes(frame))

    def _on_reader_param_updated(self, param_id, value):
        """接收线程解析到参数更新"""
        if value is None:
            return

        # 更新参数显示
        self.param_panel.update_param_value(param_id, value)

        # 如果是反馈参数，更新存储值
        if 0x60 <= param_id <= 0x68:
            self.feedback_values[param_id] = value

    def _on_reader_error(self, error_msg):
        """接收线程发生错误"""
        self.log_panel.append_error_log(f"接收错误: {error_msg}")

    def _on_reader_connection_lost(self):
        """接收线程检测到连接断开"""
        self._stop_reader()
        self.serial_panel.force_disconnect()
        self.log_panel.append_error_log("连接已断开")
        self.param_panel.set_params_enabled(False)

    def _on_read_requested(self, param_id):
        """读取参数请求"""
        if not self.serial_panel.is_connected():
            self.log_panel.append_error_log("串口未连接")
            return

        frame = self.protocol_handler.build_read_frame(param_id)
        self.serial_panel.write_data(frame)
        self.log_panel.append_send_log(frame)
        # 响应由接收线程的信号通知

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

    def closeEvent(self, event):
        """关闭窗口事件"""
        self._stop_reader()
        self.serial_panel.get_serial_port().close()
        self.config_manager.save()
        event.accept()
