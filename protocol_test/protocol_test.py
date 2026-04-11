#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
STM32 FOC 电机控制器串口测试程序
基于 PyQt5 实现的图形界面测试工具

使用说明：
1. 安装依赖：pip install -r requirements.txt
2. 运行程序：python protocol_test.py
3. 在界面中选择串口端口和波特率，点击"打开串口"
4. 通过各个标签页进行电机控制、参数设置和监控
"""

import sys
import struct
import threading
import time
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QPushButton, QLabel, QLineEdit, 
                             QTextEdit, QComboBox, QGroupBox, QTabWidget,
                             QSpinBox, QDoubleSpinBox, QTableWidget, QTableWidgetItem,
                             QHeaderView, QFrame, QCheckBox)
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QColor, QTextCharFormat, QTextCursor
import serial
import serial.tools.list_ports


class ProtocolFrame:
    """协议帧结构"""
    SOF = 0xAA
    EOF = 0x55
    FRAME_LENGTH = 20
    
    CMD_SET = 0x01
    CMD_GET = 0x02
    CMD_SET_ACK = 0x81
    CMD_GET_ACK = 0x82
    CMD_ERROR = 0xFF
    
    # 参数ID
    PARAM_POLE_PAIRS = 0x01
    PARAM_SHUNT_RESISTANCE = 0x02
    PARAM_OP_GAIN = 0x03
    PARAM_MAX_CURRENT = 0x04
    PARAM_ADC_REFERENCE = 0x05
    PARAM_PWM_FREQUENCY = 0x06
    PARAM_SPEED_CALC_FREQ = 0x07
    PARAM_ADC_BITS = 0x08
    PARAM_POSITION_CYCLE = 0x09
    
    PARAM_POSITION_PID = 0x20
    PARAM_SPEED_PID = 0x21
    PARAM_TORQUE_D_PID = 0x22
    PARAM_TORQUE_Q_PID = 0x23
    
    PARAM_CONTROL_TYPE = 0x41
    PARAM_TARGET_POSITION = 0x42
    PARAM_TARGET_SPEED = 0x43
    PARAM_TARGET_TORQUE_D = 0x44
    PARAM_TARGET_TORQUE_Q = 0x45
    
    PARAM_CURRENT_U = 0x60
    PARAM_CURRENT_V = 0x61
    PARAM_CURRENT_D = 0x62
    PARAM_CURRENT_Q = 0x63
    PARAM_MOTOR_SPEED = 0x64
    PARAM_MOTOR_ANGLE = 0x65
    PARAM_ENCODER_ANGLE = 0x66
    PARAM_ENCODER_INIT_ANGLE = 0x67
    PARAM_ROTOR_ZERO_ANGLE = 0x68


class SerialPort:
    """串口通信类"""
    def __init__(self):
        self.serial = None
        self.is_open = False
        self.rx_thread = None
        self.rx_callback = None
        self.lock = threading.Lock()
    
    def open_port(self, port, baudrate=115200):
        """打开串口"""
        try:
            self.serial = serial.Serial(port, baudrate, 
                                       timeout=1, 
                                       parity=serial.PARITY_NONE,
                                       stopbits=1)
            self.is_open = True
            self.rx_thread = threading.Thread(target=self._rx_loop, daemon=True)
            self.rx_thread.start()
            return True
        except Exception as e:
            print(f"打开串口失败: {e}")
            return False
    
    def close_port(self):
        """关闭串口"""
        self.is_open = False
        if self.serial:
            self.serial.close()
            self.serial = None
    
    def send_data(self, data):
        """发送数据"""
        if self.is_open and self.serial:
            with self.lock:
                self.serial.write(data)
    
    def _rx_loop(self):
        """接收循环"""
        while self.is_open:
            try:
                if self.serial.in_waiting > 0:
                    data = self.serial.read(self.serial.in_waiting)
                    if self.rx_callback:
                        self.rx_callback(data)
            except Exception as e:
                print(f"接收错误: {e}")
                time.sleep(0.01)


class ProtocolParser:
    """协议解析器"""
    def __init__(self):
        self.buffer = bytearray()
        self.frame_received = None
    
    def parse(self, data):
        """解析接收到的数据"""
        self.buffer.extend(data)
        
        while len(self.buffer) >= ProtocolFrame.FRAME_LENGTH:
            # 查找帧头
            if self.buffer[0] != ProtocolFrame.SOF:
                # 丢弃无效字节
                self.buffer.pop(0)
                continue
            
            # 检查帧长度
            if len(self.buffer) < ProtocolFrame.FRAME_LENGTH:
                break
            
            # 提取帧
            frame_data = self.buffer[:ProtocolFrame.FRAME_LENGTH]
            self.buffer = self.buffer[ProtocolFrame.FRAME_LENGTH:]
            
            # 验证帧尾
            if frame_data[-1] != ProtocolFrame.EOF:
                continue
            
            # 验证校验和
            checksum = sum(frame_data[1:-2]) & 0xFF
            if checksum != frame_data[-2]:
                continue
            
            # 解析帧
            self.frame_received = {
                'sof': frame_data[0],
                'cmd': frame_data[1],
                'param_id': frame_data[2],
                'data_len': frame_data[3],
                'data': list(frame_data[4:16]),
                'checksum': frame_data[16],
                'reserved': list(frame_data[17:19]),
                'eof': frame_data[19]
            }
            
            return self.frame_received
        
        return None
    
    def build_frame(self, cmd, param_id, data=None, data_len=0):
        """构建协议帧"""
        frame = bytearray(ProtocolFrame.FRAME_LENGTH)
        frame[0] = ProtocolFrame.SOF
        frame[1] = cmd
        frame[2] = param_id
        frame[3] = data_len
        
        if data:
            for i in range(min(data_len, 12)):
                frame[4 + i] = data[i]
        
        # 计算校验和
        checksum = sum(frame[1:16]) & 0xFF
        frame[16] = checksum
        frame[17] = 0
        frame[18] = 0
        frame[19] = ProtocolFrame.EOF
        
        return frame
    
    def float_to_bytes(self, value):
        """float 转字节（小端）"""
        return list(struct.pack('<f', value))
    
    def bytes_to_float(self, data):
        """字节转 float（小端）"""
        if len(data) >= 4:
            return struct.unpack('<f', bytes(data[:4]))[0]
        return 0.0


class ControlPanel(QGroupBox):
    """电机控制面板"""
    def __init__(self, parent=None):
        super().__init__("电机控制", parent)
        self.parent = parent
        
        layout = QVBoxLayout()
        
        # 控制模式选择
        mode_layout = QHBoxLayout()
        mode_layout.addWidget(QLabel("控制模式:"))
        self.mode_combo = QComboBox()
        self.mode_combo.addItems(["电流模式", "位置模式", "速度模式", "力矩模式"])
        mode_layout.addWidget(self.mode_combo)
        
        self.mode_combo.currentIndexChanged.connect(self.on_mode_changed)
        layout.addLayout(mode_layout)
        
        # 目标值设置
        target_layout = QHBoxLayout()
        target_layout.addWidget(QLabel("目标值:"))
        self.target_spin = QDoubleSpinBox()
        self.target_spin.setRange(-1000, 1000)
        self.target_spin.setDecimals(2)
        self.target_spin.setValue(0)
        target_layout.addWidget(self.target_spin)
        
        self.target_unit = QLabel("A")
        target_layout.addWidget(self.target_unit)
        
        self.apply_btn = QPushButton("应用")
        self.apply_btn.clicked.connect(self.apply_target)
        target_layout.addWidget(self.apply_btn)
        
        layout.addLayout(target_layout)
        
        self.setLayout(layout)
        self.update_mode_ui()
    
    def on_mode_changed(self, index):
        self.update_mode_ui()
    
    def update_mode_ui(self):
        modes = ["电流模式", "位置模式", "速度模式", "力矩模式"]
        units = ["A", "°", "rad/s", "A"]
        
        self.target_unit.setText(units[self.mode_combo.currentIndex()])
    
    def apply_target(self):
        mode = self.mode_combo.currentIndex()
        value = self.target_spin.value()
        
        if self.parent and self.parent.protocol:
            if mode == 0:  # 电流模式
                # 设置 Q 轴电流
                data = self.parent.protocol.float_to_bytes(value)
                frame = self.parent.protocol.build_frame(
                    ProtocolFrame.CMD_SET,
                    ProtocolFrame.PARAM_TARGET_TORQUE_Q,
                    data, 4
                )
                self.parent.serial.send_data(frame)
            elif mode == 1:  # 位置模式
                data = self.parent.protocol.float_to_bytes(value)
                frame = self.parent.protocol.build_frame(
                    ProtocolFrame.CMD_SET,
                    ProtocolFrame.PARAM_TARGET_POSITION,
                    data, 4
                )
                self.parent.serial.send_data(frame)
            elif mode == 2:  # 速度模式
                data = self.parent.protocol.float_to_bytes(value)
                frame = self.parent.protocol.build_frame(
                    ProtocolFrame.CMD_SET,
                    ProtocolFrame.PARAM_TARGET_SPEED,
                    data, 4
                )
                self.parent.serial.send_data(frame)
            elif mode == 3:  # 力矩模式
                data = self.parent.protocol.float_to_bytes(value)
                frame = self.parent.protocol.build_frame(
                    ProtocolFrame.CMD_SET,
                    ProtocolFrame.PARAM_TARGET_TORQUE_Q,
                    data, 4
                )
                self.parent.serial.send_data(frame)


class ParameterPanel(QGroupBox):
    """参数设置面板"""
    def __init__(self, parent=None):
        super().__init__("参数设置", parent)
        self.parent = parent
        
        layout = QVBoxLayout()
        
        # 参数表格
        self.table = QTableWidget(10, 3)
        self.table.setHorizontalHeaderLabels(["参数", "值", "操作"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        
        # 添加参数行
        params = [
            ("极对数", ProtocolFrame.PARAM_POLE_PAIRS, "7"),
            ("电流采样电阻(Ω)", ProtocolFrame.PARAM_SHUNT_RESISTANCE, "0.02"),
            ("运放放大倍数", ProtocolFrame.PARAM_OP_GAIN, "50"),
            ("最大Q轴电流(A)", ProtocolFrame.PARAM_MAX_CURRENT, "2"),
            ("ADC参考电压(V)", ProtocolFrame.PARAM_ADC_REFERENCE, "3.3"),
            ("PWM频率(Hz)", ProtocolFrame.PARAM_PWM_FREQUENCY, "40000"),
            ("速度计算频率(Hz)", ProtocolFrame.PARAM_SPEED_CALC_FREQ, "930"),
            ("ADC精度(bit)", ProtocolFrame.PARAM_ADC_BITS, "12"),
            ("多圈周期", ProtocolFrame.PARAM_POSITION_CYCLE, "18.85"),
        ]
        
        for i, (name, param_id, default) in enumerate(params):
            self.table.setItem(i, 0, QTableWidgetItem(name))
            
            value_item = QTableWidgetItem(default)
            value_item.param_id = param_id
            self.table.setItem(i, 1, value_item)
            
            read_btn = QPushButton("读取")
            read_btn.clicked.connect(lambda checked, p=param_id, item=value_item: 
                                    self.read_param(p, item))
            self.table.setCellWidget(i, 2, read_btn)
        
        layout.addWidget(self.table)
        self.setLayout(layout)
    
    def read_param(self, param_id, item):
        """读取参数"""
        if self.parent and self.parent.protocol:
            frame = self.parent.protocol.build_frame(
                ProtocolFrame.CMD_GET,
                param_id,
                None, 0
            )
            self.parent.serial.send_data(frame)
            item.param_id = param_id


class MotorMonitor(QGroupBox):
    """电机监控面板"""
    def __init__(self, parent=None):
        super().__init__("电机监控", parent)
        self.parent = parent
        
        layout = QVBoxLayout()
        
        # 监控数据表格
        self.table = QTableWidget(9, 2)
        self.table.setHorizontalHeaderLabels(["参数", "值"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        
        # 添加监控项
        monitors = [
            ("U相电流(A)", ProtocolFrame.PARAM_CURRENT_U),
            ("V相电流(A)", ProtocolFrame.PARAM_CURRENT_V),
            ("D轴电流(A)", ProtocolFrame.PARAM_CURRENT_D),
            ("Q轴电流(A)", ProtocolFrame.PARAM_CURRENT_Q),
            ("电机转速(rad/s)", ProtocolFrame.PARAM_MOTOR_SPEED),
            ("电机多圈角度(rad)", ProtocolFrame.PARAM_MOTOR_ANGLE),
            ("编码器角度(rad)", ProtocolFrame.PARAM_ENCODER_ANGLE),
            ("编码器初始角度(rad)", ProtocolFrame.PARAM_ENCODER_INIT_ANGLE),
            ("转子零位角度(rad)", ProtocolFrame.PARAM_ROTOR_ZERO_ANGLE),
        ]
        
        self.monitor_items = {}
        for i, (name, param_id) in enumerate(monitors):
            self.table.setItem(i, 0, QTableWidgetItem(name))
            value_item = QTableWidgetItem("--")
            value_item.param_id = param_id
            self.table.setItem(i, 1, value_item)
            self.monitor_items[param_id] = value_item
        
        layout.addWidget(self.table)
        
        # 自动刷新复选框
        self.auto_refresh_cb = QCheckBox("自动刷新(100ms)")
        self.auto_refresh_cb.setChecked(True)
        self.auto_refresh_cb.stateChanged.connect(self.toggle_auto_refresh)
        layout.addWidget(self.auto_refresh_cb)
        
        self.setLayout(layout)
        
        # 刷新定时器
        self.refresh_timer = QTimer()
        self.refresh_timer.timeout.connect(self.refresh_all)
        if self.auto_refresh_cb.isChecked():
            self.refresh_timer.start(100)
    
    def toggle_auto_refresh(self, state):
        if state == Qt.Checked:
            self.refresh_timer.start(100)
        else:
            self.refresh_timer.stop()
    
    def refresh_all(self):
        """刷新所有监控参数"""
        if self.parent and self.parent.protocol:
            for param_id in self.monitor_items.keys():
                frame = self.parent.protocol.build_frame(
                    ProtocolFrame.CMD_GET,
                    param_id,
                    None, 0
                )
                self.parent.serial.send_data(frame)
    
    def update_value(self, param_id, value):
        """更新监控值"""
        if param_id in self.monitor_items:
            self.monitor_items[param_id].setText(f"{value:.4f}")


class ProtocolTestWindow(QMainWindow):
    """主窗口"""
    def __init__(self):
        super().__init__()
        self.setWindowTitle("STM32 FOC 电机控制器测试工具")
        self.setGeometry(100, 100, 1000, 700)
        
        self.serial = SerialPort()
        self.protocol = ProtocolParser()
        
        # 接收数据处理
        self.serial.rx_callback = self.on_serial_data
        
        self.init_ui()
        self.init_timer()
    
    def init_ui(self):
        """初始化界面"""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        main_layout = QVBoxLayout()
        
        # 串口配置
        port_group = QGroupBox("串口配置")
        port_layout = QHBoxLayout()
        
        port_layout.addWidget(QLabel("端口:"))
        self.port_combo = QComboBox()
        self.refresh_ports()
        port_layout.addWidget(self.port_combo)
        
        self.refresh_btn = QPushButton("刷新端口")
        self.refresh_btn.clicked.connect(self.refresh_ports)
        port_layout.addWidget(self.refresh_btn)
        
        port_layout.addWidget(QLabel("波特率:"))
        self.baudrate_combo = QComboBox()
        self.baudrate_combo.addItems(["9600", "115200", "921600"])
        self.baudrate_combo.setCurrentText("115200")
        port_layout.addWidget(self.baudrate_combo)
        
        self.open_btn = QPushButton("打开串口")
        self.open_btn.clicked.connect(self.toggle_serial)
        port_layout.addWidget(self.open_btn)
        
        port_group.setLayout(port_layout)
        main_layout.addWidget(port_group)
        
        # 选项卡
        self.tab_widget = QTabWidget()
        
        # 控制标签页
        control_tab = QWidget()
        control_layout = QVBoxLayout()
        self.control_panel = ControlPanel(self)
        control_layout.addWidget(self.control_panel)
        control_tab.setLayout(control_layout)
        self.tab_widget.addTab(control_tab, "电机控制")
        
        # 参数标签页
        param_tab = QWidget()
        param_layout = QVBoxLayout()
        self.param_panel = ParameterPanel(self)
        param_layout.addWidget(self.param_panel)
        param_tab.setLayout(param_layout)
        self.tab_widget.addTab(param_tab, "参数设置")
        
        # 监控标签页
        monitor_tab = QWidget()
        monitor_layout = QVBoxLayout()
        self.motor_monitor = MotorMonitor(self)
        monitor_layout.addWidget(self.motor_monitor)
        monitor_tab.setLayout(monitor_layout)
        self.tab_widget.addTab(monitor_tab, "电机监控")
        
        main_layout.addWidget(self.tab_widget)
        
        # 日志输出
        log_group = QGroupBox("通信日志")
        log_layout = QVBoxLayout()
        
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setMaximumHeight(200)
        log_layout.addWidget(self.log_text)
        
        # 清除日志按钮
        clear_btn = QPushButton("清除日志")
        clear_btn.clicked.connect(self.clear_log)
        log_layout.addWidget(clear_btn)
        
        log_group.setLayout(log_layout)
        main_layout.addWidget(log_group)
        
        central_widget.setLayout(main_layout)
    
    def init_timer(self):
        """初始化定时器"""
        self.log_timer = QTimer()
        self.log_timer.timeout.connect(self.update_log)
        self.log_buffer = []
        self.log_timer.start(100)
    
    def refresh_ports(self):
        """刷新串口列表"""
        ports = [port.device for port in serial.tools.list_ports.comports()]
        self.port_combo.clear()
        self.port_combo.addItems(ports)
    
    def toggle_serial(self):
        """打开/关闭串口"""
        if self.serial.is_open:
            self.serial.close_port()
            self.open_btn.setText("打开串口")
            self.log_message("串口已关闭")
        else:
            port = self.port_combo.currentText()
            baudrate = int(self.baudrate_combo.currentText())
            if self.serial.open_port(port, baudrate):
                self.open_btn.setText("关闭串口")
                self.log_message(f"串口 {port} 已打开，波特率 {baudrate}")
            else:
                self.log_message("打开串口失败")
    
    def log_message(self, message):
        """记录日志"""
        timestamp = time.strftime("%H:%M:%S")
        self.log_buffer.append(f"[{timestamp}] {message}")
    
    def clear_log(self):
        """清除日志"""
        self.log_text.clear()
        self.log_buffer.clear()
    
    def update_log(self):
        """更新日志显示"""
        if self.log_buffer:
            for msg in self.log_buffer:
                self.log_text.append(msg)
            self.log_buffer.clear()
            self.log_text.verticalScrollBar().setValue(
                self.log_text.verticalScrollBar().maximum()
            )
    
    def on_serial_data(self, data):
        """处理串口接收数据"""
        frame = self.protocol.parse(data)
        if frame:
            self.handle_protocol_frame(frame)
    
    def handle_protocol_frame(self, frame):
        """处理协议帧"""
        cmd = frame['cmd']
        param_id = frame['param_id']
        data = frame['data']
        data_len = frame['data_len']
        
        # 解析数据
        if data_len > 0:
            value = self.protocol.bytes_to_float(data)
        else:
            value = None
        
        # 处理响应
        if cmd == ProtocolFrame.CMD_SET_ACK:
            self.log_message(f"[ACK] 设置参数 0x{param_id:02X} 成功")
        elif cmd == ProtocolFrame.CMD_GET_ACK:
            self.log_message(f"[ACK] 读取参数 0x{param_id:02X} = {value:.4f}")
            # 更新监控显示
            self.motor_monitor.update_value(param_id, value)
        elif cmd == ProtocolFrame.CMD_ERROR:
            error_code = data[0] if data_len > 0 else 0
            self.log_message(f"[ERROR] 参数 0x{param_id:02X} 错误码: {error_code}")
    
    def closeEvent(self, event):
        """关闭事件"""
        if self.serial.is_open:
            self.serial.close_port()
        event.accept()


def main():
    app = QApplication(sys.argv)
    window = ProtocolTestWindow()
    window.show()
    sys.exit(app.exec_())


if __name__ == '__main__':
    main()
