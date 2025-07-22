#!/usr/bin/env python3
"""
Biomni文件检测工具
用于检查data_lake和benchmark文件的下载状态，以及各种包的安装状态
"""

import os
import sys
import json
import yaml
import subprocess
from pathlib import Path
from typing import Dict, List, Tuple, Optional
import re
import importlib.util

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

def run_command(cmd: List[str], capture_output: bool = True) -> Tuple[int, str, str]:
    """运行命令并返回结果"""
    try:
        if capture_output:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            return result.returncode, result.stdout, result.stderr
        else:
            result = subprocess.run(cmd, timeout=30)
            return result.returncode, "", ""
    except subprocess.TimeoutExpired:
        return -1, "", "命令执行超时"
    except Exception as e:
        return -1, "", str(e)

def check_conda_package(package_name: str) -> Tuple[bool, str]:
    """检查conda包是否已安装"""
    cmd = ["conda", "list", package_name, "--json"]
    returncode, stdout, stderr = run_command(cmd)
    
    if returncode == 0:
        try:
            data = json.loads(stdout)
            if data:  # 如果返回了包信息
                version = data[0].get('version', '未知版本') if data else '未知版本'
                return True, f"✅ 已安装 (conda, {version})"
            else:
                # 检查是否有其他版本可用
                search_cmd = ["conda", "search", package_name, "--json"]
                search_returncode, search_stdout, search_stderr = run_command(search_cmd)
                if search_returncode == 0:
                    try:
                        search_data = json.loads(search_stdout)
                        if search_data and package_name in search_data:
                            versions = [pkg.get('version', '') for pkg in search_data[package_name]]
                            available_versions = ', '.join(versions[:3])  # 只显示前3个版本
                            if len(versions) > 3:
                                available_versions += f" ... (共{len(versions)}个版本)"
                            return False, f"❌ 未安装 (可用版本: {available_versions})"
                        else:
                            return False, "❌ 未安装 (包不存在)"
                    except json.JSONDecodeError:
                        return False, "❌ 未安装"
                else:
                    return False, "❌ 未安装"
        except json.JSONDecodeError:
            return False, "❌ 解析conda输出失败"
    else:
        return False, f"❌ 检查失败: {stderr}"

def check_pip_package(package_name: str) -> Tuple[bool, str]:
    """检查pip包是否已安装"""
    # 处理版本号
    base_name = package_name
    expected_version = None
    if '==' in package_name:
        base_name, expected_version = package_name.split('==', 1)
    
    cmd = [sys.executable, "-m", "pip", "show", base_name]
    returncode, stdout, stderr = run_command(cmd)
    
    if returncode == 0:
        # 解析pip show的输出获取版本信息
        lines = stdout.strip().split('\n')
        version = "未知版本"
        for line in lines:
            if line.startswith('Version:'):
                version = line.split(':', 1)[1].strip()
                break
        
        # 检查版本是否匹配
        if expected_version and version != expected_version:
            return False, f"❌ 版本不匹配 (期望: {expected_version}, 实际: {version})"
        else:
            return True, f"✅ 已安装 (pip, {version})"
    else:
        # 检查是否有其他版本可用
        search_cmd = [sys.executable, "-m", "pip", "index", "versions", base_name]
        search_returncode, search_stdout, search_stderr = run_command(search_cmd)
        
        if search_returncode == 0:
            # 解析可用版本
            lines = search_stdout.strip().split('\n')
            available_versions = []
            for line in lines:
                if 'Available versions:' in line:
                    # 提取版本信息
                    versions_str = line.split('Available versions:')[1].strip()
                    available_versions = [v.strip() for v in versions_str.split(',')]
                    break
            
            if available_versions:
                version_display = ', '.join(available_versions[:3])  # 只显示前3个版本
                if len(available_versions) > 3:
                    version_display += f" ... (共{len(available_versions)}个版本)"
                
                if expected_version:
                    return False, f"❌ 未安装 (期望版本: {expected_version}, 可用版本: {version_display})"
                else:
                    return False, f"❌ 未安装 (可用版本: {version_display})"
            else:
                if expected_version:
                    return False, f"❌ 未安装 (期望版本: {expected_version})"
                else:
                    return False, "❌ 未安装"
        else:
            if expected_version:
                return False, f"❌ 未安装 (期望版本: {expected_version})"
            else:
                return False, "❌ 未安装"

def check_r_package(package_name: str) -> Tuple[bool, str]:
    """检查R包是否已安装"""
    r_script = f"""
    if (require({package_name}, quietly = TRUE)) {{
        cat("INSTALLED")
    }} else {{
        cat("NOT_INSTALLED")
    }}
    """
    cmd = ["Rscript", "-e", r_script]
    returncode, stdout, stderr = run_command(cmd)
    
    if returncode == 0 and "INSTALLED" in stdout:
        return True, f"✅ 已安装 (R)"
    else:
        return False, "❌ 未安装"

def check_cli_tool(tool_name: str, binary_path: str) -> Tuple[bool, str]:
    """检查CLI工具是否可用"""
    # 首先检查二进制文件是否存在
    if os.path.exists(binary_path) and os.access(binary_path, os.X_OK):
        return True, f"✅ 已安装 ({binary_path})"
    
    # 检查是否在PATH中
    cmd = ["which", tool_name]
    returncode, stdout, stderr = run_command(cmd)
    
    if returncode == 0:
        path = stdout.strip()
        return True, f"✅ 已安装 ({path})"
    else:
        return False, "❌ 未安装或不在PATH中"

def parse_environment_yml(file_path: str) -> Dict[str, List[str]]:
    """解析environment.yml文件"""
    packages = {"conda": [], "pip": []}
    
    try:
        with open(file_path, 'r') as f:
            data = yaml.safe_load(f)
        
        if 'dependencies' in data:
            for dep in data['dependencies']:
                if isinstance(dep, dict) and 'pip' in dep:
                    packages['pip'].extend(dep['pip'])
                elif isinstance(dep, str):
                    packages['conda'].append(dep)
                    
    except Exception as e:
        print(f"⚠️ 解析 {file_path} 失败: {e}")
    
    return packages

def parse_bio_env_yml(file_path: str) -> Dict[str, List[str]]:
    """解析bio_env.yml文件"""
    packages = {"conda": [], "pip": []}
    
    try:
        with open(file_path, 'r') as f:
            data = yaml.safe_load(f)
        
        if 'dependencies' in data:
            for dep in data['dependencies']:
                if isinstance(dep, dict) and 'pip' in dep:
                    packages['pip'].extend(dep['pip'])
                elif isinstance(dep, str):
                    packages['conda'].append(dep)
                    
    except Exception as e:
        print(f"⚠️ 解析 {file_path} 失败: {e}")
    
    return packages

def parse_r_packages_yml(file_path: str) -> List[str]:
    """解析r_packages.yml文件"""
    packages = []
    
    try:
        with open(file_path, 'r') as f:
            data = yaml.safe_load(f)
        
        if 'dependencies' in data:
            for dep in data['dependencies']:
                if isinstance(dep, str) and dep.startswith('r-'):
                    # 移除r-前缀
                    packages.append(dep[2:])
                    
    except Exception as e:
        print(f"⚠️ 解析 {file_path} 失败: {e}")
    
    return packages

def parse_cli_tools_config(file_path: str) -> List[Dict[str, str]]:
    """解析CLI工具配置文件"""
    tools = []
    
    try:
        with open(file_path, 'r') as f:
            data = json.load(f)
        
        if 'tools' in data:
            for tool in data['tools']:
                tools.append({
                    'name': tool.get('name', ''),
                    'binary_path': tool.get('binary_path', ''),
                    'function_name': tool.get('function_name', '')
                })
                    
    except Exception as e:
        print(f"⚠️ 解析 {file_path} 失败: {e}")
    
    return tools

def parse_r_packages_from_rscript(file_path: str) -> List[str]:
    """自动解析install_r_packages.R中的R包名"""
    packages = set()
    try:
        with open(file_path, 'r') as f:
            content = f.read()
        # 解析cran_packages和bioc_packages
        for var in ["cran_packages", "bioc_packages"]:
            m = re.search(rf'{var}\s*<-\s*c\(([^)]*)\)', content, re.MULTILINE)
            if m:
                pkgs = m.group(1)
                for p in re.findall(r'"([^"]+)"', pkgs):
                    packages.add(p)
        # 解析WGCNA、clusterProfiler等特殊包
        for special in ["WGCNA", "clusterProfiler"]:
            packages.add(special)
        # 解析install_if_missing调用
        for m in re.finditer(r'install_if_missing\(("|\")(.*?)("|\")', content):
            packages.add(m.group(2))
    except Exception as e:
        print(f"⚠️ 解析 {file_path} 失败: {e}")
    return list(sorted(packages))

def check_environment_packages() -> Dict[str, Dict[str, Tuple[bool, str]]]:
    """检查environment.yml中的包"""
    print(f"\n🔍 检查environment.yml包")
    print("=" * 80)
    
    file_path = "environment.yml"
    if not os.path.exists(file_path):
        print(f"❌ {file_path} 文件不存在")
        return {}
    
    packages = parse_environment_yml(file_path)
    results = {}
    
    # 检查conda包
    if packages['conda']:
        print(f"📦 检查 {len(packages['conda'])} 个conda包:")
        for pkg in packages['conda']:
            exists, status = check_conda_package(pkg)
            results[f"conda:{pkg}"] = (exists, status)
            print(f"   {pkg}: {status}")
    
    # 检查pip包
    if packages['pip']:
        print(f"📦 检查 {len(packages['pip'])} 个pip包:")
        for pkg in packages['pip']:
            exists, status = check_pip_package(pkg)
            results[f"pip:{pkg}"] = (exists, status)
            print(f"   {pkg}: {status}")
    
    return results

def check_bio_env_packages() -> Dict[str, Tuple[bool, str]]:
    """检查bio_env.yml中的包"""
    print(f"\n🔍 检查bio_env.yml包")
    print("=" * 80)
    
    file_path = "bio_env.yml"
    if not os.path.exists(file_path):
        print(f"❌ {file_path} 文件不存在")
        return {}
    
    packages = parse_bio_env_yml(file_path)
    results = {}
    
    # 检查conda包
    if packages['conda']:
        print(f"📦 检查 {len(packages['conda'])} 个conda包:")
        for pkg in packages['conda']:
            exists, status = check_conda_package(pkg)
            results[f"conda:{pkg}"] = (exists, status)
            print(f"   {pkg}: {status}")
    
    # 检查pip包
    if packages['pip']:
        print(f"📦 检查 {len(packages['pip'])} 个pip包:")
        for pkg in packages['pip']:
            exists, status = check_pip_package(pkg)
            results[f"pip:{pkg}"] = (exists, status)
            print(f"   {pkg}: {status}")
    
    return results

def check_r_packages() -> Dict[str, Tuple[bool, str]]:
    """检查R包，包括r_packages.yml和install_r_packages.R"""
    print(f"\n🔍 检查R包")
    print("=" * 80)
    
    yml_file = "r_packages.yml"
    rscript_file = "install_r_packages.R"
    pkgs = set()
    if os.path.exists(yml_file):
        pkgs.update(parse_r_packages_yml(yml_file))
    if os.path.exists(rscript_file):
        pkgs.update(parse_r_packages_from_rscript(rscript_file))
    if not pkgs:
        print("❌ 未找到R包配置")
        return {}
    results = {}
    print(f"📦 检查 {len(pkgs)} 个R包:")
    for pkg in sorted(pkgs):
        exists, status = check_r_package(pkg)
        results[f"r:{pkg}"] = (exists, status)
        print(f"   {pkg}: {status}")
    return results

def check_cli_tools() -> Dict[str, Tuple[bool, str]]:
    """检查CLI工具"""
    print(f"\n🔍 检查CLI工具")
    print("=" * 80)
    
    file_path = "cli_tools_config.json"
    if not os.path.exists(file_path):
        print(f"❌ {file_path} 文件不存在")
        return {}
    
    tools = parse_cli_tools_config(file_path)
    results = {}
    
    if tools:
        print(f"🔧 检查 {len(tools)} 个CLI工具:")
        for tool in tools:
            name = tool['name']
            binary_path = tool['binary_path']
            
            # 检查工具是否可用
            exists, status = check_cli_tool(name.lower(), binary_path)
            results[f"cli:{name}"] = (exists, status)
            print(f"   {name}: {status}")
    
    return results

def check_install_scripts() -> Dict[str, Tuple[bool, str]]:
    """检查安装脚本是否存在"""
    print(f"\n🔍 检查安装脚本")
    print("=" * 80)
    
    scripts = {
        "install_cli_tools.sh": "CLI工具安装脚本",
        "install_r_packages.R": "R包安装脚本"
    }
    
    results = {}
    
    for script, description in scripts.items():
        exists, status = check_file_exists(script)
        results[f"script:{script}"] = (exists, status)
        print(f"   {script} ({description}): {status}")
    
    return results

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

def generate_summary_report(all_results: Dict[str, Dict[str, Tuple[bool, str]]]) -> None:
    """生成总结报告"""
    print(f"\n📋 检测总结报告")
    print("=" * 80)
    
    total_items = 0
    installed_items = 0
    
    for category, results in all_results.items():
        if results:
            category_total = len(results)
            category_installed = sum(1 for exists, _ in results.values() if exists)
            total_items += category_total
            installed_items += category_installed
            
            percentage = (category_installed / category_total * 100) if category_total > 0 else 0
            print(f"{category}: {category_installed}/{category_total} ({percentage:.1f}%)")
    
    if total_items > 0:
        overall_percentage = installed_items / total_items * 100
        print(f"\n总体完成度: {installed_items}/{total_items} ({overall_percentage:.1f}%)")
        
        if overall_percentage == 100:
            print("🎉 所有组件都已正确安装！")
        elif overall_percentage >= 80:
            print("✅ 大部分组件已安装，系统基本可用")
        elif overall_percentage >= 50:
            print("⚠️ 部分组件缺失，建议检查安装")
        else:
            print("❌ 大量组件缺失，建议重新安装")

# 检查env_desc.py中的所有数据、模块和工具

def check_env_desc():
    print(f"\n🔍 检查env_desc.py中的所有数据、模块和工具")
    print("=" * 80)
    env_desc_path = os.path.join(os.path.dirname(__file__), "..", "env_desc.py")
    env_desc_path = os.path.abspath(env_desc_path)
    if not os.path.exists(env_desc_path):
        print(f"❌ 未找到env_desc.py: {env_desc_path}")
        return {}
    # 动态导入env_desc.py
    spec = importlib.util.spec_from_file_location("env_desc", env_desc_path)
    if spec is None or spec.loader is None:
        print(f"❌ 无法加载env_desc.py: {env_desc_path}")
        return {}
    env_desc = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(env_desc)
    results = {}
    # 检查数据文件
    if hasattr(env_desc, "data_lake_dict"):
        print(f"📁 检查 data_lake_dict 数据文件: {len(env_desc.data_lake_dict)} 个")
        for fname in env_desc.data_lake_dict:
            exists, status = check_file_exists(fname)
            results[f"data:{fname}"] = (exists, status)
            print(f"   {fname}: {status}")
    # 检查Python包、R包、CLI工具
    if hasattr(env_desc, "library_content_dict"):
        py_pkgs, r_pkgs, cli_tools = set(), set(), set()
        for k in env_desc.library_content_dict:
            desc = env_desc.library_content_dict[k]
            if "[Python Package]" in desc:
                py_pkgs.add(k)
            elif "[R Package]" in desc:
                r_pkgs.add(k)
            elif "[CLI Tool]" in desc:
                cli_tools.add(k)
        # 检查Python包
        print(f"🐍 检查Python包: {len(py_pkgs)} 个")
        for pkg in sorted(py_pkgs):
            exists, status = check_pip_package(pkg)
            results[f"py:{pkg}"] = (exists, status)
            print(f"   {pkg}: {status}")
        # 检查R包
        print(f"📦 检查R包: {len(r_pkgs)} 个")
        for pkg in sorted(r_pkgs):
            exists, status = check_r_package(pkg)
            results[f"r:{pkg}"] = (exists, status)
            print(f"   {pkg}: {status}")
        # 检查CLI工具
        print(f"🔧 检查CLI工具: {len(cli_tools)} 个")
        for tool in sorted(cli_tools):
            exists, status = check_cli_tool(tool, tool)
            results[f"cli:{tool}"] = (exists, status)
            print(f"   {tool}: {status}")
    return results

def main():
    """主函数"""
    print("🧬 Biomni环境检测工具 (check_env.py)")
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
    
    # 收集所有检查结果
    all_results = {}
    
    # 检查各种包和工具
    all_results["Environment包"] = check_environment_packages()
    all_results["Bio环境包"] = check_bio_env_packages()
    all_results["R包"] = check_r_packages()
    all_results["CLI工具"] = check_cli_tools()
    all_results["安装脚本"] = check_install_scripts()
    
    # 检查数据文件
    all_results["Data Lake文件"] = check_data_lake_files(data_lake_path)
    all_results["Benchmark文件"] = check_benchmark_files(benchmark_path)
    
    # 检查env_desc.py
    all_results["env_desc内容"] = check_env_desc()
    
    # 生成总结报告
    generate_summary_report(all_results)
    
    # 提供建议
    print(f"\n💡 建议:")
    print("1. 如果包缺失，请运行相应的安装脚本:")
    print("   - pip包: pip install -r requirements.txt")
    print("   - conda包: conda env update -f environment.yml")
    print("   - R包: Rscript install_r_packages.R")
    print("   - CLI工具: bash install_cli_tools.sh")
    print("2. 如果数据文件缺失，请重新运行Biomni初始化")
    print("3. 检查网络连接和磁盘空间")
    print("4. 如果问题持续，可以尝试重新创建conda环境")

if __name__ == "__main__":
    main() 