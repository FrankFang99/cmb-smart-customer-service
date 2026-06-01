"""快速评测 - 只跑20个样本验证真实Agent能力"""
import json
import time
from src.agent.customer_service_agent import CustomerServiceAgent
from src.config import settings

# 加载数据集
with open("data/evaluation_dataset_v3.0.json", "r", encoding="utf-8") as f:
    data = json.load(f)

# 取20个样本
samples = data["samples"][:20]

# 初始化Agent
agent = CustomerServiceAgent(settings)

print(f"测试 MiniMax Agent - {len(samples)} 个样本")
print("=" * 50)

correct = 0
results = []

for i, sample in enumerate(samples):
    q = sample["question"]
    expected = sample["intent"]
    
    start = time.time()
    result = agent.chat(q)
    latency = (time.time() - start) * 1000
    
    actual = result["intent"]
    is_match = expected == actual
    
    if is_match:
        correct += 1
    
    status = "[OK]" if is_match else "[FAIL]"
    print(f"{i+1:2d}. {status} expected={expected[:25]:25s} actual={actual[:25]:25s} ({latency:.0f}ms)")
    
    results.append({
        "id": sample["id"],
        "expected": expected,
        "actual": actual,
        "match": is_match,
        "latency_ms": latency
    })

print("=" * 50)
print(f"意图识别准确率: {correct}/{len(samples)} = {correct/len(samples)*100:.1f}%")
print(f"平均延迟: {sum(r['latency_ms'] for r in results)/len(results):.0f}ms")