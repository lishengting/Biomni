#!/usr/bin/env python3
"""
S3存储桶目录列表工具 - 基于Biomni现有逻辑
使用与check_and_download_s3_files相同的HTTP请求方法来列出S3存储桶内容
"""

import requests
import os
import sys
from urllib.parse import urljoin, urlparse
import xml.etree.ElementTree as ET
from typing import Dict, List, Tuple, Optional

def list_s3_directory(s3_bucket_url: str, folder: str = "", max_keys: int = 1000) -> Dict[str, any]:
    """
    列出S3存储桶中指定文件夹的内容
    
    Args:
        s3_bucket_url: S3存储桶的基础URL (e.g., "https://biomni-release.s3.amazonaws.com")
        folder: 要列出的文件夹路径 (e.g., "data_lake", "benchmark", "")
        max_keys: 最大返回的对象数量
        
    Returns:
        包含文件和目录信息的字典
    """
    
    print(f"🔍 正在列出S3存储桶内容...")
    print(f"   存储桶URL: {s3_bucket_url}")
    print(f"   文件夹: {folder if folder else '根目录'}")
    print(f"   最大数量: {max_keys}")
    print("-" * 60)
    
    # 构建S3 ListObjectsV2 API URL
    if folder:
        # 如果有指定文件夹，添加prefix参数
        list_url = f"{s3_bucket_url}/?list-type=2&prefix={folder}/&max-keys={max_keys}"
    else:
        # 列出根目录
        list_url = f"{s3_bucket_url}/?list-type=2&max-keys={max_keys}"
    
    print(f"📡 请求URL: {list_url}")
    
    try:
        # 发送HTTP请求
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'application/xml, text/xml, */*'
        }
        
        response = requests.get(list_url, headers=headers, timeout=30)
        print(f"📊 响应状态码: {response.status_code}")
        
        if response.status_code == 200:
            print("✅ 成功获取S3存储桶内容")
            return parse_s3_xml_response(response.text, folder)
        else:
            print(f"❌ HTTP错误: {response.status_code}")
            print(f"响应内容: {response.text[:500]}...")
            return {"error": f"HTTP {response.status_code}", "details": response.text}
            
    except requests.exceptions.Timeout:
        print("❌ 请求超时")
        return {"error": "请求超时"}
    except requests.exceptions.RequestException as e:
        print(f"❌ 请求异常: {e}")
        return {"error": str(e)}
    except Exception as e:
        print(f"❌ 未知错误: {e}")
        return {"error": str(e)}

def parse_s3_xml_response(xml_content: str, folder: str) -> Dict[str, any]:
    """
    解析S3 XML响应
    
    Args:
        xml_content: S3 API返回的XML内容
        folder: 当前查询的文件夹
        
    Returns:
        解析后的文件和目录信息
    """
    
    try:
        root = ET.fromstring(xml_content)
        
        # 提取基本信息
        result = {
            "bucket_name": "",
            "prefix": "",
            "max_keys": 0,
            "is_truncated": False,
            "next_continuation_token": "",
            "files": [],
            "directories": [],
            "total_files": 0,
            "total_directories": 0,
            "total_size_bytes": 0
        }
        
        # 解析基本信息
        bucket_name_elem = root.find('.//{http://s3.amazonaws.com/doc/2006-03-01/}Name')
        if bucket_name_elem is not None:
            result["bucket_name"] = bucket_name_elem.text
            
        prefix_elem = root.find('.//{http://s3.amazonaws.com/doc/2006-03-01/}Prefix')
        if prefix_elem is not None:
            result["prefix"] = prefix_elem.text
            
        max_keys_elem = root.find('.//{http://s3.amazonaws.com/doc/2006-03-01/}MaxKeys')
        if max_keys_elem is not None:
            result["max_keys"] = int(max_keys_elem.text)
            
        is_truncated_elem = root.find('.//{http://s3.amazonaws.com/doc/2006-03-01/}IsTruncated')
        if is_truncated_elem is not None:
            result["is_truncated"] = is_truncated_elem.text.lower() == 'true'
            
        next_token_elem = root.find('.//{http://s3.amazonaws.com/doc/2006-03-01/}NextContinuationToken')
        if next_token_elem is not None:
            result["next_continuation_token"] = next_token_elem.text
        
        # 解析目录 (CommonPrefixes)
        directories = []
        for prefix_elem in root.findall('.//{http://s3.amazonaws.com/doc/2006-03-01/}CommonPrefixes'):
            prefix_text = prefix_elem.find('.//{http://s3.amazonaws.com/doc/2006-03-01/}Prefix')
            if prefix_text is not None:
                dir_name = prefix_text.text
                # 移除末尾的斜杠
                if dir_name.endswith('/'):
                    dir_name = dir_name[:-1]
                directories.append(dir_name)
        
        result["directories"] = directories
        result["total_directories"] = len(directories)
        
        # 解析文件 (Contents)
        files = []
        total_size = 0
        
        for content_elem in root.findall('.//{http://s3.amazonaws.com/doc/2006-03-01/}Contents'):
            key_elem = content_elem.find('.//{http://s3.amazonaws.com/doc/2006-03-01/}Key')
            size_elem = content_elem.find('.//{http://s3.amazonaws.com/doc/2006-03-01/}Size')
            last_modified_elem = content_elem.find('.//{http://s3.amazonaws.com/doc/2006-03-01/}LastModified')
            
            if key_elem is not None:
                file_info = {
                    "key": key_elem.text,
                    "name": os.path.basename(key_elem.text),
                    "size_bytes": int(size_elem.text) if size_elem is not None else 0,
                    "size_mb": round(int(size_elem.text) / (1024 * 1024), 2) if size_elem is not None else 0,
                    "last_modified": last_modified_elem.text if last_modified_elem is not None else "",
                }
                files.append(file_info)
                total_size += file_info["size_bytes"]
        
        result["files"] = files
        result["total_files"] = len(files)
        result["total_size_bytes"] = total_size
        result["total_size_mb"] = round(total_size / (1024 * 1024), 2)
        
        return result
        
    except ET.ParseError as e:
        print(f"❌ XML解析错误: {e}")
        print(f"XML内容: {xml_content[:500]}...")
        return {"error": f"XML解析错误: {e}", "raw_content": xml_content}

def format_file_size(size_bytes: int) -> str:
    """格式化文件大小显示"""
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    elif size_bytes < 1024 * 1024 * 1024:
        return f"{size_bytes / (1024 * 1024):.1f} MB"
    else:
        return f"{size_bytes / (1024 * 1024 * 1024):.1f} GB"

def print_directory_listing(result: Dict[str, any]):
    """打印目录列表结果"""
    
    if "error" in result:
        print(f"❌ 错误: {result['error']}")
        if "details" in result:
            print(f"详细信息: {result['details']}")
        return
    
    print(f"\n📊 S3存储桶信息:")
    print(f"   存储桶名称: {result.get('bucket_name', 'N/A')}")
    print(f"   当前前缀: {result.get('prefix', '根目录')}")
    print(f"   最大返回数量: {result.get('max_keys', 0)}")
    print(f"   是否被截断: {result.get('is_truncated', False)}")
    
    print(f"\n📁 目录列表 ({result['total_directories']} 个):")
    if result['directories']:
        for i, directory in enumerate(result['directories'], 1):
            print(f"   {i:2d}. {directory}/")
    else:
        print("   (无子目录)")
    
    print(f"\n📄 文件列表 ({result['total_files']} 个):")
    if result['files']:
        for i, file_info in enumerate(result['files'], 1):
            size_str = format_file_size(file_info['size_bytes'])
            print(f"   {i:2d}. {file_info['name']} ({size_str})")
            print(f"       路径: {file_info['key']}")
            if file_info['last_modified']:
                print(f"       修改时间: {file_info['last_modified']}")
    else:
        print("   (无文件)")
    
    print(f"\n📈 统计信息:")
    print(f"   总文件数: {result['total_files']}")
    print(f"   总目录数: {result['total_directories']}")
    print(f"   总大小: {format_file_size(result['total_size_bytes'])}")
    
    if result.get('is_truncated'):
        print(f"\n⚠️  结果被截断，还有更多内容。")
        print(f"   使用 next_continuation_token: {result.get('next_continuation_token', 'N/A')}")

def list_all_s3_content(s3_bucket_url: str) -> Dict[str, any]:
    """
    列出S3存储桶的所有内容（包括所有主要文件夹）
    
    Args:
        s3_bucket_url: S3存储桶的基础URL
        
    Returns:
        所有内容的汇总信息
    """
    
    print("🚀 开始全面扫描S3存储桶...")
    print("=" * 80)
    
    # 首先列出根目录
    root_result = list_s3_directory(s3_bucket_url, "")
    if "error" in root_result:
        return root_result
    
    print_directory_listing(root_result)
    
    # 然后列出主要文件夹
    main_folders = ["data_lake", "benchmark"]
    all_results = {"root": root_result}
    
    for folder in main_folders:
        print(f"\n{'='*20} 扫描 {folder} 文件夹 {'='*20}")
        folder_result = list_s3_directory(s3_bucket_url, folder)
        if "error" not in folder_result:
            print_directory_listing(folder_result)
            all_results[folder] = folder_result
        else:
            print(f"❌ 无法访问 {folder} 文件夹: {folder_result['error']}")
    
    return all_results

def main():
    """主函数"""
    s3_bucket_url = "https://biomni-release.s3.amazonaws.com"
    
    print("🧬 Biomni S3存储桶目录列表工具")
    print("=" * 80)
    print(f"目标存储桶: {s3_bucket_url}")
    print("=" * 80)
    
    # 检查命令行参数
    if len(sys.argv) > 1:
        folder = sys.argv[1]
        print(f"指定文件夹: {folder}")
        result = list_s3_directory(s3_bucket_url, folder)
        print_directory_listing(result)
    else:
        # 全面扫描
        all_results = list_all_s3_content(s3_bucket_url)
        
        # 生成汇总报告
        print(f"\n{'='*20} 汇总报告 {'='*20}")
        total_files = 0
        total_dirs = 0
        total_size = 0
        
        for folder_name, result in all_results.items():
            if "error" not in result:
                total_files += result.get('total_files', 0)
                total_dirs += result.get('total_directories', 0)
                total_size += result.get('total_size_bytes', 0)
                print(f"{folder_name}: {result.get('total_files', 0)} 文件, {result.get('total_directories', 0)} 目录")
        
        print(f"\n总计:")
        print(f"  文件数: {total_files}")
        print(f"  目录数: {total_dirs}")
        print(f"  总大小: {format_file_size(total_size)}")

if __name__ == "__main__":
    main() 