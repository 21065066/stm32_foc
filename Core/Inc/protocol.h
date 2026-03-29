#pragma once

#include <stdint.h>
#include <stdbool.h>

#define PROTOCOL_SOF 0xAA
#define PROTOCOL_EOF 0x55
#define PROTOCOL_MAX_DATA_LEN 32
#define PROTOCOL_MAX_FRAME_LEN (PROTOCOL_MAX_DATA_LEN + 7)

typedef enum {
    CMD_SET = 0x01,
    CMD_GET = 0x02,
    CMD_SET_ACK = 0x81,
    CMD_GET_ACK = 0x82,
    CMD_ERROR = 0xFF
} protocol_cmd_t;

typedef enum {
    ERR_UNKNOWN_PARAM = 0x01,
    ERR_DATA_LEN = 0x02,
    ERR_CHECKSUM = 0x03,
    ERR_PARAM_RANGE = 0x04,
    ERR_FRAME_FORMAT = 0x05
} protocol_error_t;

typedef enum {
    PARAM_ID_POLE_PAIRS = 0x01,
    PARAM_ID_R_SHUNT = 0x02,
    PARAM_ID_OP_GAIN = 0x03,
    PARAM_ID_MAX_CURRENT = 0x04,
    PARAM_ID_ADC_REF_VOLT = 0x05,
    PARAM_ID_PWM_FREQ = 0x06,
    PARAM_ID_SPEED_CALC_FREQ = 0x07,
    PARAM_ID_POS_PID_KP = 0x10,
    PARAM_ID_POS_PID_KI = 0x11,
    PARAM_ID_POS_PID_KD = 0x12,
    PARAM_ID_SPEED_PID_KP = 0x20,
    PARAM_ID_SPEED_PID_KI = 0x21,
    PARAM_ID_SPEED_PID_KD = 0x22,
    PARAM_ID_TORQUE_D_PID_KP = 0x30,
    PARAM_ID_TORQUE_D_PID_KI = 0x31,
    PARAM_ID_TORQUE_D_PID_KD = 0x32,
    PARAM_ID_TORQUE_Q_PID_KP = 0x40,
    PARAM_ID_TORQUE_Q_PID_KI = 0x41,
    PARAM_ID_TORQUE_Q_PID_KD = 0x42
} protocol_param_id_t;

typedef struct {
    uint8_t sof;
    uint8_t cmd;
    uint8_t param_id;
    uint8_t data_len;
    uint8_t data[PROTOCOL_MAX_DATA_LEN];
    uint8_t checksum;
    uint8_t eof;
} protocol_frame_t;

typedef struct {
    uint8_t cmd;
    uint8_t param_id;
    uint8_t data_len;
    uint8_t data[PROTOCOL_MAX_DATA_LEN];
} protocol_parsed_frame_t;

uint8_t protocol_calc_checksum(uint8_t cmd, uint8_t param_id, uint8_t data_len, const uint8_t *data);
bool protocol_parse_frame(const uint8_t *buffer, uint16_t len, protocol_parsed_frame_t *frame);
uint16_t protocol_build_frame(uint8_t *buffer, uint8_t cmd, uint8_t param_id, const uint8_t *data, uint8_t data_len);
bool protocol_get_param_value(uint8_t param_id, float *value);
bool protocol_set_param_value(uint8_t param_id, float value);
void protocol_process_frame(const protocol_parsed_frame_t *frame);