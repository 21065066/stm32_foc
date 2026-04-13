#include "protocol.h"
#include "motor/motor_runtime_param.h"
#include "motor/foc.h"
#include "usart.h"
#include "main.h"
#include <string.h>
#include <stdio.h>

/* 协议接收缓冲区 */
static uint8_t g_rx_buffer[PROTOCOL_FRAME_LENGTH * 100];

/* 协议初始化 */
void protocol_init(void)
{
    /* 启动串口接收中断，先接收PROTOCOL_FRAME_LENGTH个字节 */
    HAL_UART_Receive_IT(&huart2, g_rx_buffer, PROTOCOL_FRAME_LENGTH);
    
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
    float value = 0;
    uint8_t len = 0;
    
    switch (param_id)
    {
        /* 硬件参数 */
        case PARAM_POLE_PAIRS:
            value = (float)POLE_PAIRS;
            len = 4;
            break;
            
        case PARAM_SHUNT_RESISTANCE:
            value = R_SHUNT;
            len = 4;
            break;
            
        case PARAM_OP_GAIN:
            value = OP_GAIN;
            len = 4;
            break;
            
        case PARAM_MAX_CURRENT:
            value = MAX_CURRENT;
            len = 4;
            break;
            
        case PARAM_ADC_REFERENCE:
            value = ADC_REFERENCE_VOLT;
            len = 4;
            break;
            
        case PARAM_PWM_FREQUENCY:
            value = (float)motor_pwm_freq;
            len = 4;
            break;
            
        case PARAM_SPEED_CALC_FREQ:
            value = (float)motor_speed_calc_freq;
            len = 4;
            break;
            
        case PARAM_ADC_BITS:
            value = (float)ADC_BITS;
            len = 4;
            break;
            
        case PARAM_POSITION_CYCLE:
            value = position_cycle;
            len = 4;
            break;
            
        /* PID参数 */
        case PARAM_POSITION_PID:
            /* 需要从PID实例中读取，暂未实现 */
            len = 0;
            return ERR_UNKNOWN_PARAM_ID;
            
        case PARAM_SPEED_PID:
            len = 0;
            return ERR_UNKNOWN_PARAM_ID;
            
        case PARAM_TORQUE_D_PID:
            len = 0;
            return ERR_UNKNOWN_PARAM_ID;
            
        case PARAM_TORQUE_Q_PID:
            len = 0;
            return ERR_UNKNOWN_PARAM_ID;
            
        /* 目标值 */
        case PARAM_CONTROL_TYPE:{
            value = motor_control_context.type;
            len = 4;
        } break;
        case PARAM_TARGET_POSITION:{    
            value = (float)motor_control_context.position;
            len = 4;
        } break;
        case PARAM_TARGET_SPEED:{    
            value = (float)motor_control_context.speed;
            len = 4;
        } break;
        case PARAM_TARGET_TORQUE_D:{    
            value = (float)motor_control_context.torque_norm_d;
            len = 4;
        } break;
        case PARAM_TARGET_TORQUE_Q:{    
            value = (float)motor_control_context.torque_norm_q;
            len = 4;
        } break;

        /* 反馈值 */
        case PARAM_CURRENT_U:
            value = motor_i_u;
            len = 4;
            break;
            
        case PARAM_CURRENT_V:
            value = motor_i_v;
            len = 4;
            break;
            
        case PARAM_CURRENT_D:
            value = motor_i_d;
            len = 4;
            break;
            
        case PARAM_CURRENT_Q:
            value = motor_i_q;
            len = 4;
            break;
            
        case PARAM_MOTOR_SPEED:
            value = motor_speed;
            len = 4;
            break;
            
        case PARAM_MOTOR_ANGLE:
            value = motor_logic_angle;
            len = 4;
            break;
            
        case PARAM_ENCODER_ANGLE:
            value = encoder_angle;
            len = 4;
            break;
            
        case PARAM_ENCODER_INIT_ANGLE:
            value = encoder_init_angle;
            len = 4;
            break;
            
        case PARAM_ROTOR_ZERO_ANGLE:
            value = rotor_zero_angle;
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
        case PARAM_POLE_PAIRS:
            POLE_PAIRS = valueInt[0];
            break;
            
        case PARAM_SHUNT_RESISTANCE:
            R_SHUNT = valueFloat[0];
            break;
            
        case PARAM_OP_GAIN:
            OP_GAIN = valueFloat[0];
            break;
            
        case PARAM_MAX_CURRENT:
            MAX_CURRENT = valueInt[0];;
            break;
            
        case PARAM_ADC_REFERENCE:
            ADC_REFERENCE_VOLT = valueFloat[0];
            break;
            
        case PARAM_PWM_FREQUENCY:
            motor_pwm_freq = valueFloat[0];
            break;
            
        case PARAM_SPEED_CALC_FREQ:
            motor_speed_calc_freq = valueFloat[0];
            break;
            
        case PARAM_ADC_BITS:
            ADC_BITS = valueInt[0];
            break;
            
        case PARAM_POSITION_CYCLE:
            position_cycle = valueFloat[0];
            break;
            
        /* PID参数 */
        case PARAM_POSITION_PID:
            set_position_pid(valueFloat[0], valueFloat[1], valueFloat[2]);
            return ERR_UNKNOWN_PARAM_ID;
            
        case PARAM_SPEED_PID:
            set_speed_pid(valueFloat[0], valueFloat[1], valueFloat[2]);
            return ERR_UNKNOWN_PARAM_ID;
            
        case PARAM_TORQUE_D_PID:
            set_torque_d_pid(valueFloat[0], valueFloat[1], valueFloat[2]);
            return ERR_UNKNOWN_PARAM_ID;
            
        case PARAM_TORQUE_Q_PID:
            set_torque_q_pid(valueFloat[0], valueFloat[1], valueFloat[2]);
            return ERR_UNKNOWN_PARAM_ID;
            
        /* 目标值 */
        case PARAM_CONTROL_TYPE:
            motor_control_context.type = (motor_control_type)valueFloat[0];
            break;
            
        case PARAM_TARGET_POSITION:
            motor_control_context.position = valueFloat[0];
            break;
            
        case PARAM_TARGET_SPEED:
            motor_control_context.speed = valueFloat[0];
            break;
            
        case PARAM_TARGET_TORQUE_D: {
            motor_control_context.torque_norm_d = valueFloat[0];
		} break;
            
        case PARAM_TARGET_TORQUE_Q:
            motor_control_context.torque_norm_q = valueFloat[0];
            break;
            
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
        /* 处理帧 */
        protocol_frame_t *frame = (protocol_frame_t *)g_rx_buffer;
        protocol_process_frame(frame);
        /* 重新启动接收 */
        HAL_UART_Receive_IT(huart, g_rx_buffer, PROTOCOL_FRAME_LENGTH);
    }
}

/* 协议任务处理（在main循环中调用） */
void protocol_task(void)
{
    /* 可以在这里添加周期性任务 */
}
