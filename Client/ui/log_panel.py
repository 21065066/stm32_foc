# -*- coding: utf-8 -*-
"""日志面板"""

from PyQt5.QtWidgets import QWidget, QVBoxLayout, QTextEdit
from PyQt5.QtGui import QTextCursor, QColor
from PyQt5.QtCore import Qt


class LogPanel(QWidget):
    """日志面板"""

    # 日志类型
    LOG_SEND = "发送"
    LOG_RECEIVE = "接收"
    LOG_ERROR = "错误"
    LOG_INFO = "信息"

    def __init__(self, parent=None):
        super().__init__(parent)
        self.max_lines = 1000  # 最大日志行数

        self._init_ui()

    def _init_ui(self):
        """初始化UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # 日志文本框
        self.log_textedit = QTextEdit()
        self.log_textedit.setReadOnly(True)
        self.log_textedit.setMaximumHeight(150)
        self.log_textedit.setStyleSheet("""
            QTextEdit {
                background-color: #1E1E1E;
                color: #FFFFFF;
                font-family: 'Consolas', 'Courier New', monospace;
                font-size: 12px;
            }
        """)

        layout.addWidget(self.log_textedit)

    def _format_hex(self, data):
        """格式化十六进制字符串"""
        if isinstance(data, bytearray):
            data = bytes(data)
        return ' '.join(f'{b:02X}' for b in data)

    def _get_current_time(self):
        """获取当前时间字符串"""
        from datetime import datetime
        return datetime.now().strftime("%H:%M:%S")

    def append_log(self, log_type, data):
        """追加日志

        Args:
            log_type: 日志类型 (LOG_SEND, LOG_RECEIVE, LOG_ERROR, LOG_INFO)
            data: 日志数据 (bytes 或 str)
        """
        time_str = self._get_current_time()

        if isinstance(data, bytes):
            data_str = self._format_hex(data)
        else:
            data_str = str(data)

        # 确定颜色
        if log_type == self.LOG_SEND:
            color = "#0000FF"  # 蓝色
        elif log_type == self.LOG_RECEIVE:
            color = "#008800"  # 深绿色
        elif log_type == self.LOG_ERROR:
            color = "#FF0000"  # 红色
        else:
            color = "#FFFFFF"  # 白色

        # 构建日志行
        log_line = f'<span style="color: #888888;">{time_str}</span> '
        log_line += f'<span style="color: #888888;">[{log_type}]</span> '
        log_line += f'<span style="color: {color};">{data_str}</span>'

        # 添加到文本框
        cursor = self.log_textedit.textCursor()
        cursor.movePosition(QTextCursor.End)
        cursor.insertHtml(log_line)
        cursor.insertHtml("<br>")

        # 滚动到底部
        self.log_textedit.setTextCursor(cursor)
        self.log_textedit.ensureCursorVisible()

        # 限制行数
        self._trim_lines()

    def append_send_log(self, data):
        """追加发送日志"""
        self.append_log(self.LOG_SEND, data)

    def append_receive_log(self, data):
        """追加接收日志"""
        self.append_log(self.LOG_RECEIVE, data)

    def append_error_log(self, message):
        """追加错误日志"""
        self.append_log(self.LOG_ERROR, message)

    def append_info_log(self, message):
        """追加信息日志"""
        self.append_log(self.LOG_INFO, message)

    def _trim_lines(self):
        """限制日志行数"""
        doc = self.log_textedit.document()
        if doc.blockCount() > self.max_lines:
            cursor = QTextCursor(doc)
            cursor.movePosition(QTextCursor.Start)
            for _ in range(doc.blockCount() - self.max_lines):
                cursor.select(QTextCursor.BlockUnderCursor)
                cursor.removeSelectedText()
                cursor.deleteChar()

    def clear(self):
        """清空日志"""
        self.log_textedit.clear()
