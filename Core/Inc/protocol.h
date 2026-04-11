#ifndef __PROTOCOL_H
#define __PROTOCOL_H

#include "main.h"
#include "global_def.h"
#include "motor/foc.h"
#include "usart.h"

#ifdef __cplusplus
extern "C" {
#endif

/* 协议常量定义 */
#define PROTOCOL_SOF              0xAA      // 帧头
#define PROTOCOL_EOF              0x55      // 帧尾
#define PROTOCOL_FRAME_LENGTH     20        // 帧长度（字节）
#define PROTOCOL_DATA_MAX_LEN     12        // 数据段最大长度

/* 命令字定义 */
#define CMD_SET                   0x01      // 设置参数
#define CMD_GET                   0x02      // 读取参数
#define CMD_SET_ACK               0x81      // 设置确认
#define CMD_GET_ACK               0x82      // 读取确认
#define CMD_ERROR                 0xFF      // 错误响应

/* 错误码定义 */
#define ERR_UNKNOWN_PARAM_ID      0x01      // 未知参数ID
#define ERR_DATA_LENGTH           0x02      // 数据长度错误
#define ERR_CHECKSUM              0x03      // 校验和错误
#define ERR_VALUE_OUT_OF_RANGE    0x04      // 参数值超出范围
#define ERR_FRAME_FORMAT          0x05      // 帧格式错误

/* 参数ID定义 */
/* 硬件参数 (0x01-0x09) */
#define PARAM_POLE_PAIRS          0x01      // 极对数
#define PARAM_SHUNT_RESISTANCE    0x02      // 电流采样电阻
#define PARAM_OP_GAIN             0x03      // 运放放大倍数
#define PARAM_MAX_CURRENT         0x04      // 最大Q轴电流
#define PARAM_ADC_REFERENCE       0x05      // ADC参考电压
#define PARAM_PWM_FREQUENCY       0x06      // PWM频率
#define PARAM_SPEED_CALC_FREQ     0x07      // 速度计算频率
#define PARAM_ADC_BITS            0x08      // ADC精度
#define PARAM_POSITION_CYCLE      0x09      // 多圈周期

/* PID参数 (0x20-0x23) */
#define PARAM_POSITION_PID        0x20      // 位置PID
#define PARAM_SPEED_PID           0x21      // 速度PID
#define PARAM_TORQUE_D_PID        0x22      // D轴力矩PID
#define PARAM_TORQUE_Q_PID        0x23      // Q轴力矩PID

/* 目标值 (0x41-0x45) */
#define PARAM_CONTROL_TYPE        0x41      // 控制类型
#define PARAM_TARGET_POSITION     0x42      // 目标角度
#define PARAM_TARGET_SPEED        0x43      // 目标速度
#define PARAM_TARGET_TORQUE_D     0x44      // 目标转矩D轴
#define PARAM_TARGET_TORQUE_Q     0x45      // 目标转矩Q轴

/* 反馈值 (0x60-0x68) */
#define PARAM_CURRENT_U           0x60      // U相电流
#define PARAM_CURRENT_V           0x61      // V相电流
#define PARAM_CURRENT_D           0x62      // D轴电流
#define PARAM_CURRENT_Q           0x63      // Q轴电流
#define PARAM_MOTOR_SPEED         0x64      // 电机转速
#define PARAM_MOTOR_ANGLE         0x65      // 电机多圈角度
#define PARAM_ENCODER_ANGLE       0x66      // 编码器角度
#define PARAM_ENCODER_INIT_ANGLE  0x67      // 编码器初始角度
#define PARAM_ROTOR_ZERO_ANGLE    0x68      // 转子零位角度

/* 协议帧结构 */
typedef struct
{
    uint8_t  sof;               // 帧头 0xAA
    uint8_t  cmd;               // 命令字
    uint8_t  param_id;          // 参数ID
    uint8_t  data_len;          // 数据长度
    uint8_t  data[12];          // 数据段
    uint8_t  checksum;          // 校验和
    uint8_t  reserved[2];       // 保留字节
    uint8_t  eof;               // 帧尾 0x55
} protocol_frame_t;

/* 协议处理函数 */
void protocol_init(void);
void protocol_process_frame(protocol_frame_t *frame);
void protocol_send_response(uint8_t cmd, uint8_t param_id, uint8_t *data, uint8_t data_len);

/* 错误响应函数 */
void protocol_send_error(uint8_t param_id, uint8_t error_code);

/* 参数读写处理函数 */
uint8_t protocol_read_param(uint8_t param_id, uint8_t *data, uint8_t *data_len);
uint8_t protocol_write_param(uint8_t param_id, uint8_t *data, uint8_t data_len);

/* 校验和计算 */
uint8_t protocol_calculate_checksum(protocol_frame_t *frame);

#ifdef __cplusplus
}
#endif

#endif /* __PROTOCOL_H */
