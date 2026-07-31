"""
请求辅助工具
"""
from flask import request


def get_client_ip():
    """
    获取客户端真实IP地址

    优先级：
    1. X-Forwarded-For（反向代理）
    2. X-Real-IP（Nginx）
    3. CF-Connecting-IP（Cloudflare）
    4. request.remote_addr（直接连接）

    Returns:
        str: 客户端IP地址
    """
    # 尝试从 X-Forwarded-For 获取（可能包含多个IP，取第一个）
    if request.headers.get('X-Forwarded-For'):
        ip = request.headers.get('X-Forwarded-For').split(',')[0].strip()
        return ip

    # 尝试从 X-Real-IP 获取（Nginx常用）
    if request.headers.get('X-Real-IP'):
        return request.headers.get('X-Real-IP')

    # 尝试从 CF-Connecting-IP 获取（Cloudflare）
    if request.headers.get('CF-Connecting-IP'):
        return request.headers.get('CF-Connecting-IP')

    # 直接连接的IP（可能是代理IP）
    return request.remote_addr or 'unknown'
