# -*- coding: utf-8 -*-
"""协议常量定义"""

# 帧边界
SOF = 0xAA
EOF = 0x55
FRAME_LENGTH = 20

# 命令字
CMD_SET = 0x01
CMD_GET = 0x02
CMD_SET_ACK = 0x81
CMD_GET_ACK = 0x82
CMD_ERROR = 0xFF

# 参数定义 (param_id: (名称, 类型, 是否只读))
PARAMS = {
    # 硬件参数 (RW)
    0x01: ("极对数", "int", False),
    0x02: ("电流采样电阻(Ω)", "float", False),
    0x03: ("运放放大倍数", "float", False),
    0x04: ("最大Q轴电流(A)", "float", False),
    0x05: ("ADC参考电压(V)", "float", False),
    0x06: ("PWM频率(Hz)", "int", False),
    0x07: ("速度计算频率(Hz)", "int", False),
    0x08: ("ADC精度(bit)", "int", False),
    0x09: ("多圈周期", "float", False),

    # PID参数 (RW) - 3个float (Kp, Ki, Kd)
    0x20: ("Position PID", "float×3", False),
    0x21: ("Speed PID", "float×3", False),
    0x22: ("Torque D PID", "float×3", False),
    0x23: ("Torque Q PID", "float×3", False),

    # 目标值 (RW)
    0x41: ("控制类型", "int", False),
    0x42: ("目标角度(rad)", "float", False),
    0x43: ("目标速度(rad/s)", "float", False),
    0x44: ("目标转矩D轴", "float", False),
    0x45: ("目标转矩Q轴", "float", False),

    # 反馈值 (R)
    0x60: ("U相电流(A)", "float", True),
    0x61: ("V相电流(A)", "float", True),
    0x62: ("D轴电流(A)", "float", True),
    0x63: ("Q轴电流(A)", "float", True),
    0x64: ("电机转速(rad/s)", "float", True),
    0x65: ("电机多圈角度(rad)", "float", True),
    0x66: ("编码器角度(rad)", "float", True),
    0x67: ("编码器初始角度(rad)", "float", True),
    0x68: ("转子零位角度(rad)", "float", True),
}


def get_param_info(param_id):
    """获取参数信息"""
    return PARAMS.get(param_id, (None, None, None))


def is_readonly(param_id):
    """判断参数是否只读"""
    info = get_param_info(param_id)
    return info[2] if info else True


def get_param_name(param_id):
    """获取参数名称"""
    info = get_param_info(param_id)
    return info[0] if info else None


def get_param_type(param_id):
    """获取参数类型"""
    info = get_param_info(param_id)
    return info[1] if info else None
