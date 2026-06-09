# -*- coding: utf-8 -*-
"""
评测评分标准 v3.2 → docx 生成器（基于 v3.1 模板同款样式）
"""
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).parent))
from md_to_docx_v31 import Document, main as base_main

SRC = Path(r"D:\Learning\AI\面试\AI智能客服\docs\评测评分标准_v3.2.md")
DST = Path(r"D:\Learning\AI\面试\AI智能客服\docs\评测评分标准_v3.2.docx")

# 复用 v3.1 的所有渲染函数，但替换路径
import md_to_docx_v31
md_to_docx_v31.SRC = SRC
md_to_docx_v31.DST = DST

if __name__ == "__main__":
    base_main()
