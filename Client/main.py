# -*- coding: utf-8 -*-
"""程序入口"""

import sys
import logging
from PyQt5.QtWidgets import QApplication

from ui.main_window import MainWindow


def setup_logging():
    """配置日志"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )


def main():
    """主函数"""
    setup_logging()

    app = QApplication(sys.argv)
    app.setStyle('Fusion')

    # 设置中文字体
    from PyQt5.QtGui import QFont
    font = QFont()
    font.setFamily("Microsoft YaHei")
    app.setFont(font)

    window = MainWindow()
    window.show()

    sys.exit(app.exec_())


if __name__ == '__main__':
    main()
