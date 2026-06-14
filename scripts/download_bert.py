"""
下载 bert-base-chinese (110MB) 到项目本地
==========================================
- 一次性下载, 后续训练/推理都走本地
- 不污染 mavis 全局缓存
- 走 hf-mirror.com 国内镜像 (直连 HF 超时)
"""
import os
import sys

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MODEL_DIR = os.path.join(PROJECT_ROOT, "models", "bert-base-chinese")

# 走国内镜像 (直连 HF 超时)
os.environ["HF_ENDPOINT"] = "https://hf-mirror.com"
# 防止 transformers 下载到 mavis 全局
os.environ["TRANSFORMERS_CACHE"] = os.path.join(PROJECT_ROOT, "models", ".hf_cache")
os.environ["HF_HOME"] = os.path.join(PROJECT_ROOT, "models", ".hf_home")
os.environ["HF_HUB_CACHE"] = os.path.join(PROJECT_ROOT, "models", ".hf_hub_cache")

from transformers import BertTokenizer, BertModel

def main():
    if os.path.exists(os.path.join(MODEL_DIR, "config.json")):
        print(f"[OK] 已存在: {MODEL_DIR}")
        return

    os.makedirs(MODEL_DIR, exist_ok=True)
    print(f"下载 bert-base-chinese 到 {MODEL_DIR} ...")
    print(f"镜像: {os.environ['HF_ENDPOINT']}")
    print("预计 110MB, 取决于网络 (通常 30-60s)")

    name = "bert-base-chinese"
    tokenizer = BertTokenizer.from_pretrained(name, cache_dir=os.environ["HF_HUB_CACHE"])
    tokenizer.save_pretrained(MODEL_DIR)
    print(f"  tokenizer saved")

    model = BertModel.from_pretrained(name, cache_dir=os.environ["HF_HUB_CACHE"])
    model.save_pretrained(MODEL_DIR)
    print(f"  model saved")

    print(f"\n[OK] 下载完成: {MODEL_DIR}")
    print(f"     文件: {os.listdir(MODEL_DIR)}")


if __name__ == "__main__":
    main()
