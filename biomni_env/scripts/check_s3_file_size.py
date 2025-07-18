#!/usr/bin/env python3
"""
S3文件大小检查工具
直接查询S3存储桶中特定文件的大小和可访问性
"""

import requests
import os
import sys
from urllib.parse import urljoin
from typing import Dict, List, Tuple, Optional
import time

def check_file_size(s3_bucket_url: str, file_path: str) -> Dict[str, any]:
    """
    检查S3存储桶中特定文件的大小和可访问性
    
    Args:
        s3_bucket_url: S3存储桶的基础URL (e.g., "https://biomni-release.s3.amazonaws.com")
        file_path: 文件在存储桶中的路径 (e.g., "data_lake/gene_info.parquet")
        
    Returns:
        包含文件信息的字典
    """
    
    # 构建完整的文件URL
    file_url = urljoin(s3_bucket_url + "/", file_path)
    
    print(f"🔍 检查文件: {file_path}")
    print(f"📡 URL: {file_url}")
    
    try:
        # 发送HEAD请求来获取文件信息（不下载内容）
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        
        response = requests.head(file_url, headers=headers, timeout=30)
        
        result = {
            "file_path": file_path,
            "url": file_url,
            "status_code": response.status_code,
            "accessible": False,
            "size_bytes": 0,
            "size_mb": 0,
            "content_type": "",
            "last_modified": "",
            "etag": "",
            "error": None
        }
        
        if response.status_code == 200:
            # 文件存在且可访问
            result["accessible"] = True
            
            # 获取文件大小
            content_length = response.headers.get('content-length')
            if content_length:
                result["size_bytes"] = int(content_length)
                result["size_mb"] = round(int(content_length) / (1024 * 1024), 2)
            
            # 获取其他信息
            result["content_type"] = response.headers.get('content-type', '')
            result["last_modified"] = response.headers.get('last-modified', '')
            result["etag"] = response.headers.get('etag', '')
            
            print(f"✅ 文件可访问")
            print(f"   大小: {format_file_size(result['size_bytes'])}")
            print(f"   类型: {result['content_type']}")
            if result['last_modified']:
                print(f"   修改时间: {result['last_modified']}")
                
        elif response.status_code == 404:
            result["error"] = "文件不存在"
            print(f"❌ 文件不存在 (404)")
        elif response.status_code == 403:
            result["error"] = "访问被拒绝"
            print(f"❌ 访问被拒绝 (403)")
        else:
            result["error"] = f"HTTP错误: {response.status_code}"
            print(f"❌ HTTP错误: {response.status_code}")
            
        return result
        
    except requests.exceptions.Timeout:
        error_msg = "请求超时"
        print(f"❌ {error_msg}")
        return {
            "file_path": file_path,
            "url": file_url,
            "status_code": None,
            "accessible": False,
            "size_bytes": 0,
            "size_mb": 0,
            "error": error_msg
        }
    except requests.exceptions.RequestException as e:
        error_msg = f"请求异常: {e}"
        print(f"❌ {error_msg}")
        return {
            "file_path": file_path,
            "url": file_url,
            "status_code": None,
            "accessible": False,
            "size_bytes": 0,
            "size_mb": 0,
            "error": error_msg
        }
    except Exception as e:
        error_msg = f"未知错误: {e}"
        print(f"❌ {error_msg}")
        return {
            "file_path": file_path,
            "url": file_url,
            "status_code": None,
            "accessible": False,
            "size_bytes": 0,
            "size_mb": 0,
            "error": error_msg
        }

def format_file_size(size_bytes: int) -> str:
    """格式化文件大小显示"""
    if size_bytes == 0:
        return "0 B"
    elif size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    elif size_bytes < 1024 * 1024 * 1024:
        return f"{size_bytes / (1024 * 1024):.1f} MB"
    else:
        return f"{size_bytes / (1024 * 1024 * 1024):.1f} GB"

def check_multiple_files(s3_bucket_url: str, file_list: List[str], delay: float = 0.1) -> List[Dict[str, any]]:
    """
    检查多个文件的大小和可访问性
    
    Args:
        s3_bucket_url: S3存储桶的基础URL
        file_list: 文件路径列表
        delay: 请求之间的延迟（秒）
        
    Returns:
        文件信息列表
    """
    
    print(f"🚀 开始检查 {len(file_list)} 个文件...")
    print("=" * 80)
    
    results = []
    accessible_count = 0
    total_size = 0
    
    for i, file_path in enumerate(file_list, 1):
        print(f"\n[{i}/{len(file_list)}] ", end="")
        result = check_file_size(s3_bucket_url, file_path)
        results.append(result)
        
        if result["accessible"]:
            accessible_count += 1
            total_size += result["size_bytes"]
        
        # 添加延迟避免请求过快
        if i < len(file_list):
            time.sleep(delay)
    
    # 打印汇总信息
    print(f"\n{'='*20} 检查结果汇总 {'='*20}")
    print(f"总文件数: {len(file_list)}")
    print(f"可访问文件: {accessible_count}")
    print(f"不可访问文件: {len(file_list) - accessible_count}")
    print(f"成功率: {accessible_count/len(file_list)*100:.1f}%")
    print(f"总大小: {format_file_size(total_size)}")
    
    return results

def get_expected_files_from_env_desc() -> List[str]:
    """从env_desc.py获取期望的文件列表"""
    try:
        # 尝试导入data_lake_dict
        import sys
        import os
        
        # 添加项目路径
        project_root = os.path.dirname(os.path.abspath(__file__))
        if project_root.endswith('scripts'):
            project_root = os.path.dirname(project_root)
        sys.path.insert(0, project_root)
        
        from biomni.env_desc import data_lake_dict
        
        # 获取data_lake文件列表
        data_lake_files = [f"data_lake/{filename}" for filename in data_lake_dict.keys()]
        
        # 添加benchmark文件
        benchmark_files = [
            "benchmark.zip"  # benchmark文件夹通常作为zip文件下载
        ]
        
        return data_lake_files + benchmark_files
        
    except ImportError as e:
        print(f"⚠️ 无法导入biomni模块: {e}")
        print("将使用默认文件列表")
        return []

def main():
    """主函数"""
    s3_bucket_url = "https://biomni-release.s3.amazonaws.com"
    
    print("🧬 Biomni S3文件大小检查工具")
    print("=" * 80)
    print(f"目标存储桶: {s3_bucket_url}")
    print("=" * 80)
    
    # 检查命令行参数
    if len(sys.argv) > 1:
        # 检查指定的文件
        file_path = sys.argv[1]
        print(f"检查指定文件: {file_path}")
        result = check_file_size(s3_bucket_url, file_path)
        
        if result["accessible"]:
            print(f"\n✅ 文件信息:")
            print(f"   路径: {result['file_path']}")
            print(f"   大小: {format_file_size(result['size_bytes'])}")
            print(f"   类型: {result['content_type']}")
            if result['last_modified']:
                print(f"   修改时间: {result['last_modified']}")
        else:
            print(f"\n❌ 文件不可访问: {result['error']}")
    else:
        # 检查所有期望的文件
        print("获取期望的文件列表...")
        expected_files = get_expected_files_from_env_desc()
        
        if not expected_files:
            # 使用一些常见的文件作为示例
            expected_files = [
                "data_lake/gene_info.parquet",
                "data_lake/hp.obo",
                "data_lake/txgnn_name_mapping.pkl",
                "data_lake/txgnn_prediction.pkl",
                "data_lake/sgRNA/KO_SP_human.txt",
                "data_lake/sgRNA/KO_SP_mouse.txt",
                "benchmark.zip"
            ]
            print("使用示例文件列表")
        
        print(f"将检查 {len(expected_files)} 个文件")
        
        # 询问用户是否继续
        response = input("\n是否继续检查所有文件? (y/n): ").lower().strip()
        if response in ['y', 'yes', '是']:
            results = check_multiple_files(s3_bucket_url, expected_files)
            
            # 保存结果到文件
            output_file = "s3_file_check_results.txt"
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write("S3文件检查结果\n")
                f.write("=" * 50 + "\n")
                f.write(f"检查时间: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"存储桶: {s3_bucket_url}\n\n")
                
                for result in results:
                    f.write(f"文件: {result['file_path']}\n")
                    f.write(f"状态: {'可访问' if result['accessible'] else '不可访问'}\n")
                    if result['accessible']:
                        f.write(f"大小: {format_file_size(result['size_bytes'])}\n")
                        f.write(f"类型: {result['content_type']}\n")
                    else:
                        f.write(f"错误: {result['error']}\n")
                    f.write("-" * 30 + "\n")
            
            print(f"\n结果已保存到: {output_file}")
        else:
            print("检查已取消")

if __name__ == "__main__":
    main() 