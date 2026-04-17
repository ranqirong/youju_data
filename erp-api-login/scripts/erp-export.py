#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ERP API 客户端 - 最终成功版本
支持完整登录和人事数据导出
"""

import requests
import json
import base64
import hashlib
import time
from datetime import datetime
from pathlib import Path
from Crypto.PublicKey import RSA
from Crypto.Cipher import PKCS1_v1_5

# ============== 配置 ==============

ERP_BASE_URL = "https://erp.yjzf.com"

# 接口别名映射（用于输出显示，隐藏真实接口地址）
API_ALIASES = {
    "/api/sso/security/k": "【公钥接口】",
    "/api/sso/oidc/authorize": "【授权接口】",
    "/api/sso/security/faceLogin": "【人脸登录接口】",
    "/api/sso/oidc/execute": "【密码登录接口】",
    "/api/sso/oidc/accessToken": "【令牌接口】",
    "/api/erp.settings.api/common/userInfo": "【用户信息接口】",
    "/api/common.stats.api/statistics/personnel/export": "【人事数据导出接口】",
    "/api/common.stats.api/customization/statistics/dict": "【指标字典接口】",
    "/api/common.stats.api/customization/statistics/export": "【创建导出接口】",
    "/api/common.stats.api/quantification/statistics/file/list": "【导出文件列表接口】",
    "/api/erp.contract.api/order/estate/query/exportNew": "【新房合同导出接口】",
    "/login": "【登录页面】",
}

def get_api_alias(url):
    """获取接口别名，如果没有匹配则返回 URL 本身"""
    for path, alias in API_ALIASES.items():
        if path in url:
            return alias
    return url

# 默认导出配置
# 【安全提示】不包含默认用户名和密码，必须由用户主动提供
DEFAULT_CONFIG = {
    "phone": None,  # 必须由用户提供
    "password": None,  # 必须由用户提供
    "brand_id": "593347894961426496",
    "branch_ids": [],  # 空数组表示获取所有分支机构
    "export_dir": "~/Downloads/ERP 导出"
}

def get_user_credentials():
    """从配置文件或环境变量获取用户凭证"""
    import os
    
    # 尝试从配置文件读取
    config_paths = [
        os.path.expanduser("~/.openclaw/workspace/configs/erp-credentials.env"),
        os.path.expanduser("~/erp-credentials.env"),
        "configs/erp-credentials.env",
    ]
    
    for config_path in config_paths:
        if os.path.exists(config_path):
            try:
                with open(config_path, 'r', encoding='utf-8') as f:
                    config = {}
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith('#') and '=' in line:
                            key, value = line.split('=', 1)
                            config[key.strip()] = value.strip()
                    
                    phone = config.get('ERP_USERNAME') or config.get('ERP_PHONE')
                    password = config.get('ERP_PASSWORD')
                    
                    # 尝试 base64 解码（兼容旧配置）
                    if phone and len(phone) > 15 and phone.isalnum():
                        try:
                            import base64
                            decoded = base64.b64decode(phone).decode('utf-8')
                            if decoded.isdigit() and len(decoded) >= 10:
                                phone = decoded
                        except:
                            pass  # 不是 base64，使用原值
                    
                    if phone and password:
                        return phone, password
            except Exception as e:
                print(f"⚠️ 读取配置文件失败：{config_path} - {e}")
    
    # 尝试从环境变量读取
    phone = os.environ.get('ERP_USERNAME') or os.environ.get('ERP_PHONE')
    password = os.environ.get('ERP_PASSWORD')
    
    if phone and password:
        return phone, password
    
    return None, None

# ============== ERP API 客户端 ==============

class ERPAPIClient:
    """ERP API 客户端 - 支持完整登录和数据导出"""
    
    def __init__(self, phone, password):
        self.phone = phone
        self.password = password
        self.session = requests.Session()
        self.token = None
        self.user_id = None
        self.headers = self._create_base_headers()
    
    def _create_base_headers(self):
        """创建基础 headers"""
        return {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:148.0) Gecko/20100101 Firefox/148.0',
            'Accept': 'application/json, text/plain, */*',
            'Accept-Language': 'zh-CN,zh;q=0.9,zh-TW;q=0.8,zh-HK;q=0.7,en-US;q=0.6,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate, br, zstd',
            'Content-Type': 'application/json;charset=utf-8',
            'X-Requested-With': 'XMLHttpRequest',
            'Cache-Control': 'no-cache',
            'x-user-agent': 'YJYJ-ERP/v2.5.0',
            'Origin': 'https://erp.yjzf.com',
            'Connection': 'keep-alive',
            'Referer': 'https://erp.yjzf.com/',
            'Sec-Fetch-Dest': 'empty',
            'Sec-Fetch-Mode': 'cors',
            'Sec-Fetch-Site': 'same-origin',
            'TE': 'trailers',
        }
    
    def _rsa_encrypt(self, data):
        """RSA 加密密码"""
        # 获取公钥
        response = self.session.get(
            f"{ERP_BASE_URL}/api/sso/security/k",
            headers=self.headers
        )
        public_key_b64 = response.json()['data']
        
        # URL-safe Base64 转标准 Base64
        public_key_std = public_key_b64.replace('_', '/').replace('-', '+')
        padding = 4 - (len(public_key_std) % 4)
        if padding != 4:
            public_key_std += '=' * padding
        
        # 解码并导入公钥
        key_bytes = base64.b64decode(public_key_std)
        public_key = RSA.import_key(key_bytes)
        
        # 加密
        cipher = PKCS1_v1_5.new(public_key)
        encrypted = cipher.encrypt(data.encode('utf-8'))
        
        return base64.b64encode(encrypted).decode('utf-8')
    
    def login(self):
        """完整登录流程（带严格验证）"""
        print("="*70)
        print("ERP API 登录")
        print("="*70)
        
        try:
            # 1. 访问登录页面获取 Cookie
            print("\n步骤 1: 访问登录页面")
            self.session.get(f"{ERP_BASE_URL}/login")
            print(f"✅ {get_api_alias('/login')} - Cookie 获取成功")
            
            # 2. 获取 RSA 公钥
            print("\n步骤 2: 获取 RSA 公钥")
            response = self.session.get(
                f"{ERP_BASE_URL}/api/sso/security/k",
                headers=self.headers
            )
            if response.status_code != 200:
                print(f"❌ {get_api_alias('/api/sso/security/k')} - 请求失败：{response.status_code}")
                print("\n" + "="*70)
                print("❌ 登录失败：无法获取公钥，请检查网络连接")
                print("="*70)
                return False
            
            try:
                public_key_b64 = response.json()['data']
            except (KeyError, json.JSONDecodeError) as e:
                print(f"❌ {get_api_alias('/api/sso/security/k')} - 响应格式错误：{e}")
                print("\n" + "="*70)
                print("❌ 登录失败：服务器响应异常，请稍后重试")
                print("="*70)
                return False
            
            print(f"✅ {get_api_alias('/api/sso/security/k')} - 公钥获取成功")
            
            # 3. 获取 code_key
            print("\n步骤 3: 获取 code_key")
            state = hashlib.md5(f"{int(time.time()*1000)}".encode()).hexdigest()
            params = {
                'scope': 'openid',
                'response_type': 'code',
                'client_id': '123456789',
                'redirect_url': 'https://localhost:8443/uac/',
                'state': state,
                'auth_type': 'BPassword',
                'date': datetime.now().isoformat()
            }
            
            response = self.session.get(
                f"{ERP_BASE_URL}/api/sso/oidc/authorize",
                headers=self.headers,
                params=params,
                allow_redirects=False
            )
            
            if response.status_code != 200:
                print(f"❌ {get_api_alias('/api/sso/oidc/authorize')} - 请求失败：{response.status_code}")
                print("\n" + "="*70)
                print("❌ 登录失败：授权接口异常，请检查账号权限")
                print("="*70)
                return False
            
            try:
                code_key = response.json()['data']['code_key']
            except (KeyError, json.JSONDecodeError) as e:
                print(f"❌ {get_api_alias('/api/sso/oidc/authorize')} - 响应格式错误：{e}")
                print("\n" + "="*70)
                print("❌ 登录失败：服务器响应异常，请稍后重试")
                print("="*70)
                return False
            
            print(f"✅ {get_api_alias('/api/sso/oidc/authorize')} - code_key: {code_key}")
            
            # 4. FaceLogin
            print("\n步骤 4: FaceLogin")
            data = {"phone": self.phone}
            response = self.session.post(
                f"{ERP_BASE_URL}/api/sso/security/faceLogin",
                headers=self.headers,
                json=data
            )
            
            if response.status_code != 200:
                print(f"❌ {get_api_alias('/api/sso/security/faceLogin')} - 请求失败：{response.status_code}")
                print("\n" + "="*70)
                print("❌ 登录失败：账号不存在或无权限")
                print(f"   手机号：{self.phone}")
                print("="*70)
                return False
            
            try:
                result = response.json()
                if not result.get('succeed') and not result.get('code') == '200':
                    error_msg = result.get('msg', '未知错误')
                    print(f"❌ {get_api_alias('/api/sso/security/faceLogin')} - 验证失败：{error_msg}")
                    print("\n" + "="*70)
                    print("❌ 登录失败：账号验证未通过")
                    print(f"   手机号：{self.phone}")
                    print(f"   错误信息：{error_msg}")
                    print("="*70)
                    return False
                
                self.user_id = result['data']['userId']
            except (KeyError, json.JSONDecodeError, TypeError) as e:
                print(f"❌ {get_api_alias('/api/sso/security/faceLogin')} - 响应格式错误：{e}")
                print("\n" + "="*70)
                print("❌ 登录失败：服务器响应异常，请稍后重试")
                print("="*70)
                return False
            
            print(f"✅ {get_api_alias('/api/sso/security/faceLogin')} - userId: {self.user_id}")
            
            # 5. Execute 登录
            print("\n步骤 5: Execute 登录")
            encrypted_password = self._rsa_encrypt(self.password)
            data = {
                "c_name": "BPasswordLogin",
                "code_key": code_key,
                "input_param": {
                    "username": self.phone,
                    "password": encrypted_password,
                    "regionCode": 86
                }
            }
            
            response = self.session.post(
                f"{ERP_BASE_URL}/api/sso/oidc/execute",
                headers=self.headers,
                json=data
            )
            
            if response.status_code != 200:
                print(f"❌ {get_api_alias('/api/sso/oidc/execute')} - 请求失败：{response.status_code}")
                print("\n" + "="*70)
                print("❌ 登录失败：密码验证接口异常")
                print(f"   手机号：{self.phone}")
                print("="*70)
                return False
            
            try:
                result = response.json()
                if not result.get('succeed') and not result.get('code') == '200':
                    error_msg = result.get('msg', '未知错误')
                    print(f"❌ {get_api_alias('/api/sso/oidc/execute')} - 验证失败：{error_msg}")
                    print("\n" + "="*70)
                    print("❌ 登录失败：用户名或密码错误")
                    print(f"   手机号：{self.phone}")
                    print(f"   错误信息：{error_msg}")
                    print("="*70)
                    print("\n💡 请检查:")
                    print("   1. 手机号是否正确")
                    print("   2. 密码是否正确（注意大小写）")
                    print("   3. 账号是否已被锁定或禁用")
                    print("="*70)
                    return False
                
                code = result['data']['code']
            except (KeyError, json.JSONDecodeError, TypeError) as e:
                print(f"❌ {get_api_alias('/api/sso/oidc/execute')} - 响应格式错误：{e}")
                print("\n" + "="*70)
                print("❌ 登录失败：服务器响应异常，请稍后重试")
                print("="*70)
                return False
            
            print(f"✅ {get_api_alias('/api/sso/oidc/execute')} - code: {code}")
            
            # 6. AccessToken
            print("\n步骤 6: 获取 AccessToken")
            token_data = {
                "code": code,
                "state": state,
                "userId": self.user_id,
                "client_id": "585014642717982720",
                "client_secret": "b9c7398eebe909a01603d5fba2c55086"
            }
            
            response = self.session.post(
                f"{ERP_BASE_URL}/api/sso/oidc/accessToken",
                headers=self.headers,
                json=token_data
            )
            
            if response.status_code != 200:
                print(f"❌ {get_api_alias('/api/sso/oidc/accessToken')} - 请求失败：{response.status_code}")
                print("\n" + "="*70)
                print("❌ 登录失败：Token 接口异常")
                print("="*70)
                return False
            
            try:
                result = response.json()
                if not result.get('succeed') and not result.get('code') == '200':
                    error_msg = result.get('msg', '未知错误')
                    print(f"❌ {get_api_alias('/api/sso/oidc/accessToken')} - 获取失败：{error_msg}")
                    print("\n" + "="*70)
                    print("❌ 登录失败：无法获取访问令牌")
                    print(f"   错误信息：{error_msg}")
                    print("="*70)
                    return False
                
                self.token = result['data']['access_token']
            except (KeyError, json.JSONDecodeError, TypeError) as e:
                print(f"❌ {get_api_alias('/api/sso/oidc/accessToken')} - 响应格式错误：{e}")
                print("\n" + "="*70)
                print("❌ 登录失败：服务器响应异常，请稍后重试")
                print("="*70)
                return False
            
            print(f"✅ {get_api_alias('/api/sso/oidc/accessToken')} - 获取成功")
            print(f"   Token: {self.token[:50]}...")
            
            print("\n" + "="*70)
            print("✅ 登录成功！")
            print("="*70)
            return True
            
        except Exception as e:
            print(f"\n❌ 登录过程发生异常：{e}")
            print("\n" + "="*70)
            print("❌ 登录失败：系统异常")
            print(f"   错误信息：{e}")
            print("="*70)
            return False
    
    def get_user_info(self):
        """获取用户信息（带严格验证）"""
        if not self.token:
            print("❌ 未登录，无法获取用户信息")
            print("\n" + "="*70)
            print("❌ 请先登录")
            print("="*70)
            return None
        
        headers = self.headers.copy()
        headers['Authorization'] = self.token  # 【关键】不加 Bearer 前缀
        headers['X-Organ-Id'] = '593347894961426496'
        headers['X-City-Code'] = '150200'
        headers['X-Brand-Id'] = '593347894961426496'
        
        response = self.session.post(
            f"{ERP_BASE_URL}/api/erp.settings.api/common/userInfo",
            headers=headers,
            json={"code": "pc"}
        )
        
        print(f"\n{get_api_alias('/api/erp.settings.api/common/userInfo')} 状态码：{response.status_code}")
        
        if response.status_code != 200:
            print(f"❌ {get_api_alias('/api/erp.settings.api/common/userInfo')} - 请求失败：{response.status_code}")
            print("\n" + "="*70)
            print("❌ 用户信息获取失败：接口异常")
            print("="*70)
            return None
        
        try:
            result = response.json()
            if not result.get('succeed') and not result.get('code') == '200':
                error_msg = result.get('msg', '未知错误')
                print(f"❌ {get_api_alias('/api/erp.settings.api/common/userInfo')} - 返回错误：{error_msg}")
                print("\n" + "="*70)
                print("❌ 用户信息获取失败")
                print(f"   错误信息：{error_msg}")
                print("="*70)
                return None
            
            data = result.get('data')
            if not data:
                print(f"❌ {get_api_alias('/api/erp.settings.api/common/userInfo')} - 返回数据为空")
                print("\n" + "="*70)
                print("❌ 用户信息获取失败：数据为空")
                print("="*70)
                print("\n💡 可能原因:")
                print("   1. 账号权限不足")
                print("   2. 账号已被禁用")
                print("   3. 系统配置异常")
                print("="*70)
                return None
            
            # 验证关键字段
            user_name = data.get('userName', '')
            if not user_name:
                print(f"❌ {get_api_alias('/api/erp.settings.api/common/userInfo')} - 用户名为空")
                print("\n" + "="*70)
                print("❌ 用户信息不完整：缺少用户名")
                print("="*70)
                return None
            
            print(f"✅ {get_api_alias('/api/erp.settings.api/common/userInfo')} - 获取用户信息成功")
            print(f"   用户：{user_name}")
            if data.get('organName'):
                print(f"   组织：{data.get('organName')}")
            if data.get('phone'):
                print(f"   手机：{data.get('phone')}")
            
            return data
            
        except json.JSONDecodeError as e:
            print(f"❌ {get_api_alias('/api/erp.settings.api/common/userInfo')} - 响应格式错误：{e}")
            print("\n" + "="*70)
            print("❌ 用户信息获取失败：服务器响应异常")
            print("="*70)
            return None
        except Exception as e:
            print(f"❌ {get_api_alias('/api/erp.settings.api/common/userInfo')} - 发生异常：{e}")
            print("\n" + "="*70)
            print("❌ 用户信息获取失败：系统异常")
            print("="*70)
            return None
    
    def get_statistics_dict(self, dict_type=None):
        """获取指标字典/统计指标信息"""
        if not self.token:
            print("❌ 未登录")
            return None
        
        headers = self.headers.copy()
        headers['Authorization'] = self.token  # 【关键】不加 Bearer 前缀
        headers['X-Organ-Id'] = '593347894961426496'
        headers['X-City-Code'] = '150200'
        headers['X-Brand-Id'] = '593347894961426496'
        
        print(f"\n获取指标字典...")
        # 请求体为 '5'，可能是字典类型参数
        response = self.session.post(
            f"{ERP_BASE_URL}/api/common.stats.api/customization/statistics/dict",
            headers=headers,
            data='5'  # 原始数据，非 JSON
        )
        
        print(f"{get_api_alias('/api/common.stats.api/customization/statistics/dict')} 状态码：{response.status_code}")
        
        if response.status_code == 200:
            try:
                result = response.json()
                if result.get('succeed') or result.get('code') == '200':
                    print(f"✅ {get_api_alias('/api/common.stats.api/customization/statistics/dict')} - 获取成功")
                    data = result.get('data', [])
                    print(f"   指标数量：{len(data) if isinstance(data, list) else 'N/A'}")
                    return result
                else:
                    print(f"❌ 获取失败：{result.get('msg', '未知错误')}")
                    return result
            except json.JSONDecodeError:
                print(f"⚠️ 响应非 JSON 格式")
                return {'raw': response.text}
        return None
    
    def create_custom_export(self, agent_code_queries=None, start_time=None, end_time=None, 
                              file_name=None, brand_id=None, branch_ids=None):
        """创建自定义统计报表导出"""
        if not self.token:
            print("❌ 未登录")
            return None
        
        headers = self.headers.copy()
        headers['Authorization'] = self.token
        headers['X-Organ-Id'] = brand_id or '593347894961426496'
        headers['X-City-Code'] = '150200'
        headers['X-Brand-Id'] = brand_id or '593347894961426496'
        
        # 默认指标查询（经纪人认证 + 门店数）
        if agent_code_queries is None:
            agent_code_queries = [
                {"codeName": "经纪人认证", "topCodeName": "经纪人指标", "code": "51", "hasChild": 0, "percentDisplay": 0, "childNodes": []},
                {"codeName": "门店数", "topCodeName": "门店指标", "code": "29", "hasChild": 1, "childNodes": [
                    {"codeName": "营业", "topCodeName": "门店数", "code": "36", "percentDisplay": 0},
                    {"codeName": "启用", "topCodeName": "门店数", "code": "46", "percentDisplay": 0}
                ]}
            ]
        
        # 默认时间范围（最近 30 天）
        if start_time is None:
            from datetime import datetime, timedelta
            start_dt = datetime.now() - timedelta(days=30)
            start_time = int(start_dt.timestamp() * 1000)
        if end_time is None:
            end_time = int(datetime.now().timestamp() * 1000)
        
        # 默认文件名
        if file_name is None:
            from datetime import datetime
            file_name = datetime.now().strftime('%Y-%m-%d') + "自定义报表导出"
        
        # 构建请求体
        export_data = {
            "agentCodeQueries": agent_code_queries,
            "brandId": brand_id or "593347894961426496",
            "cityCode": "150200",
            "playerId": brand_id or "593347894961426496",
            "level": 6,
            "termsLevel": 5,
            "fileName": file_name,
            "branchIds": branch_ids or [],
            "startTime": start_time,
            "endTime": end_time,
            "pageNo": 1,
            "pageSize": 10,
            "districtCodes": [],
            "storeManagerIds": [],
            "tradingAreaIds": [],
            "status": "",
            "isEnabled": "",
            "subBranchIds": []
        }
        
        print(f"\n创建自定义导出...")
        response = self.session.post(
            f"{ERP_BASE_URL}/api/common.stats.api/customization/statistics/export",
            headers=headers,
            json=export_data
        )
        
        print(f"{get_api_alias('/api/common.stats.api/customization/statistics/export')} 状态码：{response.status_code}")
        
        if response.status_code == 200:
            try:
                result = response.json()
                if result.get('succeed') or result.get('code') == '200':
                    print(f"✅ {get_api_alias('/api/common.stats.api/customization/statistics/export')} - 创建成功")
                    data = result.get('data', {})
                    if data:
                        print(f"   导出 ID: {data.get('id', 'N/A')}")
                        print(f"   文件名：{data.get('fileName', 'N/A')}")
                        print(f"   状态：{data.get('status', 'N/A')}")
                    return result
                else:
                    print(f"❌ 创建失败：{result.get('msg', '未知错误')}")
                    return result
            except json.JSONDecodeError:
                print(f"⚠️ 响应非 JSON 格式")
                return {'raw': response.text}
        else:
            print(f"❌ 请求失败：{response.text[:200]}")
            return {'success': False, 'error': f'请求失败：{response.status_code}'}
        return None
    
    def get_export_file_list(self, start_time=None, end_time=None):
        """获取我的导出文件列表"""
        if not self.token:
            print("❌ 未登录")
            return None
        
        headers = self.headers.copy()
        headers['Authorization'] = self.token
        headers['X-Organ-Id'] = '593347894961426496'
        headers['X-City-Code'] = '150200'
        headers['X-Brand-Id'] = '593347894961426496'
        
        # 默认时间范围（最近 30 天）
        if start_time is None:
            from datetime import datetime, timedelta
            start_dt = datetime.now() - timedelta(days=30)
            start_time = int(start_dt.timestamp() * 1000)
        if end_time is None:
            end_time = int(datetime.now().timestamp() * 1000)
        
        # 构建请求体
        list_data = {
            "startInc": start_time,
            "endExc": end_time
        }
        
        print(f"\n获取导出文件列表...")
        response = self.session.post(
            f"{ERP_BASE_URL}/api/common.stats.api/quantification/statistics/file/list",
            headers=headers,
            json=list_data
        )
        
        print(f"{get_api_alias('/api/common.stats.api/quantification/statistics/file/list')} 状态码：{response.status_code}")
        
        if response.status_code == 200:
            try:
                result = response.json()
                if result.get('succeed') or result.get('code') == '200':
                    print(f"✅ {get_api_alias('/api/common.stats.api/quantification/statistics/file/list')} - 获取成功")
                    data = result.get('data', [])
                    
                    # data 可能是列表或包含 records 的对象
                    if isinstance(data, list):
                        records = data
                        total = len(data)
                    elif isinstance(data, dict):
                        records = data.get('records', [])
                        total = data.get('total', len(records))
                    else:
                        records = []
                        total = 0
                    
                    print(f"   文件数量：{len(records)}")
                    print(f"   总数：{total}")
                    
                    # 显示前 5 个文件
                    for i, file in enumerate(records[:5], 1):
                        file_name = file.get('fileName', '未知')
                        create_time = file.get('createTime', 'N/A')
                        status = file.get('status', 'N/A')
                        file_size = file.get('fileSize', 'N/A')
                        print(f"   {i}. {file_name} [{status}] {create_time} ({file_size} 字节)")
                    
                    if len(records) > 5:
                        print(f"   ... 还有 {len(records) - 5} 个文件")
                    
                    return result
                else:
                    print(f"❌ 获取失败：{result.get('msg', '未知错误')}")
                    return result
            except json.JSONDecodeError:
                print(f"⚠️ 响应非 JSON 格式")
                return {'raw': response.text}
        else:
            print(f"❌ 请求失败：{response.text[:200]}")
            return {'success': False, 'error': f'请求失败：{response.status_code}'}
        return None
    
    def export_new_house_contracts(self, start_time=None, end_time=None, city_code='450100', 
                                    organ_id='625864877560328320', output_dir=None,
                                    sign_tm_start=None, sign_tm_end=None):
        """导出新房合同信息（返回 Excel 文件）
        
        Args:
            start_time: 查询日期范围开始时间戳（毫秒）
            end_time: 查询日期范围结束时间戳（毫秒）
            sign_tm_start: 签约开始时间戳（毫秒），默认同 start_time
            sign_tm_end: 签约结束时间戳（毫秒），默认同 end_time
        """
        if not self.token:
            print("❌ 未登录")
            return None
        
        from datetime import datetime, timedelta
        
        # 默认时间范围（今日）
        if start_time is None:
            today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
            start_time = int(today.timestamp() * 1000)
            end_time = int((today + timedelta(days=1)).timestamp() * 1000) - 1
        
        # 签约时间范围，默认与查询日期范围相同
        if sign_tm_start is None:
            sign_tm_start = start_time
        if sign_tm_end is None:
            sign_tm_end = end_time
        
        headers = self.headers.copy()
        headers['Authorization'] = self.token
        headers['X-Organ-Id'] = organ_id
        headers['X-City-Code'] = city_code
        headers['X-Brand-Id'] = '593347894961426496'
        
        # 构建请求体（根据抓包数据结构）
        export_data = {
            "queryType": 1,
            "dateType": 1,
            "solidifyType": 1,
            "approvalStatusList": [],
            "reportTypeList": [],
            "statusList": [],
            "roleType": 100,
            "date": [start_time, end_time],  # 查询日期范围
            "pageNo": 1,
            "pageSize": 100,
            "signTmStart": sign_tm_start,  # 签约开始时间
            "signTmEnd": sign_tm_end,      # 签约结束时间
            "status": None
        }
        
        print(f"\n导出新房合同信息...")
        response = self.session.post(
            f"{ERP_BASE_URL}/api/erp.contract.api/order/estate/query/exportNew",
            headers=headers,
            json=export_data
        )
        
        print(f"{get_api_alias('/api/erp.contract.api/order/estate/query/exportNew')} 状态码：{response.status_code}")
        print(f"Content-Type: {response.headers.get('Content-Type')}")
        
        if response.status_code == 200:
            # 保存 Excel 文件
            output_dir = Path(output_dir or '~/Downloads/ERP 导出').expanduser()
            output_dir.mkdir(parents=True, exist_ok=True)
            
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            output_file = output_dir / f"新房合同_{timestamp}.xlsx"
            
            with open(output_file, 'wb') as f:
                f.write(response.content)
            
            file_size = len(response.content)
            print(f"✅ {get_api_alias('/api/erp.contract.api/order/estate/query/exportNew')} - 导出成功")
            print(f"   文件：{output_file}")
            print(f"   大小：{file_size} 字节")
            
            return {
                'success': True,
                'file': str(output_file),
                'size': file_size,
                'excel_file': output_file
            }
        else:
            print(f"❌ 请求失败：{response.text[:200]}")
            return {'success': False, 'error': f'请求失败：{response.status_code}'}
        return None
    
    def export_personnel_data(self, brand_id=None, branch_ids=None, output_dir=None):
        """导出人事数据"""
        if not self.token:
            print("❌ 未登录")
            return None
        
        # 使用默认配置
        brand_id = brand_id or DEFAULT_CONFIG['brand_id']
        branch_ids = branch_ids or DEFAULT_CONFIG['branch_ids']
        output_dir = output_dir or DEFAULT_CONFIG['export_dir']
        
        # 创建导出目录
        output_dir = Path(output_dir).expanduser()
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # 准备请求
        headers = self.headers.copy()
        headers['Authorization'] = self.token  # 【关键】不加 Bearer 前缀
        headers['X-Organ-Id'] = brand_id
        headers['X-City-Code'] = '150200'
        headers['X-Brand-Id'] = brand_id
        
        export_data = {
            "affiliationType": [],
            "businessDept": [],
            "brandLogo": [],
            "pageNo": 1,
            "pageSize": 100,
            "brandId": brand_id,
            "branchIds": branch_ids
        }
        
        print("\n导出人事数据...")
        response = self.session.post(
            f"{ERP_BASE_URL}/api/common.stats.api/statistics/personnel/export",
            headers=headers,
            json=export_data
        )
        
        print(f"{get_api_alias('/api/common.stats.api/statistics/personnel/export')} 状态码：{response.status_code}")
        print(f"Content-Type: {response.headers.get('Content-Type')}")
        
        if response.status_code == 200:
            # 检查是否是 Excel 文件
            content_type = response.headers.get('Content-Type', '')
            content_disposition = response.headers.get('Content-Disposition', '')
            
            if 'application/octet-stream' in content_type or 'excel' in content_type.lower():
                # 保存 Excel 文件
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                output_file = output_dir / f"人事数据_{timestamp}.xlsx"
                
                with open(output_file, 'wb') as f:
                    f.write(response.content)
                
                print(f"✅ 人事数据导出成功！")
                print(f"   文件：{output_file}")
                print(f"   大小：{len(response.content)} 字节")
                
                return {
                    'success': True,
                    'file': str(output_file),
                    'size': len(response.content)
                }
            else:
                # 尝试解析 JSON
                try:
                    result = response.json()
                    if result.get('succeed') or result.get('code') == '200':
                        print(f"✅ 人事数据导出成功！")
                        data = result.get('data', {})
                        records = data.get('records', [])
                        total = data.get('total', 0)
                        print(f"   记录数：{len(records)}")
                        print(f"   总数：{total}")
                        
                        # 保存 JSON
                        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                        output_file = output_dir / f"人事数据_{timestamp}.json"
                        
                        with open(output_file, 'w', encoding='utf-8') as f:
                            json.dump(result, f, ensure_ascii=False, indent=2)
                        
                        print(f"   文件：{output_file}")
                        
                        return {
                            'success': True,
                            'file': str(output_file),
                            'records': len(records),
                            'total': total
                        }
                    else:
                        print(f"❌ 导出失败：{result.get('msg')}")
                        return {'success': False, 'error': result.get('msg')}
                except:
                    print(f"❌ 无法解析响应：{response.text[:200]}")
                    return {'success': False, 'error': '无法解析响应'}
        else:
            print(f"❌ 请求失败：{response.status_code}")
            print(f"响应：{response.text[:200]}")
            return {'success': False, 'error': f'请求失败：{response.status_code}'}
    
    def export_project_list(self, sale_status=1, project_manager_dept_list=None, 
                            onsite_dept_list=None, page_no=1, page_size=100,
                            proxy_id='625864877560328320', buz_id=1,
                            district_codes=None, output_dir=None):
        """导出项目明细列表
        
        Args:
            sale_status: 销售状态 (1: 在售，2: 待售，3: 售罄，4: 停售)
            project_manager_dept_list: 项目部经理部门列表
            onsite_dept_list: 驻场部门列表
            page_no: 页码
            page_size: 每页数量
            proxy_id: 代理 ID (默认：625864877560328320)
            buz_id: 业务 ID (默认：1)
            district_codes: 区域代码列表
            output_dir: 输出目录
        
        Returns:
            导出结果字典
        """
        if not self.token:
            print("❌ 未登录")
            return None
        
        from datetime import datetime
        
        # 默认参数
        if project_manager_dept_list is None:
            project_manager_dept_list = []
        if onsite_dept_list is None:
            onsite_dept_list = []
        if district_codes is None:
            district_codes = []
        
        output_dir = Path(output_dir or '~/Downloads/ERP 导出').expanduser()
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # 准备请求
        headers = self.headers.copy()
        headers['Authorization'] = self.token
        headers['X-Organ-Id'] = proxy_id
        headers['X-City-Code'] = '450100'
        headers['X-Brand-Id'] = '593347894961426496'
        
        export_data = {
            "saleStatus": sale_status,
            "projectManagerDeptList": project_manager_dept_list,
            "onsiteDeptList": onsite_dept_list,
            "pageNo": page_no,
            "pageSize": page_size,
            "proxyId": proxy_id,
            "buzId": buz_id,
            "districtCodes": district_codes
        }
        
        print("\n导出项目明细列表...")
        print(f"  销售状态：{sale_status}")
        print(f"  页码：{page_no}, 每页：{page_size}")
        
        response = self.session.post(
            f"{ERP_BASE_URL}/api/erp.newhouse.api/erp/projectList/export/myListV3",
            headers=headers,
            json=export_data
        )
        
        print(f"【项目明细导出接口】状态码：{response.status_code}")
        print(f"Content-Type: {response.headers.get('Content-Type')}")
        
        if response.status_code == 200:
            # 检查是否是 Excel 文件
            content_type = response.headers.get('Content-Type', '')
            
            if 'application/vnd.ms-excel' in content_type or 'application/msexcel' in content_type:
                # 保存 Excel 文件
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                output_file = output_dir / f"项目明细_{timestamp}.xlsx"
                
                with open(output_file, 'wb') as f:
                    f.write(response.content)
                
                file_size = len(response.content)
                print(f"✅ 【项目明细导出接口】- 导出成功")
                print(f"   文件：{output_file}")
                print(f"   大小：{file_size} 字节")
                
                return {
                    'success': True,
                    'file': str(output_file),
                    'size': file_size,
                    'excel_file': output_file
                }
            else:
                # 尝试解析 JSON
                try:
                    result = response.json()
                    if result.get('succeed') or result.get('code') == '200':
                        print(f"✅ 【项目明细导出接口】- 导出成功")
                        data = result.get('data', {})
                        records = data.get('records', [])
                        total = data.get('total', 0)
                        
                        print(f"   记录数：{len(records)}")
                        print(f"   总数：{total}")
                        
                        # 保存 JSON
                        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                        output_file = output_dir / f"项目明细_{timestamp}.json"
                        
                        with open(output_file, 'w', encoding='utf-8') as f:
                            json.dump(result, f, ensure_ascii=False, indent=2)
                        
                        print(f"   文件：{output_file}")
                        
                        return {
                            'success': True,
                            'file': str(output_file),
                            'records': len(records),
                            'total': total,
                            'data': result
                        }
                    else:
                        print(f"❌ 导出失败：{result.get('msg')}")
                        return {'success': False, 'error': result.get('msg')}
                except json.JSONDecodeError:
                    print(f"⚠️ 响应非 JSON 格式")
                    return {'raw': response.text}
        else:
            print(f"❌ 请求失败：{response.text[:200]}")
            return {'success': False, 'error': f'请求失败：{response.status_code}'}
    
    def export_visit_list(self, visit_start_tm=None, visit_end_tm=None, page_no=1, page_size=100,
                          role_type=100, report_type_list=None, onsite_ids=None,
                          project_manager_ids=None, channel_manager_ids=None,
                          phone_flag=1, output_dir=None):
        """导出新房带看数据
        
        Args:
            visit_start_tm: 带看开始时间戳（毫秒）
            visit_end_tm: 带看结束时间戳（毫秒）
            page_no: 页码
            page_size: 每页数量
            role_type: 角色类型（默认 100）
            report_type_list: 报表类型列表
            onsite_ids: 驻场 ID 列表
            project_manager_ids: 项目经理 ID 列表
            channel_manager_ids: 渠道经理 ID 列表
            phone_flag: 手机号显示标识（1: 显示，0: 隐藏）
            output_dir: 输出目录
        
        Returns:
            导出结果字典
        """
        if not self.token:
            print("❌ 未登录")
            return None
        
        from datetime import datetime
        
        # 默认参数
        if report_type_list is None:
            report_type_list = []
        if onsite_ids is None:
            onsite_ids = []
        if project_manager_ids is None:
            project_manager_ids = []
        if channel_manager_ids is None:
            channel_manager_ids = []
        
        output_dir = Path(output_dir or '~/Downloads/ERP 导出').expanduser()
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # 准备请求
        headers = self.headers.copy()
        headers['Authorization'] = self.token
        headers['X-Organ-Id'] = '625864877560328320'
        headers['X-City-Code'] = '450100'
        headers['X-Brand-Id'] = '593347894961426496'
        
        export_data = {
            "pageNo": page_no,
            "pageSize": page_size,
            "roleType": role_type,
            "reportTypeList": report_type_list,
            "visitStartTm": visit_start_tm,
            "visitEndTm": visit_end_tm,
            "onsiterIds": onsite_ids,
            "projectMangerIds": project_manager_ids,
            "channelManagerIds": channel_manager_ids,
            "phoneFlag": phone_flag
        }
        
        print("\n导出新房带看数据...")
        if visit_start_tm and visit_end_tm:
            start_dt = datetime.fromtimestamp(visit_start_tm / 1000)
            end_dt = datetime.fromtimestamp(visit_end_tm / 1000)
            print(f"  带看时间：{start_dt.strftime('%Y-%m-%d')} ~ {end_dt.strftime('%Y-%m-%d')}")
        print(f"  页码：{page_no}, 每页：{page_size}")
        
        response = self.session.post(
            f"{ERP_BASE_URL}/api/erp.newhouse.api/reportinfo/pc/exportVisitList",
            headers=headers,
            json=export_data
        )
        
        print(f"【带看数据导出接口】状态码：{response.status_code}")
        print(f"Content-Type: {response.headers.get('Content-Type')}")
        
        if response.status_code == 200:
            content_type = response.headers.get('Content-Type', '')
            
            if 'application/vnd.ms-excel' in content_type or 'application/msexcel' in content_type:
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                output_file = output_dir / f"带看数据_{timestamp}.xlsx"
                
                with open(output_file, 'wb') as f:
                    f.write(response.content)
                
                file_size = len(response.content)
                print(f"✅ 【带看数据导出接口】- 导出成功")
                print(f"   文件：{output_file}")
                print(f"   大小：{file_size} 字节")
                
                return {
                    'success': True,
                    'file': str(output_file),
                    'size': file_size,
                    'excel_file': output_file
                }
            else:
                try:
                    result = response.json()
                    if result.get('succeed') or result.get('code') == '200':
                        data = result.get('data', {})
                        records = data.get('records', [])
                        total = data.get('total', 0)
                        
                        print(f"✅ 【带看数据导出接口】- 导出成功")
                        print(f"   记录数：{len(records)}")
                        print(f"   总数：{total}")
                        
                        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                        output_file = output_dir / f"带看数据_{timestamp}.json"
                        
                        with open(output_file, 'w', encoding='utf-8') as f:
                            json.dump(result, f, ensure_ascii=False, indent=2)
                        
                        print(f"   文件：{output_file}")
                        
                        return {
                            'success': True,
                            'file': str(output_file),
                            'records': len(records),
                            'total': total,
                            'data': result
                        }
                    else:
                        print(f"❌ 导出失败：{result.get('msg')}")
                        return {'success': False, 'error': result.get('msg')}
                except json.JSONDecodeError:
                    print(f"⚠️ 响应非 JSON 格式")
                    return {'raw': response.text}
        else:
            print(f"❌ 请求失败：{response.text[:200]}")
            return {'success': False, 'error': f'请求失败：{response.status_code}'}
    
    def export_rival_stats(self, summary_type=1, dept_ids=None, rival_ids=None,
                           start_inclusive=None, end_exclusive=None,
                           file_name='竞对数据导出', output_dir=None):
        """导出竞对数据
        
        Args:
            summary_type: 统计类型 (1: 按项目，2: 按区域)
            dept_ids: 部门 ID 列表
            rival_ids: 竞对公司 ID 列表
            start_inclusive: 开始时间戳（毫秒）
            end_exclusive: 结束时间戳（毫秒）
            file_name: 导出文件名
            output_dir: 输出目录
        
        Returns:
            导出任务 ID
        """
        if not self.token:
            print("❌ 未登录")
            return None
        
        from datetime import datetime
        
        # 默认参数
        if dept_ids is None:
            dept_ids = ['625864877560328320']
        if rival_ids is None:
            rival_ids = []
        
        output_dir = Path(output_dir or '~/Downloads/ERP 导出').expanduser()
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # 准备请求
        headers = self.headers.copy()
        headers['Authorization'] = self.token
        headers['X-Organ-Id'] = '625864877560328320'
        headers['X-City-Code'] = '450100'
        headers['X-Brand-Id'] = '593347894961426496'
        
        export_data = {
            "summaryType": summary_type,
            "deptIds": dept_ids,
            "rivalIds": rival_ids,
            "startInclusive": start_inclusive,
            "endExclusive": end_exclusive,
            "fileName": file_name
        }
        
        print("\n导出竞对数据...")
        if start_inclusive and end_exclusive:
            start_dt = datetime.fromtimestamp(start_inclusive / 1000)
            end_dt = datetime.fromtimestamp(end_exclusive / 1000)
            print(f"  统计时间：{start_dt.strftime('%Y-%m-%d')} ~ {end_dt.strftime('%Y-%m-%d')}")
        print(f"  统计类型：{summary_type}")
        print(f"  竞对公司数：{len(rival_ids)}")
        
        response = self.session.post(
            f"{ERP_BASE_URL}/api/common.stats.api/rival/stats/pcPkExport",
            headers=headers,
            json=export_data
        )
        
        print(f"【竞对数据导出接口】状态码：{response.status_code}")
        
        if response.status_code == 200:
            try:
                result = response.json()
                if result.get('succeed') or result.get('code') == '200':
                    print(f"✅ 【竞对数据导出接口】- 导出任务已创建")
                    
                    # 返回任务信息，需要后续调用 get_export_file_list 获取文件
                    return {
                        'success': True,
                        'message': '导出任务已创建，请调用 get_export_file_list 获取文件',
                        'data': result.get('data', {})
                    }
                else:
                    print(f"❌ 导出失败：{result.get('msg')}")
                    return {'success': False, 'error': result.get('msg')}
            except json.JSONDecodeError:
                print(f"⚠️ 响应非 JSON 格式")
                return {'raw': response.text}
        else:
            print(f"❌ 请求失败：{response.text[:200]}")
            return {'success': False, 'error': f'请求失败：{response.status_code}'}
    
    def get_export_file_list(self, start_time=None, end_time=None, output_dir=None):
        """获取导出文件列表
        
        Args:
            start_time: 开始时间戳（毫秒）
            end_time: 结束时间戳（毫秒）
            output_dir: 输出目录
        
        Returns:
            文件列表
        """
        if not self.token:
            print("❌ 未登录")
            return None
        
        from datetime import datetime
        
        # 默认时间范围（最近 30 天）
        if start_time is None:
            start_dt = datetime.now() - timedelta(days=30)
            start_time = int(start_dt.timestamp() * 1000)
        if end_time is None:
            end_time = int(datetime.now().timestamp() * 1000)
        
        output_dir = Path(output_dir or '~/Downloads/ERP 导出').expanduser()
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # 准备请求
        headers = self.headers.copy()
        headers['Authorization'] = self.token
        headers['X-Organ-Id'] = '625864877560328320'
        headers['X-City-Code'] = '450100'
        headers['X-Brand-Id'] = '593347894961426496'
        
        list_data = {
            "startInc": start_time,
            "endExc": end_time
        }
        
        print("\n获取导出文件列表...")
        
        response = self.session.post(
            f"{ERP_BASE_URL}/api/common.stats.api/quantification/statistics/file/list",
            headers=headers,
            json=list_data
        )
        
        print(f"【导出文件列表接口】状态码：{response.status_code}")
        
        if response.status_code == 200:
            try:
                result = response.json()
                if result.get('succeed') or result.get('code') == '200':
                    data = result.get('data', [])
                    
                    # 处理数据格式（可能是列表或包含 records 的对象）
                    if isinstance(data, list):
                        files = data
                    elif isinstance(data, dict):
                        files = data.get('records', [])
                    else:
                        files = []
                    
                    print(f"✅ 【导出文件列表接口】- 获取成功")
                    print(f"   文件数量：{len(files)}")
                    
                    # 显示前 5 个文件
                    for i, file in enumerate(files[:5], 1):
                        file_name = file.get('fileName', '未知')
                        create_time = file.get('createTime', 'N/A')
                        status = file.get('status', 'N/A')
                        file_size = file.get('fileSize', 'N/A')
                        print(f"   {i}. {file_name} [{status}] {create_time} ({file_size} 字节)")
                    
                    if len(files) > 5:
                        print(f"   ... 还有 {len(files) - 5} 个文件")
                    
                    return {
                        'success': True,
                        'files': files,
                        'total': len(files)
                    }
                else:
                    print(f"❌ 获取失败：{result.get('msg')}")
                    return {'success': False, 'error': result.get('msg')}
            except json.JSONDecodeError:
                print(f"⚠️ 响应非 JSON 格式")
                return {'raw': response.text}
        else:
            print(f"❌ 请求失败：{response.text[:200]}")
            return {'success': False, 'error': f'请求失败：{response.status_code}'}
    
    def export_lagging_projects(self, dept_ids=None, rival_ids=None,
                                start_inclusive=None, end_exclusive=None,
                                output_dir=None):
        """导出落后项目数据报表
        
        Args:
            dept_ids: 部门 ID 列表
            rival_ids: 竞对公司 ID 列表
            start_inclusive: 开始时间戳（毫秒）
            end_exclusive: 结束时间戳（毫秒）
            output_dir: 输出目录
        
        Returns:
            导出结果
        """
        if not self.token:
            print("❌ 未登录")
            return None
        
        from datetime import datetime
        
        # 默认参数
        if dept_ids is None:
            dept_ids = ['625864877560328320']
        if rival_ids is None:
            rival_ids = []
        
        output_dir = Path(output_dir or '~/Downloads/ERP 导出').expanduser()
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # 准备请求
        headers = self.headers.copy()
        headers['Authorization'] = self.token
        headers['X-Organ-Id'] = '625864877560328320'
        headers['X-City-Code'] = '450100'
        headers['X-Brand-Id'] = '593347894961426496'
        
        export_data = {
            "summaryType": 1,
            "deptIds": dept_ids,
            "rivalIds": rival_ids,
            "startInclusive": start_inclusive,
            "endExclusive": end_exclusive,
            "fileName": "落后项目数据导出"
        }
        
        print("\n导出落后项目数据...")
        if start_inclusive and end_exclusive:
            start_dt = datetime.fromtimestamp(start_inclusive / 1000)
            end_dt = datetime.fromtimestamp(end_exclusive / 1000)
            print(f"  统计时间：{start_dt.strftime('%Y-%m-%d')} ~ {end_dt.strftime('%Y-%m-%d')}")
        print(f"  部门数：{len(dept_ids)}")
        print(f"  竞对公司数：{len(rival_ids)}")
        
        response = self.session.post(
            f"{ERP_BASE_URL}/api/common.stats.api/rival/stats/pcPkExport",
            headers=headers,
            json=export_data
        )
        
        print(f"【落后项目导出接口】状态码：{response.status_code}")
        
        if response.status_code == 200:
            try:
                result = response.json()
                if result.get('succeed') or result.get('code') == '200':
                    print(f"✅ 【落后项目导出接口】- 导出任务已创建")
                    
                    return {
                        'success': True,
                        'message': '导出任务已创建，请调用 get_export_file_list 获取文件',
                        'data': result.get('data', {})
                    }
                else:
                    print(f"❌ 导出失败：{result.get('msg')}")
                    return {'success': False, 'error': result.get('msg')}
            except json.JSONDecodeError:
                print(f"⚠️ 响应非 JSON 格式")
                return {'raw': response.text}
        else:
            print(f"❌ 请求失败：{response.text[:200]}")
            return {'success': False, 'error': f'请求失败：{response.status_code}'}

# ============== 主函数 ==============

def main():
    """主函数"""
    print("="*70)
    print("ERP 人事数据导出工具")
    print("="*70)
    
    # 【安全检查】获取用户凭证
    phone = DEFAULT_CONFIG['phone']
    password = DEFAULT_CONFIG['password']
    
    # 1. 尝试从配置文件或环境变量获取
    if not phone or not password:
        config_phone, config_password = get_user_credentials()
        if config_phone and config_password:
            phone = config_phone
            password = config_password
    
    # 2. 如果仍没有凭证，提示用户输入
    if not phone or not password:
        print("\n" + "="*70)
        print("⚠️ 未找到 ERP 登录凭证")
        print("="*70)
        print("\n💡 请通过以下任一方式提供凭证:")
        print("")
        print("方式 1: 配置文件")
        print(f"   编辑：~/.openclaw/workspace/configs/erp-credentials.env")
        print("   添加:")
        print("   ERP_USERNAME=你的手机号")
        print("   ERP_PASSWORD=你的密码")
        print("")
        print("方式 2: 环境变量")
        print("   export ERP_USERNAME=你的手机号")
        print("   export ERP_PASSWORD=你的密码")
        print("")
        print("方式 3: 命令行参数")
        print(f"   python3 erp-export.py --phone 你的手机号 --password 你的密码")
        print("")
        print("="*70)
        
        # 尝试从命令行参数获取
        import sys
        args = sys.argv[1:]
        for i, arg in enumerate(args):
            if arg == '--phone' and i + 1 < len(args):
                phone = args[i + 1]
            elif arg == '--password' and i + 1 < len(args):
                password = args[i + 1]
        
        # 如果仍然没有，尝试交互式输入
        if not phone or not password:
            print("\n请输入登录凭证:")
            if not phone:
                phone = input("手机号：").strip()
            if not password:
                import getpass
                password = getpass.getpass("密码：").strip()
        
        # 最后检查
        if not phone or not password:
            print("\n❌ 错误：必须提供手机号和密码")
            print("="*70)
            return
    
    # 创建客户端
    print(f"\n使用账号：{phone}")
    client = ERPAPIClient(
        phone=phone,
        password=password
    )
    
    # 登录
    if not client.login():
        print("\n❌ 登录失败")
        print("\n💡 请检查:")
        print("   1. 手机号和密码是否正确")
        print("   2. 账号是否有 ERP 系统访问权限")
        print("   3. 联系系统管理员确认账号状态")
        return
    
    # 获取用户信息（带严格验证）
    print("\n获取用户信息...")
    user_info = client.get_user_info()
    
    # 【关键检查】用户信息为空，立即终止
    if not user_info:
        print("\n" + "="*70)
        print("❌ 程序终止：用户信息获取失败")
        print("="*70)
        print("\n💡 解决方案:")
        print("   1. 检查账号是否有 ERP 系统访问权限")
        print("   2. 联系系统管理员确认账号状态")
        print("   3. 尝试使用其他账号登录")
        print("="*70)
        return
    
    print(f"✅ 用户：{user_info.get('userName')}")
    if user_info.get('organName'):
        print(f"   组织：{user_info.get('organName')}")
    
    # 获取指标字典（可选）
    # dict_data = client.get_statistics_dict()
    # if dict_data:
    #     print(f"   数据：{dict_data.get('data', [])[:3]}...")  # 显示前 3 条
    
    # 导出人事数据
    result = client.export_personnel_data()
    
    if result and result.get('success'):
        print("\n" + "="*70)
        print("✅ 导出完成！")
        print("="*70)
        print(f"文件：{result['file']}")
        if 'size' in result:
            print(f"大小：{result['size']} 字节")
        if 'records' in result:
            print(f"记录数：{result['records']}")
    else:
        print("\n" + "="*70)
        print("❌ 导出失败")
        print("="*70)
        if result:
            print(f"错误：{result.get('error')}")

if __name__ == "__main__":
    main()
