# -*- coding: utf-8 -*-
"""
纯粹的串口读取和解析脚本
用于验证 DATA: 格式数据的接收
"""

import serial
import serial.tools.list_ports
import time

def list_available_ports():
    """列出所有可用串口"""
    ports = serial.tools.list_ports.comports()
    return [port.device for port in ports]

def main():
    # 1. 自动寻找或手动指定串口
    available_ports = list_available_ports()
    if not available_ports:
        print("未发现可用串口！")
        return

    print("可用串口列表:")
    for i, port in enumerate(available_ports):
        print(f"{i}: {port}")
    
    # 默认选择第一个，或者你可以手动修改这里
    port_index = 0
    port_name = available_ports[port_index]
    baudrate = 115200

    print(f"\n正在尝试打开串口: {port_name} @ {baudrate}...")

    try:
        # 2. 打开串口
        ser = serial.Serial(port_name, baudrate, timeout=1)
        print(f"串口 {port_name} 已打开。按 Ctrl+C 停止读取。\n")

        buffer = b""
        
        while True:
            # 3. 读取数据
            if ser.in_waiting > 0:
                new_data = ser.read(ser.in_waiting)
                buffer += new_data

                # 4. 按行处理
                while b'\n' in buffer:
                    line_bytes, buffer = buffer.split(b'\n', 1)
                    try:
                        line = line_bytes.decode('utf-8', errors='ignore').strip()
                        
                        # 5. 解析 DATA: 格式
                        if line.startswith("DATA:"):
                            data_str = line[5:]
                            values = [v.strip() for v in data_str.split(',')]
                            
                            if len(values) == 6:
                                motor_speed = float(values[0])
                                current_d = float(values[1])
                                current_q = float(values[2])
                                motor_angle = float(values[3])
                                current_u = float(values[4])
                                current_v = float(values[5])
                                
                                print(f"[{time.strftime('%H:%M:%S')}] 解析成功:")
                                print(f"  速度: {motor_speed:>8.3f} | D轴电流: {current_d:>8.3f} | Q轴电流: {current_q:>8.3f}")
                                print(f"  角度: {motor_angle:>8.3f} | U相电流: {current_u:>8.3f} | V相电流: {current_v:>8.3f}")
                                print("-" * 60)
                            else:
                                print(f"收到非标准数据行: {line}")
                        elif line:
                            print(f"收到普通文本: {line}")
                            
                    except Exception as e:
                        print(f"处理行失败: {e}, 原始数据: {line_bytes}")

            time.sleep(0.01)  # 稍微休眠，降低 CPU 占用

    except serial.SerialException as e:
        print(f"串口错误: {e}")
    except KeyboardInterrupt:
        print("\n用户停止读取。")
    finally:
        if 'ser' in locals() and ser.is_open:
            ser.close()
            print("串口已关闭。")

if __name__ == "__main__":
    main()
