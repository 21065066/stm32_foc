#include "motor_runtime_param.h"
#include "conf.h"

float motor_i_u;
float motor_i_v;
float motor_i_d;
float motor_i_q;
float motor_speed;
float motor_logic_angle;
float encoder_angle;
float encoder_init_angle;
float rotor_zero_angle;

/* 协议参数 */
float MAX_CURRENT = 2.0f;
float position_cycle = (6.0f * 3.14159265358979f);
