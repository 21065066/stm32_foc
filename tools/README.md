# STM32电机控制器参数协议测试工具

## 功能说明

这是一个基于PyQt5开发的串口协议测试工具，用于测试STM32电机控制器的参数读写协议。

### 主要功能

1. **串口连接管理**
   - 自动扫描可用串口
   - 支持多种波特率（9600, 115200, 230400, 460800）
   - 实时日志显示

2. **参数读取**
   - 支持读取所有电机参数
   - 实时显示当前参数值

3. **参数设置**
   - 支持设置所有可写参数
   - 支持float类型参数输入

4. **协议调试**
   - 手动构建和发送协议帧
   - 自动解析接收到的协议帧
   - 协议帧详细解析显示

## 支持的参数

### 硬件参数
- 极对数 (POLE_PAIRS)
- 电流采样电阻 (R_SHUNT)
- 运放放大倍数 (OP_GAIN)
- 最大Q轴电流 (MAX_CURRENT)
- ADC参考电压 (ADC_REF_VOLT)

### 配置参数
- PWM频率 (PWM_FREQ)
- 速度计算频率 (SPEED_CALC_FREQ)

### PID参数
- 位置PID (Kp, Ki, Kd)
- 速度PID (Kp, Ki, Kd)
- 转矩D轴PID (Kp, Ki, Kd)
- 转矩Q轴PID (Kp, Ki, Kd)

## 安装依赖

```bash
pip install -r requirements.txt
```

或手动安装：

```bash
pip install PyQt5 pyserial
```

## 使用方法

1. 运行程序：
   ```bash
   python protocol_tester.py
   ```

2. 选择串口和波特率（默认115200）

3. 点击"连接"按钮建立串口连接

4. 在"参数读取"或"参数设置"标签页进行操作

5. 在"协议调试"标签页可以手动发送和解析协议帧

## 协议格式

### 帧结构

| 字节 | 长度 | 字段 | 说明 |
|------|------|------|------|
| 0 | 1 | SOF | 帧头 (0xAA) |
| 1 | 1 | CMD | 命令字 |
| 2 | 1 | PARAM_ID | 参数ID |
| 3 | 1 | DATA_LEN | 数据长度 |
| 4~N | N | DATA | 数据 |
| N+1 | 1 | CHECKSUM | 校验和 |
| N+2 | 1 | EOF | 帧尾 (0x55) |

### 校验和计算

```
CHECKSUM = (CMD + PARAM_ID + DATA_LEN + DATA[0] + ... + DATA[N-1]) & 0xFF
```

### 命令字

| CMD | 名称 | 说明 |
|-----|------|------|
| 0x01 | CMD_SET | 设置参数 |
| 0x02 | CMD_GET | 读取参数 |
| 0x81 | CMD_SET_ACK | 设置成功确认 |
| 0x82 | CMD_GET_ACK | 读取响应 |
| 0xFF | CMD_ERROR | 错误响应 |

## 注意事项

1. 确保STM32端的串口配置与工具一致（波特率115200）
2. 数据传输使用小端序（Little-Endian）
3. Float类型数据占4字节
4. 校验和计算不包含SOF和EOF

## 许可证

MIT License
