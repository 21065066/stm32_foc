# -*- coding: utf-8 -*-
"""串口面板"""

from PyQt5.QtWidgets import (QWidget, QHBoxLayout, QComboBox, QPushButton,
                             QLabel, QFrame)
from PyQt5.QtCore import pyqtSignal, Qt

from utils.serial_port import SerialPort


class SerialPanel(QWidget):
    """串口连接控制面板"""

    # 信号: 连接状态改变 (is_connected)
    connection_changed = pyqtSignal(bool)

    # 信号: 发送数据请求 (bytes)
    send_requested = pyqtSignal(bytes)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.serial_port = SerialPort()
        self._is_connected = False

        self._init_ui()

    def _init_ui(self):
        """初始化UI"""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(10)

        # 串口选择下拉框
        self.port_combo = QComboBox()
        self.port_combo.setMinimumWidth(120)
        self._refresh_ports()
        layout.addWidget(QLabel("串口:"))
        layout.addWidget(self.port_combo)

        # 刷新按钮
        self.btn_refresh = QPushButton("刷新")
        self.btn_refresh.setFixedWidth(60)
        self.btn_refresh.clicked.connect(self._refresh_ports)
        layout.addWidget(self.btn_refresh)

        # 波特率选择
        self.baud_combo = QComboBox()
        self.baud_combo.setMinimumWidth(100)
        baud_rates = ['9600', '19200', '38400', '57600', '115200', '230400', '460800']
        self.baud_combo.addItems(baud_rates)
        self.baud_combo.setCurrentText('115200')
        layout.addWidget(QLabel("波特率:"))
        layout.addWidget(self.baud_combo)

        # 连接按钮
        self.btn_connect = QPushButton("连接")
        self.btn_connect.setFixedWidth(80)
        self.btn_connect.clicked.connect(self._on_connect_clicked)
        layout.addWidget(self.btn_connect)

        # 断开按钮
        self.btn_disconnect = QPushButton("断开")
        self.btn_disconnect.setFixedWidth(80)
        self.btn_disconnect.setEnabled(False)
        self.btn_disconnect.clicked.connect(self._on_disconnect_clicked)
        layout.addWidget(self.btn_disconnect)

        # 状态标签
        layout.addSpacing(20)
        layout.addWidget(QLabel("状态:"))

        self.status_indicator = QFrame()
        self.status_indicator.setFixedSize(12, 12)
        self.status_indicator.setStyleSheet("background-color: #FF0000; border-radius: 6px;")
        layout.addWidget(self.status_indicator)

        self.status_label = QLabel("未连接")
        layout.addWidget(self.status_label)

        layout.addStretch()

        # 滑动条配置按钮
        self.btn_config = QPushButton("滑动条配置")
        self.btn_config.setFixedWidth(100)
        layout.addWidget(self.btn_config)

    def _refresh_ports(self):
        """刷新串口列表"""
        self.port_combo.clear()
        ports = SerialPort.list_ports()
        if ports:
            for port, desc in ports:
                self.port_combo.addItem(f"{port} - {desc}", port)
        else:
            self.port_combo.addItem("无可用串口", None)

    def _on_connect_clicked(self):
        """连接按钮点击"""
        port_info = self.port_combo.currentData()
        if not port_info:
            return

        baudrate = int(self.baud_combo.currentText())

        if self.serial_port.open(port_info, baudrate):
            self._set_connected(True)
        else:
            self._set_connected(False)

    def _on_disconnect_clicked(self):
        """断开按钮点击"""
        self.serial_port.close()
        self._set_connected(False)

    def _set_connected(self, connected):
        """设置连接状态

        Args:
            connected: 是否已连接
        """
        self._is_connected = connected

        if connected:
            self.status_indicator.setStyleSheet("background-color: #00FF00; border-radius: 6px;")
            self.status_label.setText("已连接")
            self.btn_connect.setEnabled(False)
            self.btn_disconnect.setEnabled(True)
            self.port_combo.setEnabled(False)
            self.baud_combo.setEnabled(False)
            self.btn_refresh.setEnabled(False)
        else:
            self.status_indicator.setStyleSheet("background-color: #FF0000; border-radius: 6px;")
            self.status_label.setText("未连接")
            self.btn_connect.setEnabled(True)
            self.btn_disconnect.setEnabled(False)
            self.port_combo.setEnabled(True)
            self.baud_combo.setEnabled(True)
            self.btn_refresh.setEnabled(True)

        self.connection_changed.emit(connected)

    def is_connected(self):
        """检查是否已连接"""
        return self._is_connected

    def get_serial_port(self):
        """获取串口对象"""
        return self.serial_port

    def write_data(self, data):
        """写入数据

        Args:
            data: 字节数据

        Returns:
            int: 写入的字节数
        """
        if self._is_connected:
            return self.serial_port.write(data)
        return 0

    def read_data(self, size=1):
        """读取数据

        Args:
            size: 要读取的字节数

        Returns:
            bytes: 读取的数据
        """
        if self._is_connected:
            return self.serial_port.read(size)
        return b''
