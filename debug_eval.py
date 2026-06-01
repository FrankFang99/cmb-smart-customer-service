import json
import sys
sys.path.insert(0, '.')

from src.agent.customer_service_agent import CustomerServiceAgent
from src.config import settings

# 加载数据集
with open("data/evaluation_dataset_v3.0.json", "r", encoding="utf-8") as f:
    data = json.load(f)

samples = data["samples"][:20]
agent = CustomerServiceAgent(settings)

print("测试意图识别（规则+LLM兜底）")
print("=" * 70)

for i, sample in enumerate(samples):
    q = sample["question"]
    expected = sample["intent"]
    
    result = agent.chat(q)
    actual = result["intent"]
    
    # 判断匹配类型
    if expected == actual:
        match = "OK"
    elif expected.startswith("sec_") and actual.startswith("sec_"):
        match = "SEC-MATCH"
    elif expected.startswith("cons_urg") and actual.startswith("cons_urg"):
        match = "URG-MATCH"
    else:
        match = "FAIL"
    
    print(f"{i+1:2d}. [{match}] exp={expected:25s} got={actual:25s}")
    print(f"       Q: {q[:50]}")

print("=" * 70)
print("Done")