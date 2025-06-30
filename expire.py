import base64
import json
import os
import datetime as dt
from pathlib import Path
from dotenv import load_dotenv

def decode_jwt(token_str):
    """解码JWT令牌，并返回解析后的信息"""
    # 移除可能的引号
    token_str = token_str.strip("'\"")
    
    # 分割JWT的三个部分
    try:
        header_b64, payload_b64, signature = token_str.split(".")
    except ValueError:
        return "无效的JWT格式：应该包含3个由'.'分隔的部分"
    
    # 解码头部
    try:
        # 处理base64填充
        header_pad = header_b64 + '=' * (4 - len(header_b64) % 4) if len(header_b64) % 4 else header_b64
        header_json = base64.urlsafe_b64decode(header_pad)
        header = json.loads(header_json)
    except Exception as e:
        return f"头部解码失败: {str(e)}"
    
    # 解码载荷
    try:
        # 处理base64填充
        payload_pad = payload_b64 + '=' * (4 - len(payload_b64) % 4) if len(payload_b64) % 4 else payload_b64
        payload_json = base64.urlsafe_b64decode(payload_pad)
        payload = json.loads(payload_json)
    except Exception as e:
        return f"载荷解码失败: {str(e)}"
    
    # 检查是否有时间相关字段并转换
    time_fields = {}
    for field in ['iat', 'nbf', 'exp']:
        if field in payload:
            time_stamp = payload[field]
            time_fields[field] = {
                'timestamp': time_stamp,
                'datetime': dt.datetime.fromtimestamp(time_stamp),
                'human': dt.datetime.fromtimestamp(time_stamp).strftime('%Y-%m-%d %H:%M:%S')
            }
    
    # 计算相关时间
    now = dt.datetime.now()
    time_info = {}
    
    if 'exp' in time_fields:
        exp_time = time_fields['exp']['datetime']
        is_expired = now > exp_time
        time_to_expire = (exp_time - now).total_seconds() if not is_expired else 0
        
        time_info['expired'] = is_expired
        time_info['expires_in'] = {
            'seconds': time_to_expire,
            'minutes': time_to_expire / 60,
            'hours': time_to_expire / 3600,
            'human': f"{int(time_to_expire/3600)}小时{int((time_to_expire%3600)/60)}分钟"
        }
    
    if 'iat' in time_fields and 'exp' in time_fields:
        total_validity = (time_fields['exp']['datetime'] - time_fields['iat']['datetime']).total_seconds()
        time_info['total_validity'] = {
            'seconds': total_validity,
            'hours': total_validity / 3600,
            'human': f"{total_validity/3600:.2f}小时"
        }
    
    return {
        'header': header,
        'payload': payload,
        'time_fields': time_fields,
        'time_info': time_info,
        'raw': {
            'header_b64': header_b64,
            'payload_b64': payload_b64,
            'signature': signature
        }
    }

def load_jwt_from_env():
    """从.env文件加载JWT令牌"""
    # 加载.env文件
    env_path = Path('.') / '.env'
    if not env_path.exists():
        return "错误：在当前目录下找不到.env文件"
    
    load_dotenv(env_path)
    
    # 获取JM_TOKEN
    token = os.getenv('JM_TOKEN')
    if not token:
        return "错误：在.env文件中找不到JM_TOKEN变量"
    
    return token

def pretty_print_jwt_info(jwt_info):
    """美化打印JWT信息"""
    if isinstance(jwt_info, str):
        print(jwt_info)
        return
    
    print("\n===== JWT令牌分析 =====\n")
    
    print("📋 头部信息:")
    for k, v in jwt_info['header'].items():
        print(f"  - {k}: {v}")
    
    print("\n👤 载荷信息:")
    # 处理嵌套结构
    for k, v in jwt_info['payload'].items():
        if k == 'extend' and isinstance(v, dict):
            print(f"  - {k}:")
            for ext_k, ext_v in v.items():
                print(f"    • {ext_k}: {ext_v}")
        else:
            print(f"  - {k}: {v}")
    
    print("\n⏰ 时间信息:")
    for field_name, field_data in jwt_info['time_fields'].items():
        field_desc = {
            'iat': '颁发时间',
            'nbf': '生效时间',
            'exp': '过期时间'
        }.get(field_name, field_name)
        
        print(f"  - {field_desc}: {field_data['human']} (时间戳: {field_data['timestamp']})")
    
    print("\n⚠️ 状态信息:")
    if 'expired' in jwt_info['time_info']:
        status = "已过期❌" if jwt_info['time_info']['expired'] else "有效✅"
        print(f"  - 当前状态: {status}")
    
    if 'expires_in' in jwt_info['time_info']:
        if jwt_info['time_info']['expired']:
            print("  - 过期时长: 已过期")
        else:
            print(f"  - 剩余有效期: {jwt_info['time_info']['expires_in']['human']}")
    
    if 'total_validity' in jwt_info['time_info']:
        print(f"  - 总有效期: {jwt_info['time_info']['total_validity']['human']}")

if __name__ == "__main__":
    # 从.env文件加载JWT令牌
    token = load_jwt_from_env()
    if isinstance(token, str) and token.startswith("错误"):
        print(token)
    else:
        # 解码并分析JWT
        jwt_info = decode_jwt(token)
        # 打印分析结果
        pretty_print_jwt_info(jwt_info)
