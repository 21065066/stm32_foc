# -*- coding: utf-8 -*-
"""串口接收线程"""

import logging
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
        while self._running:
            frame = self._protocol_handler.read_frame()
            if frame:
                self.frame_received.emit(bytearray(frame))
                result = self._protocol_handler.parse_frame(frame)
                if result['success']:
                    self.param_updated.emit(result['param_id'], result['value'])
                else:
                    error_msg = result.get('error', '解析失败')
                    self.error_occurred.emit(error_msg)
                    logger.warning(f"帧解析失败: {error_msg}")

            # 检查串口是否断开
            if not self._serial_port.is_open:
                logger.warning("串口已断开")
                self.connection_lost.emit()
                break

        logger.info("接收线程停止")

    @property
    def is_running(self):
        """检查是否正在运行"""
        return self._running
