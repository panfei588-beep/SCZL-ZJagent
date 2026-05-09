"""
初始化 Milvus 知识库
将预置的质量案例数据导入向量数据库
"""

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from knowledge_base.milvus_client import build_knowledge_base


def init_knowledge_base():
    cases_file = os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "cases", "quality_cases.json"
    )

    with open(cases_file, "r", encoding="utf-8") as f:
        cases = json.load(f)

    print(f"加载了 {len(cases)} 条质量案例")
    count = build_knowledge_base(cases)
    print(f"成功导入 {count} 条案例到 Milvus 知识库")


if __name__ == "__main__":
    init_knowledge_base()
