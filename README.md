# Huawei Health Data Processor for OpenClaw

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![OpenClaw](https://img.shields.io/badge/OpenClaw-compatible-green.svg)](https://openclaws.io)

一个功能强大的OpenClaw技能,用于从华为运动健康服务API获取用户的运动健康数据,并进行自动化分析处理。

## ✨ 功能特性

- 🔐 **完整的OAuth 2.0认证流程** - 支持用户授权、令牌获取和自动刷新
- 📊 **多维度健康数据支持** - 步数、卡路里、距离、心率、睡眠、血氧、压力
- 🧹 **智能数据清洗** - 自动处理缺失值、异常值和重复数据
- 📈 **统计分析与趋势识别** - 移动平均、线性回归、异常检测
- 📝 **自动化报告生成** - 文本报告、健康建议和可视化图表
- 🔒 **安全可靠** - 支持令牌加密存储、SSL验证和请求限流
- ⚙️ **高度可配置** - 支持自定义处理策略、分析参数和输出格式

## 📋 系统要求

- **Python**: 3.8 或更高版本
- **OpenClaw**: 最新版本
- **华为开发者账号**: 需要在[华为开发者联盟](https://developer.huawei.com)注册并通过运动健康服务审核

## 🚀 快速开始

### 1. 安装依赖

```bash
pip install -r scripts/requirements.txt
```

### 2. 配置认证信息

在华为开发者联盟完成以下步骤:
1. 创建应用项目,获取 `client_id` 和 `client_secret`
2. 申请运动健康服务权限
3. 在 `config.yaml` 中配置认证信息:

```yaml
auth:
  client_id: "your_client_id"
  client_secret: "your_client_secret"
  redirect_uri: "http://localhost:8080/callback"
```

### 3. 完成OAuth授权

运行以下命令获取授权URL:

```python
from scripts.auth import HuaweiHealthAuth

auth = HuaweiHealthAuth(
    client_id="your_client_id",
    client_secret="your_client_secret",
    redirect_uri="http://localhost:8080/callback"
)

auth_url = auth.get_authorization_url()
print(f"请访问以下URL完成授权: {auth_url}")
```

访问授权URL,完成授权后会获取授权码,使用授权码换取访问令牌:

```python
token_info = auth.exchange_code_for_token(authorization_code="your_auth_code")
```

### 4. 使用技能

获取最近30天的步数数据:

```python
from scripts.data_fetcher import HuaweiHealthDataFetcher
from scripts.data_analyzer import HealthDataAnalyzer

# 初始化数据获取器
fetcher = HuaweiHealthDataFetcher(auth=auth, config=config)

# 获取步数数据
steps_df = fetcher.get_daily_steps(days=30)

# 分析数据
analyzer = HealthDataAnalyzer(config=config)
cleaned_data = analyzer.clean_data(steps_df)
statistics = analyzer.calculate_statistics(cleaned_data, value_column='steps_steps')
trends = analyzer.analyze_trends(cleaned_data, value_column='steps_steps')

# 生成报告
report = analyzer.generate_text_report({**statistics, **trends}, data_type='steps')
print(report)
```

## 📖 使用示例

### 示例1: 获取多维度健康数据

```python
# 获取心率数据
heart_rate_df = fetcher.get_heart_rate_samples(hours=24)

# 获取睡眠记录
sleep_records = fetcher.get_sleep_records(days=7)

# 获取每日摘要
daily_summary = fetcher.get_daily_summary(date="2026-03-23")
```

### 示例2: 异常检测

```python
# 检测数据中的异常点
anomalies = analyzer.detect_anomalies_in_data(data, value_column='heart_rate_bpm')

for anomaly in anomalies:
    print(f"异常点: 时间={anomaly['timestamp']}, 值={anomaly['value']}")
```

### 示例3: 生成周度报告

```python
# 生成周度分析报告
weekly_report = analyzer.generate_weekly_report(steps_df)

# 获取健康建议
recommendations = analyzer.get_recommendations(
    analysis_result=weekly_report['weekly_summary'],
    data_type='steps'
)

print("健康建议:")
for rec in recommendations:
    print(f"  • {rec}")
```

### 示例4: 在OpenClaw中使用

```bash
# 安装技能
openclaw skill install huawei-health-processor-skill.zip

# 在OpenClaw中使用自然语言查询
"请帮我获取最近30天的步数数据,并生成趋势分析报告"
"分析上周的睡眠数据,告诉我平均睡眠时长和睡眠质量评分"
"检测我的运动数据中是否存在异常值,并给出建议"
```

## 🏗️ 技术架构

```
huawei-health-processor/
├── SKILL.md                  # 技能描述文档
├── config.yaml              # 配置文件
└── scripts/
    ├── __init__.py          # 包初始化
    ├── auth.py              # OAuth 2.0认证模块
    ├── data_fetcher.py      # 数据获取模块
    ├── data_analyzer.py     # 数据分析模块
    └── requirements.txt     # Python依赖包
```

### 核心模块说明

| 模块 | 功能 |
|------|------|
| `HuaweiHealthAuth` | 处理OAuth 2.0认证流程,包括授权、令牌获取和刷新 |
| `HuaweiHealthDataFetcher` | 从华为健康API获取各类运动健康数据 |
| `HealthDataAnalyzer` | 数据清洗、统计分析、趋势检测和报告生成 |

## ⚙️ 配置说明

### 认证配置 (config.yaml)

```yaml
auth:
  client_id: "${HUAWEI_CLIENT_ID}"
  client_secret: "${HUAWEI_CLIENT_SECRET}"
  redirect_uri: "http://localhost:8080/callback"
  scope: "openid profile healthkit.read healthkit.write"
```

### 数据处理配置

```yaml
processing:
  anomaly_detection:
    enabled: true
    method: "iqr"  # iqr或zscore
    threshold: 1.5

  missing_value:
    strategy: "interpolate"  # interpolate/forward_fill/drop

  timezone: "Asia/Shanghai"
```

### 分析配置

```yaml
analysis:
  trend:
    enabled: true
    window_size: 7

  report:
    include_charts: true
    include_recommendations: true
```

## 🔒 安全性

- **令牌加密存储**: 支持将访问令牌加密存储到本地文件
- **SSL验证**: 所有API请求使用HTTPS和SSL证书验证
- **请求限流**: 内置请求限流机制,防止超过API配额
- **环境变量**: 敏感信息通过环境变量配置,避免硬编码

## 📊 支持的数据类型

| 数据类型 | API标识 | 单位 | 说明 |
|----------|---------|------|------|
| 步数 | `com.huawei.continuous.steps.delta` | steps | 每日步数 |
| 卡路里 | `com.huawei.continuous.calories.burnt` | kcal | 消耗的卡路里 |
| 距离 | `com.huawei.continuous.distance.delta` | km | 运动距离 |
| 心率 | `com.huawei.instantaneous.heart_rate` | bpm | 实时心率 |
| 睡眠 | `com.huawei.continuous.sleep.summary` | minutes | 睡眠时长和质量 |
| 血氧 | `com.huawei.instantaneous.spo2` | % | 血氧饱和度 |
| 压力 | `com.huawei.instantaneous.stress` | score | 压力指数 |

## 🐛 常见问题

### Q1: 如何获取华为运动健康服务权限?

A: 需要在[华为开发者联盟](https://developer.huawei.com)注册账号,创建应用项目,然后在AppGallery Connect中申请运动健康服务权限。审核通常需要3-5个工作日。

### Q2: Access Token过期怎么办?

A: 技能会自动检测token过期并使用refresh_token进行刷新。如果refresh_token也过期,需要重新完成OAuth授权流程。

### Q3: 数据时区显示不正确?

A: 在`config.yaml`中配置正确的时区:
```yaml
processing:
  timezone: "Asia/Shanghai"  # 或你所在的时区
```

### Q4: 如何处理API限流?

A: 技能内置了请求限流机制,可以通过以下配置调整:
```yaml
security:
  rate_limit:
    enabled: true
    max_requests: 100
    time_window: 3600
```

## 🤝 贡献指南

欢迎提交Issue和Pull Request!

1. Fork本仓库
2. 创建特性分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 开启Pull Request

## 📝 更新日志

### [1.0.0] - 2026-03-23

- ✨ 初始版本发布
- ✅ 支持OAuth 2.0认证
- ✅ 支持步数、心率、睡眠等7种数据类型
- ✅ 实现数据清洗和异常检测
- ✅ 生成统计分析和趋势报告
- ✅ 提供完整的配置选项

## 📄 许可证

本项目采用MIT许可证 - 详见 [LICENSE](LICENSE) 文件

## 🙏 致谢

- 华为运动健康服务提供的API支持
- OpenClaw社区提供的技能框架

## 📞 联系方式

- 项目主页: [GitHub Repository](https://github.com/yourusername/huawei-health-processor)
- 问题反馈: [Issues](https://github.com/yourusername/huawei-health-processor/issues)

---

**注意**: 本技能处理的数据包含个人健康信息,请遵守当地法律法规和个人信息保护要求,妥善保管访问令牌和认证密钥。用户有权随时撤销数据访问权限。

如果你觉得这个技能有用,请给个⭐Star支持一下!
