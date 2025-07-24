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
        
        # 尝试获取可用模型列表
        try:
            # 查看CompoundPred的属性和方法
            print("📋 CompoundPred的属性和方法:")
            for attr in dir(CompoundPred):
                if not attr.startswith('_'):
                    print(f"  - {attr}")
            
            # 尝试一些常见的模型名称
            common_models = [
                "DAVIS",
                "KIBA", 
                "BindingDB",
                "DrugBank",
                "ChEMBL",
                "Tox21",
                "SIDER",
                "ClinTox",
                "BBBP",
                "HIV"
            ]
            
            print("\n🧪 测试常见模型名称:")
            for model_name in common_models:
                try:
                    print(f"  测试: {model_name}")
                    model = CompoundPred.model_pretrained(model=model_name)
                    print(f"  ✅ {model_name} 可用!")
                except Exception as e:
                    print(f"  ❌ {model_name}: {str(e)[:50]}...")
                    
        except Exception as e:
            print(f"❌ 获取模型列表失败: {e}")
            
    except ImportError as e:
        print(f"❌ 导入失败: {e}")
    except Exception as e:
        print(f"❌ 检查失败: {e}")

if __name__ == "__main__":
    check_available_models() 