# -*- coding: utf-8 -*-
"""配置管理"""

import json
import os
from pathlib import Path


class ConfigManager:
    """配置管理器"""

    def __init__(self, config_path=None):
        if config_path is None:
            # 默认配置路径: 用户目录/.stm32_foc_client/config.json
            user_dir = Path.home()
            self.config_path = user_dir / ".stm32_foc_client" / "config.json"
        else:
            self.config_path = Path(config_path)

        self._ensure_dir()
        self.config = self._load()

    def _ensure_dir(self):
        """确保配置目录存在"""
        self.config_path.parent.mkdir(parents=True, exist_ok=True)

    def _load(self):
        """加载配置"""
        if self.config_path.exists():
            try:
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception:
                return {}
        return {}

    def save(self):
        """保存配置"""
        try:
            with open(self.config_path, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, indent=2, ensure_ascii=False)
            return True
        except Exception:
            return False

    def get(self, key, default=None):
        """获取配置值"""
        return self.config.get(key, default)

    def set(self, key, value):
        """设置配置值"""
        self.config[key] = value

    def get_serial_port(self):
        """获取上次使用的串口"""
        return self.get('serial_port')

    def set_serial_port(self, port):
        """保存串口"""
        self.set('serial_port', port)

    def get_baudrate(self):
        """获取上次使用的波特率"""
        return self.get('baudrate', 115200)

    def set_baudrate(self, baudrate):
        """保存波特率"""
        self.set('baudrate', baudrate)

    def get_param(self, param_id, default=None):
        """获取参数值"""
        return self.config.get(f'param_{param_id:02X}', default)

    def set_param(self, param_id, value):
        """保存参数值"""
        self.config[f'param_{param_id:02X}'] = value

    def get_all_params(self):
        """获取所有保存的参数"""
        params = {}
        for key, value in self.config.items():
            if key.startswith('param_'):
                param_id = int(key[6:], 16)
                params[param_id] = value
        return params

    def clear_params(self):
        """清除所有保存的参数"""
        keys_to_remove = [k for k in self.config.keys() if k.startswith('param_')]
        for key in keys_to_remove:
            del self.config[key]

    def get_slider_range(self, param_id, default=None):
        """获取滑动条范围

        Args:
            param_id: 参数ID
            default: 默认值，如 (0, 100)

        Returns:
            tuple or None: (min, max)
        """
        range_data = self.get(f'slider_range_{param_id:02X}')
        if range_data and isinstance(range_data, list) and len(range_data) == 2:
            return tuple(range_data)
        return default

    def set_slider_range(self, param_id, min_val, max_val):
        """设置滑动条范围

        Args:
            param_id: 参数ID
            min_val: 最小值
            max_val: 最大值
        """
        self.set(f'slider_range_{param_id:02X}', [min_val, max_val])

    def get_all_slider_ranges(self):
        """获取所有滑动条范围配置"""
        ranges = {}
        for key, value in self.config.items():
            if key.startswith('slider_range_'):
                param_id = int(key[13:], 16)
                if isinstance(value, list) and len(value) == 2:
                    ranges[param_id] = tuple(value)
        return ranges
