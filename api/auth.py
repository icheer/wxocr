"""
API认证模块
"""
import os
from functools import wraps
from flask import request, jsonify


def get_api_key() -> str:
    """获取配置的API密钥"""
    return os.getenv('API_KEY', '')


def require_api_key(f):
    """
    API密钥验证装饰器
    如果设置了API_KEY环境变量，则要求请求头包含正确的Bearer token
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        configured_key = get_api_key()

        # 如果没有配置API_KEY，直接放行
        if not configured_key:
            return f(*args, **kwargs)

        # 检查Authorization头
        auth_header = request.headers.get('Authorization', '')

        if not auth_header:
            return jsonify({
                'code': 401,
                'message': '缺少认证信息',
                'data': None
            }), 401

        # 验证Bearer token格式
        parts = auth_header.split()
        if len(parts) != 2 or parts[0].lower() != 'bearer':
            return jsonify({
                'code': 401,
                'message': '认证格式错误，应为: Bearer <token>',
                'data': None
            }), 401

        token = parts[1]

        # 验证token是否匹配
        if token != configured_key:
            return jsonify({
                'code': 401,
                'message': '认证失败',
                'data': None
            }), 401

        return f(*args, **kwargs)

    return decorated_function
