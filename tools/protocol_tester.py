#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
STM32电机控制器参数协议测试工具
基于PyQt5实现的串口协议测试界面
"""

import sys
import struct
import serial
import serial.tools.list_ports
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QPushButton, QLabel, QLineEdit, 
                             QComboBox, QTextEdit, QGroupBox, QTabWidget,
                             QProgressBar, QSpinBox, QDoubleSpinBox)
from PyQt5.QtCore import Qt, QTimer, QThread, pyqtSignal
from PyQt5.QtGui import QTextCursor, QColor, QTextCharFormat


class SerialThread(QThread):
    """串口接收线程"""
    data_received = pyqtSignal(bytes)
    
    def __init__(self, port, baudrate=115200):
        super().__init__()
        self.port = port
        self.baudrate = baudrate
        self.ser = None
        self.running = False
    
    def run(self):
        try:
            self.ser = serial.Serial(self.port, self.baudrate, 
                                    timeout=0.1, bytesize=8, parity='N', stopbits=1)
            self.running = True
            while self.running:
                if self.ser.in_waiting:
                    data = self.ser.read(self.ser.in_waiting)
                    if data:
                        self.data_received.emit(data)
                self.msleep(10)
        except Exception as e:
            print(f"Serial error: {e}")
    
    def stop(self):
        self.running = False
        if self.ser and self.ser.is_open:
            self.ser.close()
    
    def write(self, data):
        if self.ser and self.ser.is_open:
            try:
                self.ser.write(data)
            except Exception as e:
                print(f"Write error: {e}")


class ProtocolTester(QMainWindow):
    """主窗口类"""
    
    # 协议常量
    SOF = 0xAA
    EOF = 0x55
    
    CMD_SET = 0x01
    CMD_GET = 0x02
    CMD_SET_ACK = 0x81
    CMD_GET_ACK = 0x82
    CMD_ERROR = 0xFF
    
    PARAM_IDS = {
        "极对数 (POLE_PAIRS)": 0x01,
        "电流采样电阻 (R_SHUNT)": 0x02,
        "运放放大倍数 (OP_GAIN)": 0x03,
        "最大Q轴电流 (MAX_CURRENT)": 0x04,
        "ADC参考电压 (ADC_REF_VOLT)": 0x05,
        "PWM频率 (PWM_FREQ)": 0x06,
        "速度计算频率 (SPEED_CALC_FREQ)": 0x07,
        "位置PID - Kp": 0x10,
        "位置PID - Ki": 0x11,
        "位置PID - Kd": 0x12,
        "速度PID - Kp": 0x20,
        "速度PID - Ki": 0x21,
        "速度PID - Kd": 0x22,
        "转矩D轴PID - Kp": 0x30,
        "转矩D轴PID - Ki": 0x31,
        "转矩D轴PID - Kd": 0x32,
        "转矩Q轴PID - Kp": 0x40,
        "转矩Q轴PID - Ki": 0x41,
        "转矩Q轴PID - Kd": 0x42,
    }
    
    def __init__(self):
        super().__init__()
        self.serial_thread = None
        self.init_ui()
        self.init_serial()
    
    def init_ui(self):
        """初始化界面"""
        self.setWindowTitle("STM32电机控制器协议测试工具 v1.0")
        self.setGeometry(100, 100, 1000, 700)
        
        # 主部件
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        
        # 标题
        title_label = QLabel("STM32电机控制器参数协议测试工具")
        title_label.setStyleSheet("font-size: 16px; font-weight: bold;")
        title_label.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(title_label)
        
        # 串口配置组
        serial_group = QGroupBox("串口配置")
        serial_layout = QHBoxLayout()
        
        serial_layout.addWidget(QLabel("端口:"))
        self.port_combo = QComboBox()
        self.refresh_ports()
        serial_layout.addWidget(self.port_combo)
        
        refresh_btn = QPushButton("刷新")
        refresh_btn.clicked.connect(self.refresh_ports)
        serial_layout.addWidget(refresh_btn)
        
        serial_layout.addWidget(QLabel("波特率:"))
        self.baudrate_combo = QComboBox()
        self.baudrate_combo.addItems(["9600", "115200", "230400", "460800"])
        self.baudrate_combo.setCurrentText("115200")
        serial_layout.addWidget(self.baudrate_combo)
        
        self.connect_btn = QPushButton("连接")
        self.connect_btn.clicked.connect(self.toggle_serial)
        serial_layout.addWidget(self.connect_btn)
        
        serial_group.setLayout(serial_layout)
        main_layout.addWidget(serial_group)
        
        # 标签页
        tabs = QTabWidget()
        
        # 参数读取标签
        read_tab = QWidget()
        read_layout = QVBoxLayout(read_tab)
        
        read_param_group = QGroupBox("读取参数")
        read_param_layout = QHBoxLayout()
        
        read_param_layout.addWidget(QLabel("参数:"))
        self.read_param_combo = QComboBox()
        for param_name in self.PARAM_IDS.keys():
            self.read_param_combo.addItem(param_name)
        read_param_layout.addWidget(self.read_param_combo)
        
        read_btn = QPushButton("读取")
        read_btn.clicked.connect(self.read_parameter)
        read_param_layout.addWidget(read_btn)
        
        read_param_group.setLayout(read_param_layout)
        read_layout.addWidget(read_param_group)
        
        self.read_value_label = QLabel("当前值: --")
        self.read_value_label.setStyleSheet("font-size: 14px; font-weight: bold;")
        read_layout.addWidget(self.read_value_label)
        
        # 参数设置标签
        write_tab = QWidget()
        write_layout = QVBoxLayout(write_tab)
        
        write_param_group = QGroupBox("设置参数")
        write_param_layout = QHBoxLayout()
        
        write_param_layout.addWidget(QLabel("参数:"))
        self.write_param_combo = QComboBox()
        for param_name in self.PARAM_IDS.keys():
            self.write_param_combo.addItem(param_name)
        write_param_layout.addWidget(self.write_param_combo)
        
        write_param_layout.addWidget(QLabel("值:"))
        self.write_value_spin = QDoubleSpinBox()
        self.write_value_spin.setDecimals(6)
        self.write_value_spin.setRange(-999999, 999999)
        self.write_value_spin.setValue(0.0)
        write_param_layout.addWidget(self.write_value_spin)
        
        write_btn = QPushButton("写入")
        write_btn.clicked.connect(self.write_parameter)
        write_param_layout.addWidget(write_btn)
        
        write_param_group.setLayout(write_param_layout)
        write_layout.addWidget(write_param_group)
        
        # 协议调试标签
        debug_tab = QWidget()
        debug_layout = QVBoxLayout(debug_tab)
        
        # 协议发送
        send_group = QGroupBox("手动发送协议帧")
        send_layout = QHBoxLayout()
        
        send_layout.addWidget(QLabel("CMD:"))
        self.send_cmd_combo = QComboBox()
        self.send_cmd_combo.addItems(["0x01 (SET)", "0x02 (GET)", "0x81 (SET_ACK)", 
                                      "0x82 (GET_ACK)", "0xFF (ERROR)"])
        self.send_cmd_combo.setCurrentIndex(0)
        send_layout.addWidget(self.send_cmd_combo)
        
        send_layout.addWidget(QLabel("PARAM_ID:"))
        self.send_param_id_combo = QComboBox()
        for param_name, param_id in self.PARAM_IDS.items():
            self.send_param_id_combo.addItem(f"0x{param_id:02X} ({param_name})", param_id)
        send_layout.addWidget(self.send_param_id_combo)
        
        send_layout.addWidget(QLabel("DATA_LEN:"))
        self.send_data_len_spin = QSpinBox()
        self.send_data_len_spin.setRange(0, 32)
        self.send_data_len_spin.setValue(0)
        send_layout.addWidget(self.send_data_len_spin)
        
        send_layout.addWidget(QLabel("DATA:"))
        self.send_data_edit = QLineEdit()
        self.send_data_edit.setPlaceholderText("十六进制，空格分隔，例如: 00 00 80 3F")
        send_layout.addWidget(self.send_data_edit)
        
        send_btn = QPushButton("发送")
        send_btn.clicked.connect(self.send_custom_frame)
        send_layout.addWidget(send_btn)
        
        send_group.setLayout(send_layout)
        debug_layout.addWidget(send_group)
        
        # 协议解析
        parse_group = QGroupBox("协议解析")
        parse_layout = QVBoxLayout()
        
        self.parse_output = QTextEdit()
        self.parse_output.setReadOnly(True)
        self.parse_output.setMaximumHeight(200)
        parse_layout.addWidget(self.parse_output)
        
        debug_layout.addLayout(parse_layout)
        debug_layout.addStretch()
        
        tabs.addTab(read_tab, "参数读取")
        tabs.addTab(write_tab, "参数设置")
        tabs.addTab(debug_tab, "协议调试")
        
        main_layout.addWidget(tabs)
        
        # 日志输出
        log_group = QGroupBox("通信日志")
        log_layout = QVBoxLayout()
        
        self.log_output = QTextEdit()
        self.log_output.setReadOnly(True)
        log_layout.addWidget(self.log_output)
        
        # 清除按钮
        clear_btn = QPushButton("清除日志")
        clear_btn.clicked.connect(self.clear_log)
        log_layout.addWidget(clear_btn)
        
        log_group.setLayout(log_layout)
        main_layout.addWidget(log_group)
        
        # 状态栏
        self.statusBar().showMessage("就绪")
    
    def init_serial(self):
        """初始化串口"""
        self.serial_thread = SerialThread("")
        self.serial_thread.data_received.connect(self.handle_serial_data)
    
    def refresh_ports(self):
        """刷新串口列表"""
        ports = [p.device for p in serial.tools.list_ports.comports()]
        self.port_combo.clear()
        self.port_combo.addItems(ports)
    
    def toggle_serial(self):
        """切换串口连接状态"""
        if self.serial_thread.ser and self.serial_thread.ser.is_open:
            # 断开连接
            self.serial_thread.stop()
            self.connect_btn.setText("连接")
            self.statusBar().showMessage("串口已断开")
            self.log_message("串口已断开")
        else:
            # 连接串口
            port = self.port_combo.currentText()
            if not port:
                self.statusBar().showMessage("请选择串口")
                return
            
            baudrate = int(self.baudrate_combo.currentText())
            self.serial_thread = SerialThread(port, baudrate)
            self.serial_thread.data_received.connect(self.handle_serial_data)
            self.serial_thread.start()
            
            self.connect_btn.setText("断开")
            self.statusBar().showMessage(f"已连接到 {port} @ {baudrate} baud")
            self.log_message(f"已连接到 {port} @ {baudrate} baud")
    
    def handle_serial_data(self, data):
        """处理串口接收数据"""
        self.log_message(f"RX: {data.hex(' ').upper()}", "rx")
        
        # 尝试解析协议帧
        self.parse_protocol_frame(data)
    
    def log_message(self, msg, msg_type="info"):
        """添加日志消息"""
        cursor = self.log_output.textCursor()
        cursor.movePosition(QTextCursor.End)
        
        format = QTextCharFormat()
        if msg_type == "tx":
            format.setForeground(QColor("#008800"))
        elif msg_type == "rx":
            format.setForeground(QColor("#000088"))
        elif msg_type == "error":
            format.setForeground(QColor("#880000"))
        else:
            format.setForeground(QColor("#000000"))
        
        format.setFontWeight(50)
        cursor.setCharFormat(format)
        cursor.insertText(f"[{self.get_timestamp()}] {msg}\n")
        
        self.log_output.ensureCursorVisible()
    
    def get_timestamp(self):
        """获取时间戳"""
        from datetime import datetime
        return datetime.now().strftime("%H:%M:%S.%f")[:-3]
    
    def clear_log(self):
        """清除日志"""
        self.log_output.clear()
    
    def calculate_checksum(self, cmd, param_id, data_len, data_bytes):
        """计算校验和"""
        checksum = cmd + param_id + data_len
        for b in data_bytes:
            checksum += b
        return checksum & 0xFF
    
    def build_frame(self, cmd, param_id, data=None):
        """构建协议帧"""
        data_bytes = data if data else b''
        data_len = len(data_bytes)
        
        frame = bytearray()
        frame.append(self.SOF)
        frame.append(cmd)
        frame.append(param_id)
        frame.append(data_len)
        frame.extend(data_bytes)
        
        checksum = self.calculate_checksum(cmd, param_id, data_len, data_bytes)
        frame.append(checksum)
        frame.append(self.EOF)
        
        return frame
    
    def send_frame(self, frame):
        """发送协议帧"""
        if self.serial_thread and self.serial_thread.ser and self.serial_thread.ser.is_open:
            self.log_message(f"TX: {frame.hex(' ').upper()}", "tx")
            self.serial_thread.write(frame)
        else:
            self.statusBar().showMessage("串口未连接")
            self.log_message("错误: 串口未连接", "error")
    
    def read_parameter(self):
        """读取参数"""
        param_name = self.read_param_combo.currentText()
        param_id = self.PARAM_IDS[param_name]
        
        frame = self.build_frame(self.CMD_GET, param_id)
        self.send_frame(frame)
    
    def write_parameter(self):
        """写入参数"""
        param_name = self.write_param_combo.currentText()
        param_id = self.PARAM_IDS[param_name]
        value = self.write_value_spin.value()
        
        # 将float转换为4字节小端序
        data = struct.pack('<f', value)
        
        frame = self.build_frame(self.CMD_SET, param_id, data)
        self.send_frame(frame)
    
    def send_custom_frame(self):
        """发送自定义帧"""
        cmd_text = self.send_cmd_combo.currentText()
        cmd = int(cmd_text.split()[0], 16)
        
        param_id = self.send_param_id_combo.currentData()
        data_len = self.send_data_len_spin.value()
        
        data_str = self.send_data_edit.text().strip()
        data_bytes = b''
        if data_str:
            try:
                hex_values = data_str.split()
                data_bytes = bytes([int(h, 16) for h in hex_values])
                if len(data_bytes) != data_len:
                    self.log_message(f"错误: 数据长度不匹配 (期望 {data_len}, 实际 {len(data_bytes)})", "error")
                    return
            except ValueError as e:
                self.log_message(f"错误: 无效的十六进制数据 - {e}", "error")
                return
        
        frame = self.build_frame(cmd, param_id, data_bytes)
        self.send_frame(frame)
    
    def parse_protocol_frame(self, data):
        """解析协议帧"""
        if len(data) < 6:
            return
        
        # 查找帧头
        sof_index = data.find(bytes([self.SOF]))
        if sof_index == -1:
            return
        
        # 从帧头开始解析
        frame_data = data[sof_index:]
        
        if len(frame_data) < 6:
            return
        
        cmd = frame_data[1]
        param_id = frame_data[2]
        data_len = frame_data[3]
        
        expected_len = 6 + data_len
        if len(frame_data) < expected_len:
            return
        
        if frame_data[expected_len - 1] != self.EOF:
            return
        
        # 计算校验和
        calc_checksum = self.calculate_checksum(cmd, param_id, data_len, frame_data[4:4+data_len])
        rx_checksum = frame_data[4 + data_len]
        
        if calc_checksum != rx_checksum:
            self.log_message(f"警告: 校验和错误 (期望 {calc_checksum:02X}, 实际 {rx_checksum:02X})", "error")
            return
        
        # 解析成功
        param_name = "未知"
        for name, pid in self.PARAM_IDS.items():
            if pid == param_id:
                param_name = name
                break
        
        output = []
        output.append(f"=== 协议帧解析成功 ===")
        output.append(f"CMD: 0x{cmd:02X}")
        output.append(f"PARAM_ID: 0x{param_id:02X} ({param_name})")
        output.append(f"DATA_LEN: {data_len}")
        output.append(f"CHECKSUM: 0x{rx_checksum:02X}")
        output.append(f"EOF: 0x{self.EOF:02X}")
        
        if data_len > 0:
            data_bytes = frame_data[4:4+data_len]
            output.append(f"DATA: {data_bytes.hex(' ').upper()}")
            
            # 尝试解析为float
            if data_len == 4:
                value = struct.unpack('<f', data_bytes)[0]
                output.append(f"值 (float): {value:.6f}")
        
        self.parse_output.setPlainText('\n'.join(output))
        
        # 如果是ACK或GET响应，更新UI
        if cmd == self.CMD_GET_ACK and data_len == 4:
            value = struct.unpack('<f', frame_data[4:8])[0]
            self.read_value_label.setText(f"当前值: {value:.6f}")
            self.statusBar().showMessage(f"读取成功: {value:.6f}")
        elif cmd == self.CMD_SET_ACK:
            self.statusBar().showMessage("写入成功")
            self.log_message("写入成功 (ACK received)")
        elif cmd == self.CMD_ERROR:
            error_code = frame_data[4] if data_len > 0 else 0
            self.log_message(f"错误响应: error_code=0x{error_code:02X}", "error")
            self.statusBar().showMessage(f"错误: 0x{error_code:02X}")
    
    def closeEvent(self, event):
        """关闭事件"""
        if self.serial_thread and self.serial_thread.ser:
            self.serial_thread.stop()
        event.accept()


def main():
    app = QApplication(sys.argv)
    window = ProtocolTester()
    window.show()
    sys.exit(app.exec_())


if __name__ == '__main__':
    main()
