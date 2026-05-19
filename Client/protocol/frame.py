# -*- coding: utf-8 -*-
"""帧打包/解包"""

import struct
from .constants import SOF, EOF, FRAME_LENGTH


def calc_checksum(frame_bytes):
    """计算校验和: (CMD + PARAM_ID + DATA_LEN + DATA[0:12]) & 0xFF"""
    return sum(frame_bytes[1:16]) & 0xFF


def pack_frame(cmd, param_id, data=None, data_len=0):
    """打包帧

    帧结构 (20字节):
    字节:  0     1     2     3     4~15      16    17~18   19
         +-----+-----+-----+-----+----------+-----+--------+-----+
         | SOF | CMD | ID  | LEN | DATA(12) | CHK | RSV ×2 | EOF |
         +-----+-----+-----+-----+----------+-----+--------+-----+
          0xAA                              &0xFF    0      0x55

    Args:
        cmd: 命令字
        param_id: 参数ID
        data: 数据 (bytes/bytearray, 最大12字节)
        data_len: 数据长度

    Returns:
        bytearray: 20字节帧
    """
    frame = bytearray(FRAME_LENGTH)
    frame[0] = SOF  # 0xAA
    frame[1] = cmd
    frame[2] = param_id
    frame[3] = data_len

    if data:
        # 将数据复制到 DATA 区域
        if isinstance(data, bytes):
            data = bytearray(data)
        frame[4:4 + len(data)] = data[:12]

    # 计算校验和
    frame[16] = calc_checksum(frame)

    # 保留字 (17-18)
    frame[17] = 0
    frame[18] = 0

    # EOF
    frame[19] = EOF  # 0x55

    return frame


def unpack_frame(frame_bytes):
    """解包帧

    Args:
        frame_bytes: 原始字节数据

    Returns:
        dict: {
            'valid': bool,      # 帧是否有效
            'sof': int,         # 起始符
            'cmd': int,         # 命令字
            'param_id': int,    # 参数ID
            'data_len': int,    # 数据长度
            'data': bytearray,  # 数据
            'checksum': int,    # 校验和
            'error': str        # 错误信息
        }
    """
    result = {
        'valid': False,
        'sof': 0,
        'cmd': 0,
        'param_id': 0,
        'data_len': 0,
        'data': bytearray(),
        'checksum': 0,
        'error': ''
    }

    if len(frame_bytes) < FRAME_LENGTH:
        result['error'] = f'帧长度不足: 期望{FRAME_LENGTH}, 实际{len(frame_bytes)}'
        return result

    frame = frame_bytes[:FRAME_LENGTH]

    # 检查 SOF
    if frame[0] != SOF:
        result['error'] = f'SOF错误: 期望0x{SOF:02X}, 实际0x{frame[0]:02X}'
        return result

    # 检查 EOF
    if frame[19] != EOF:
        result['error'] = f'EOF错误: 期望0x{EOF:02X}, 实际0x{frame[19]:02X}'
        return result

    # 提取字段
    result['sof'] = frame[0]
    result['cmd'] = frame[1]
    result['param_id'] = frame[2]
    result['data_len'] = frame[3]
    result['data'] = bytearray(frame[4:4 + frame[3]])
    result['checksum'] = frame[16]

    # 验证校验和
    calc_chk = calc_checksum(frame)
    if calc_chk != result['checksum']:
        result['error'] = f'校验和不匹配: 计算{calc_chk:02X}, 帧内{result["checksum"]:02X}'
        return result

    result['valid'] = True
    return result


def int_to_bytes(value, length=4):
    """int转bytes (小端序)"""
    return value.to_bytes(length, byteorder='little')


def bytes_to_int(data, length=4):
    """bytes转int (小端序)"""
    if isinstance(data, bytearray):
        data = bytes(data)
    return int.from_bytes(data[:length], byteorder='little')


def float_to_bytes(value):
    """float转bytes"""
    return struct.pack('<f', value)


def bytes_to_float(data):
    """bytes转float"""
    if isinstance(data, bytearray):
        data = bytes(data)
    return struct.unpack('<f', data[:4])[0]


def pack_param_value(value, data_type):
    """打包参数值

    Args:
        value: 参数值
        data_type: 类型 ('int', 'float', 'float×3')

    Returns:
        tuple: (packed_data, data_len)
    """
    if data_type == 'int':
        data = int_to_bytes(int(value))
        return data, 4

    elif data_type == 'float':
        data = float_to_bytes(float(value))
        return data, 4

    elif data_type == 'float×3':
        # 3个float: Kp, Ki, Kd
        if len(value) != 3:
            raise ValueError("float×3 需要3个值")
        data = bytearray()
        for v in value:
            data.extend(float_to_bytes(float(v)))
        return data, 12

    else:
        raise ValueError(f"不支持的数据类型: {data_type}")


def unpack_param_value(data, data_len, data_type):
    """解包参数值

    Args:
        data: 原始数据
        data_len: 数据长度
        data_type: 类型

    Returns:
        解包后的值，如果 data_len 为 0 则返回 None
    """
    if data_len == 0:
        return None

    if data_type == 'int':
        return bytes_to_int(data, data_len)

    elif data_type == 'float':
        return bytes_to_float(data)

    elif data_type == 'float×3':
        values = []
        for i in range(3):
            if data_len >= (i + 1) * 4:
                values.append(bytes_to_float(data[i * 4:(i + 1) * 4]))
        return values

    else:
        raise ValueError(f"不支持的数据类型: {data_type}")
