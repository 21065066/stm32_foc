#include "protocol.h"
#include "motor/motor_runtime_param.h"
#include "motor/foc.h"
#include "usart.h"
#include "main.h"
#include <string.h>
#include <stdio.h>
#include "../../Drivers/motor/foc.h"

/* 协议接收相关 */
#define PROTOCOL_FIFO_SIZE 10
static protocol_frame_t g_rx_fifo[PROTOCOL_FIFO_SIZE];
static volatile uint8_t g_fifo_head = 0;
static volatile uint8_t g_fifo_tail = 0;

static uint8_t g_rx_byte;                     // 当前接收到的字节
static uint8_t g_frame_buf[PROTOCOL_FRAME_LENGTH]; // 帧组装缓冲区
static uint8_t g_frame_index = 0;             // 当前组装进度

/* 协议初始化 */
void protocol_init(void)
{
    /* 启动串口接收中断，每次接收1个字节 */
    HAL_UART_Receive_IT(&huart2, &g_rx_byte, 1);
    
    /* 测试：发送初始化完成消息 */
    const char *msg = "Protocol initialized\r\n";
    HAL_UART_Transmit(&huart2, (uint8_t *)msg, strlen(msg), 100);
}

/* 校验和计算 */
uint8_t protocol_calculate_checksum(protocol_frame_t *frame)
{
    uint8_t checksum = 0;
    checksum += frame->cmd;
    checksum += frame->param_id;
    checksum += frame->data_len;
    for (uint8_t i = 0; i < 12; i++)
    {
        checksum += frame->data[i];
    }
    return checksum;
}

/* 发送响应帧 */
void protocol_send_response(uint8_t cmd, uint8_t param_id, uint8_t *data, uint8_t data_len)
{
    protocol_frame_t frame;
    
    frame.sof = PROTOCOL_SOF;
    frame.cmd = cmd;
    frame.param_id = param_id;
    frame.data_len = data_len;
    
    /* 复制数据 */
    memset(frame.data, 0, 12);
    if (data_len > 0 && data != NULL)
    {
        uint8_t copy_len = (data_len > 12) ? 12 : data_len;
        memcpy(frame.data, data, copy_len);
    }
    
    frame.checksum = protocol_calculate_checksum(&frame);
    frame.reserved[0] = 0;
    frame.reserved[1] = 0;
    frame.eof = PROTOCOL_EOF;
    
    /* 发送帧 */
    HAL_UART_Transmit(&huart2, (uint8_t *)&frame, PROTOCOL_FRAME_LENGTH, 100);
}

/* 发送错误响应 */
void protocol_send_error(uint8_t param_id, uint8_t error_code)
{
    uint8_t data[1] = {error_code};
    protocol_send_response(CMD_ERROR, param_id, data, 1);
}

/* 读取参数 */
uint8_t protocol_read_param(uint8_t param_id, uint8_t *data, uint8_t *data_len)
{
    uint8_t value[12] = {0};
    uint8_t len = 0;
    
    switch (param_id)
    {
        /* 硬件参数 */
        case PARAM_POLE_PAIRS:
            memcpy(value, &POLE_PAIRS, sizeof(POLE_PAIRS));
            len = 4;
            break;
            
        case PARAM_SHUNT_RESISTANCE:
            memcpy(value, &R_SHUNT, sizeof(R_SHUNT));
            len = 4;
            break;
            
        case PARAM_OP_GAIN:
            memcpy(value, &OP_GAIN, sizeof(OP_GAIN));
            len = 4;
            break;
            
        case PARAM_MAX_CURRENT:
            memcpy(value, &MAX_CURRENT, sizeof(MAX_CURRENT));
            len = 4;
            break;
            
        case PARAM_ADC_REFERENCE:
            memcpy(value, &ADC_REFERENCE_VOLT, sizeof(ADC_REFERENCE_VOLT));
            len = 4;
            break;
            
        case PARAM_PWM_FREQUENCY:
            memcpy(value, &motor_pwm_freq, sizeof(motor_pwm_freq));
            len = 4;
            break;
            
        case PARAM_SPEED_CALC_FREQ:
            memcpy(value, &motor_speed_calc_freq, sizeof(motor_speed_calc_freq));
            len = 4;
            break;
            
        case PARAM_ADC_BITS:
            memcpy(value, &ADC_BITS, sizeof(ADC_BITS));
            len = 4;
            break;
            
        case PARAM_POSITION_CYCLE:
            memcpy(value, &position_cycle, sizeof(position_cycle));
            len = 4;
            break;
            
        /* PID参数 */
        case PARAM_POSITION_PID:{
            float position_p = 0, position_i = 0, position_d = 0;
            get_position_pid(&position_p, &position_i, &position_d);
            memcpy(value, &position_p, sizeof(position_p));
            memcpy(value + 4, &position_i, sizeof(position_i)); 
            memcpy(value + 8, &position_d, sizeof(position_d));
            len = 12;
        } break;
            
        case PARAM_SPEED_PID:{
            float speed_p = 0, speed_i = 0, speed_d = 0;
            get_speed_pid(&speed_p, &speed_i, &speed_d);
            memcpy(value, &speed_p, sizeof(speed_p));
            memcpy(value + 4, &speed_i, sizeof(speed_i)); 
            memcpy(value + 8, &speed_d, sizeof(speed_d));
            len = 12;
        } break;
            
        case PARAM_TORQUE_D_PID:{
            float torque_d_p = 0, torque_d_i = 0, torque_d_d = 0;
            get_torque_d_pid(&torque_d_p, &torque_d_i, &torque_d_d);
            memcpy(value, &torque_d_p, sizeof(torque_d_p));
            memcpy(value + 4, &torque_d_i, sizeof(torque_d_i)); 
            memcpy(value + 8, &torque_d_d, sizeof(torque_d_d));
            len = 12;
        } break;
            
        case PARAM_TORQUE_Q_PID:{
            float torque_q_p = 0, torque_q_i = 0, torque_q_d = 0;
            get_torque_q_pid(&torque_q_p, &torque_q_i, &torque_q_d);
            memcpy(value, &torque_q_p, sizeof(torque_q_p));
            memcpy(value + 4, &torque_q_i, sizeof(torque_q_i)); 
            memcpy(value + 8, &torque_q_d, sizeof(torque_q_d));
            len = 12;
        } break;
            
        /* 目标值 */
        case PARAM_CONTROL_TYPE:{
            memcpy(value, &motor_control_context.type, sizeof(motor_control_context.type));
            len = 4;
        } break;
        case PARAM_TARGET_POSITION:{    
            memcpy(value, &motor_control_context.position, sizeof(motor_control_context.position));
            len = 4;
        } break;
        case PARAM_TARGET_SPEED:{    
            memcpy(value, &motor_control_context.speed, sizeof(motor_control_context.speed));
            len = 4;
        } break;
        case PARAM_TARGET_TORQUE_D:{    
            memcpy(value, &motor_control_context.torque_norm_d, sizeof(motor_control_context.torque_norm_d));
            len = 4;
        } break;
        case PARAM_TARGET_TORQUE_Q:{    
            memcpy(value, &motor_control_context.torque_norm_q, sizeof(motor_control_context.torque_norm_q));
            len = 4;
        } break;

        /* 反馈值 */
        case PARAM_CURRENT_U:
            memcpy(value, &motor_i_u, sizeof(motor_i_u));
            len = 4;
            break;
            
        case PARAM_CURRENT_V:
            memcpy(value, &motor_i_v, sizeof(motor_i_v));
            len = 4;
            break;
            
        case PARAM_CURRENT_D:
            memcpy(value, &motor_i_d, sizeof(motor_i_d));
            len = 4;
            break;
        case PARAM_CURRENT_Q:
            memcpy(value, &motor_i_q, sizeof(motor_i_q));
            len = 4;
            break;
        case PARAM_MOTOR_SPEED:
            memcpy(value, &motor_speed, sizeof(motor_speed));
            len = 4;
            break;
            
        case PARAM_MOTOR_ANGLE:
            memcpy(value, &motor_logic_angle, sizeof(motor_logic_angle));
            len = 4;
            break;
            
        case PARAM_ENCODER_ANGLE:
            memcpy(value, &encoder_angle, sizeof(encoder_angle));
            len = 4;
            break;
            
        case PARAM_ENCODER_INIT_ANGLE:
            memcpy(value, &encoder_init_angle, sizeof(encoder_init_angle));
            len = 4;
            break;
            
        case PARAM_ROTOR_ZERO_ANGLE:
            memcpy(value, &rotor_zero_angle, sizeof(rotor_zero_angle));
            len = 4;
            break;
            
        default:
            return ERR_UNKNOWN_PARAM_ID;
    }
    
    /* 复制float值到data */
    if (len > 0 && data != NULL && data_len != NULL)
    {
        memcpy(data, &value, len);
        *data_len = len;
        return 0; /* 成功 */
    }
    
    return ERR_DATA_LENGTH;
}

/* 写入参数 */
uint8_t protocol_write_param(uint8_t param_id, uint8_t *data, uint8_t data_len)
{
    int32_t valueInt[3] = {0};
    float valueFloat[3] = {0};
    if (data == NULL || data_len == 0)
    {
        return ERR_DATA_LENGTH;
    }

    memcpy(valueInt, data, 12);
    memcpy(valueFloat, data, 12);
    
    switch (param_id)
    {
        /* 硬件参数 */
        case PARAM_POLE_PAIRS: {
            memcpy(&POLE_PAIRS, &valueInt[0], sizeof(int32_t));
        } break;
            
        case PARAM_SHUNT_RESISTANCE: {
            memcpy(&R_SHUNT, &valueFloat[0], sizeof(float));
        } break;
            
        case PARAM_OP_GAIN: {
            memcpy(&OP_GAIN, &valueFloat[0], sizeof(float));
        } break;
            
        case PARAM_MAX_CURRENT: {
            memcpy(&MAX_CURRENT, &valueInt[0], sizeof(int32_t));
        } break;
            
        case PARAM_ADC_REFERENCE: {
            memcpy(&ADC_REFERENCE_VOLT, &valueFloat[0], sizeof(float));
        } break;
            
        case PARAM_PWM_FREQUENCY: {
            memcpy(&motor_pwm_freq, &valueFloat[0], sizeof(float));
        } break;
            
        case PARAM_SPEED_CALC_FREQ: {
            memcpy(&motor_speed_calc_freq, &valueFloat[0], sizeof(float));
        } break;
            
        case PARAM_ADC_BITS: {
            memcpy(&ADC_BITS, &valueInt[0], sizeof(int32_t));
        } break;
            
        case PARAM_POSITION_CYCLE: {
            memcpy(&position_cycle, &valueFloat[0], sizeof(float));
        } break;
            
        /* PID参数 */
        case PARAM_POSITION_PID: {
            float position_p = 0, position_i = 0, position_d = 0;
            memcpy(&position_p, &valueFloat[0], sizeof(float));
            memcpy(&position_i, &valueFloat[1], sizeof(float));
            memcpy(&position_d, &valueFloat[2], sizeof(float));
            set_position_pid(position_p, position_i, position_d);
        } break;
        case PARAM_SPEED_PID: {
            float speed_p = 0, speed_i = 0, speed_d = 0;
            memcpy(&speed_p, &valueFloat[0], sizeof(float));
            memcpy(&speed_i, &valueFloat[1], sizeof(float));
            memcpy(&speed_d, &valueFloat[2], sizeof(float));
            set_speed_pid(speed_p, speed_i, speed_d);
        } break;
            
        case PARAM_TORQUE_D_PID: {
            float torque_d_p = 0, torque_d_i = 0, torque_d_d = 0;
            memcpy(&torque_d_p, &valueFloat[0], sizeof(float));
            memcpy(&torque_d_i, &valueFloat[1], sizeof(float));
            memcpy(&torque_d_d, &valueFloat[2], sizeof(float));
            set_torque_d_pid(torque_d_p, torque_d_i, torque_d_d);
        } break;
            
        case PARAM_TORQUE_Q_PID: {
            float torque_q_p = 0, torque_q_i = 0, torque_q_d = 0;
            memcpy(&torque_q_p, &valueFloat[0], sizeof(float));
            memcpy(&torque_q_i, &valueFloat[1], sizeof(float));
            memcpy(&torque_q_d, &valueFloat[2], sizeof(float));
            set_torque_q_pid(torque_q_p, torque_q_i, torque_q_d);
        } break;
            
        /* 目标值 */
        case PARAM_CONTROL_TYPE: {
            memcpy(&motor_control_context.type, &valueInt[0], sizeof(motor_control_context.type));
        } break;
        case PARAM_TARGET_POSITION: {
            memcpy(&motor_control_context.position, &valueFloat[0], sizeof(float));
        } break;
        case PARAM_TARGET_SPEED: {
            memcpy(&motor_control_context.speed, &valueFloat[0], sizeof(float));
        } break;
        case PARAM_TARGET_TORQUE_D: {
            memcpy(&motor_control_context.torque_norm_d, &valueFloat[0], sizeof(float));
		} break;
            
        case PARAM_TARGET_TORQUE_Q: {
            memcpy(&motor_control_context.torque_norm_q, &valueFloat[0], sizeof(float));
        } break;   
        default:
            return ERR_UNKNOWN_PARAM_ID;
    }
    
    return 0; /* 成功 */
}

/* 处理接收到的帧 */
void protocol_process_frame(protocol_frame_t *frame)
{
    uint8_t error_code = 0;
    uint8_t calc_checksum;
    
    /* 验证帧格式 */
    if (frame->sof != PROTOCOL_SOF || frame->eof != PROTOCOL_EOF)
    {
        protocol_send_error(frame->param_id, ERR_FRAME_FORMAT);
        return;
    }
    
    /* 验证校验和 */
    calc_checksum = protocol_calculate_checksum(frame);
    if (calc_checksum != frame->checksum)
    {
        protocol_send_error(frame->param_id, ERR_CHECKSUM);
        return;
    }
    
    /* 处理命令 */
    switch (frame->cmd)
    {
        case CMD_SET:
            /* 设置参数 */
            error_code = protocol_write_param(frame->param_id, frame->data, frame->data_len);
            if (error_code == 0)
            {
                protocol_send_response(CMD_SET_ACK, frame->param_id, NULL, 0);
            }
            else
            {
                protocol_send_error(frame->param_id, error_code);
            }
            break;
            
        case CMD_GET:{
            /* 读取参数 */
            uint8_t response_len = 0;
            uint8_t response_data[12];
            error_code = protocol_read_param(frame->param_id, response_data, &response_len);
            
            if (error_code == 0)
            {
                protocol_send_response(CMD_GET_ACK, frame->param_id, response_data, response_len);
            }
            else
            {
                protocol_send_error(frame->param_id, error_code);
            }
        } break;
        default:
            protocol_send_error(frame->param_id, ERR_UNKNOWN_PARAM_ID);
            break;
    }
}

/* 串口接收回调函数 */
void HAL_UART_RxCpltCallback(UART_HandleTypeDef *huart)
{
    if (huart->Instance == USART2)
    {
        /* 状态机解析二进制协议帧 */
        if (g_frame_index == 0)
        {
            if (g_rx_byte == PROTOCOL_SOF)
            {
                g_frame_buf[g_frame_index++] = g_rx_byte;
            }
        }
        else
        {
            g_frame_buf[g_frame_index++] = g_rx_byte;
            
            if (g_frame_index >= PROTOCOL_FRAME_LENGTH)
            {
                /* 收到完整长度，检查帧尾 */
                if (g_frame_buf[PROTOCOL_FRAME_LENGTH - 1] == PROTOCOL_EOF)
                {
                    /* 将接收到的数据存入 FIFO */
                    uint8_t next_head = (g_fifo_head + 1) % PROTOCOL_FIFO_SIZE;
                    if (next_head != g_fifo_tail)
                    {
                        memcpy(&g_rx_fifo[g_fifo_head], g_frame_buf, PROTOCOL_FRAME_LENGTH);
                        g_fifo_head = next_head;
                    }
                }
                /* 无论成功失败，重置状态机 */
                g_frame_index = 0;
            }
        }
        
        /* 重新启动接收 */
        HAL_UART_Receive_IT(huart, &g_rx_byte, 1);
    }
}

/* 协议任务处理（在main循环中调用） */
void protocol_task(void)
{
    /* 处理 FIFO 中的帧 */
    while (g_fifo_tail != g_fifo_head)
    {
        protocol_process_frame(&g_rx_fifo[g_fifo_tail]);
        g_fifo_tail = (g_fifo_tail + 1) % PROTOCOL_FIFO_SIZE;
    }
}
