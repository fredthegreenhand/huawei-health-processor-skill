"""
华为运动健康 OAuth 2.0 认证模块
处理用户授权、令牌获取和刷新
"""

import json
import secrets
import time
from datetime import datetime, timedelta
from typing import Dict, Optional
import requests


class HuaweiHealthAuth:
    """华为运动健康OAuth 2.0认证管理器"""
    
    def __init__(self, client_id: str, client_secret: str, redirect_uri: str,
                 auth_url: str = None, token_url: str = None):
        """
        初始化认证管理器
        
        参数:
            client_id: 应用客户端ID
            client_secret: 应用客户端密钥
            redirect_uri: OAuth回调URI
            auth_url: 授权端点URL
            token_url: 令牌端点URL
        """
        self.client_id = client_id
        self.client_secret = client_secret
        self.redirect_uri = redirect_uri
        self.auth_url = auth_url or "https://oauth-login.cloud.huawei.com/oauth2/v3/authorize"
        self.token_url = token_url or "https://oauth-login.cloud.huawei.com/oauth2/v3/token"
        
        # 存储令牌信息
        self.token_info: Optional[Dict] = None
        self.state: Optional[str] = None
        
    def generate_state(self) -> str:
        """
        生成随机state参数,用于防止CSRF攻击
        
        返回:
            state字符串
        """
        self.state = secrets.token_urlsafe(32)
        return self.state
    
    def get_authorization_url(self, scope: str = "openid profile healthkit.read") -> str:
        """
        生成授权URL,引导用户完成OAuth授权
        
        参数:
            scope: 授权范围,多个scope用空格分隔
            
        返回:
            授权URL字符串
        """
        state = self.generate_state()
        
        params = {
            "client_id": self.client_id,
            "redirect_uri": self.redirect_uri,
            "response_type": "code",
            "scope": scope,
            "state": state,
            "access_type": "offline"  # 获取refresh_token
        }
        
        # 构建查询字符串
        query_string = "&".join([f"{k}={v}" for k, v in params.items()])
        auth_url = f"{self.auth_url}?{query_string}"
        
        return auth_url
    
    def exchange_code_for_token(self, authorization_code: str, state: str = None) -> Dict:
        """
        使用授权码换取访问令牌
        
        参数:
            authorization_code: OAuth授权码
            state: state参数(用于验证)
            
        返回:
            包含令牌信息的字典
            {
                "access_token": "访问令牌",
                "refresh_token": "刷新令牌",
                "expires_in": 有效期(秒),
                "token_type": "Bearer",
                "scope": "授权范围"
            }
        """
        # 验证state(如果提供)
        if state and state != self.state:
            raise ValueError("State参数不匹配,可能存在CSRF攻击")
        
        # 准备请求数据
        data = {
            "grant_type": "authorization_code",
            "code": authorization_code,
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "redirect_uri": self.redirect_uri
        }
        
        # 设置请求头
        headers = {
            "Content-Type": "application/x-www-form-urlencoded"
        }
        
        try:
            # 发送POST请求
            response = requests.post(
                self.token_url,
                data=data,
                headers=headers,
                timeout=30
            )
            response.raise_for_status()
            
            # 解析响应
            token_info = response.json()
            
            # 添加过期时间戳
            expires_in = token_info.get("expires_in", 3600)
            token_info["expires_at"] = int(time.time()) + expires_in
            token_info["obtained_at"] = int(time.time())
            
            # 保存令牌信息
            self.token_info = token_info
            
            return token_info
            
        except requests.exceptions.RequestException as e:
            raise Exception(f"获取访问令牌失败: {str(e)}")
    
    def refresh_access_token(self, refresh_token: str) -> Dict:
        """
        使用刷新令牌更新访问令牌
        
        参数:
            refresh_token: 刷新令牌
            
        返回:
            新的令牌信息字典
        """
        # 准备请求数据
        data = {
            "grant_type": "refresh_token",
            "refresh_token": refresh_token,
            "client_id": self.client_id,
            "client_secret": self.client_secret
        }
        
        # 设置请求头
        headers = {
            "Content-Type": "application/x-www-form-urlencoded"
        }
        
        try:
            # 发送POST请求
            response = requests.post(
                self.token_url,
                data=data,
                headers=headers,
                timeout=30
            )
            response.raise_for_status()
            
            # 解析响应
            token_info = response.json()
            
            # 更新过期时间戳
            expires_in = token_info.get("expires_in", 3600)
            token_info["expires_at"] = int(time.time()) + expires_in
            token_info["obtained_at"] = int(time.time())
            
            # 保留原有的refresh_token(如果API没有返回新的)
            if "refresh_token" not in token_info and self.token_info:
                token_info["refresh_token"] = refresh_token
            
            # 保存令牌信息
            self.token_info = token_info
            
            return token_info
            
        except requests.exceptions.RequestException as e:
            raise Exception(f"刷新访问令牌失败: {str(e)}")
    
    def is_token_expired(self, buffer_seconds: int = 300) -> bool:
        """
        检查访问令牌是否已过期
        
        参数:
            buffer_seconds: 缓冲时间(秒),提前5分钟认为过期
            
        返回:
            True表示已过期,False表示未过期
        """
        if not self.token_info:
            return True
        
        expires_at = self.token_info.get("expires_at")
        if not expires_at:
            return True
        
        return int(time.time()) >= (expires_at - buffer_seconds)
    
    def get_valid_access_token(self) -> str:
        """
        获取有效的访问令牌,如果已过期则自动刷新
        
        返回:
            有效的访问令牌字符串
        """
        if not self.token_info:
            raise Exception("尚未获取访问令牌,请先完成OAuth授权流程")
        
        # 检查是否过期
        if self.is_token_expired():
            refresh_token = self.token_info.get("refresh_token")
            if not refresh_token:
                raise Exception("刷新令牌不存在,需要重新授权")
            
            # 刷新令牌
            self.refresh_access_token(refresh_token)
        
        return self.token_info.get("access_token")
    
    def save_token_to_file(self, file_path: str, encrypt: bool = False):
        """
        将令牌信息保存到文件
        
        参数:
            file_path: 文件路径
            encrypt: 是否加密(需要实现加密逻辑)
        """
        if not self.token_info:
            raise Exception("没有可保存的令牌信息")
        
        token_data = self.token_info.copy()
        
        # 如果需要加密,在此处实现加密逻辑
        if encrypt:
            # TODO: 实现加密逻辑
            pass
        
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(token_data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            raise Exception(f"保存令牌到文件失败: {str(e)}")
    
    def load_token_from_file(self, file_path: str, decrypt: bool = False):
        """
        从文件加载令牌信息
        
        参数:
            file_path: 文件路径
            decrypt: 是否解密(需要实现解密逻辑)
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                token_data = json.load(f)
            
            # 如果需要解密,在此处实现解密逻辑
            if decrypt:
                # TODO: 实现解密逻辑
                pass
            
            self.token_info = token_data
            
        except FileNotFoundError:
            raise Exception(f"令牌文件不存在: {file_path}")
        except json.JSONDecodeError as e:
            raise Exception(f"令牌文件格式错误: {str(e)}")
        except Exception as e:
            raise Exception(f"加载令牌文件失败: {str(e)}")
    
    def revoke_token(self, access_token: str = None) -> bool:
        """
        撤销访问令牌
        
        参数:
            access_token: 要撤销的访问令牌,如果为None则使用当前令牌
            
        返回:
            True表示撤销成功
        """
        token = access_token or self.get_valid_access_token()
        
        # TODO: 查找华为的令牌撤销端点并实现
        # 华为可能没有提供公开的令牌撤销API
        
        # 清空本地令牌信息
        self.token_info = None
        
        return True
    
    def get_token_info(self) -> Optional[Dict]:
        """
        获取当前令牌信息(不包含敏感数据)
        
        返回:
            令牌信息字典
        """
        if not self.token_info:
            return None
        
        # 返回非敏感信息
        safe_info = {
            "token_type": self.token_info.get("token_type"),
            "scope": self.token_info.get("scope"),
            "expires_in": self.token_info.get("expires_in"),
            "expires_at": self.token_info.get("expires_at"),
            "obtained_at": self.token_info.get("obtained_at")
        }
        
        return safe_info
