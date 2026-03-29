# STM32 电机控制器通信协议测试指南

## 协议概述

本协议基于 UART 串口通信，用于上位机与 STM32 电机控制器之间的参数读写。

### 通信参数
- 波特率：115200
- 数据位：8
- 停止位：1
- 校验：无
- 字节序：小端（Little-Endian）

## 帧格式

### 通用帧结构
| 字节偏移 | 长度    | 字段名       | 说明                              |
|----------|---------|--------------|-----------------------------------|
| 0        | 1 Byte  | SOF          | 帧头，固定 `0xAA`                 |
| 1        | 1 Byte  | CMD          | 命令字                            |
| 2        | 1 Byte  | PARAM_ID     | 参数 ID                           |
| 3        | 1 Byte  | DATA_LEN     | 数据段字节数（0 表示无数据）      |
| 4 ~ N    | N Bytes | DATA         | 数据段（float 为 4 字节，小端）   |
| N+1      | 1 Byte  | CHECKSUM     | 校验和                            |
| N+2      | 1 Byte  | EOF          | 帧尾，固定 `0x55`                 |

## 命令字（CMD）

| CMD 值 | 名称             | 方向         | 说明                          |
|--------|------------------|--------------|-------------------------------|
| 0x01   | CMD_SET          | 上位机 → STM32 | 设置参数                      |
| 0x02   | CMD_GET          | 上位机 → STM32 | 请求读取参数                  |
| 0x81   | CMD_SET_ACK      | STM32 → 上位机 | 设置成功确认                  |
| 0x82   | CMD_GET_ACK      | STM32 → 上位机 | 读取响应（携带参数值）        |
| 0xFF   | CMD_ERROR        | STM32 → 上位机 | 错误响应                      |

## 参数 ID 表（PARAM_ID）

所有参数值均以 IEEE 754 单精度浮点（float，4字节，小端）传输。

### 硬件参数
| PARAM_ID | 参数名称                   | 单位   | 说明                    |
|----------|----------------------------|--------|-------------------------|
| 0x01     | 极对数                     | 无     | 整数值存为 float        |
| 0x02     | 电流采样电阻               | Ω      |                         |
| 0x03     | 运放放大倍数               | 无     |                         |
| 0x04     | 最大 Q 轴电流              | A      |                         |
| 0x05     | 电流采样 ADC 参考电压      | V      |                         |
| 0x06     | 驱动桥 PWM 频率            | Hz     |                         |
| 0x07     | 电机速度计算频率            | Hz     |                         |

### PID 参数
| PARAM_ID | 参数名称                   | 单位   | 说明                    |
|----------|----------------------------|--------|-------------------------|
| 0x10     | Position PID — Kp          | 无     |                         |
| 0x11     | Position PID — Ki          | 无     |                         |
| 0x12     | Position PID — Kd          | 无     |                         |
| 0x20     | Speed PID — Kp             | 无     |                         |
| 0x21     | Speed PID — Ki             | 无     |                         |
| 0x22     | Speed PID — Kd             | 无     |                         |
| 0x30     | Torque D PID — Kp          | 无     |                         |
| 0x31     | Torque D PID — Ki          | 无     |                         |
| 0x32     | Torque D PID — Kd          | 无     |                         |
| 0x40     | Torque Q PID — Kp          | 无     |                         |
| 0x41     | Torque Q PID — Ki          | 无     |                         |
| 0x42     | Torque Q PID — Kd          | 无     |                         |

## 交互流程

### 1. 设置参数（写）
```
上位机 → STM32:  AA 01 PARAM_ID 04 [float 4字节] CHECKSUM 55
STM32  → 上位机:  AA 81 PARAM_ID 00 CHECKSUM 55   ← 成功 ACK
               或: AA FF PARAM_ID 01 [ERR_CODE] CHECKSUM 55  ← 失败
```

### 2. 读取参数（读）
```
上位机 → STM32:  AA 02 PARAM_ID 00 CHECKSUM 55
STM32  → 上位机:  AA 82 PARAM_ID 04 [float 4字节] CHECKSUM 55  ← 携带参数值
               或: AA FF PARAM_ID 01 [ERR_CODE] CHECKSUM 55    ← 失败
```

## 校验和计算规则

```
CHECKSUM = (CMD + PARAM_ID + DATA_LEN + DATA[0] + ... + DATA[N-1]) & 0xFF
```

注意：SOF（0xAA）和 EOF（0x55）不参与校验计算。

## 错误码（ERR_CODE，1 Byte）

| 错误码 | 含义                       |
|--------|----------------------------|
| 0x01   | 未知参数 ID                |
| 0x02   | 数据长度错误               |
| 0x03   | 校验和错误                 |
| 0x04   | 参数值超出范围             |
| 0x05   | 帧格式错误（SOF/EOF 异常）|

## 测试示例

### 示例1：读取极对数（PARAM_ID = 0x01）
发送帧：`AA 02 01 00 02 55`
- SOF: 0xAA
- CMD: 0x02 (CMD_GET)
- PARAM_ID: 0x01
- DATA_LEN: 0x00
- CHECKSUM: 0x02 (0x02 + 0x01 + 0x00)
- EOF: 0x55

预期响应：`AA 82 01 04 [7.0的float值] CHECKSUM 55`

### 示例2：设置Speed PID Kp（PARAM_ID = 0x20，值为2.5）
发送帧：`AA 01 20 04 [0x00 0x00 0x20 0x40] 65 55`
- SOF: 0xAA
- CMD: 0x01 (CMD_SET)
- PARAM_ID: 0x20
- DATA_LEN: 0x04
- DATA: 0x00 0x00 0x20 0x40 (float 2.5 的小端表示)
- CHECKSUM: 0x65 (0x01 + 0x20 + 0x04 + 0x00 + 0x00 + 0x20 + 0x40)
- EOF: 0x55

预期响应：`AA 81 20 00 A1 55`
- SOF: 0xAA
- CMD: 0x81 (CMD_SET_ACK)
- PARAM_ID: 0x20
- DATA_LEN: 0x00
- CHECKSUM: 0xA1 (0x81 + 0x20 + 0x00)
- EOF: 0x55

## 编译说明

在 Keil 中添加以下文件到项目：
1. Core/Src/protocol.c
2. Core/Inc/protocol.h

确保 protocol.c 已添加到编译列表中。

## 注意事项

1. 所有浮点数使用 IEEE 754 单精度格式（4字节）
2. 字节序为小端（Little-Endian）
3. 每次通信都会收到 ACK 确认或错误响应
4. DMA 接收缓冲区大小为 128 字节，支持最大 32 字节数据的帧
5. 协议使用空闲中断检测帧结束