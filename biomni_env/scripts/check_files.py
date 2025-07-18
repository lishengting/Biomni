#!/usr/bin/env python3
"""
Biomni文件检测工具
用于检查data_lake和benchmark文件的下载状态
"""

import os
import sys
from pathlib import Path
from typing import Dict, List, Tuple

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

try:
    from biomni.env_desc import data_lake_dict
except ImportError:
    print("❌ 无法导入biomni模块，请确保在正确的环境中运行")
    sys.exit(1)

def get_expected_files() -> Dict[str, List[str]]:
    """获取期望的文件列表"""
    return {
        "data_lake": list(data_lake_dict.keys()),
        "benchmark": ["hle"]  # benchmark文件夹应该包含hle子目录
    }

def check_file_exists(file_path: str) -> Tuple[bool, str]:
    """检查文件是否存在并返回状态信息"""
    if os.path.exists(file_path):
        if os.path.isfile(file_path):
            size = os.path.getsize(file_path)
            return True, f"✅ 文件存在 ({size:,} bytes)"
        elif os.path.isdir(file_path):
            return True, "✅ 目录存在"
        else:
            return False, "❌ 路径存在但不是文件或目录"
    else:
        return False, "❌ 文件不存在"

def check_data_lake_files(data_lake_path: str) -> Dict[str, Tuple[bool, str]]:
    """检查data_lake文件"""
    print(f"\n🔍 检查data_lake文件 (路径: {data_lake_path})")
    print("=" * 80)
    
    expected_files = get_expected_files()["data_lake"]
    results = {}
    
    # 检查目录是否存在
    if not os.path.exists(data_lake_path):
        print(f"❌ data_lake目录不存在: {data_lake_path}")
        return {}
    
    print(f"📁 data_lake目录存在")
    print(f"📋 期望文件数量: {len(expected_files)}")
    
    # 检查每个期望的文件
    existing_files = []
    missing_files = []
    
    for filename in expected_files:
        file_path = os.path.join(data_lake_path, filename)
        exists, status = check_file_exists(file_path)
        results[filename] = (exists, status)
        
        if exists:
            existing_files.append(filename)
        else:
            missing_files.append(filename)
    
    # 显示统计信息
    print(f"\n📊 统计信息:")
    print(f"   ✅ 已下载: {len(existing_files)}/{len(expected_files)} ({len(existing_files)/len(expected_files)*100:.1f}%)")
    print(f"   ❌ 缺失: {len(missing_files)}/{len(expected_files)} ({len(missing_files)/len(expected_files)*100:.1f}%)")
    
    # 显示缺失的文件
    if missing_files:
        print(f"\n❌ 缺失的文件:")
        for i, filename in enumerate(missing_files[:10], 1):  # 只显示前10个
            print(f"   {i:2d}. {filename}")
        if len(missing_files) > 10:
            print(f"   ... 还有 {len(missing_files) - 10} 个文件")
    
    return results

def check_benchmark_files(benchmark_path: str) -> Dict[str, Tuple[bool, str]]:
    """检查benchmark文件"""
    print(f"\n🔍 检查benchmark文件 (路径: {benchmark_path})")
    print("=" * 80)
    
    results = {}
    
    # 检查主目录
    exists, status = check_file_exists(benchmark_path)
    results["benchmark_dir"] = (exists, status)
    
    if not exists:
        print("❌ benchmark目录不存在")
        return results
    
    print("✅ benchmark目录存在")
    
    # 检查hle子目录
    hle_path = os.path.join(benchmark_path, "hle")
    exists, status = check_file_exists(hle_path)
    results["hle"] = (exists, status)
    
    if exists:
        # 列出hle目录中的内容
        try:
            hle_contents = os.listdir(hle_path)
            print(f"📁 hle目录内容 ({len(hle_contents)} 个项目):")
            for item in hle_contents[:10]:  # 只显示前10个
                item_path = os.path.join(hle_path, item)
                if os.path.isfile(item_path):
                    size = os.path.getsize(item_path)
                    print(f"   📄 {item} ({size:,} bytes)")
                else:
                    print(f"   📁 {item}/")
            if len(hle_contents) > 10:
                print(f"   ... 还有 {len(hle_contents) - 10} 个项目")
        except Exception as e:
            print(f"⚠️ 无法读取hle目录内容: {e}")
    else:
        print("❌ hle子目录不存在")
    
    return results

def check_disk_space(path: str) -> None:
    """检查磁盘空间"""
    print(f"\n💾 检查磁盘空间 (路径: {path})")
    print("=" * 80)
    
    try:
        import shutil
        total, used, free = shutil.disk_usage(path)
        
        print(f"总空间: {total / (1024**3):.1f} GB")
        print(f"已使用: {used / (1024**3):.1f} GB")
        print(f"可用空间: {free / (1024**3):.1f} GB")
        print(f"使用率: {used / total * 100:.1f}%")
        
        if free < 5 * 1024**3:  # 小于5GB
            print("⚠️ 警告: 可用空间不足5GB，可能影响文件下载")
        else:
            print("✅ 磁盘空间充足")
            
    except Exception as e:
        print(f"⚠️ 无法检查磁盘空间: {e}")

def main():
    """主函数"""
    print("🧬 Biomni文件检测工具")
    print("=" * 80)
    
    # 获取数据路径
    data_path = os.getenv("BIOMNI_DATA_PATH", "./data")
    biomni_data_path = os.path.join(data_path, "biomni_data")
    data_lake_path = os.path.join(biomni_data_path, "data_lake")
    benchmark_path = os.path.join(biomni_data_path, "benchmark")
    
    print(f"📂 数据根目录: {data_path}")
    print(f"📂 Biomni数据目录: {biomni_data_path}")
    
    # 检查磁盘空间
    check_disk_space(data_path)
    
    # 检查data_lake文件
    data_lake_results = check_data_lake_files(data_lake_path)
    
    # 检查benchmark文件
    benchmark_results = check_benchmark_files(benchmark_path)
    
    # 总结
    print(f"\n📋 检测总结")
    print("=" * 80)
    
    total_expected = len(get_expected_files()["data_lake"]) + 1  # +1 for hle directory
    total_existing = sum(1 for exists, _ in data_lake_results.values() if exists) + \
                    sum(1 for exists, _ in benchmark_results.values() if exists)
    
    print(f"总期望文件/目录: {total_expected}")
    print(f"已存在文件/目录: {total_existing}")
    print(f"完成度: {total_existing/total_expected*100:.1f}%")
    
    if total_existing == total_expected:
        print("🎉 所有文件都已下载完成！")
    else:
        print("⚠️ 部分文件缺失，建议重新运行Biomni初始化或手动下载")
        
        # 提供下载建议
        print(f"\n💡 下载建议:")
        print("1. 重新运行Biomni agent初始化，会自动下载缺失文件")
        print("2. 检查网络连接，确保可以访问 https://biomni-release.s3.amazonaws.com")
        print("3. 确保有足够的磁盘空间（建议至少10GB可用空间）")
        print("4. 如果问题持续，可以尝试手动下载或联系技术支持")

if __name__ == "__main__":
    main() 