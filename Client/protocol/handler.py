# -*- coding: utf-8 -*-
"""协议处理器"""

import logging
from .constants import CMD_SET, CMD_GET, CMD_SET_ACK, CMD_GET_ACK, CMD_ERROR
from .frame import pack_frame, unpack_frame, pack_param_value, unpack_param_value, calc_checksum


logger = logging.getLogger(__name__)


class ProtocolHandler:
    """协议处理器"""

    def __init__(self, serial_port=None):
        self.serial_port = serial_port
        self.pending_requests = {}  # param_id -> callback
        self.feedback_callback = None

    def set_serial_port(self, serial_port):
        """设置串口"""
        self.serial_port = serial_port

    def set_feedback_callback(self, callback):
        """设置反馈数据回调

        Args:
            callback: 回调函数, 签名: callback(param_id, value)
        """
        self.feedback_callback = callback

    def register_request(self, param_id, callback):
        """注册请求回调 (用于等待响应)"""
        self.pending_requests[param_id] = callback

    def unregister_request(self, param_id):
        """取消注册请求回调"""
        if param_id in self.pending_requests:
            del self.pending_requests[param_id]

    def build_read_frame(self, param_id):
        """构建读取帧

        Args:
            param_id: 参数ID

        Returns:
            bytearray: 20字节帧
        """
        return pack_frame(CMD_GET, param_id)

    def build_write_frame(self, param_id, value, data_type):
        """构建写入帧

        Args:
            param_id: 参数ID
            value: 参数值
            data_type: 数据类型

        Returns:
            bytearray: 20字节帧
        """
        data, data_len = pack_param_value(value, data_type)
        return pack_frame(CMD_SET, param_id, data, data_len)

    def send_frame(self, frame):
        """发送帧

        Args:
            frame: 字节数据

        Returns:
            bool: 是否发送成功
        """
        if not self.serial_port or not self.serial_port.is_open:
            logger.error("串口未打开")
            return False

        try:
            self.serial_port.write(frame)
            return True
        except Exception as e:
            logger.error(f"发送帧失败: {e}")
            return False

    def read_frame(self):
        """读取一帧数据

        Returns:
            bytearray or None: 帧数据
        """
        if not self.serial_port or not self.serial_port.is_open:
            return None

        try:
            # 等待 SOF (0xAA)
            while True:
                byte = self.serial_port.read(1)
                if not byte:
                    return None
                if byte[0] == 0xAA:
                    break

            # 读取剩余 19 字节
            data = bytearray([0xAA])
            remaining = self.serial_port.read(19)
            if len(remaining) < 19:
                return None

            data.extend(remaining)
            return bytes(data)

        except Exception as e:
            logger.error(f"读取帧失败: {e}")
            return None

    def send_and_wait_response(self, frame, param_id, timeout=2.0):
        """发送帧并等待响应

        Args:
            frame: 要发送的帧
            param_id: 参数ID (用于匹配响应)
            timeout: 超时时间(秒)

        Returns:
            tuple: (success, response_data)
        """
        import time

        if not self.send_frame(frame):
            return False, "发送失败"

        start_time = time.time()

        while time.time() - start_time < timeout:
            raw_frame = self.read_frame()
            if not raw_frame:
                time.sleep(0.01)
                continue

            result = unpack_frame(raw_frame)
            if not result['valid']:
                logger.warning(f"无效帧: {result['error']}")
                continue

            # 检查是否是针对该param_id的响应
            if result['param_id'] != param_id:
                continue

            cmd = result['cmd']
            if cmd == CMD_GET_ACK:
                return True, result
            elif cmd == CMD_ERROR:
                return False, f"错误响应: param_id=0x{param_id:02X}"
            else:
                return False, f"未知响应命令: 0x{cmd:02X}"

        return False, "超时"

    def parse_frame(self, raw_frame):
        """解析帧

        Args:
            raw_frame: 原始帧数据

        Returns:
            dict: 解析结果
        """
        result = unpack_frame(raw_frame)

        if not result['valid']:
            return {'success': False, 'error': result['error']}

        cmd = result['cmd']
        param_id = result['param_id']
        data = result['data']
        data_len = result['data_len']

        # 获取参数类型
        from .constants import get_param_type, PARAMS
        if param_id not in PARAMS:
            return {'success': False, 'error': f'未知参数ID: 0x{param_id:02X}'}

        param_name, data_type, is_readonly = PARAMS[param_id]

        # 解析数据
        try:
            value = unpack_param_value(data, data_len, data_type)
        except Exception as e:
            return {'success': False, 'error': f'数据解析失败: {e}'}

        return {
            'success': True,
            'cmd': cmd,
            'param_id': param_id,
            'param_name': param_name,
            'data_type': data_type,
            'value': value,
            'is_readonly': is_readonly
        }

    def handle_received_frame(self, raw_frame):
        """处理接收到的帧

        Args:
            raw_frame: 原始帧数据

        Returns:
            dict: 解析结果
        """
        result = self.parse_frame(raw_frame)

        if not result['success']:
            logger.warning(f"帧解析失败: {result.get('error')}")
            return result

        # 回调反馈数据
        if self.feedback_callback:
            try:
                self.feedback_callback(result['param_id'], result['value'])
            except Exception as e:
                logger.error(f"反馈回调执行失败: {e}")

        return result

    def get_readable_frame_str(self, frame_bytes):
        """获取可读的帧字符串

        Args:
            frame_bytes: 帧数据

        Returns:
            str: 十六进制字符串
        """
        if isinstance(frame_bytes, bytearray):
            frame_bytes = bytes(frame_bytes)
        return ' '.join(f'{b:02X}' for b in frame_bytes)
