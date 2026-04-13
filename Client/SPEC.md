# STM32 FOC 电机控制器客户端 - 软件设计文档

## 1. 概述

### 1.1 项目背景
基于 STM32 FOC 电机控制器的上位机客户端，用于通过串口连接控制器，实现参数的读取、写入和实时监控。

### 1.2 技术选型
| 项目 | 选择 |
|------|------|
| 语言 | Python 3.8+ |
| GUI框架 | PyQt5 |
| 串口通信 | PySerial |
| 图表库 | PyQtGraph (实时折线图) |
| 打包工具 | PyInstaller |

### 1.3 功能需求
- 串口连接/断开
- 读取/写入所有电机参数
- 实时数据显示
- 参数按权限分类显示（只读/可读写）
- 实时曲线显示（转速、电流、角度等）

---

## 2. 界面设计

### 2.1 整体布局 (左右分栏)

```
┌───────────────────────────────────────────────────────────┬─────────────────────────────────────────┐
│                          连接控制区                        │                                         │
│  [串口选择 ▼] [波特率 ▼] [连接] [断开]    状态: ● 已连接     │                                         │
├───────────────────────────────────────────────────────────┼─────────────────────────────────────────┤
│                                                           │                                         │
│  参数控制面板 (左侧 60%)                                    │   数据可视化面板 (右侧 40%)              │
│  (QScrollArea 垂直滚动)                                    │   (QWidget 图表区域)                     │
│                                                           │                                         │
│  ┌─ 硬件参数 ───────────────────────┐                     │   ┌─ 实时曲线 ───────────────────────┐   │
│  │ 极对数          [7   ] [读取][设置]│                    │   │                                 │   │
│  │ 电流采样电阻    [0.02] [读取][设置]│                    │   │  [折线图: 转速 / 电流 / 角度]     │   │
│  │ 运放放大倍数    [50.0] [读取][设置]│                    │   │                                 │   │
│  │ 最大Q轴电流     [2.0 ] [读取][设置]│                    │   │  Y轴: 数值                       │   │
│  │ ADC参考电压     [3.3 ] [读取][设置]│                    │   │  X轴: 时间 (秒)                  │   │
│  │ PWM频率        [40000] [读取][设置]│                    │   │                                 │   │
│  │ 速度计算频率   [930  ] [读取][设置]│                    │   │  ~~~曲线绘制区域~~~              │   │
│  │ ADC精度        [12   ] [读取][设置]│                    │   │                                 │   │
│  │ 多圈周期       [18.85] [读取][设置]│                    │   └─────────────────────────────────┘   │
│  └──────────────────────────────────┘                     │                                         │
│                                                           │   ┌─ 曲线选择 ──────────────────────┐   │
│  ┌─ PID参数 ────────────────────────────────────────┐     │   │ ☑ 电机转速  ☑ D轴电流           │   │
│  │ Position PID Kp[3.5] Ki[0] Kd[7]   [读取][设置] │      │   │ ☑ Q轴电流  ☐ 电机角度           │   │
│  │ Speed PID     Kp[0.02] Ki[0.001]   [读取][设置] │      │   │ ☐ U相电流  ☐ V相电流            │   │
│  │ Torque D PID  Kp[1.2]  Ki[0.02]   [读取][设置] │       │   │                                 │   │
│  │ Torque Q PID  Kp[1.2]  Ki[0.02]   [读取][设置] │       │   │ [开始采集] [停止采集] [清空]      │   │
│  └──────────────────────────────────────────────────┘     │   └─────────────────────────────────┘   │
│                                                           │                                         │
│  ┌─ 目标值 ───────────────────────────────────────┐       │                                         │
│  │ 控制类型      [2  ] [读取][设置]                │       │                                         │
│  │ 目标角度      [0  ] [读取][设置]                │       │                                         │
│  │ 目标速度      [10 ] [读取][设置]                │       │                                         │
│  │ 目标转矩D轴   [0  ] [读取][设置]                │       │                                         │
│  │ 目标转矩Q轴   [0.4] [读取][设置]                │       │                                         │
│  └────────────────────────────────────────────────┘       │                                         │
│                                                           │                                         │
│  ┌─ 反馈值 (只读) ─────────────────────────────────┐       │                                         │
│  │ U相电流: 0.00 A           [读取]               │       │                                         │
│  │ V相电流: 0.00 A           [读取]               │       │                                         │
│  │ D轴电流: 0.00 A           [读取]               │       │                                         │
│  │ Q轴电流: 0.00 A           [读取]               │       │                                         │
│  │ 电机转速: 0.00 rad/s      [读取]               │       │                                         │
│  │ 电机角度: 0.00 rad        [读取]               │       │                                         │
│  │ 编码器角度: 0.00 rad      [读取]               │       │                                          │
│  └────────────────────────────────────────────────┘       │                                         │
│                                                           │                                         │
├───────────────────────────────────────────────────────────┴─────────────────────────────────────────┤
│  日志区 (固定高度 150px)                                                                             │
│  10:00:00 [发送] AA 02 01 00 00 00 00 00 00 00 00 00 00 00 00 00 00 03 00 55                        │
│  10:00:00 [接收] AA 82 01 04 00 00 00 00 00 00 00 00 00 00 00 00 00 07 00 55                        │
└─────────────────────────────────────────────────────────────────────────────────────────────────────┘
```

## 3. 模块设计

### 3.1 类图

```
MainWindow (QMainWindow)
├── SerialPanel        # 串口连接控制面板
│   ├── port_combo     # 串口选择下拉框
│   ├── baud_combo    # 波特率选择
│   ├── connect_btn   # 连接按钮
│   ├── disconnect_btn# 断开按钮
│   └── status_label  # 连接状态标签
│
├── QWidget (中央widget)
│   └── QSplitter (Qt::Horizontal 左右分割)
│       │
│       ├── QWidget (左侧) 参数面板
│       │   └── ParameterPanel (QScrollArea)
│       │       ├── HardwareParamGroup    # 硬件参数组
│       │       │   └── ParamWidget × 9
│       │       ├── PidParamGroup         # PID参数组
│       │       │   └── ParamWidget × 4
│       │       ├── TargetParamGroup      # 目标值组
│       │       │   └── ParamWidget × 5
│       │       └── FeedbackParamGroup    # 反馈值组(只读)
│       │           └── ParamWidget × 9
│       │
│       └── QWidget (右侧) 图表面板
│           └── ChartPanel
│               ├── PlotWidget (pyqtgraph) # 折线图控件
│               ├── curve_checkboxes[]      # 曲线选择复选框
│               ├── btn_start              # 开始采集按钮
│               ├── btn_stop              # 停止采集按钮
│               └── btn_clear             # 清空数据按钮
│
├── LogPanel           # 日志面板 (底部固定高度)
│   └── log_textedit   # 日志文本框
│
└── ProtocolHandler    # 协议处理类(非UI)
    ├── send_frame()   # 发送帧
    ├── parse_frame()  # 解析接收帧
    └── checksum_calc()# 校验和计算
```

### 3.2 ParamWidget 参数行组件

每个参数行组件包含:
```python
class ParamWidget(QWidget):
    label_name: QLabel           # 参数名称 (左侧固定宽度)
    spin_box: QSpinBox          # int类型参数值输入框
    double_spin_box: QDoubleSpinBox  # float类型参数值输入框
    kp_spin: QDoubleSpinBox     # float×3类型的Kp输入框
    ki_spin: QDoubleSpinBox     # float×3类型的Ki输入框
    kd_spin: QDoubleSpinBox     # float×3类型的Kd输入框
    btn_read: QPushButton       # 读取按钮
    btn_write: QPushButton      # 设置按钮 (只读参数无此按钮)
    param_id: int               # 参数ID
    data_type: str              # "int" / "float" / "float×3"
    is_readonly: bool           # 是否只读
```

---

## 4. 协议实现

### 4.1 帧结构 (20字节)

```
字节:  0     1     2     3     4~15      16    17~18   19
     +-----+-----+-----+-----+----------+-----+--------+-----+
     | SOF | CMD | ID  | LEN | DATA(12) | CHK | RSV ×2 | EOF |
     +-----+-----+-----+-----+----------+-----+--------+-----+
      0xAA                              &0xFF    0      0x55
```

### 4.2 协议常量定义

```python
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
```

### 4.3 校验和计算

```python
def calc_checksum(frame_bytes):
    """计算校验和: (CMD + PARAM_ID + DATA_LEN + DATA[0:12]) & 0xFF"""
    return sum(frame_bytes[1:16]) & 0xFF
```

---

## 5. 文件结构

```
Client/
├── main.py              # 程序入口
├── SPEC.md              # 本文档
├── ui/
│   ├── __init__.py
│   ├── main_window.py   # 主窗口
│   ├── serial_panel.py  # 串口面板
│   ├── param_panel.py   # 参数面板
│   ├── param_widget.py  # 参数行组件
│   ├── chart_panel.py   # 图表面板
│   ├── log_panel.py     # 日志面板
│   └── slider_config_dialog.py  # 滑动条配置对话框
├── protocol/
│   ├── __init__.py
│   ├── constants.py     # 协议常量
│   ├── frame.py         # 帧打包/解包
│   └── handler.py       # 协议处理器
├── utils/
│   ├── __init__.py
│   ├── serial_port.py   # 串口工具类
│   └── config_manager.py # 配置管理
├── data/
│   ├── __init__.py
│   └── data_collector.py # 数据采集器(环形缓冲区)
└── requirements.txt
    # PyQt5
    # pyserial
    # pyqtgraph
    # numpy
```

---

## 6. 数据采集器设计

```python
class DataCollector:
    """数据采集器 - 环形缓冲区"""

    CURVE_KEYS = ['motor_speed', 'current_d', 'current_q',
                  'motor_angle', 'current_u', 'current_v']

    def __init__(self, max_points=1000):
        self.max_points = max_points
        self.timestamps = deque(maxlen=max_points)
        self.data = {key: deque(maxlen=max_points) for key in self.CURVE_KEYS}

    def append(self, timestamp, feedback_data):
        """添加一组数据点"""
        self.timestamps.append(timestamp)
        for key in self.CURVE_KEYS:
            if key in feedback_data:
                self.data[key].append(feedback_data[key])
            else:
                self.data[key].append(None)

    def get_data(self, *keys):
        """获取指定曲线的数据"""
        return list(self.timestamps), [self.data[k] for k in keys]

    def clear(self):
        """清空所有数据"""
        self.timestamps.clear()
        for d in self.data.values():
            d.clear()
```

---

## 7. 数据流

```
[串口接收数据]
    ↓
ProtocolHandler.parse_frame() → 解析反馈参数值
    ↓
┌───────────────────────────────────────┐
│           数据分发                     │
├───────────────────────────────────────┤
│  1. ParamWidget.update_value()         │ → 更新参数显示
│  2. DataCollector.append()            │ → 添加到数据缓冲区
│  3. ChartPanel.update_plot()          │ → 刷新曲线图
└───────────────────────────────────────┘
    ↓
[日志区显示接收帧]
```

### 7.1 采集模式

**轮询模式** (图表采集时):
- 每隔 100ms 发送 CMD_GET (0x64 电机转速) 等反馈参数
- 持续获取反馈数据用于图表显示

**停止采集**:
- 暂停轮询发送
- 图表保持当前数据

---

## 8. 错误处理

| 错误类型 | 处理方式 |
|----------|----------|
| 串口打开失败 | 弹窗提示 "串口被占用或不存在" |
| 校验和不匹配 | 日志显示红色错误帧，可选择重发 |
| 参数ID不存在 | 日志显示 "未知参数ID" |
| 串口断开 | 自动切换UI为断开状态，弹窗提示 |

---

## 9. 验收标准

1. **串口连接**: 可扫描并列出所有可用串口，成功打开/关闭
2. **参数显示**: 4个分组的所有参数完整显示，权限正确
3. **读取功能**: 点击读取按钮，2秒内获得响应并更新界面
4. **设置功能**: 设置参数后，电机行为有明显变化
5. **日志记录**: 发送/接收的每一帧都记录到日志区
6. **图表显示**: 至少支持6条曲线同时显示，流畅刷新
7. **稳定性**: 连续运行1小时无崩溃

---

## 10. 配置管理

配置文件位于: `~/.stm32_foc_client/config.json` (JSON格式)

### 10.1 配置内容
| 配置项 | 说明 |
|--------|------|
| serial_port | 上次使用的串口设备名 |
| baudrate | 上次使用的波特率 |
| param_xx | 各参数ID对应的值 (xx为十六进制) |
| slider_range_xx | 滑动条范围配置 [min, max] |

### 10.2 配置加载/保存时机
- **加载**: 程序启动时恢复串口设置，连接成功后加载参数值到界面
- **保存**: 设置参数时自动保存，程序退出时保存

### 10.3 滑动条配置对话框
点击 "滑动条配置" 按钮打开对话框，可配置以下参数的范围：
- 硬件参数: 电流采样电阻、运放放大倍数、最大Q轴电流、ADC参考电压、PWM频率、速度计算频率、ADC精度、多圈周期
- 目标值: 目标角度、目标速度、目标转矩D轴、目标转矩Q轴

对话框包含:
- 最小值/最大值的 SpinBox 编辑
- 保存按钮: 保存配置并应用到界面
- 取消按钮: 取消更改
- 重置按钮: 恢复到默认值

---

## 11. 后续扩展 (可选)

- [ ] 多电机控制 (同时连接多个串口)
- [x] 参数配置文件 (保存/加载常用配置) - 已实现
- [ ] 自动重连机制
- [ ] 数据导出 (CSV格式)
