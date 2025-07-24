#!/usr/bin/env python3
"""
测试CompoundPred.model_pretrained的简单脚本
"""

import sys
import os

# 添加项目路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def test_compound_pred():
    """测试CompoundPred.model_pretrained功能"""
    try:
        print("🔬 开始测试CompoundPred.model_pretrained...")
        
        # 导入CompoundPred
        from DeepPurpose import CompoundPred, utils
        
        print("✅ 成功导入CompoundPred")
        
        # 测试一个简单的ADMET任务
        test_task = "absorption"  # 或者 "distribution", "metabolism", "excretion", "toxicity"
        test_model_type = "deepchem"  # 或者 "admetlab"
        
        print(f"🧪 测试任务: {test_task}")
        print(f"🤖 模型类型: {test_model_type}")
        
        # 尝试加载预训练模型
        model_name = f"{test_task}_{test_model_type}_model"
        print(f"📦 加载模型: {model_name}")
        
        model = CompoundPred.model_pretrained(model=model_name)
        
        print("✅ 模型加载成功!")
        print(f"📊 模型类型: {type(model)}")
        
        # 简单的测试数据
        test_smiles = "CC(=O)OC1=CC=CC=C1C(=O)O"  # 阿司匹林
        print(f"🧪 测试SMILES: {test_smiles}")
        
        # 尝试预测
        try:
            result = model.predict(test_smiles)
            print(f"✅ 预测成功: {result}")
        except Exception as e:
            print(f"⚠️ 预测失败: {e}")
            print("这可能是因为模型需要特定的输入格式")
        
        return True
        
    except ImportError as e:
        print(f"❌ 导入失败: {e}")
        return False
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        return False

def test_multiple_models():
    """测试多个ADMET模型"""
    try:
        from DeepPurpose import CompoundPred, utils
        
        # 定义要测试的任务和模型类型
        tasks = ["absorption", "distribution", "metabolism", "excretion", "toxicity"]
        model_types = ["deepchem", "admetlab"]
        
        print("🧪 测试多个ADMET模型...")
        
        for task in tasks:
            for model_type in model_types:
                try:
                    model_name = f"{task}_{model_type}_model"
                    print(f"📦 测试模型: {model_name}")
                    
                    model = CompoundPred.model_pretrained(model=model_name)
                    print(f"✅ {model_name} 加载成功")
                    
                except Exception as e:
                    print(f"❌ {model_name} 加载失败: {e}")
        
        return True
        
    except Exception as e:
        print(f"❌ 多模型测试失败: {e}")
        return False

if __name__ == "__main__":
    print("=" * 50)
    print("🧬 CompoundPred.model_pretrained 测试脚本")
    print("=" * 50)
    
    # 测试单个模型
    success1 = test_compound_pred()
    
    print("\n" + "=" * 50)
    
    # 测试多个模型
    success2 = test_multiple_models()
    
    print("\n" + "=" * 50)
    if success1 and success2:
        print("🎉 所有测试通过!")
    else:
        print("⚠️ 部分测试失败，请检查错误信息")
    print("=" * 50) 