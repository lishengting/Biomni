#!/usr/bin/env python3
"""
S3存储桶文件列表工具
尝试多种方法列出S3存储桶中的文件和目录
"""

import requests
import boto3
import json
import sys
import os
from urllib.parse import urlparse
from botocore.exceptions import ClientError, NoCredentialsError
import xml.etree.ElementTree as ET

def try_http_listing(bucket_url):
    """尝试通过HTTP请求列出文件"""
    print("🔍 尝试HTTP请求方法...")
    
    try:
        # 尝试不同的路径
        test_paths = [
            "",
            "/",
            "/data_lake/",
            "/benchmark/",
            "/?list-type=2",  # S3 ListObjectsV2 API
            "/?prefix=&list-type=2",
            "/?delimiter=/&list-type=2"
        ]
        
        for path in test_paths:
            url = f"{bucket_url}{path}"
            print(f"  尝试: {url}")
            
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            
            response = requests.get(url, headers=headers, timeout=10)
            print(f"  状态码: {response.status_code}")
            
            if response.status_code == 200:
                print(f"  响应长度: {len(response.text)} 字符")
                print(f"  响应内容前500字符: {response.text[:500]}")
                
                # 尝试解析XML响应
                try:
                    root = ET.fromstring(response.text)
                    print("  ✅ 成功解析XML响应")
                    
                    # 查找CommonPrefixes (目录)
                    prefixes = root.findall('.//{http://s3.amazonaws.com/doc/2006-03-01/}CommonPrefixes')
                    for prefix in prefixes:
                        prefix_text = prefix.find('.//{http://s3.amazonaws.com/doc/2006-03-01/}Prefix')
                        if prefix_text is not None:
                            print(f"  目录: {prefix_text.text}")
                    
                    # 查找Contents (文件)
                    contents = root.findall('.//{http://s3.amazonaws.com/doc/2006-03-01/}Contents')
                    for content in contents:
                        key = content.find('.//{http://s3.amazonaws.com/doc/2006-03-01/}Key')
                        size = content.find('.//{http://s3.amazonaws.com/doc/2006-03-01/}Size')
                        if key is not None:
                            size_str = f" ({size.text} bytes)" if size is not None else ""
                            print(f"  文件: {key.text}{size_str}")
                    
                    return True
                    
                except ET.ParseError:
                    print("  ❌ 无法解析XML，可能是HTML错误页面")
                    if "Access Denied" in response.text:
                        print("  ❌ 访问被拒绝")
                    elif "NoSuchBucket" in response.text:
                        print("  ❌ 存储桶不存在")
                    else:
                        print(f"  响应内容: {response.text[:200]}...")
            else:
                print(f"  ❌ HTTP错误: {response.status_code}")
                
    except requests.exceptions.RequestException as e:
        print(f"  ❌ 请求异常: {e}")
    
    return False

def try_boto3_listing(bucket_name):
    """尝试使用boto3列出文件"""
    print("\n🔍 尝试boto3方法...")
    
    try:
        # 尝试不同的认证方式
        auth_methods = [
            ("默认配置", {}),
            ("匿名访问", {"aws_access_key_id": "", "aws_secret_access_key": ""}),
        ]
        
        for method_name, credentials in auth_methods:
            print(f"  尝试{method_name}...")
            
            try:
                if credentials:
                    s3_client = boto3.client('s3', **credentials)
                else:
                    s3_client = boto3.client('s3')
                
                # 尝试列出对象
                response = s3_client.list_objects_v2(
                    Bucket=bucket_name,
                    MaxKeys=1000
                )
                
                print(f"  ✅ {method_name}成功!")
                print(f"  找到 {response.get('KeyCount', 0)} 个对象")
                
                if 'Contents' in response:
                    print("\n  文件列表:")
                    for obj in response['Contents']:
                        size_mb = obj['Size'] / (1024 * 1024)
                        print(f"    {obj['Key']} ({size_mb:.2f} MB)")
                
                if 'CommonPrefixes' in response:
                    print("\n  目录列表:")
                    for prefix in response['CommonPrefixes']:
                        print(f"    {prefix['Prefix']}")
                
                return True
                
            except NoCredentialsError:
                print(f"  ❌ {method_name}失败: 无凭据")
            except ClientError as e:
                error_code = e.response['Error']['Code']
                error_message = e.response['Error']['Message']
                print(f"  ❌ {method_name}失败: {error_code} - {error_message}")
            except Exception as e:
                print(f"  ❌ {method_name}失败: {e}")
    
    except Exception as e:
        print(f"  ❌ boto3初始化失败: {e}")
    
    return False

def try_aws_cli_listing(bucket_name):
    """尝试使用AWS CLI列出文件"""
    print("\n🔍 尝试AWS CLI方法...")
    
    try:
        import subprocess
        
        # 尝试不同的命令
        commands = [
            f"aws s3 ls s3://{bucket_name}/ --recursive",
            f"aws s3 ls s3://{bucket_name}/ --human-readable",
            f"aws s3 ls s3://{bucket_name}/data_lake/ --recursive",
            f"aws s3 ls s3://{bucket_name}/benchmark/ --recursive",
        ]
        
        for cmd in commands:
            print(f"  执行命令: {cmd}")
            try:
                result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=30)
                
                if result.returncode == 0:
                    print("  ✅ 命令执行成功!")
                    print("  输出:")
                    print(result.stdout)
                    return True
                else:
                    print(f"  ❌ 命令失败: {result.stderr}")
                    
            except subprocess.TimeoutExpired:
                print("  ❌ 命令超时")
            except Exception as e:
                print(f"  ❌ 命令异常: {e}")
    
    except ImportError:
        print("  ❌ 无法导入subprocess模块")
    except Exception as e:
        print(f"  ❌ AWS CLI方法失败: {e}")
    
    return False

def try_s3cmd_listing(bucket_name):
    """尝试使用s3cmd列出文件"""
    print("\n🔍 尝试s3cmd方法...")
    
    try:
        import subprocess
        
        commands = [
            f"s3cmd ls s3://{bucket_name}/",
            f"s3cmd ls s3://{bucket_name}/data_lake/",
            f"s3cmd ls s3://{bucket_name}/benchmark/",
        ]
        
        for cmd in commands:
            print(f"  执行命令: {cmd}")
            try:
                result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=30)
                
                if result.returncode == 0:
                    print("  ✅ 命令执行成功!")
                    print("  输出:")
                    print(result.stdout)
                    return True
                else:
                    print(f"  ❌ 命令失败: {result.stderr}")
                    
            except subprocess.TimeoutExpired:
                print("  ❌ 命令超时")
            except Exception as e:
                print(f"  ❌ 命令异常: {e}")
    
    except ImportError:
        print("  ❌ 无法导入subprocess模块")
    except Exception as e:
        print(f"  ❌ s3cmd方法失败: {e}")
    
    return False

def check_environment():
    """检查环境配置"""
    print("🔍 检查环境配置...")
    
    # 检查AWS配置
    aws_config_file = os.path.expanduser("~/.aws/config")
    aws_credentials_file = os.path.expanduser("~/.aws/credentials")
    
    print(f"  AWS配置文件: {aws_config_file}")
    if os.path.exists(aws_config_file):
        print("  ✅ AWS配置文件存在")
        with open(aws_config_file, 'r') as f:
            print(f"  内容: {f.read()[:200]}...")
    else:
        print("  ❌ AWS配置文件不存在")
    
    print(f"  AWS凭据文件: {aws_credentials_file}")
    if os.path.exists(aws_credentials_file):
        print("  ✅ AWS凭据文件存在")
        with open(aws_credentials_file, 'r') as f:
            print(f"  内容: {f.read()[:200]}...")
    else:
        print("  ❌ AWS凭据文件不存在")
    
    # 检查环境变量
    aws_vars = ['AWS_ACCESS_KEY_ID', 'AWS_SECRET_ACCESS_KEY', 'AWS_DEFAULT_REGION']
    for var in aws_vars:
        value = os.environ.get(var)
        if value:
            print(f"  ✅ {var}: {value[:10]}..." if len(value) > 10 else f"  ✅ {var}: {value}")
        else:
            print(f"  ❌ {var}: 未设置")

def main():
    """主函数"""
    bucket_url = "https://biomni-release.s3.amazonaws.com"
    bucket_name = "biomni-release"
    
    print("🚀 S3存储桶文件列表工具")
    print("=" * 50)
    print(f"目标存储桶: {bucket_name}")
    print(f"URL: {bucket_url}")
    print("=" * 50)
    
    # 检查环境
    check_environment()
    
    # 尝试不同方法
    methods = [
        ("HTTP请求", lambda: try_http_listing(bucket_url)),
        ("boto3", lambda: try_boto3_listing(bucket_name)),
        ("AWS CLI", lambda: try_aws_cli_listing(bucket_name)),
        ("s3cmd", lambda: try_s3cmd_listing(bucket_name)),
    ]
    
    success = False
    for method_name, method_func in methods:
        print(f"\n{'='*20} {method_name} {'='*20}")
        if method_func():
            success = True
            print(f"✅ {method_name}方法成功!")
            break
        else:
            print(f"❌ {method_name}方法失败")
    
    if not success:
        print("\n❌ 所有方法都失败了")
        print("\n💡 建议:")
        print("1. 检查网络连接")
        print("2. 确认存储桶名称是否正确")
        print("3. 检查AWS凭据配置")
        print("4. 尝试使用AWS CLI配置: aws configure")
        print("5. 联系存储桶管理员获取访问权限")

if __name__ == "__main__":
    main() 