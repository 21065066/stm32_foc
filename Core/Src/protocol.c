#include "protocol.h"
#include "usart.h"
#include "motor/foc.h"
#include "motor/conf.h"
#include "arm_math.h"
#include <string.h>
#include <stdio.h>

uint8_t protocol_calc_checksum(uint8_t cmd, uint8_t param_id, uint8_t data_len, const uint8_t *data)
{
    uint8_t checksum = cmd + param_id + data_len;
    for (uint8_t i = 0; i < data_len; i++) {
        checksum += data[i];
    }
    return checksum & 0xFF;
}

bool protocol_parse_frame(const uint8_t *buffer, uint16_t len, protocol_parsed_frame_t *frame)
{
    if (len < 6) return false;
    if (buffer[0] != PROTOCOL_SOF) return false;
    if (buffer[len - 1] != PROTOCOL_EOF) return false;

    uint8_t cmd = buffer[1];
    uint8_t param_id = buffer[2];
    uint8_t data_len = buffer[3];

    if (len != 6 + data_len) return false;

    uint8_t calc_checksum = protocol_calc_checksum(cmd, param_id, data_len, &buffer[4]);
    if (calc_checksum != buffer[4 + data_len]) return false;

    frame->cmd = cmd;
    frame->param_id = param_id;
    frame->data_len = data_len;
    memcpy(frame->data, &buffer[4], data_len);
    printf("Received frame: cmd=%d, param_id=%d, data_len=%d, checksum=%d\r\n", cmd, param_id, data_len, calc_checksum);

    return true;
}

uint16_t protocol_build_frame(uint8_t *buffer, uint8_t cmd, uint8_t param_id, const uint8_t *data, uint8_t data_len)
{
    buffer[0] = PROTOCOL_SOF;
    buffer[1] = cmd;
    buffer[2] = param_id;
    buffer[3] = data_len;

    if (data_len > 0 && data != NULL) {
        memcpy(&buffer[4], data, data_len);
    }

    uint8_t checksum = protocol_calc_checksum(cmd, param_id, data_len, &buffer[4]);
    buffer[4 + data_len] = checksum;
    buffer[5 + data_len] = PROTOCOL_EOF;

    return 6 + data_len;
}

bool protocol_get_param_value(uint8_t param_id, float *value)
{
    extern arm_pid_instance_f32 pid_position;
    extern arm_pid_instance_f32 pid_speed;
    extern arm_pid_instance_f32 pid_torque_d;
    extern arm_pid_instance_f32 pid_torque_q;

    switch (param_id) {
        case PARAM_ID_POLE_PAIRS:
            *value = (float)POLE_PAIRS;
            return true;
        case PARAM_ID_R_SHUNT:
            *value = R_SHUNT;
            return true;
        case PARAM_ID_OP_GAIN:
            *value = OP_GAIN;
            return true;
        case PARAM_ID_MAX_CURRENT:
            *value = MAX_CURRENT;
            return true;
        case PARAM_ID_ADC_REF_VOLT:
            *value = ADC_REFERENCE_VOLT;
            return true;
        case PARAM_ID_PWM_FREQ:
            *value = (float)motor_pwm_freq;
            return true;
        case PARAM_ID_SPEED_CALC_FREQ:
            *value = (float)motor_speed_calc_freq;
            return true;
        case PARAM_ID_POS_PID_KP:
            *value = pid_position.Kp;
            return true;
        case PARAM_ID_POS_PID_KI:
            *value = pid_position.Ki;
            return true;
        case PARAM_ID_POS_PID_KD:
            *value = pid_position.Kd;
            return true;
        case PARAM_ID_SPEED_PID_KP:
            *value = pid_speed.Kp;
            return true;
        case PARAM_ID_SPEED_PID_KI:
            *value = pid_speed.Ki;
            return true;
        case PARAM_ID_SPEED_PID_KD:
            *value = pid_speed.Kd;
            return true;
        case PARAM_ID_TORQUE_D_PID_KP:
            *value = pid_torque_d.Kp;
            return true;
        case PARAM_ID_TORQUE_D_PID_KI:
            *value = pid_torque_d.Ki;
            return true;
        case PARAM_ID_TORQUE_D_PID_KD:
            *value = pid_torque_d.Kd;
            return true;
        case PARAM_ID_TORQUE_Q_PID_KP:
            *value = pid_torque_q.Kp;
            return true;
        case PARAM_ID_TORQUE_Q_PID_KI:
            *value = pid_torque_q.Ki;
            return true;
        case PARAM_ID_TORQUE_Q_PID_KD:
            *value = pid_torque_q.Kd;
            return true;
        default:
            return false;
    }
}

bool protocol_set_param_value(uint8_t param_id, float value)
{
    extern arm_pid_instance_f32 pid_position;
    extern arm_pid_instance_f32 pid_speed;
    extern arm_pid_instance_f32 pid_torque_d;
    extern arm_pid_instance_f32 pid_torque_q;

    switch (param_id) {
        case PARAM_ID_POS_PID_KP:
            pid_position.Kp = value;
            return true;
        case PARAM_ID_POS_PID_KI:
            pid_position.Ki = value;
            return true;
        case PARAM_ID_POS_PID_KD:
            pid_position.Kd = value;
            return true;
        case PARAM_ID_SPEED_PID_KP:
            pid_speed.Kp = value;
            return true;
        case PARAM_ID_SPEED_PID_KI:
            pid_speed.Ki = value;
            return true;
        case PARAM_ID_SPEED_PID_KD:
            pid_speed.Kd = value;
            return true;
        case PARAM_ID_TORQUE_D_PID_KP:
            pid_torque_d.Kp = value;
            return true;
        case PARAM_ID_TORQUE_D_PID_KI:
            pid_torque_d.Ki = value;
            return true;
        case PARAM_ID_TORQUE_D_PID_KD:
            pid_torque_d.Kd = value;
            return true;
        case PARAM_ID_TORQUE_Q_PID_KP:
            pid_torque_q.Kp = value;
            return true;
        case PARAM_ID_TORQUE_Q_PID_KI:
            pid_torque_q.Ki = value;
            return true;
        case PARAM_ID_TORQUE_Q_PID_KD:
            pid_torque_q.Kd = value;
            return true;
        default:
            return false;
    }
}

void protocol_send_ack(uint8_t cmd, uint8_t param_id, const uint8_t *data, uint8_t data_len)
{
    uint8_t buffer[PROTOCOL_MAX_FRAME_LEN];
    uint16_t frame_len = protocol_build_frame(buffer, cmd, param_id, data, data_len);
    HAL_UART_Transmit(&huart2, buffer, frame_len, 100);
}

void protocol_send_error(uint8_t param_id, uint8_t error_code)
{
    uint8_t buffer[PROTOCOL_MAX_FRAME_LEN];
    buffer[0] = PROTOCOL_SOF;
    buffer[1] = CMD_ERROR;
    buffer[2] = param_id;
    buffer[3] = 1;
    buffer[4] = error_code;
    buffer[5] = protocol_calc_checksum(CMD_ERROR, param_id, 1, &error_code);
    buffer[6] = PROTOCOL_EOF;
    HAL_UART_Transmit(&huart2, buffer, 7, 100);
}

void protocol_process_frame(const protocol_parsed_frame_t *frame)
{
    if (frame->cmd == CMD_SET) {
        if (frame->data_len != 4) {
            protocol_send_error(frame->param_id, ERR_DATA_LEN);
            return;
        }

        float value;
        memcpy(&value, frame->data, 4);

        if (!protocol_set_param_value(frame->param_id, value)) {
            protocol_send_error(frame->param_id, ERR_UNKNOWN_PARAM);
            return;
        }

        protocol_send_ack(CMD_SET_ACK, frame->param_id, NULL, 0);

    } else if (frame->cmd == CMD_GET) {
        if (frame->data_len != 0) {
            protocol_send_error(frame->param_id, ERR_DATA_LEN);
            return;
        }

        float value;
        if (!protocol_get_param_value(frame->param_id, &value)) {
            protocol_send_error(frame->param_id, ERR_UNKNOWN_PARAM);
            return;
        }

        protocol_send_ack(CMD_GET_ACK, frame->param_id, (uint8_t *)&value, 4);

    } else {
        protocol_send_error(frame->param_id, ERR_FRAME_FORMAT);
    }
}