#!/usr/bin/env python3
"""
快速测试CompoundPred.model_pretrained
"""

import sys
import os

# 添加项目路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def quick_test():
    """快速测试"""
    try:
        print("🔬 快速测试CompoundPred.model_pretrained...")
        
        # 导入
        from biomni.tool.pharmacology import CompoundPred
        print("✅ 导入成功")
        
        # 测试一个模型
        model = CompoundPred.model_pretrained(model="absorption_deepchem_model")
        print("✅ 模型加载成功")
        
        # 测试预测
        result = model.predict("CC(=O)OC1=CC=CC=C1C(=O)O")
        print(f"✅ 预测成功: {result}")
        
        return True
        
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        return False

if __name__ == "__main__":
    success = quick_test()
    print("🎉 测试完成!" if success else "❌ 测试失败!") 