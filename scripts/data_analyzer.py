"""
华为运动健康数据分析模块
提供数据清洗、统计分析和可视化功能
"""

import json
import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import pandas as pd
import numpy as np
from pytz import timezone


class HealthDataAnalyzer:
    """健康数据分析器"""
    
    def __init__(self, config: Dict = None):
        """
        初始化分析器
        
        参数:
            config: 配置字典
        """
        self.config = config or {}
        self.processing_config = self.config.get('processing', {})
        self.analysis_config = self.config.get('analysis', {})
        
        # 时区设置
        self.timezone_str = self.processing_config.get('timezone', 'Asia/Shanghai')
        self.timezone = timezone(self.timezone_str)
        
        # 异常值检测配置
        self.anomaly_config = self.processing_config.get('anomaly_detection', {})
        self.anomaly_enabled = self.anomaly_config.get('enabled', True)
        self.anomaly_method = self.anomaly_config.get('method', 'iqr')
        self.anomaly_threshold = self.anomaly_config.get('threshold', 1.5)
        
        # 缺失值处理配置
        self.missing_config = self.processing_config.get('missing_value', {})
        self.missing_strategy = self.missing_config.get('strategy', 'interpolate')
        
        # 统计配置
        self.stats_config = self.analysis_config.get('statistics', {})
        
    def clean_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        清洗数据:处理缺失值、异常值和重复数据
        
        参数:
            df: 原始数据DataFrame
            
        返回:
            清洗后的DataFrame
        """
        if df.empty:
            return df
        
        df_cleaned = df.copy()
        
        # 1. 删除重复数据
        df_cleaned = df_cleaned.drop_duplicates()
        
        # 2. 处理缺失值
        df_cleaned = self._handle_missing_values(df_cleaned)
        
        # 3. 检测和处理异常值
        if self.anomaly_enabled:
            df_cleaned = self._detect_and_handle_anomalies(df_cleaned)
        
        # 4. 排序数据
        if 'start_time' in df_cleaned.columns:
            df_cleaned = df_cleaned.sort_values('start_time')
        
        return df_cleaned
    
    def _handle_missing_values(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        处理缺失值
        
        参数:
            df: 数据DataFrame
            
        返回:
            处理后的DataFrame
        """
        df_handled = df.copy()
        
        # 识别数值列
        numeric_columns = df_handled.select_dtypes(include=[np.number]).columns
        
        if self.missing_strategy == 'interpolate':
            # 线性插值
            df_handled[numeric_columns] = df_handled[numeric_columns].interpolate(method='linear')
        elif self.missing_strategy == 'forward_fill':
            # 前向填充
            df_handled[numeric_columns] = df_handled[numeric_columns].fillna(method='ffill')
        elif self.missing_strategy == 'drop':
            # 删除缺失值
            df_handled = df_handled.dropna(subset=numeric_columns)
        
        # 用0填充剩余的缺失值
        df_handled[numeric_columns] = df_handled[numeric_columns].fillna(0)
        
        return df_handled
    
    def _detect_and_handle_anomalies(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        检测和处理异常值
        
        参数:
            df: 数据DataFrame
            
        返回:
            处理异常值后的DataFrame
        """
        df_handled = df.copy()
        
        # 识别数值列
        numeric_columns = df_handled.select_dtypes(include=[np.number]).columns
        
        for col in numeric_columns:
            if col in ['start_time', 'end_time']:
                continue
            
            if self.anomaly_method == 'iqr':
                # 四分位距法
                Q1 = df_handled[col].quantile(0.25)
                Q3 = df_handled[col].quantile(0.75)
                IQR = Q3 - Q1
                lower_bound = Q1 - self.anomaly_threshold * IQR
                upper_bound = Q3 + self.anomaly_threshold * IQR
                
                # 标记异常值
                anomalies = (df_handled[col] < lower_bound) | (df_handled[col] > upper_bound)
                
                # 用边界值替换异常值(缩尾处理)
                df_handled.loc[df_handled[col] < lower_bound, col] = lower_bound
                df_handled.loc[df_handled[col] > upper_bound, col] = upper_bound
                
            elif self.anomaly_method == 'zscore':
                # Z分数法
                mean = df_handled[col].mean()
                std = df_handled[col].std()
                if std > 0:
                    z_scores = np.abs((df_handled[col] - mean) / std)
                    # 用平均值替换异常值
                    df_handled.loc[z_scores > self.anomaly_threshold, col] = mean
        
        return df_handled
    
    def calculate_statistics(self, df: pd.DataFrame, value_column: str = None) -> Dict:
        """
        计算统计指标
        
        参数:
            df: 数据DataFrame
            value_column: 要分析的数值列名,如果为None则自动识别
            
        返回:
            统计指标字典
        """
        if df.empty:
            return {}
        
        # 自动识别数值列
        if value_column is None:
            numeric_columns = df.select_dtypes(include=[np.number]).columns.tolist()
            # 排除时间列
            numeric_columns = [col for col in numeric_columns 
                             if col not in ['start_time', 'end_time']]
            if numeric_columns:
                value_column = numeric_columns[0]
            else:
                return {}
        
        if value_column not in df.columns:
            return {}
        
        values = df[value_column].dropna()
        
        stats = {
            'column': value_column,
            'count': len(values),
            'mean': float(values.mean()) if self.stats_config.get('calculate_mean', True) else None,
            'median': float(values.median()) if self.stats_config.get('calculate_median', True) else None,
            'std': float(values.std()) if self.stats_config.get('calculate_std', True) else None,
            'min': float(values.min()) if self.stats_config.get('calculate_min_max', True) else None,
            'max': float(values.max()) if self.stats_config.get('calculate_min_max', True) else None,
            'q25': float(values.quantile(0.25)),
            'q75': float(values.quantile(0.75))
        }
        
        # 移除None值
        stats = {k: v for k, v in stats.items() if v is not None}
        
        return stats
    
    def analyze_trends(self, df: pd.DataFrame, value_column: str = None,
                     window_size: int = 7) -> Dict:
        """
        分析数据趋势
        
        参数:
            df: 数据DataFrame
            value_column: 数值列名
            window_size: 移动平均窗口大小
            
        返回:
            趋势分析结果
        """
        if df.empty:
            return {}
        
        # 自动识别数值列
        if value_column is None:
            numeric_columns = df.select_dtypes(include=[np.number]).columns.tolist()
            numeric_columns = [col for col in numeric_columns 
                             if col not in ['start_time', 'end_time']]
            if numeric_columns:
                value_column = numeric_columns[0]
            else:
                return {}
        
        if value_column not in df.columns or 'start_time' not in df.columns:
            return {}
        
        df_sorted = df.sort_values('start_time').copy()
        df_sorted['date'] = df_sorted['start_time'].dt.date
        
        # 按日期聚合
        daily_data = df_sorted.groupby('date')[value_column].sum().reset_index()
        
        # 计算移动平均
        window = min(window_size, len(daily_data))
        if window > 0:
            daily_data['moving_avg'] = daily_data[value_column].rolling(
                window=window, min_periods=1
            ).mean()
        else:
            daily_data['moving_avg'] = daily_data[value_column]
        
        # 计算趋势(线性回归斜率)
        if len(daily_data) > 1:
            x = np.arange(len(daily_data))
            y = daily_data[value_column].values
            slope = np.polyfit(x, y, 1)[0]
            
            # 判断趋势方向
            if slope > 0.01:
                trend = '上升'
            elif slope < -0.01:
                trend = '下降'
            else:
                trend = '稳定'
        else:
            slope = 0
            trend = '数据不足'
        
        trend_info = {
            'trend': trend,
            'slope': float(slope),
            'current_value': float(daily_data[value_column].iloc[-1]) if len(daily_data) > 0 else 0,
            'average_value': float(daily_data[value_column].mean()),
            'max_value': float(daily_data[value_column].max()),
            'min_value': float(daily_data[value_column].min()),
            'data_points': len(daily_data)
        }
        
        return trend_info
    
    def detect_anomalies_in_data(self, df: pd.DataFrame, 
                                value_column: str = None) -> List[Dict]:
        """
        检测数据中的异常点(不修改数据)
        
        参数:
            df: 数据DataFrame
            value_column: 数值列名
            
        返回:
            异常点列表
        """
        if df.empty:
            return []
        
        # 自动识别数值列
        if value_column is None:
            numeric_columns = df.select_dtypes(include=[np.number]).columns.tolist()
            numeric_columns = [col for col in numeric_columns 
                             if col not in ['start_time', 'end_time']]
            if numeric_columns:
                value_column = numeric_columns[0]
            else:
                return []
        
        if value_column not in df.columns:
            return []
        
        anomalies = []
        
        if self.anomaly_method == 'iqr':
            Q1 = df[value_column].quantile(0.25)
            Q3 = df[value_column].quantile(0.75)
            IQR = Q3 - Q1
            lower_bound = Q1 - self.anomaly_threshold * IQR
            upper_bound = Q3 + self.anomaly_threshold * IQR
            
            # 找出异常点
            anomaly_mask = (df[value_column] < lower_bound) | (df[value_column] > upper_bound)
            anomaly_df = df[anomaly_mask]
            
            for idx, row in anomaly_df.iterrows():
                anomalies.append({
                    'index': idx,
                    'value': float(row[value_column]),
                    'timestamp': row.get('start_time', 'N/A'),
                    'type': 'low' if row[value_column] < lower_bound else 'high',
                    'expected_range': f"{lower_bound:.2f} - {upper_bound:.2f}"
                })
        
        elif self.anomaly_method == 'zscore':
            mean = df[value_column].mean()
            std = df[value_column].std()
            
            if std > 0:
                z_scores = np.abs((df[value_column] - mean) / std)
                anomaly_mask = z_scores > self.anomaly_threshold
                anomaly_df = df[anomaly_mask]
                
                for idx, row in anomaly_df.iterrows():
                    anomalies.append({
                        'index': idx,
                        'value': float(row[value_column]),
                        'timestamp': row.get('start_time', 'N/A'),
                        'z_score': float(z_scores[idx]),
                        'mean': float(mean),
                        'std': float(std)
                    })
        
        return anomalies
    
    def generate_weekly_report(self, df: pd.DataFrame) -> Dict:
        """
        生成周度数据报告
        
        参数:
            df: 数据DataFrame
            
        返回:
            周度报告字典
        """
        if df.empty:
            return {'error': '数据为空'}
        
        df_sorted = df.sort_values('start_time').copy()
        df_sorted['date'] = df_sorted['start_time'].dt.date
        df_sorted['weekday'] = df_sorted['start_time'].dt.day_name()
        
        # 按日期和星期聚合
        numeric_columns = df_sorted.select_dtypes(include=[np.number]).columns.tolist()
        numeric_columns = [col for col in numeric_columns 
                         if col not in ['start_time', 'end_time']]
        
        daily_summary = []
        for date, group in df_sorted.groupby('date'):
            day_data = {
                'date': date.strftime("%Y-%m-%d"),
                'weekday': group['weekday'].iloc[0]
            }
            
            for col in numeric_columns:
                day_data[col] = float(group[col].sum())
            
            daily_summary.append(day_data)
        
        # 计算周汇总
        weekly_summary = {}
        for col in numeric_columns:
            weekly_summary[col] = float(df_sorted[col].sum())
        
        # 识别趋势
        if len(daily_summary) >= 2:
            first_half_avg = np.mean([day.get(numeric_columns[0], 0) 
                                    for day in daily_summary[:len(daily_summary)//2]])
            second_half_avg = np.mean([day.get(numeric_columns[0], 0) 
                                     for day in daily_summary[len(daily_summary)//2:]])
            
            if second_half_avg > first_half_avg * 1.1:
                trend = '本周呈上升趋势'
            elif second_half_avg < first_half_avg * 0.9:
                trend = '本周呈下降趋势'
            else:
                trend = '本周保持稳定'
        else:
            trend = '数据不足以判断趋势'
        
        report = {
            'period': 'weekly',
            'start_date': df_sorted['date'].min().strftime("%Y-%m-%d"),
            'end_date': df_sorted['date'].max().strftime("%Y-%m-%d"),
            'daily_summary': daily_summary,
            'weekly_summary': weekly_summary,
            'trend': trend,
            'data_points': len(df_sorted)
        }
        
        return report
    
    def generate_text_report(self, analysis_result: Dict, 
                           data_type: str = 'steps') -> str:
        """
        生成文本格式的分析报告
        
        参数:
            analysis_result: 分析结果字典
            data_type: 数据类型名称
            
        返回:
            文本报告字符串
        """
        report_lines = []
        report_lines.append("=" * 60)
        report_lines.append(f"华为运动健康数据分析报告 - {data_type}")
        report_lines.append("=" * 60)
        report_lines.append("")
        
        # 统计信息
        if 'mean' in analysis_result:
            stats = analysis_result
            report_lines.append("【统计摘要】")
            report_lines.append(f"  数据点数量: {stats.get('count', 0)}")
            report_lines.append(f"  平均值: {stats.get('mean', 0):.2f}")
            report_lines.append(f"  中位数: {stats.get('median', 0):.2f}")
            report_lines.append(f"  标准差: {stats.get('std', 0):.2f}")
            report_lines.append(f"  最小值: {stats.get('min', 0):.2f}")
            report_lines.append(f"  最大值: {stats.get('max', 0):.2f}")
            report_lines.append("")
        
        # 趋势分析
        if 'trend' in analysis_result:
            trend = analysis_result
            report_lines.append("【趋势分析】")
            report_lines.append(f"  趋势方向: {trend.get('trend', 'N/A')}")
            report_lines.append(f"  当前值: {trend.get('current_value', 0):.2f}")
            report_lines.append(f"  平均值: {trend.get('average_value', 0):.2f}")
            report_lines.append(f"  变化率: {trend.get('slope', 0):.4f}")
            report_lines.append("")
        
        # 异常检测
        if isinstance(analysis_result, dict) and 'anomalies' in analysis_result:
            anomalies = analysis_result['anomalies']
            report_lines.append("【异常检测】")
            if anomalies:
                report_lines.append(f"  检测到 {len(anomalies)} 个异常点:")
                for i, anomaly in enumerate(anomalies[:5], 1):  # 只显示前5个
                    report_lines.append(f"    {i}. 时间: {anomaly.get('timestamp', 'N/A')}, "
                                      f"值: {anomaly.get('value', 0):.2f}")
                if len(anomalies) > 5:
                    report_lines.append(f"    ... 以及其他 {len(anomalies) - 5} 个异常点")
            else:
                report_lines.append("  未检测到异常数据点")
            report_lines.append("")
        
        # 建议
        report_lines.append("【健康建议】")
        if 'trend' in analysis_result:
            trend = analysis_result.get('trend', '')
            if '上升' in trend and data_type == 'steps':
                report_lines.append("  ✓ 您的步数呈上升趋势,请继续保持!")
            elif '下降' in trend and data_type == 'steps':
                report_lines.append("  ⚠ 您的步数有所下降,建议适当增加日常活动量")
        
        report_lines.append("")
        report_lines.append(f"报告生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report_lines.append("=" * 60)
        
        return "\n".join(report_lines)
    
    def get_recommendations(self, analysis_result: Dict, 
                          data_type: str = 'steps') -> List[str]:
        """
        基于分析结果生成健康建议
        
        参数:
            analysis_result: 分析结果字典
            data_type: 数据类型名称
            
        返回:
            建议列表
        """
        recommendations = []
        
        if data_type == 'steps':
            if 'mean' in analysis_result:
                avg_steps = analysis_result.get('mean', 0)
                if avg_steps < 5000:
                    recommendations.append(
                        "您的日均步数较低,建议每天至少步行30分钟,目标逐步提高到8000步"
                    )
                elif avg_steps < 8000:
                    recommendations.append(
                        "您的步数适中,可以尝试增加快走或慢跑,目标提高到10000步"
                    )
                else:
                    recommendations.append(
                        "您的步数表现优秀,继续保持!注意适度休息,避免过度疲劳"
                    )
        
        elif data_type == 'heart_rate':
            if 'mean' in analysis_result:
                avg_hr = analysis_result.get('mean', 0)
                if avg_hr > 100:
                    recommendations.append(
                        "您的平均心率偏高,建议进行适度有氧运动,改善心肺功能"
                    )
                elif avg_hr < 60:
                    recommendations.append(
                        "您的平均心率较低,这可能表示良好的心肺功能,建议定期监测"
                    )
        
        elif data_type == 'sleep':
            if 'mean' in analysis_result:
                avg_sleep = analysis_result.get('mean', 0)
                if avg_sleep < 6 * 60:  # 少于6小时
                    recommendations.append(
                        "您的平均睡眠时间不足,建议保证每天7-8小时的睡眠"
                    )
                elif avg_sleep > 10 * 60:  # 超过10小时
                    recommendations.append(
                        "您的睡眠时间较长,如无特殊需要,建议适当调整作息"
                    )
        
        if not recommendations:
            recommendations.append("数据表现正常,请继续保持健康的生活方式")
        
        return recommendations
