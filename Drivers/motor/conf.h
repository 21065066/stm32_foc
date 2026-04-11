#pragma once
#include "global_def.h"
// 电机物理参数：
extern int POLE_PAIRS; // 极对数

// 电路参数：
extern float R_SHUNT;           // 电流采样电阻，欧姆
extern float OP_GAIN;             // 运放放大倍数
extern float MAX_CURRENT;      // 最大q轴电流，安培A
extern float ADC_REFERENCE_VOLT; // 电流采样adc参考电压，伏
extern int ADC_BITS;            // ADC精度，bit

// 单片机配置参数：
extern int motor_pwm_freq;      // 驱动桥pwm频率，Hz
extern int motor_speed_calc_freq; // 电机速度计算频率，Hz

// 软件参数：

// 电机软件上的多圈周期，位置模式下能控制的范围，等于正半周期+负半周期，可以任意修改(比如改为1234*pi)
extern float position_cycle;
