#!/usr/bin/env python3
"""
S3存储桶文件列表工具 - 简化版
尝试多种方法列出S3存储桶中的文件和目录
"""

import requests
import json
import sys
import os
import subprocess
from urllib.parse import urlparse
import xml.etree.ElementTree as ET

def try_http_listing(bucket_url):
    """尝试通过HTTP请求列出文件"""
    print("🔍 尝试HTTP请求方法...")
    
    try:
        # 尝试不同的路径和参数
        test_paths = [
            "",
            "/",
            "/data_lake/",
            "/benchmark/",
            "/?list-type=2",  # S3 ListObjectsV2 API
            "/?prefix=&list-type=2",
            "/?delimiter=/&list-type=2",
            "/?max-keys=1000&list-type=2"
        ]
        
        for path in test_paths:
            url = f"{bucket_url}{path}"
            print(f"  尝试: {url}")
            
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'Accept': 'application/xml, text/xml, */*'
            }
            
            try:
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
                        if prefixes:
                            print("  目录列表:")
                            for prefix in prefixes:
                                prefix_text = prefix.find('.//{http://s3.amazonaws.com/doc/2006-03-01/}Prefix')
                                if prefix_text is not None:
                                    print(f"    {prefix_text.text}")
                        
                        # 查找Contents (文件)
                        contents = root.findall('.//{http://s3.amazonaws.com/doc/2006-03-01/}Contents')
                        if contents:
                            print("  文件列表:")
                            for content in contents:
                                key = content.find('.//{http://s3.amazonaws.com/doc/2006-03-01/}Key')
                                size = content.find('.//{http://s3.amazonaws.com/doc/2006-03-01/}Size')
                                if key is not None:
                                    size_str = f" ({size.text} bytes)" if size is not None else ""
                                    print(f"    {key.text}{size_str}")
                        
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
                    
            except requests.exceptions.Timeout:
                print("  ❌ 请求超时")
            except requests.exceptions.RequestException as e:
                print(f"  ❌ 请求异常: {e}")
                
    except Exception as e:
        print(f"  ❌ HTTP方法失败: {e}")
    
    return False

def try_curl_listing(bucket_name):
    """尝试使用curl命令列出文件"""
    print("\n🔍 尝试curl方法...")
    
    try:
        # 尝试不同的curl命令
        commands = [
            f"curl -s 'https://{bucket_name}.s3.amazonaws.com/?list-type=2'",
            f"curl -s 'https://{bucket_name}.s3.amazonaws.com/?prefix=&list-type=2'",
            f"curl -s 'https://{bucket_name}.s3.amazonaws.com/data_lake/?list-type=2'",
            f"curl -s 'https://{bucket_name}.s3.amazonaws.com/benchmark/?list-type=2'",
            f"curl -s -H 'User-Agent: Mozilla/5.0' 'https://{bucket_name}.s3.amazonaws.com/?list-type=2'",
        ]
        
        for cmd in commands:
            print(f"  执行命令: {cmd}")
            try:
                result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=30)
                
                if result.returncode == 0 and result.stdout.strip():
                    print("  ✅ 命令执行成功!")
                    print("  输出:")
                    print(result.stdout)
                    
                    # 尝试解析XML输出
                    try:
                        root = ET.fromstring(result.stdout)
                        print("  ✅ 成功解析XML输出")
                        
                        # 查找文件
                        contents = root.findall('.//{http://s3.amazonaws.com/doc/2006-03-01/}Contents')
                        if contents:
                            print("  文件列表:")
                            for content in contents:
                                key = content.find('.//{http://s3.amazonaws.com/doc/2006-03-01/}Key')
                                size = content.find('.//{http://s3.amazonaws.com/doc/2006-03-01/}Size')
                                if key is not None and key.text is not None:
                                    size_text = size.text if size is not None else "0"
                                    size_mb = int(size_text) / (1024 * 1024)
                                    print(f"    {key.text} ({size_mb:.2f} MB)")
                        
                        return True
                        
                    except ET.ParseError:
                        print("  ❌ 无法解析XML输出")
                        if "Access Denied" in result.stdout:
                            print("  ❌ 访问被拒绝")
                        else:
                            print(f"  输出内容: {result.stdout[:200]}...")
                else:
                    print(f"  ❌ 命令失败或无输出: {result.stderr}")
                    
            except subprocess.TimeoutExpired:
                print("  ❌ 命令超时")
            except Exception as e:
                print(f"  ❌ 命令异常: {e}")
    
    except Exception as e:
        print(f"  ❌ curl方法失败: {e}")
    
    return False

def try_aws_cli_listing(bucket_name):
    """尝试使用AWS CLI列出文件"""
    print("\n🔍 尝试AWS CLI方法...")
    
    try:
        # 尝试不同的AWS CLI命令
        commands = [
            f"aws s3 ls s3://{bucket_name}/ --recursive",
            f"aws s3 ls s3://{bucket_name}/ --human-readable",
            f"aws s3 ls s3://{bucket_name}/data_lake/ --recursive",
            f"aws s3 ls s3://{bucket_name}/benchmark/ --recursive",
            f"aws s3api list-objects-v2 --bucket {bucket_name} --max-items 1000",
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
    
    except Exception as e:
        print(f"  ❌ AWS CLI方法失败: {e}")
    
    return False

def try_s3cmd_listing(bucket_name):
    """尝试使用s3cmd列出文件"""
    print("\n🔍 尝试s3cmd方法...")
    
    try:
        commands = [
            f"s3cmd ls s3://{bucket_name}/",
            f"s3cmd ls s3://{bucket_name}/data_lake/",
            f"s3cmd ls s3://{bucket_name}/benchmark/",
            f"s3cmd ls s3://{bucket_name}/ --recursive",
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
    
    except Exception as e:
        print(f"  ❌ s3cmd方法失败: {e}")
    
    return False

def check_tools():
    """检查可用的工具"""
    print("🔍 检查可用工具...")
    
    tools = {
        "curl": "curl --version",
        "aws": "aws --version",
        "s3cmd": "s3cmd --version",
    }
    
    available_tools = []
    for tool_name, version_cmd in tools.items():
        try:
            result = subprocess.run(version_cmd, shell=True, capture_output=True, text=True, timeout=10)
            if result.returncode == 0:
                print(f"  ✅ {tool_name}: 可用")
                available_tools.append(tool_name)
            else:
                print(f"  ❌ {tool_name}: 不可用")
        except Exception:
            print(f"  ❌ {tool_name}: 不可用")
    
    return available_tools

def check_network():
    """检查网络连接"""
    print("🔍 检查网络连接...")
    
    try:
        # 测试基本网络连接
        response = requests.get("https://www.google.com", timeout=5)
        if response.status_code == 200:
            print("  ✅ 基本网络连接正常")
        else:
            print("  ❌ 基本网络连接异常")
            return False
    except Exception as e:
        print(f"  ❌ 网络连接失败: {e}")
        return False
    
    # 测试S3连接
    try:
        response = requests.get("https://biomni-release.s3.amazonaws.com", timeout=10)
        print(f"  S3连接状态码: {response.status_code}")
        if response.status_code in [200, 403, 404]:
            print("  ✅ S3服务可访问")
            return True
        else:
            print("  ❌ S3服务不可访问")
            return False
    except Exception as e:
        print(f"  ❌ S3连接失败: {e}")
        return False

def main():
    """主函数"""
    bucket_url = "https://biomni-release.s3.amazonaws.com"
    bucket_name = "biomni-release"
    
    print("🚀 S3存储桶文件列表工具 - 简化版")
    print("=" * 50)
    print(f"目标存储桶: {bucket_name}")
    print(f"URL: {bucket_url}")
    print("=" * 50)
    
    # 检查网络连接
    if not check_network():
        print("❌ 网络连接检查失败，退出")
        return
    
    # 检查可用工具
    available_tools = check_tools()
    
    # 尝试不同方法
    methods = [
        ("HTTP请求", lambda: try_http_listing(bucket_url)),
        ("curl", lambda: try_curl_listing(bucket_name)),
    ]
    
    # 如果AWS CLI可用，添加到方法列表
    if "aws" in available_tools:
        methods.append(("AWS CLI", lambda: try_aws_cli_listing(bucket_name)))
    
    # 如果s3cmd可用，添加到方法列表
    if "s3cmd" in available_tools:
        methods.append(("s3cmd", lambda: try_s3cmd_listing(bucket_name)))
    
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
        print("3. 安装AWS CLI: pip install awscli")
        print("4. 配置AWS凭据: aws configure")
        print("5. 安装s3cmd: pip install s3cmd")
        print("6. 联系存储桶管理员获取访问权限")
        print("\n🔧 手动尝试命令:")
        print(f"curl -s 'https://{bucket_name}.s3.amazonaws.com/?list-type=2'")
        print(f"aws s3 ls s3://{bucket_name}/ --recursive")

if __name__ == "__main__":
    main() 