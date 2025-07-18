#!/usr/bin/env python3
"""
S3文件大小检查工具
直接查询S3存储桶中特定文件的大小和可访问性，支持下载和断点续传
"""

import requests
import os
import sys
from urllib.parse import urljoin
from typing import Dict, List, Tuple, Optional, Any
import time
import hashlib

def check_file_size(s3_bucket_url: str, file_path: str) -> Dict[str, Any]:
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

def download_file_with_resume(s3_bucket_url: str, file_path: str, local_dir: str = ".", chunk_size: int = 8192, max_retries: int = 3, retry_delay: float = 5.0) -> Dict[str, Any]:
    """
    下载文件，支持断点续传和自动重试
    
    Args:
        s3_bucket_url: S3存储桶的基础URL
        file_path: 文件在存储桶中的路径
        local_dir: 本地保存目录
        chunk_size: 下载块大小
        max_retries: 最大重试次数
        retry_delay: 重试间隔（秒）
        
    Returns:
        下载结果字典
    """
    
    # 构建完整的文件URL
    file_url = urljoin(s3_bucket_url + "/", file_path)
    
    # 确定本地文件路径
    filename = os.path.basename(file_path)
    local_file_path = os.path.join(local_dir, filename)
    temp_file_path = local_file_path + ".tmp"
    
    print(f"📥 开始下载文件: {file_path}")
    print(f"📡 URL: {file_url}")
    print(f"💾 本地路径: {local_file_path}")
    
    # 确保目录存在
    os.makedirs(local_dir, exist_ok=True)
    
    # 检查是否存在临时文件（断点续传）
    resume_pos = 0
    if os.path.exists(temp_file_path):
        resume_pos = os.path.getsize(temp_file_path)
        print(f"🔄 发现临时文件，从 {format_file_size(resume_pos)} 处继续下载")
    
    # 重试逻辑
    for retry_count in range(max_retries + 1):
        try:
            # 首先检查文件信息
            file_info = check_file_size(s3_bucket_url, file_path)
            if not file_info["accessible"]:
                return {
                    "success": False,
                    "error": file_info["error"],
                    "file_path": file_path,
                    "local_path": local_file_path
                }
            
            total_size = file_info["size_bytes"]
            
            # 如果文件已完整下载，直接返回
            if os.path.exists(local_file_path) and os.path.getsize(local_file_path) == total_size:
                print(f"✅ 文件已完整下载: {local_file_path}")
                return {
                    "success": True,
                    "file_path": file_path,
                    "local_path": local_file_path,
                    "size": total_size,
                    "message": "文件已存在且完整"
                }
            
            # 设置请求头，支持断点续传
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            
            if resume_pos > 0:
                headers['Range'] = f'bytes={resume_pos}-'
            
            # 开始下载
            response = requests.get(file_url, headers=headers, stream=True, timeout=30)
            
            if response.status_code not in [200, 206]:
                return {
                    "success": False,
                    "error": f"HTTP错误: {response.status_code}",
                    "file_path": file_path,
                    "local_path": local_file_path
                }
            
            # 打开文件进行写入
            mode = 'ab' if resume_pos > 0 else 'wb'
            with open(temp_file_path, mode) as f:
                downloaded = resume_pos
                last_progress_time = time.time()
                session_start_time = time.time()  # 本次会话开始时间
                session_downloaded = 0  # 本次会话下载的字节数
                
                for chunk in response.iter_content(chunk_size=chunk_size):
                    if chunk:
                        f.write(chunk)
                        downloaded += len(chunk)
                        session_downloaded += len(chunk)
                        
                        # 显示进度（每秒更新一次）
                        current_time = time.time()
                        if current_time - last_progress_time >= 1.0:
                            progress = (downloaded / total_size) * 100
                            # 计算实际下载速度（从本次会话开始到现在）
                            speed = session_downloaded / (current_time - session_start_time) if (current_time - session_start_time) > 0 else 0
                            print(f"📊 进度: {progress:.1f}% ({format_file_size(downloaded)}/{format_file_size(total_size)}) "
                                  f"速度: {format_file_size(int(speed))}/s")
                            last_progress_time = current_time
            
            # 下载完成，重命名临时文件
            if os.path.exists(local_file_path):
                os.remove(local_file_path)  # 删除旧文件
            os.rename(temp_file_path, local_file_path)
            
            # 验证文件大小
            final_size = os.path.getsize(local_file_path)
            if final_size == total_size:
                print(f"✅ 下载完成: {local_file_path}")
                print(f"   大小: {format_file_size(final_size)}")
                return {
                    "success": True,
                    "file_path": file_path,
                    "local_path": local_file_path,
                    "size": final_size,
                    "message": "下载成功"
                }
            else:
                print(f"⚠️ 文件大小不匹配: 期望 {format_file_size(total_size)}, 实际 {format_file_size(final_size)}")
                return {
                    "success": False,
                    "error": f"文件大小不匹配: 期望 {total_size}, 实际 {final_size}",
                    "file_path": file_path,
                    "local_path": local_file_path
                }
                
        except (requests.exceptions.Timeout, requests.exceptions.RequestException) as e:
            error_msg = f"下载异常: {e}"
            print(f"❌ {error_msg}")
            
            if retry_count < max_retries:
                print(f"🔄 {retry_delay}秒后进行第{retry_count + 1}次重试...")
                time.sleep(retry_delay)
                # 更新断点位置（重新检查临时文件大小）
                if os.path.exists(temp_file_path):
                    resume_pos = os.path.getsize(temp_file_path)
                    print(f"🔄 断点续传位置: {format_file_size(resume_pos)}")
                continue
            else:
                print(f"❌ 重试{max_retries}次后仍然失败")
                return {
                    "success": False,
                    "error": error_msg,
                    "file_path": file_path,
                    "local_path": local_file_path
                }
        except Exception as e:
            error_msg = f"未知错误: {e}"
            print(f"❌ {error_msg}")
            return {
                "success": False,
                "error": error_msg,
                "file_path": file_path,
                "local_path": local_file_path
            }
    
    # 默认返回值（理论上不会执行到这里）
    return {
        "success": False,
        "error": "未知错误",
        "file_path": file_path,
        "local_path": local_file_path
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

def check_multiple_files(s3_bucket_url: str, file_list: List[str], local_dir: Optional[str] = None, delay: float = 0.1) -> List[Dict[str, Any]]:
    """
    检查多个文件的大小和可访问性，可选比较本地文件大小
    
    Args:
        s3_bucket_url: S3存储桶的基础URL
        file_list: 文件路径列表
        local_dir: 本地目录路径，用于比较文件大小
        delay: 请求之间的延迟（秒）
        
    Returns:
        文件信息列表
    """
    
    print(f"🚀 开始检查 {len(file_list)} 个文件...")
    if local_dir:
        print(f"📁 将比较本地目录: {local_dir}")
    print("=" * 80)
    
    results = []
    accessible_count = 0
    total_size = 0
    mismatch_count = 0
    
    for i, file_path in enumerate(file_list, 1):
        print(f"\n[{i}/{len(file_list)}] ", end="")
        result = check_file_size(s3_bucket_url, file_path)
        
        # 如果指定了本地目录，检查本地文件大小
        if local_dir and result["accessible"]:
            # 保持完整的目录结构
            local_file_path = os.path.join(local_dir, file_path)
            
            if os.path.exists(local_file_path):
                local_size = os.path.getsize(local_file_path)
                result["local_size"] = local_size
                result["local_size_formatted"] = format_file_size(local_size)
                
                if local_size != result["size_bytes"]:
                    result["size_mismatch"] = True
                    mismatch_count += 1
                    print(f"⚠️ 大小不匹配: 网络 {format_file_size(result['size_bytes'])}, 本地 {format_file_size(local_size)}")
                else:
                    result["size_mismatch"] = False
                    print(f"✅ 大小匹配: {format_file_size(local_size)}")
            else:
                result["local_size"] = 0
                result["local_size_formatted"] = "文件不存在"
                result["size_mismatch"] = False
                print(f"📁 本地文件不存在")
        
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
    
    if local_dir:
        print(f"本地目录: {local_dir}")
        print(f"大小不匹配文件: {mismatch_count}")
        if mismatch_count > 0:
            print("⚠️ 发现大小不匹配的文件，建议重新下载")
    
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

def show_usage():
    """显示使用说明"""
    print("""
🧬 Biomni S3文件工具 - 使用说明

用法:
  python check_s3_file.py [命令] [参数]

命令:
  check <文件路径>           - 检查指定文件的大小和可访问性
  download <文件路径> [目录]  - 下载指定文件到本地目录（默认当前目录）
  list [本地目录]            - 检查所有期望的文件，可选比较本地文件大小
  help                      - 显示此帮助信息

示例:
  python check_s3_file.py check data_lake/gene_info.parquet
  python check_s3_file.py download data_lake/gene_info.parquet
  python check_s3_file.py download data_lake/gene_info.parquet ./downloads
  python check_s3_file.py list
  python check_s3_file.py list ./data/biomni_data

特性:
  ✅ 支持断点续传
  ✅ 自动重试（网络异常时）
  ✅ 显示下载进度和速度
  ✅ 自动验证文件完整性
  ✅ 支持批量检查
  ✅ 比较网络和本地文件大小
""")

def main():
    """主函数"""
    s3_bucket_url = "https://biomni-release.s3.amazonaws.com"
    
    print("🧬 Biomni S3文件工具")
    print("=" * 80)
    print(f"目标存储桶: {s3_bucket_url}")
    print("=" * 80)
    
    # 检查命令行参数
    if len(sys.argv) < 2:
        show_usage()
        return
    
    command = sys.argv[1].lower()
    
    if command == "help":
        show_usage()
        return
    
    elif command == "check":
        if len(sys.argv) < 3:
            print("❌ 请指定要检查的文件路径")
            print("用法: python check_s3_file.py check <文件路径>")
            return
        
        file_path = sys.argv[2]
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
    
    elif command == "download":
        if len(sys.argv) < 3:
            print("❌ 请指定要下载的文件路径")
            print("用法: python check_s3_file.py download <文件路径> [目录]")
            return
        
        file_path = sys.argv[2]
        local_dir = sys.argv[3] if len(sys.argv) > 3 else "."
        
        print(f"下载文件: {file_path} 到目录: {local_dir}")
        result = download_file_with_resume(s3_bucket_url, file_path, local_dir)
        
        if result["success"]:
            print(f"\n✅ 下载成功: {result['local_path']}")
            print(f"   大小: {format_file_size(result['size'])}")
        else:
            print(f"\n❌ 下载失败: {result['error']}")
    
    elif command == "list":
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
        
        # 检查是否有本地目录参数
        local_dir = None
        if len(sys.argv) > 2:
            local_dir = sys.argv[2]
            print(f"将比较本地目录: {local_dir}")
        
        print(f"将检查 {len(expected_files)} 个文件")
        
        # 询问用户是否继续
        response = input("\n是否继续检查所有文件? (y/n): ").lower().strip()
        if response in ['y', 'yes', '是']:
            results = check_multiple_files(s3_bucket_url, expected_files, local_dir)
            
            # 保存结果到文件
            output_file = "s3_file_check_results.txt"
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write("S3文件检查结果\n")
                f.write("=" * 50 + "\n")
                f.write(f"检查时间: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"存储桶: {s3_bucket_url}\n")
                if local_dir:
                    f.write(f"本地目录: {local_dir}\n")
                f.write("\n")
                
                for result in results:
                    f.write(f"文件: {result['file_path']}\n")
                    f.write(f"状态: {'可访问' if result['accessible'] else '不可访问'}\n")
                    if result['accessible']:
                        f.write(f"大小: {format_file_size(result['size_bytes'])}\n")
                        f.write(f"类型: {result['content_type']}\n")
                        if local_dir and 'local_size' in result:
                            f.write(f"本地大小: {result['local_size_formatted']}\n")
                            if result.get('size_mismatch', False):
                                f.write("⚠️ 大小不匹配\n")
                    else:
                        f.write(f"错误: {result['error']}\n")
                    f.write("-" * 30 + "\n")
            
            print(f"\n结果已保存到: {output_file}")
        else:
            print("检查已取消")
    
    else:
        print(f"❌ 未知命令: {command}")
        show_usage()

if __name__ == "__main__":
    main() 