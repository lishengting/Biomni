#!/usr/bin/env python3
"""
用wget完全模拟requests.get的下载函数，并添加批量下载所有DeepPurpose模型的功能
"""

import subprocess
import os
import sys
import time
import zipfile
from typing import Optional

# 从down.py复制的三个字典
name2ids = {
	'cnn_cnn_bindingdb': 4159715,
	'daylight_aac_bindingdb': 4159667,
	'daylight_aac_davis': 4159679,
	'daylight_aac_kiba': 4159649,
	'cnn_cnn_davis': 4159673,
	'morgan_aac_bindingdb': 4159694,
	'morgan_aac_davis': 4159706,
	'morgan_aac_kiba': 4159690,
	'morgan_cnn_bindingdb': 4159708,
	'morgan_cnn_davis': 4159705,
	'morgan_cnn_kiba': 4159676,
	'mpnn_aac_davis': 4159661,
	'mpnn_cnn_bindingdb': 4204178,
	'mpnn_cnn_davis': 4159677,
	'mpnn_cnn_kiba': 4159696,
	'transformer_cnn_bindingdb': 4159655,
	'pretrained_models': 4159682,
	'models_configs': 4159714,
	'aqsoldb_cnn_model': 4159704,
	'aqsoldb_morgan_model': 4159688,
	'aqsoldb_mpnn_model': 4159691,
	'bbb_molnet_cnn_model': 4159651,
	'bbb_molnet_mpnn_model': 4159709,
	'bbb_molnet_morgan_model': 4159703,
	'bioavailability_cnn_model': 4159663,
	'bioavailability_mpnn_model': 4159654,
	'bioavailability_morgan_model': 4159717,
	'cyp1a2_cnn_model': 4159675,
	'cyp1a2_mpnn_model': 4159671,
	'cyp1a2_morgan_model': 4159707,
	'cyp2c19_cnn_model': 4159669,
	'cyp2c19_mpnn_model': 4159687,
	'cyp2c19_morgan_model': 4159710,
	'cyp2c9_cnn_model': 4159702,
	'cyp2c9_mpnn_model': 4159686,
	'cyp2c9_morgan_model': 4159659,
	'cyp2d6_cnn_model': 4159697,
	'cyp2d6_mpnn_model': 4159674,
	'cyp2d6_morgan_model': 4159660,
	'cyp3a4_cnn_model': 4159670,
	'cyp3a4_mpnn_model': 4159678,
	'cyp3a4_morgan_model': 4159700,
	'caco2_cnn_model': 4159701,
	'caco2_mpnn_model': 4159657,
	'caco2_morgan_model': 4159662,
	'clearance_edrug3d_cnn_model': 4159699,
	'clearance_edrug3d_mpnn_model': 4159665,
	'clearance_edrug3d_morgan_model': 4159656,
	'clintox_cnn_model': 4159658,
	'clintox_mpnn_model': 4159668,
	'clintox_morgan_model': 4159713,
	'hia_cnn_model': 4159680,
	'hia_mpnn_model': 4159653,
	'hia_morgan_model': 4159711,
	'half_life_edrug3d_cnn_model': 4159716,
	'half_life_edrug3d_mpnn_model': 4159692,
	'half_life_edrug3d_morgan_model': 4159689,
	'lipo_az_cnn_model': 4159693,
	'lipo_az_mpnn_model': 4159684,
	'lipo_az_morgan_model': 4159664,
	'ppbr_cnn_model': 4159666,
	'ppbr_mpnn_model': 4159647,
	'ppbr_morgan_model': 4159685,
	'pgp_inhibitor_cnn_model': 4159646,
	'pgp_inhibitor_mpnn_model': 4159683,
	'pgp_inhibitor_morgan_model': 4159712,
	'cnn_cnn_bindingdb_ic50': 4203606,
	'daylight_aac_bindingdb_ic50': 4203604,
	'morgan_aac_bindingdb_ic50': 4203602,
	'morgan_cnn_bindingdb_ic50': 4203603,
	'mpnn_cnn_bindingdb_ic50': 4203605
 }

name2zipfilename = {
	'cnn_cnn_bindingdb': 'model_cnn_cnn_bindingdb',
	'daylight_aac_bindingdb': 'model_daylight_aac_bindingdb',
	'daylight_aac_davis': 'model_daylight_aac_davis',
	'daylight_aac_kiba': 'model_daylight_aac_kiba',
	'cnn_cnn_davis': 'model_cnn_cnn_davis',
	'morgan_aac_bindingdb': 'model_morgan_aac_bindingdb',
	'morgan_aac_davis': 'model_morgan_aac_davis',
	'morgan_aac_kiba': 'model_morgan_aac_kiba',
	'morgan_cnn_bindingdb': 'model_morgan_cnn_bindingdb',
	'morgan_cnn_davis': 'model_morgan_cnn_davis',
	'morgan_cnn_kiba': 'model_morgan_aac_kiba',
	'mpnn_aac_davis': ' model_mpnn_aac_davis',
	'mpnn_cnn_bindingdb': 'model_mpnn_cnn_bindingdb',
	'mpnn_cnn_davis': 'model_mpnn_cnn_davis',
	'mpnn_cnn_kiba': 'model_mpnn_cnn_kiba',
	'transformer_cnn_bindingdb': 'model_transformer_cnn_bindingdb',
	'pretrained_models': 'pretrained_models',
	'models_configs': 'models_configs',
	'aqsoldb_cnn_model': 'AqSolDB_CNN_model',
	'aqsoldb_mpnn_model': 'AqSolDB_MPNN_model',
	'aqsoldb_morgan_model': 'AqSolDB_Morgan_model',
	'bbb_molnet_cnn_model': 'BBB_MolNet_CNN_model',
	'bbb_molnet_mpnn_model': 'BBB_MolNet_MPNN_model',
	'bbb_molnet_morgan_model': 'BBB_MolNet_Morgan_model',
	'bioavailability_cnn_model': 'Bioavailability_CNN_model',
	'bioavailability_mpnn_model': 'Bioavailability_MPNN_model',
	'bioavailability_morgan_model': 'Bioavailability_Morgan_model',
	'cyp1a2_cnn_model': 'CYP1A2_CNN_model',
	'cyp1a2_mpnn_model': 'CYP1A2_MPNN_model',
	'cyp1a2_morgan_model': 'CYP1A2_Morgan_model',
	'cyp2c19_cnn_model': 'CYP2C19_CNN_model',
	'cyp2c19_mpnn_model': 'CYP2C19_MPNN_model',
	'cyp2c19_morgan_model': 'CYP2C19_Morgan_model',
	'cyp2c9_cnn_model': 'CYP2C9_CNN_model',
	'cyp2c9_mpnn_model': 'CYP2C9_MPNN_model',
	'cyp2c9_morgan_model': 'CYP2C9_Morgan_model',
	'cyp2d6_cnn_model': 'CYP2D6_CNN_model',
	'cyp2d6_mpnn_model': 'CYP2D6_MPNN_model',
	'cyp2d6_morgan_model': 'CYP2D6_Morgan_model',
	'cyp3a4_cnn_model': 'CYP3A4_CNN_model',
	'cyp3a4_mpnn_model': 'CYP3A4_MPNN_model',
	'cyp3a4_morgan_model': 'CYP3A4_Morgan_model',
	'caco2_cnn_model': 'Caco2_CNN_model',
	'caco2_mpnn_model': 'Caco2_MPNN_model',
	'caco2_morgan_model': 'Caco2_Morgan_model',
	'clearance_edrug3d_cnn_model': 'Clearance_eDrug3D_CNN_model',
	'clearance_edrug3d_mpnn_model': 'Clearance_eDrug3D_MPNN_model',
	'clearance_edrug3d_morgan_model': 'Clearance_eDrug3D_Morgan_model',
	'clintox_cnn_model': 'ClinTox_CNN_model',
	'clintox_mpnn_model': 'ClinTox_MPNN_model',
	'clintox_morgan_model': 'ClinTox_Morgan_model',
	'hia_cnn_model': 'HIA_CNN_model',
	'hia_mpnn_model': 'HIA_MPNN_model',
	'hia_morgan_model': 'HIA_Morgan_model',
	'half_life_edrug3d_cnn_model': 'Half_life_eDrug3D_CNN_model',
	'half_life_edrug3d_mpnn_model': 'Half_life_eDrug3D_MPNN_model',
	'half_life_edrug3d_morgan_model': 'Half_life_eDrug3D_Morgan_model',
	'lipo_az_cnn_model': 'Lipo_AZ_CNN_model',
	'lipo_az_mpnn_model': 'Lipo_AZ_MPNN_model',
	'lipo_az_morgan_model': 'Lipo_AZ_Morgan_model',
	'ppbr_cnn_model': 'PPBR_CNN_model',
	'ppbr_mpnn_model': 'PPBR_MPNN_model',
	'ppbr_morgan_model': 'PPBR_Morgan_model',
	'pgp_inhibitor_cnn_model': 'Pgp_inhibitor_CNN_model',
	'pgp_inhibitor_mpnn_model': 'Pgp_inhibitor_MPNN_model',
	'pgp_inhibitor_morgan_model': 'Pgp_inhibitor_Morgan_model',
	'cnn_cnn_bindingdb_ic50': 'cnn_cnn_bindingdb_ic50',
	'daylight_aac_bindingdb_ic50': 'daylight_aac_bindingdb_ic50',
	'morgan_aac_bindingdb_ic50': 'morgan_aac_bindingdb_ic50',
	'morgan_cnn_bindingdb_ic50': 'morgan_cnn_bindingdb_ic50',
	'mpnn_cnn_bindingdb_ic50': 'mpnn_cnn_bindingdb_ic50'
}

name2filename = {
	'cnn_cnn_bindingdb': 'model_cnn_cnn_bindingdb',
	'daylight_aac_bindingdb': 'model_daylight_aac_bindingdb',
	'daylight_aac_davis': 'model_daylight_aac_davis',
	'daylight_aac_kiba': 'model_daylight_aac_kiba',
	'cnn_cnn_davis': 'model_DeepDTA_DAVIS',
	'morgan_aac_bindingdb': 'model_morgan_aac_bindingdb',
	'morgan_aac_davis': 'model_morgan_aac_davis',
	'morgan_aac_kiba': 'model_morgan_aac_kiba',
	'morgan_cnn_bindingdb': 'model_morgan_cnn_bindingdb',
	'morgan_cnn_davis': 'model_morgan_cnn_davis',
	'morgan_cnn_kiba': 'model_morgan_aac_kiba',
	'mpnn_aac_davis': ' model_mpnn_aac_davis',
	'mpnn_cnn_bindingdb': 'model_MPNN_CNN',
	'mpnn_cnn_davis': 'model_mpnn_cnn_davis',
	'mpnn_cnn_kiba': 'model_mpnn_cnn_kiba',
	'transformer_cnn_bindingdb': 'model_transformer_cnn_bindingdb',
	'pretrained_models': 'DeepPurpose_BindingDB',
	'models_configs': 'models_configs',
	'aqsoldb_cnn_model': 'AqSolDB_CNN_model',
	'aqsoldb_mpnn_model': 'AqSolDB_MPNN_model',
	'aqsoldb_morgan_model': 'AqSolDB_Morgan_model',
	'bbb_molnet_cnn_model': 'BBB_MolNet_CNN_model',
	'bbb_molnet_mpnn_model': 'BBB_MolNet_MPNN_model',
	'bbb_molnet_morgan_model': 'BBB_MolNet_Morgan_model',
	'bioavailability_cnn_model': 'Bioavailability_CNN_model',
	'bioavailability_mpnn_model': 'Bioavailability_MPNN_model',
	'bioavailability_morgan_model': 'Bioavailability_Morgan_model',
	'cyp1a2_cnn_model': 'CYP1A2_CNN_model',
	'cyp1a2_mpnn_model': 'CYP1A2_MPNN_model',
	'cyp1a2_morgan_model': 'CYP1A2_Morgan_model',
	'cyp2c19_cnn_model': 'CYP2C19_CNN_model',
	'cyp2c19_mpnn_model': 'CYP2C19_MPNN_model',
	'cyp2c19_morgan_model': 'CYP2C19_Morgan_model',
	'cyp2c9_cnn_model': 'CYP2C9_CNN_model',
	'cyp2c9_mpnn_model': 'CYP2C9_MPNN_model',
	'cyp2c9_morgan_model': 'CYP2C9_Morgan_model',
	'cyp2d6_cnn_model': 'CYP2D6_CNN_model',
	'cyp2d6_mpnn_model': 'CYP2D6_MPNN_model',
	'cyp2d6_morgan_model': 'CYP2D6_Morgan_model',
	'cyp3a4_cnn_model': 'CYP3A4_CNN_model',
	'cyp3a4_mpnn_model': 'CYP3A4_MPNN_model',
	'cyp3a4_morgan_model': 'CYP3A4_Morgan_model',
	'caco2_cnn_model': 'Caco2_CNN_model',
	'caco2_mpnn_model': 'Caco2_MPNN_model',
	'caco2_morgan_model': 'Caco2_Morgan_model',
	'clearance_edrug3d_cnn_model': 'Clearance_eDrug3D_CNN_model',
	'clearance_edrug3d_mpnn_model': 'Clearance_eDrug3D_MPNN_model',
	'clearance_edrug3d_morgan_model': 'Clearance_eDrug3D_Morgan_model',
	'clintox_cnn_model': 'ClinTox_CNN_model',
	'clintox_mpnn_model': 'ClinTox_MPNN_model',
	'clintox_morgan_model': 'ClinTox_Morgan_model',
	'hia_cnn_model': 'HIA_CNN_model',
	'hia_mpnn_model': 'HIA_MPNN_model',
	'hia_morgan_model': 'HIA_Morgan_model',
	'half_life_edrug3d_cnn_model': 'Half_life_eDrug3D_CNN_model',
	'half_life_edrug3d_mpnn_model': 'Half_life_eDrug3D_MPNN_model',
	'half_life_edrug3d_morgan_model': 'Half_life_eDrug3D_Morgan_model',
	'lipo_az_cnn_model': 'Lipo_AZ_CNN_model',
	'lipo_az_mpnn_model': 'Lipo_AZ_MPNN_model',
	'lipo_az_morgan_model': 'Lipo_AZ_Morgan_model',
	'ppbr_cnn_model': 'PPBR_CNN_model',
	'ppbr_mpnn_model': 'PPBR_MPNN_model',
	'ppbr_morgan_model': 'PPBR_Morgan_model',
	'pgp_inhibitor_cnn_model': 'Pgp_inhibitor_CNN_model',
	'pgp_inhibitor_mpnn_model': 'Pgp_inhibitor_MPNN_model',
	'pgp_inhibitor_morgan_model': 'Pgp_inhibitor_Morgan_model',
	'cnn_cnn_bindingdb_ic50': 'cnn_cnn_bindingdb_ic50',
	'daylight_aac_bindingdb_ic50': 'daylight_aac_bindingdb_ic50',
	'morgan_aac_bindingdb_ic50': 'morgan_aac_bindingdb_ic50',
	'morgan_cnn_bindingdb_ic50': 'morgan_cnn_bindingdb_ic50',
	'mpnn_cnn_bindingdb_ic50': 'mpnn_cnn_bindingdb_ic50'
}

def check_file_integrity(file_path: str) -> bool:
    """
    检查文件完整性，判断是否为有效的zip文件
    
    Args:
        file_path: 文件路径
    
    Returns:
        bool: 文件是否完整有效
    """
    if not os.path.exists(file_path):
        return False
    
    try:
        with zipfile.ZipFile(file_path, 'r') as zip_file:
            # 测试zip文件完整性
            zip_file.testzip()
            return True
    except (zipfile.BadZipFile, Exception):
        return False

def download_url_wget(url: str, save_path: str, proxy_url: Optional[str] = None, chunk_size: int = 128) -> bool:
    """
    用wget完全模拟requests.get的下载行为
    
    Args:
        url: 下载URL
        save_path: 保存路径
        proxy_url: 代理URL (可选)
        chunk_size: 块大小 (wget不使用，但保持接口一致)
    
    Returns:
        bool: 下载是否成功
    """
    
    # 构建wget命令
    wget_cmd = ["wget"]
    
    # 设置User-Agent，模拟浏览器请求
    user_agent = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    wget_cmd.extend(["--user-agent", user_agent])
    
    # 添加请求头，模拟requests.get
    headers = [
        ("Accept", "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8"),
        ("Accept-Language", "en-US,en;q=0.5"),
        ("Accept-Encoding", "gzip, deflate"),
        ("Connection", "keep-alive"),
        ("Upgrade-Insecure-Requests", "1")
    ]
    
    for header_name, header_value in headers:
        wget_cmd.extend(["--header", f"{header_name}: {header_value}"])
    
    # 添加代理支持
    if proxy_url:
        wget_cmd.extend(["--proxy=on"])
        # 设置代理环境变量
        env = os.environ.copy()
        env.update({
            'http_proxy': proxy_url,
            'https_proxy': proxy_url,
            'HTTP_PROXY': proxy_url,
            'HTTPS_PROXY': proxy_url
        })
    else:
        env = os.environ.copy()
    
    # 添加其他选项，模拟requests.get的行为，并显示进度
    wget_cmd.extend([
        "--no-check-certificate",  # 忽略SSL证书验证
        "--timeout=30",           # 设置超时
        "--tries=3",              # 重试次数
        "--retry-connrefused",    # 连接被拒绝时重试
        "--continue",             # 支持断点续传
        "--output-document", save_path,  # 指定输出文件
        "--progress=bar",         # 显示进度条
        "--show-progress",        # 显示详细进度信息
        #"--quiet",                # 静默模式
        url
    ])
    
    try:
        print(f"执行wget命令: {' '.join(wget_cmd)}")
        
        # 执行wget命令，实时显示输出
        result = subprocess.run(
            wget_cmd,
            env=env,
            text=True,
            timeout=60*60*4  # 4小时超时
            #capture_output=True,
        )
        
        if result.returncode == 0:
            print(f"✅ 下载成功: {save_path}")
            if os.path.exists(save_path):
                size = os.path.getsize(save_path)
                print(f"文件大小: {size:,} bytes")
            return True
        else:
            print(f"❌ 下载失败 (返回码: {result.returncode})")
            #print(f"错误输出: {result.stderr}")
            return False
            
    except subprocess.TimeoutExpired:
        print("❌ 下载超时")
        return False
    except Exception as e:
        print(f"❌ 下载异常: {e}")
        return False

def download_url_stream_wget(url: str, save_path: str, proxy_url: Optional[str] = None) -> bool:
    """
    模拟requests.get的stream=True行为，用wget实现
    
    Args:
        url: 下载URL
        save_path: 保存路径
        proxy_url: 代理URL (可选)
    
    Returns:
        bool: 下载是否成功
    """
    return download_url_wget(url, save_path, proxy_url)

def download_single_model(model_name: str, save_dir: str = './save_folder', proxy_url: str = '127.0.0.1:7890', max_retries: int = 15) -> bool:
    """
    下载单个模型，包含重试机制和文件完整性检查
    
    Args:
        model_name: 模型名称
        save_dir: 保存目录
        proxy_url: 代理URL
        max_retries: 最大重试次数
    
    Returns:
        bool: 下载是否成功
    """
    print(f"\n{'='*60}")
    print(f"开始下载模型: {model_name}")
    print(f"{'='*60}")
    
    # 检查模型名称是否有效
    if model_name.lower() not in name2ids:
        print(f"❌ 无效的模型名称: {model_name}")
        return False
    
    # 构建下载URL和保存路径
    server_path = 'https://dataverse.harvard.edu/api/access/datafile/'
    url = server_path + str(name2ids[model_name.lower()])
    zip_filename = name2zipfilename[model_name.lower()] + '.zip'
    save_path = os.path.join(save_dir, zip_filename)
    
    print(f"下载URL: {url}")
    print(f"保存路径: {save_path}")
    print(f"代理设置: {proxy_url}")
    
    # 检查文件是否已存在且完整
    if check_file_integrity(save_path):
        print(f"✅ 文件已存在且完整: {save_path}")
        return True
    
    # 创建保存目录
    os.makedirs(save_dir, exist_ok=True)
    
    # 重试下载
    for attempt in range(max_retries):
        print(f"\n尝试下载 (第 {attempt + 1}/{max_retries} 次):")
        
        success = download_url_wget(url, save_path, proxy_url)
        
        if success:
            # 验证下载的文件完整性
            if check_file_integrity(save_path):
                print(f"✅ 模型 {model_name} 下载成功并验证完整!")
                return True
            else:
                print(f"❌ 下载的文件不完整，将重试...")
                # 删除损坏的文件
                if os.path.exists(save_path):
                    os.remove(save_path)
        else:
            print(f"❌ 下载失败，将重试...")
            # 删除可能损坏的文件
            if os.path.exists(save_path):
                os.remove(save_path)
        
        # 重试前等待
        if attempt < max_retries - 1:
            wait_time = (attempt + 1) * 5  # 递增等待时间
            print(f"等待 {wait_time} 秒后重试...")
            time.sleep(wait_time)
    
    print(f"❌ 模型 {model_name} 下载失败，已达到最大重试次数")
    return False

def download_all_models(save_dir: str = './save_folder', proxy_url: str = '127.0.0.1:7890', max_retries: int = 15) -> dict:
    """
    下载所有模型
    
    Args:
        save_dir: 保存目录
        proxy_url: 代理URL
        max_retries: 最大重试次数
    
    Returns:
        dict: 下载结果统计
    """
    print(f"开始批量下载所有DeepPurpose模型...")
    print(f"保存目录: {save_dir}")
    print(f"代理设置: {proxy_url}")
    print(f"最大重试次数: {max_retries}")
    
    # 创建保存目录
    os.makedirs(save_dir, exist_ok=True)
    
    results = {
        'success': [],
        'failed': [],
        'skipped': []
    }
    
    total_models = len(name2ids)
    print(f"\n总共需要下载 {total_models} 个模型")
    
    for i, model_name in enumerate(name2ids.keys(), 1):
        print(f"\n进度: {i}/{total_models}")
        
        # 检查文件是否已存在且完整
        zip_filename = name2zipfilename[model_name] + '.zip'
        save_path = os.path.join(save_dir, zip_filename)
        
        if check_file_integrity(save_path):
            print(f"⏭️  跳过已存在的完整文件: {model_name}")
            results['skipped'].append(model_name)
            continue
        
        # 下载模型
        if download_single_model(model_name, save_dir, proxy_url, max_retries):
            results['success'].append(model_name)
        else:
            results['failed'].append(model_name)
    
    # 打印统计结果
    print(f"\n{'='*60}")
    print(f"下载完成统计:")
    print(f"成功: {len(results['success'])} 个")
    print(f"失败: {len(results['failed'])} 个")
    print(f"跳过: {len(results['skipped'])} 个")
    print(f"{'='*60}")
    
    if results['success']:
        print(f"✅ 成功下载的模型:")
        for model in results['success']:
            print(f"  - {model}")
    
    if results['failed']:
        print(f"❌ 下载失败的模型:")
        for model in results['failed']:
            print(f"  - {model}")
    
    if results['skipped']:
        print(f"⏭️  跳过的模型:")
        for model in results['skipped']:
            print(f"  - {model}")
    
    return results

def generate_download_info() -> list:
    """
    生成所有模型的下载信息
    
    Returns:
        list: 包含(URL, save_path)元组的列表
    """
    server_path = 'https://dataverse.harvard.edu/api/access/datafile/'
    download_info = []
    
    for model_name, model_id in name2ids.items():
        url = server_path + str(model_id)
        save_path = name2zipfilename[model_name] + '.zip'
        download_info.append((url, save_path))
    
    return download_info

# 使用示例
if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("用法:")
        print("  1. 下载单个模型: python wget_requests_equivalent.py single <model_name> [save_dir] [proxy_url]")
        print("  2. 下载所有模型: python wget_requests_equivalent.py all [save_dir] [proxy_url]")
        print("  3. 显示下载信息: python wget_requests_equivalent.py info")
        sys.exit(1)
    
    command = sys.argv[1]
    
    if command == "single":
        if len(sys.argv) < 3:
            print("错误: 需要指定模型名称")
            sys.exit(1)
        
        model_name = sys.argv[2]
        save_dir = sys.argv[3] if len(sys.argv) > 3 else './save_folder'
        proxy_url = sys.argv[4] if len(sys.argv) > 4 else '127.0.0.1:7890'
        
        success = download_single_model(model_name, save_dir, proxy_url)
        if success:
            print("下载完成！")
        else:
            print("下载失败！")
            sys.exit(1)
    
    elif command == "all":
        save_dir = sys.argv[2] if len(sys.argv) > 2 else './save_folder'
        proxy_url = sys.argv[3] if len(sys.argv) > 3 else '127.0.0.1:7890'
        
        results = download_all_models(save_dir, proxy_url)
        if results['failed']:
            sys.exit(1)
    
    elif command == "info":
        download_info = generate_download_info()
        print("所有模型的下载信息:")
        for i, (url, save_path) in enumerate(download_info, 1):
            print(f"{i:2d}. URL: {url}")
            print(f"    Save: {save_path}")
            print()
    
    else:
        print(f"错误: 未知命令 '{command}'")
        sys.exit(1) 