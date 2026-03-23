"""
华为运动健康数据处理 Skill
包初始化文件
"""

__version__ = "1.0.0"
__author__ = "OpenClaw Community"

from .auth import HuaweiHealthAuth
from .data_fetcher import HuaweiHealthDataFetcher
from .data_analyzer import HealthDataAnalyzer

__all__ = [
    'HuaweiHealthAuth',
    'HuaweiHealthDataFetcher',
    'HealthDataAnalyzer'
]
