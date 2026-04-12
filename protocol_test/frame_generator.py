#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
STM32 FOC 协议帧生成器
根据协议规范生成符合格式的通信帧
"""

import sys
import struct
import serial
import serial.tools.list_ports
from datetime import datetime
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QPushButton, QLabel, QLineEdit, 
                             QTextEdit, QComboBox, QGroupBox, QSpinBox,
                             QDoubleSpinBox, QTableWidget, QTableWidgetItem,
                             QHeaderView, QTabWidget, QFrame)
from PyQt5.QtCore import Qt


# 协议常量
PROTOCOL_SOF = 0xAA
PROTOCOL_EOF = 0x55
PROTOCOL_FRAME_LENGTH = 20
PROTOCOL_DATA_MAX_LEN = 12

# 命令字定义
CMD_SET = 0x01
CMD_GET = 0x02
CMD_SET_ACK = 0x81
CMD_GET_ACK = 0x82
CMD_ERROR = 0xFF

CMD_NAMES = {
    CMD_SET: "CMD_SET (设置参数)",
    CMD_GET: "CMD_GET (读取参数)",
    CMD_SET_ACK: "CMD_SET_ACK (设置确认)",
    CMD_GET_ACK: "CMD_GET_ACK (读取确认)",
    CMD_ERROR: "CMD_ERROR (错误响应)",
}

# 参数ID定义
PARAM_NAMES = {
    # 硬件参数 (0x01-0x09)
    0x01: "PARAM_POLE_PAIRS (极对数)",
    0x02: "PARAM_SHUNT_RESISTANCE (电流采样电阻)",
    0x03: "PARAM_OP_GAIN (运放放大倍数)",
    0x04: "PARAM_MAX_CURRENT (最大Q轴电流)",
    0x05: "PARAM_ADC_REFERENCE (ADC参考电压)",
    0x06: "PARAM_PWM_FREQUENCY (PWM频率)",
    0x07: "PARAM_SPEED_CALC_FREQ (速度计算频率)",
    0x08: "PARAM_ADC_BITS (ADC精度)",
    0x09: "PARAM_POSITION_CYCLE (多圈周期)",
    
    # PID参数 (0x20-0x23)
    0x20: "PARAM_POSITION_PID (位置PID)",
    0x21: "PARAM_SPEED_PID (速度PID)",
    0x22: "PARAM_TORQUE_D_PID (D轴力矩PID)",
    0x23: "PARAM_TORQUE_Q_PID (Q轴力矩PID)",
    
    # 目标值 (0x41-0x45)
    0x41: "PARAM_CONTROL_TYPE (控制类型)",
    0x42: "PARAM_TARGET_POSITION (目标角度)",
    0x43: "PARAM_TARGET_SPEED (目标速度)",
    0x44: "PARAM_TARGET_TORQUE_D (目标转矩D轴)",
    0x45: "PARAM_TARGET_TORQUE_Q (目标转矩Q轴)",
    
    # 反馈值 (0x60-0x68)
    0x60: "PARAM_CURRENT_U (U相电流)",
    0x61: "PARAM_CURRENT_V (V相电流)",
    0x62: "PARAM_CURRENT_D (D轴电流)",
    0x63: "PARAM_CURRENT_Q (Q轴电流)",
    0x64: "PARAM_MOTOR_SPEED (电机转速)",
    0x65: "PARAM_MOTOR_ANGLE (电机多圈角度)",
    0x66: "PARAM_ENCODER_ANGLE (编码器角度)",
    0x67: "PARAM_ENCODER_INIT_ANGLE (编码器初始角度)",
    0x68: "PARAM_ROTOR_ZERO_ANGLE (转子零位角度)",
}


class ProtocolFrameGenerator:
    """协议帧生成器"""
    
    @staticmethod
    def calculate_checksum(cmd, param_id, data_len, data):
        """计算校验和"""
        checksum = cmd + param_id + data_len
        for i in range(12):  # 固定计算12个字节
            if i < len(data):
                checksum += data[i]
            else:
                checksum += 0
        return checksum & 0xFF
    
    @staticmethod
    def float_to_bytes(value):
        """float 转字节（小端）"""
        return list(struct.pack('<f', value))
    
    @staticmethod
    def int_to_bytes(value, byte_count):
        """int 转字节（小端）"""
        if byte_count == 1:
            return [value & 0xFF]
        elif byte_count == 2:
            return [value & 0xFF, (value >> 8) & 0xFF]
        elif byte_count == 4:
            return list(struct.pack('<I', value & 0xFFFFFFFF))
        else:
            return []
    
    @staticmethod
    def generate_frame(cmd, param_id, data_len, data):
        """生成协议帧"""
        frame = bytearray(PROTOCOL_FRAME_LENGTH)
        
        # 填充帧头
        frame[0] = PROTOCOL_SOF
        frame[1] = cmd
        frame[2] = param_id
        frame[3] = data_len
        
        # 填充数据段（固定12字节）
        for i in range(12):
            if i < len(data):
                frame[4 + i] = data[i]
            else:
                frame[4 + i] = 0
        
        # 计算校验和
        checksum = ProtocolFrameGenerator.calculate_checksum(cmd, param_id, data_len, data)
        frame[16] = checksum
        
        # 填充保留字节
        frame[17] = 0
        frame[18] = 0
        
        # 填充帧尾
        frame[19] = PROTOCOL_EOF
        
        return frame
    
    @staticmethod
    def frame_to_hex_string(frame):
        """帧转十六进制字符串"""
        return ' '.join(f'{b:02X}' for b in frame)


class DataEntryWidget(QWidget):
    """数据段输入控件"""
    def __init__(self, index, parent=None):
        super().__init__(parent)
        self.index = index
        
        layout = QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        
        # 数据类型选择
        self.type_combo = QComboBox()
        self.type_combo.addItems(["uint8", "int16", "int32", "float32"])
        self.type_combo.currentIndexChanged.connect(self.on_type_changed)
        layout.addWidget(self.type_combo)
        
        # 数据值输入
        self.value_spin = QDoubleSpinBox()
        self.value_spin.setRange(-1e6, 1e6)
        self.value_spin.setDecimals(4)
        self.value_spin.setValue(0)
        layout.addWidget(self.value_spin)
        
        # 显示字节
        self.bytes_label = QLabel("00 00 00 00")
        self.bytes_label.setStyleSheet("background-color: #f0f0f0; padding: 2px;")
        layout.addWidget(self.bytes_label)
        
        self.setLayout(layout)
        self.update_bytes()
    
    def on_type_changed(self, index):
        self.update_bytes()
    
    def get_data(self):
        """获取数据字节"""
        data_type = self.type_combo.currentText()
        value = self.value_spin.value()
        
        if data_type == "uint8":
            return ProtocolFrameGenerator.int_to_bytes(int(value), 1)
        elif data_type == "int16":
            return ProtocolFrameGenerator.int_to_bytes(int(value), 2)
        elif data_type == "int32":
            return ProtocolFrameGenerator.int_to_bytes(int(value), 4)
        elif data_type == "float32":
            return ProtocolFrameGenerator.float_to_bytes(float(value))
        
        return []
    
    def update_bytes(self):
        """更新字节显示"""
        data = self.get_data()
        hex_str = ' '.join(f'{b:02X}' for b in data)
        self.bytes_label.setText(hex_str)


class FrameGeneratorWindow(QMainWindow):
    """帧生成器主窗口"""
    def __init__(self):
        super().__init__()
        self.setWindowTitle("STM32 FOC 协议帧生成器与发送工具")
        self.setGeometry(100, 100, 800, 800)
        
        self.serial = None
        self.current_frame = None
        
        self.init_ui()
    
    def init_ui(self):
        """初始化界面"""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        main_layout = QVBoxLayout()
        
        # 串口配置
        serial_group = QGroupBox("串口连接")
        serial_layout = QHBoxLayout()
        
        serial_layout.addWidget(QLabel("端口:"))
        self.port_combo = QComboBox()
        self.refresh_ports()
        serial_layout.addWidget(self.port_combo)
        
        self.refresh_btn = QPushButton("刷新")
        self.refresh_btn.clicked.connect(self.refresh_ports)
        serial_layout.addWidget(self.refresh_btn)
        
        serial_layout.addWidget(QLabel("波特率:"))
        self.baud_combo = QComboBox()
        self.baud_combo.addItems(["9600", "115200", "921600"])
        self.baud_combo.setCurrentText("115200")
        serial_layout.addWidget(self.baud_combo)
        
        self.open_btn = QPushButton("打开串口")
        self.open_btn.clicked.connect(self.toggle_serial)
        serial_layout.addWidget(self.open_btn)
        
        serial_group.setLayout(serial_layout)
        main_layout.addWidget(serial_group)
        
        # 帧基本信息
        frame_group = QGroupBox("帧基本信息")
        frame_layout = QHBoxLayout()
        
        # 命令字选择
        frame_layout.addWidget(QLabel("命令字:"))
        self.cmd_combo = QComboBox()
        for cmd, name in CMD_NAMES.items():
            self.cmd_combo.addItem(name, cmd)
        frame_layout.addWidget(self.cmd_combo)
        
        # 参数ID选择
        frame_layout.addWidget(QLabel("参数ID:"))
        self.param_combo = QComboBox()
        for param_id, name in PARAM_NAMES.items():
            self.param_combo.addItem(name, param_id)
        frame_layout.addWidget(self.param_combo)
        
        # 数据长度选择
        frame_layout.addWidget(QLabel("数据长度:"))
        self.data_len_spin = QSpinBox()
        self.data_len_spin.setRange(0, 12)
        self.data_len_spin.setValue(4)
        self.data_len_spin.valueChanged.connect(self.on_data_len_changed)
        frame_layout.addWidget(self.data_len_spin)
        
        frame_group.setLayout(frame_layout)
        main_layout.addWidget(frame_group)
        
        # 数据段输入
        data_group = QGroupBox("数据段 (最多3个数据)")
        data_layout = QVBoxLayout()
        
        self.data_entries = []
        for i in range(3):
            entry = DataEntryWidget(i)
            self.data_entries.append(entry)
            data_layout.addWidget(entry)
        
        data_group.setLayout(data_layout)
        main_layout.addWidget(data_group)
        
        # 操作按钮
        btn_layout = QHBoxLayout()
        self.generate_btn = QPushButton("生成帧")
        self.generate_btn.clicked.connect(self.generate_frame)
        self.generate_btn.setStyleSheet("font-size: 14px; font-weight: bold;")
        btn_layout.addWidget(self.generate_btn)
        
        self.send_btn = QPushButton("发送帧")
        self.send_btn.clicked.connect(self.send_frame)
        self.send_btn.setStyleSheet("font-size: 14px; font-weight: bold; color: blue;")
        self.send_btn.setEnabled(False)
        btn_layout.addWidget(self.send_btn)
        main_layout.addLayout(btn_layout)
        
        # 输出显示
        output_group = QGroupBox("生成结果与日志")
        output_layout = QVBoxLayout()
        
        # 十六进制显示
        self.hex_edit = QTextEdit()
        self.hex_edit.setReadOnly(True)
        self.hex_edit.setMaximumHeight(80)
        self.hex_edit.setStyleSheet("font-family: 'Courier New';")
        output_layout.addWidget(QLabel("十六进制格式:"))
        output_layout.addWidget(self.hex_edit)
        
        # C语言数组显示
        self.c_array_edit = QTextEdit()
        self.c_array_edit.setReadOnly(True)
        self.c_array_edit.setMaximumHeight(80)
        self.c_array_edit.setStyleSheet("font-family: 'Courier New';")
        output_layout.addWidget(QLabel("C语言数组格式:"))
        output_layout.addWidget(self.c_array_edit)
        
        # 详细信息与日志
        log_tab = QTabWidget()
        
        self.detail_edit = QTextEdit()
        self.detail_edit.setReadOnly(True)
        log_tab.addTab(self.detail_edit, "帧详细解析")
        
        self.log_edit = QTextEdit()
        self.log_edit.setReadOnly(True)
        self.log_edit.setStyleSheet("background-color: #1e1e1e; color: #d4d4d4;")
        log_tab.addTab(self.log_edit, "通信日志")
        
        output_layout.addWidget(log_tab)
        
        output_group.setLayout(output_layout)
        main_layout.addWidget(output_group)
        
        # 清除按钮
        self.clear_btn = QPushButton("清除")
        self.clear_btn.clicked.connect(self.clear_output)
        main_layout.addWidget(self.clear_btn)
        
        central_widget.setLayout(main_layout)
        
        # 默认值设置
        self.cmd_combo.setCurrentIndex(0)  # CMD_SET
        self.param_combo.setCurrentIndex(0)  # PARAM_POLE_PAIRS
        self.data_len_spin.setValue(4)
    
    def on_data_len_changed(self, value):
        """数据长度改变时的处理"""
        # 根据数据长度调整数据段的可用性
        for i, entry in enumerate(self.data_entries):
            if i < value:
                entry.setEnabled(True)
            else:
                entry.setEnabled(False)
    
    def refresh_ports(self):
        """刷新串口列表"""
        ports = [port.device for port in serial.tools.list_ports.comports()]
        self.port_combo.clear()
        self.port_combo.addItems(ports)
        
    def toggle_serial(self):
        """打开/关闭串口"""
        if self.serial and self.serial.is_open:
            self.serial.close()
            self.serial = None
            self.open_btn.setText("打开串口")
            self.send_btn.setEnabled(False)
            self.log("串口已关闭")
        else:
            try:
                port = self.port_combo.currentText()
                baud = int(self.baud_combo.currentText())
                if not port:
                    self.log("错误: 未选择串口")
                    return
                self.serial = serial.Serial(port, baud, timeout=1)
                self.open_btn.setText("关闭串口")
                if self.current_frame:
                    self.send_btn.setEnabled(True)
                self.log(f"成功连接串口: {port} (波特率: {baud})")
            except Exception as e:
                self.log(f"打开串口失败: {str(e)}")
                
    def send_frame(self):
        """发送生成的帧"""
        if self.serial and self.serial.is_open and self.current_frame:
            try:
                self.serial.write(self.current_frame)
                self.log(f"已发送: {ProtocolFrameGenerator.frame_to_hex_string(self.current_frame)}")
            except Exception as e:
                self.log(f"发送错误: {str(e)}")
        else:
            self.log("错误: 串口未打开或未生成帧")
            
    def log(self, message):
        """记录日志"""
        timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
        self.log_edit.append(f"[{timestamp}] {message}")
        # 自动滚动到底部
        self.log_edit.moveCursor(self.log_edit.textCursor().End)

    def generate_frame(self):
        """生成协议帧"""
        # 获取帧基本信息
        cmd = self.cmd_combo.currentData()
        param_id = self.param_combo.currentData()
        data_len = self.data_len_spin.value()
        
        # 获取数据段
        data = []
        for i in range(data_len):
            data.extend(self.data_entries[i].get_data())
        
        # 生成帧
        self.current_frame = ProtocolFrameGenerator.generate_frame(cmd, param_id, data_len, data)
        
        # 如果串口已打开，启用发送按钮
        if self.serial and self.serial.is_open:
            self.send_btn.setEnabled(True)
        
        # 显示结果
        hex_str = ProtocolFrameGenerator.frame_to_hex_string(self.current_frame)
        self.hex_edit.setText(hex_str)
        
        # C语言数组格式
        c_array = "uint8_t frame[] = {" + ', '.join(f'0x{b:02X}' for b in self.current_frame) + "};"
        self.c_array_edit.setText(c_array)
        
        # 详细信息
        detail = f"""
帧长度: {len(self.current_frame)} 字节
帧头 (SOF): 0x{self.current_frame[0]:02X}
命令字 (CMD): 0x{self.current_frame[1]:02X} ({CMD_NAMES.get(cmd, "Unknown")})
参数ID (PARAM_ID): 0x{self.current_frame[2]:02X} ({PARAM_NAMES.get(param_id, "Unknown")})
数据长度 (DATA_LEN): {self.current_frame[3]}
数据段: {' '.join(f'0x{b:02X}' for b in self.current_frame[4:16])}
校验和 (CHECKSUM): 0x{self.current_frame[16]:02X}
保留字节: 0x{self.current_frame[17]:02X} 0x{self.current_frame[18]:02X}
帧尾 (EOF): 0x{self.current_frame[19]:02X}
"""
        self.detail_edit.setText(detail.strip())
        self.log(f"已生成帧: {hex_str}")
    
    def clear_output(self):
        """清除输出"""
        self.hex_edit.clear()
        self.c_array_edit.clear()
        self.detail_edit.clear()
        self.log_edit.clear()
        self.current_frame = None
        self.send_btn.setEnabled(False)


def main():
    app = QApplication(sys.argv)
    window = FrameGeneratorWindow()
    window.show()
    sys.exit(app.exec_())


if __name__ == '__main__':
    main()
