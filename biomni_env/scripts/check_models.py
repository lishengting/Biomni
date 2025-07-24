#!/usr/bin/env python3
"""
查看DeepPurpose可用的预训练模型
"""

import sys
import os

# 添加项目路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def check_available_models():
    """查看可用的预训练模型"""
    try:
        print("🔍 查看DeepPurpose可用的预训练模型...")
        
        # 导入DeepPurpose
        from DeepPurpose import CompoundPred
        
        print("✅ 成功导入DeepPurpose.CompoundPred")
        
        # 查看URLs属性，这应该包含可用的模型
        print("📋 可用的预训练模型:")
        if hasattr(CompoundPred, 'URLs'):
            urls = CompoundPred.URLs
            print(f"URLs类型: {type(urls)}")
            if isinstance(urls, dict):
                for model_name in urls.keys():
                    print(f"  - {model_name}")
            else:
                print(f"URLs内容: {urls}")
        else:
            print("❌ 没有找到URLs属性")
            
        # 查看name2filename属性
        print("\n📋 name2filename映射:")
        if hasattr(CompoundPred, 'name2filename'):
            name2filename = CompoundPred.name2filename
            print(f"name2filename类型: {type(name2filename)}")
            if isinstance(name2filename, dict):
                for model_name in name2filename.keys():
                    print(f"  - {model_name}")
            else:
                print(f"name2filename内容: {name2filename}")
        else:
            print("❌ 没有找到name2filename属性")
            
    except ImportError as e:
        print(f"❌ 导入失败: {e}")
    except Exception as e:
        print(f"❌ 检查失败: {e}")

if __name__ == "__main__":
    check_available_models() 