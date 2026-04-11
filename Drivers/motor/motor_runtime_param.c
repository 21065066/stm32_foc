#include "motor_runtime_param.h"
#include "conf.h"


float motor_u;
float motor_i_u;
float motor_i_v;
float motor_i_d;
float motor_i_q;
float motor_speed;
float motor_logic_angle;
float encoder_angle;
float encoder_init_angle;
float rotor_zero_angle;


int POLE_PAIRS = 7;

/* 协议参数 */
float R_SHUNT = 0.02f;
float OP_GAIN = 50.0f;
float MAX_CURRENT = 2.0f;
float ADC_REFERENCE_VOLT = 3.3f;
int ADC_BITS = 12;
float position_cycle = (6.0f * 3.14159265358979f);

int motor_pwm_freq = 40000;
int motor_speed_calc_freq = 930;
