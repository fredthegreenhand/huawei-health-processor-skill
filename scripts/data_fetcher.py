"""
华为运动健康数据获取模块
负责从华为健康API获取各类运动健康数据
"""

import json
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Union
from typing import TYPE_CHECKING
import requests
import pandas as pd
import pytz

if TYPE_CHECKING:
    from .auth import HuaweiHealthAuth


class HuaweiHealthDataFetcher:
    """华为运动健康数据获取器"""
    
    def __init__(self, auth: 'HuaweiHealthAuth', config: Dict):
        """
        初始化数据获取器
        
        参数:
            auth: 认证管理器实例
            config: 配置字典
        """
        self.auth = auth
        self.config = config
        
        # API配置
        self.base_url = config.get('api', {}).get('base_url', '')
        self.timeout = config.get('api', {}).get('timeout', 30)
        self.retry_times = config.get('api', {}).get('retry_times', 3)
        self.retry_delay = config.get('api', {}).get('retry_delay', 1)
        
        # 数据配置
        self.data_config = config.get('data', {})
        self.supported_types = self.data_config.get('supported_types', {})
        self.max_batch_size = self.data_config.get('max_batch_size', 100)
        
        # 时区设置
        self.timezone_str = config.get('processing', {}).get('timezone', 'Asia/Shanghai')
        self.timezone = pytz.timezone(self.timezone_str)
        
        # 初始化session
        self.session = requests.Session()
    
    def _get_headers(self) -> Dict[str, str]:
        """
        获取请求头
        
        返回:
            请求头字典
        """
        access_token = self.auth.get_valid_access_token()
        
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
            "x-client-id": self.auth.client_id,
            "x-version": "1.0.0"
        }
        
        return headers
    
    def _make_request(self, method: str, endpoint: str, params: Dict = None,
                     data: Dict = None) -> Dict:
        """
        发送HTTP请求(带重试机制)
        
        参数:
            method: HTTP方法(GET/POST/PUT/DELETE)
            endpoint: API端点
            params: 查询参数
            data: 请求体数据
            
        返回:
            响应JSON数据
        """
        url = f"{self.base_url}{endpoint}"
        
        for attempt in range(self.retry_times):
            try:
                response = self.session.request(
                    method=method,
                    url=url,
                    headers=self._get_headers(),
                    params=params,
                    json=data,
                    timeout=self.timeout
                )
                response.raise_for_status()
                return response.json()
                
            except requests.exceptions.Timeout:
                if attempt == self.retry_times - 1:
                    raise Exception(f"请求超时: {url}")
            except requests.exceptions.HTTPError as e:
                if response.status_code == 401:
                    # Token过期,尝试刷新
                    if attempt == 0:
                        continue  # 重试一次
                    else:
                        raise Exception("认证失败,请重新授权")
                else:
                    raise Exception(f"HTTP错误: {response.status_code} - {str(e)}")
            except requests.exceptions.RequestException as e:
                if attempt == self.retry_times - 1:
                    raise Exception(f"请求失败: {str(e)}")
            
            # 等待后重试
            import time
            time.sleep(self.retry_delay * (attempt + 1))
    
    def _convert_to_dataframe(self, data_points: List[Dict], data_type: str) -> pd.DataFrame:
        """
        将API返回的数据点转换为DataFrame
        
        参数:
            data_points: 数据点列表
            data_type: 数据类型(steps, calories等)
            
        返回:
            pandas DataFrame
        """
        if not data_points:
            return pd.DataFrame()
        
        rows = []
        for point in data_points:
            row = {
                'start_time': point.get('startTime'),
                'end_time': point.get('endTime'),
                'data_source_id': point.get('dataSourceId')
            }
            
            # 提取数值
            for value in point.get('values', []):
                field = value.get('field')
                val = value.get('value')
                unit = value.get('unit', '')
                
                # 构建列名
                if unit:
                    col_name = f"{field}_{unit}"
                else:
                    col_name = field
                
                row[col_name] = val
            
            rows.append(row)
        
        df = pd.DataFrame(rows)
        
        # 转换时间列为datetime
        if 'start_time' in df.columns:
            df['start_time'] = pd.to_datetime(df['start_time'])
        if 'end_time' in df.columns:
            df['end_time'] = pd.to_datetime(df['end_time'])
        
        return df
    
    def get_data_collector_id(self, data_type: str) -> Optional[str]:
        """
        获取数据收集器ID
        注意: 实际使用时需要先调用API创建或查询数据收集器
        
        参数:
            data_type: 数据类型标识
            
        返回:
            数据收集器ID
        """
        # TODO: 实现数据收集器查询逻辑
        # 这里需要调用华为API获取或创建数据收集器
        # 返回一个示例ID
        return f"collector_{data_type}"
    
    def get_daily_steps(self, days: int = 30) -> pd.DataFrame:
        """
        获取每日步数数据
        
        参数:
            days: 获取最近多少天的数据
            
        返回:
            包含步数数据的DataFrame
        """
        end_time = datetime.now(self.timezone)
        start_time = end_time - timedelta(days=days)
        
        data_type_config = self.supported_types.get('steps', {})
        data_type = data_type_config.get('data_type', 'com.huawei.continuous.steps.delta')
        
        # 构建查询参数
        params = {
            "dataTypeName": data_type,
            "startTime": start_time.strftime("%Y-%m-%dT%H:%M:%S.000%z"),
            "endTime": end_time.strftime("%Y-%m-%dT%H:%M:%S.000%z"),
            "limit": self.max_batch_size
        }
        
        # 调用API
        response = self._make_request("GET", "/dataCollectors/{data_collector_id}/data", params=params)
        data_points = response.get('dataPoints', [])
        
        # 转换为DataFrame
        df = self._convert_to_dataframe(data_points, 'steps')
        
        return df
    
    def get_heart_rate_samples(self, hours: int = 24) -> pd.DataFrame:
        """
        获取心率样本数据
        
        参数:
            hours: 获取最近多少小时的数据
            
        返回:
            包含心率数据的DataFrame
        """
        end_time = datetime.now(self.timezone)
        start_time = end_time - timedelta(hours=hours)
        
        data_type_config = self.supported_types.get('heart_rate', {})
        data_type = data_type_config.get('data_type', 'com.huawei.instantaneous.heart_rate')
        
        params = {
            "dataTypeName": data_type,
            "startTime": start_time.strftime("%Y-%m-%dT%H:%M:%S.000%z"),
            "endTime": end_time.strftime("%Y-%m-%dT%H:%M:%S.000%z"),
            "limit": self.max_batch_size
        }
        
        response = self._make_request("GET", "/dataCollectors/{data_collector_id}/data", params=params)
        data_points = response.get('dataPoints', [])
        
        df = self._convert_to_dataframe(data_points, 'heart_rate')
        
        return df
    
    def get_sleep_records(self, days: int = 7) -> List[Dict]:
        """
        获取睡眠记录
        
        参数:
            days: 获取最近多少天的睡眠记录
            
        返回:
            睡眠记录列表
        """
        end_time = datetime.now(self.timezone)
        start_time = end_time - timedelta(days=days)
        
        data_type_config = self.supported_types.get('sleep', {})
        data_type = data_type_config.get('data_type', 'com.huawei.continuous.sleep.summary')
        
        params = {
            "dataTypeName": data_type,
            "startTime": start_time.strftime("%Y-%m-%dT%H:%M:%S.000%z"),
            "endTime": end_time.strftime("%Y-%m-%dT%H:%M:%S.000%z"),
            "limit": self.max_batch_size
        }
        
        response = self._make_request("GET", "/healthRecords", params=params)
        sleep_records = response.get('sleepRecords', [])
        
        return sleep_records
    
    def get_daily_summary(self, date: Union[str, datetime] = None) -> Dict:
        """
        获取指定日期的健康数据摘要
        
        参数:
            date: 日期,如果为None则返回今天的摘要
            
        返回:
            包含各类健康数据摘要的字典
        """
        if date is None:
            date = datetime.now(self.timezone)
        elif isinstance(date, str):
            date = datetime.strptime(date, "%Y-%m-%d").replace(tzinfo=self.timezone)
        
        start_of_day = date.replace(hour=0, minute=0, second=0, microsecond=0)
        end_of_day = start_of_day + timedelta(days=1) - timedelta(microseconds=1)
        
        # 获取步数
        steps_df = self.get_data_by_range('steps', start_of_day, end_of_day)
        total_steps = steps_df['steps_steps'].sum() if 'steps_steps' in steps_df.columns else 0
        
        # 获取卡路里
        calories_df = self.get_data_by_range('calories', start_of_day, end_of_day)
        total_calories = calories_df['calories_kcal'].sum() if 'calories_kcal' in calories_df.columns else 0
        
        # 获取距离
        distance_df = self.get_data_by_range('distance', start_of_day, end_of_day)
        total_distance = distance_df['distance_km'].sum() if 'distance_km' in distance_df.columns else 0
        
        summary = {
            'date': date.strftime("%Y-%m-%d"),
            'steps': total_steps,
            'calories': total_calories,
            'distance_km': total_distance
        }
        
        return summary
    
    def get_data_by_range(self, data_type: str, start_time: datetime, 
                        end_time: datetime) -> pd.DataFrame:
        """
        获取指定时间范围的数据
        
        参数:
            data_type: 数据类型(steps, calories, distance等)
            start_time: 开始时间
            end_time: 结束时间
            
        返回:
            数据DataFrame
        """
        data_type_config = self.supported_types.get(data_type, {})
        data_type_name = data_type_config.get('data_type')
        
        if not data_type_name:
            raise ValueError(f"不支持的数据类型: {data_type}")
        
        params = {
            "dataTypeName": data_type_name,
            "startTime": start_time.strftime("%Y-%m-%dT%H:%M:%S.000%z"),
            "endTime": end_time.strftime("%Y-%m-%dT%H:%M:%S.000%z"),
            "limit": self.max_batch_size
        }
        
        response = self._make_request("GET", "/dataCollectors/{data_collector_id}/data", params=params)
        data_points = response.get('dataPoints', [])
        
        df = self._convert_to_dataframe(data_points, data_type)
        
        return df
    
    def get_activity_report(self) -> Dict:
        """
        获取运动活动报告(三环数据)
        
        返回:
            活动报告字典
        """
        response = self._make_request("GET", "/activityReport")
        return response
    
    def close(self):
        """
        关闭session
        """
        self.session.close()
