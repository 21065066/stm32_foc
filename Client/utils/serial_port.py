# -*- coding: utf-8 -*-
"""串口工具类"""

import logging
import serial
import serial.tools.list_ports


logger = logging.getLogger(__name__)


class SerialPort:
    """串口封装类"""

    def __init__(self):
        self.serial = None
        self._is_open = False

    @property
    def is_open(self):
        """检查串口是否打开"""
        return self._is_open and self.serial and self.serial.is_open

    @staticmethod
    def list_ports():
        """列出所有可用串口

        Returns:
            list: [(port_name, description), ...]
        """
        ports = []
        for port_info in serial.tools.list_ports.comports():
            ports.append((port_info.device, port_info.description or 'Unknown'))
        return ports

    def open(self, port, baudrate=115200, bytesize=serial.EIGHTBITS,
             parity=serial.PARITY_NONE, stopbits=serial.STOPBITS_ONE, timeout=0.1):
        """打开串口

        Args:
            port: 串口名 (如 'COM1')
            baudrate: 波特率
            bytesize: 数据位
            parity: 校验位
            stopbits: 停止位
            timeout: 读超时时间(秒)

        Returns:
            bool: 是否成功
        """
        try:
            if self.is_open:
                self.close()

            self.serial = serial.Serial(
                port=port,
                baudrate=baudrate,
                bytesize=bytesize,
                parity=parity,
                stopbits=stopbits,
                timeout=timeout
            )
            self._is_open = True
            logger.info(f"串口打开成功: {port} @ {baudrate}")
            return True

        except serial.SerialException as e:
            logger.error(f"串口打开失败: {e}")
            self._is_open = False
            return False

        except Exception as e:
            logger.error(f"串口打开异常: {e}")
            self._is_open = False
            return False

    def close(self):
        """关闭串口"""
        if self.serial and self.serial.is_open:
            try:
                self.serial.close()
                logger.info("串口已关闭")
            except Exception as e:
                logger.error(f"关闭串口时发生异常: {e}")
        self._is_open = False

    def write(self, data):
        """写入数据

        Args:
            data: 字节数据

        Returns:
            int: 写入的字节数
        """
        if not self.is_open:
            return 0

        try:
            if isinstance(data, bytearray):
                data = bytes(data)
            return self.serial.write(data)
        except Exception as e:
            logger.error(f"写入数据失败: {e}")
            return 0

    def read(self, size=1):
        """读取数据

        Args:
            size: 要读取的字节数

        Returns:
            bytes: 读取的数据
        """
        if not self.is_open:
            return b''

        try:
            return self.serial.read(size)
        except Exception as e:
            logger.error(f"读取数据失败: {e}")
            return b''

    def read_all(self):
        """读取所有可用数据

        Returns:
            bytes: 读取的数据
        """
        if not self.is_open:
            return b''

        try:
            return self.serial.read_all()
        except Exception as e:
            logger.error(f"读取数据失败: {e}")
            return b''

    def in_waiting(self):
        """返回接收缓冲区中的字节数

        Returns:
            int: 可读字节数
        """
        if not self.is_open:
            return 0

        try:
            return self.serial.in_waiting
        except Exception as e:
            logger.error(f"获取等待字节数失败: {e}")
            return 0

    def flush(self):
        """刷新缓冲区"""
        if self.is_open:
            try:
                self.serial.flush()
            except Exception as e:
                logger.error(f"刷新缓冲区失败: {e}")

    def __del__(self):
        """析构函数"""
        self.close()
