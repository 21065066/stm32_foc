# -*- coding: utf-8 -*-
"""串口接收线程"""

import logging
import time
from PyQt5.QtCore import QObject, pyqtSignal

logger = logging.getLogger(__name__)


class SerialReader(QObject):
    """串口接收线程类

    使用 Worker + moveToThread 模式，在后台线程持续监听串口数据，
    收到完整帧后解析并通过信号通知主线程。
    """

    # 信号: 收到完整帧（供日志显示）
    frame_received = pyqtSignal(bytearray)

    # 信号: 参数更新（param_id, value）
    param_updated = pyqtSignal(int, object)

    # 信号: 错误发生
    error_occurred = pyqtSignal(str)

    # 信号: 连接断开
    connection_lost = pyqtSignal()

    # 信号: 收到 DATA: 格式的数据行 (dict)
    data_line_received = pyqtSignal(dict)

    def __init__(self, serial_port, protocol_handler):
        """初始化接收线程

        Args:
            serial_port: SerialPort 实例
            protocol_handler: ProtocolHandler 实例
        """
        super().__init__()
        self._serial_port = serial_port
        self._protocol_handler = protocol_handler
        self._running = False

    def start_reader(self):
        """启动读取循环（在后台线程中调用）"""
        self._running = True
        self._read_loop()

    def stop_reader(self):
        """停止读取循环"""
        self._running = False

    def _read_loop(self):
        """后台线程主循环"""
        logger.info("接收线程启动")
        buffer = b""
        while self._running:
            try:
                if self._serial_port.in_waiting() > 0:
                    new_data = self._serial_port.read(self._serial_port.in_waiting())
                    buffer += new_data

                    # 处理逻辑：
                    # 1. 检查是否有完整的二进制帧 (以 0xAA 开头, 20字节)
                    # 2. 检查是否有完整的文本行 (以 \n 结尾)
                    
                    while len(buffer) > 0:
                        # 尝试寻找二进制帧头
                        if buffer[0] == 0xAA:
                            if len(buffer) >= 20:
                                frame = buffer[:20]
                                buffer = buffer[20:]
                                self._process_binary_frame(frame)
                                continue
                            else:
                                # 等待更多数据以组成完整帧
                                break
                        
                        # 尝试寻找换行符
                        elif b'\n' in buffer:
                            line_bytes, buffer = buffer.split(b'\n', 1)
                            try:
                                line = line_bytes.decode('utf-8', errors='ignore').strip()
                                if line.startswith("DATA:"):
                                    self._process_data_line(line)
                                elif line:
                                    logger.info(f"收到普通文本: {line}")
                            except Exception as e:
                                logger.error(f"处理文本行失败: {e}")
                            continue
                        
                        else:
                            # 如果既不是以 0xAA 开头，也没有换行符
                            # 尝试寻找下一个可能的起点 (0xAA 或 \n)
                            next_aa = buffer.find(b'\xaa', 1)
                            next_nl = buffer.find(b'\n', 1)
                            
                            # 确定最近的一个起点
                            potential_starts = [pos for pos in [next_aa, next_nl] if pos != -1]
                            
                            if potential_starts:
                                # 丢弃到最近的起点之前的所有内容
                                buffer = buffer[min(potential_starts):]
                            elif len(buffer) > 1024:
                                # 没找到起点且 buffer 太长，清空
                                buffer = b""
                            break
                else:
                    time.sleep(0.005)

                # 检查串口是否断开
                if not self._serial_port.is_open:
                    logger.warning("串口已断开")
                    self.connection_lost.emit()
                    break

            except Exception as e:
                logger.error(f"读取循环异常: {e}")
                time.sleep(0.1)

        logger.info("接收线程停止")

    def _process_binary_frame(self, frame):
        """处理二进制帧"""
        self.frame_received.emit(bytearray(frame))
        result = self._protocol_handler.parse_frame(frame)
        if result['success']:
            self.param_updated.emit(result['param_id'], result['value'])
        else:
            error_msg = result.get('error', '解析失败')
            self.error_occurred.emit(error_msg)
            logger.warning(f"帧解析失败: {error_msg}")

    def _process_data_line(self, line):
        """处理 DATA: 格式的数据行"""
        try:
            data_str = line[5:]
            values = [v.strip() for v in data_str.split(',')]
            if len(values) == 6:
                data_dict = {
                    'motor_speed': float(values[0]),
                    'current_d': float(values[1]),
                    'current_q': float(values[2]),
                    'motor_angle': float(values[3]),
                    'current_u': float(values[4]),
                    'current_v': float(values[5]),
                }
                self.data_line_received.emit(data_dict)
        except Exception as e:
            logger.error(f"解析 DATA 行失败: {e}, 原始行: {line}")

    @property
    def is_running(self):
        """检查是否正在运行"""
        return self._running
