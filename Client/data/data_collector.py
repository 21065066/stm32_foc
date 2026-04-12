# -*- coding: utf-8 -*-
"""数据采集器 - 环形缓冲区"""

from collections import deque


class DataCollector:
    """数据采集器 - 环形缓冲区

    用于存储实时采集的电机数据，支持6条曲线同时显示
    """

    # 曲线key定义
    CURVE_KEYS = ['motor_speed', 'current_d', 'current_q',
                  'motor_angle', 'current_u', 'current_v']

    def __init__(self, max_points=1000):
        """初始化数据采集器

        Args:
            max_points: 最大数据点数
        """
        self.max_points = max_points
        self.timestamps = deque(maxlen=max_points)
        self.data = {key: deque(maxlen=max_points) for key in self.CURVE_KEYS}
        self._start_time = None

    def set_start_time(self, timestamp):
        """设置起始时间

        Args:
            timestamp: 起始时间戳 (秒)
        """
        self._start_time = timestamp

    def append(self, timestamp, feedback_data):
        """添加一组数据点

        Args:
            timestamp: 时间戳 (秒)
            feedback_data: 反馈数据字典
                {
                    'motor_speed': float,   # 电机转速 (rad/s)
                    'current_d': float,     # D轴电流 (A)
                    'current_q': float,     # Q轴电流 (A)
                    'motor_angle': float,   # 电机角度 (rad)
                    'current_u': float,     # U相电流 (A)
                    'current_v': float,     # V相电流 (A)
                }
        """
        self.timestamps.append(timestamp)

        for key in self.CURVE_KEYS:
            if key in feedback_data:
                self.data[key].append(feedback_data[key])
            else:
                self.data[key].append(None)

    def get_data(self, *keys):
        """获取指定曲线的数据

        Args:
            *keys: 要获取的曲线key

        Returns:
            tuple: (timestamps, [curve_data_list])
                - timestamps: 时间戳列表
                - curve_data_list: 各曲线数据的列表
        """
        # 计算相对时间
        if self._start_time is not None:
            timestamps = [t - self._start_time for t in self.timestamps]
        else:
            timestamps = list(self.timestamps)

        curves = []
        for key in keys:
            if key in self.data:
                curves.append(list(self.data[key]))
            else:
                curves.append([None] * len(timestamps))

        return timestamps, curves

    def get_all_data(self):
        """获取所有曲线数据

        Returns:
            tuple: (timestamps, data_dict)
        """
        if self._start_time is not None:
            timestamps = [t - self._start_time for t in self.timestamps]
        else:
            timestamps = list(self.timestamps)

        return timestamps, dict(self.data)

    def clear(self):
        """清空所有数据"""
        self.timestamps.clear()
        for d in self.data.values():
            d.clear()

    def get_latest(self, key):
        """获取最新一个数据点

        Args:
            key: 曲线key

        Returns:
            最新的数据值，如果不存在返回None
        """
        if key in self.data and len(self.data[key]) > 0:
            return self.data[key][-1]
        return None

    def get_point_count(self):
        """获取当前数据点数"""
        return len(self.timestamps)
