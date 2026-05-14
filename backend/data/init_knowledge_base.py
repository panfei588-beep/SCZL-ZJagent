"""
初始化双知识库
将预置的质量案例数据拆分为诊断知识库和改善知识库
"""

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from knowledge_base.milvus_client import build_diagnosis_kb, build_improvement_kb


def init_knowledge_base():
    cases_file = os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "cases", "quality_cases.json"
    )

    with open(cases_file, "r", encoding="utf-8") as f:
        cases = json.load(f)

    print(f"加载了 {len(cases)} 条质量案例")

    d_count = build_diagnosis_kb(cases)
    print(f"诊断知识库(diagnosis_cases): 导入 {d_count} 条案例")

    i_count = build_improvement_kb(cases)
    print(f"改善知识库(improvement_cases): 导入 {i_count} 条案例")

    print(f"知识库初始化完成，共 {d_count + i_count} 条文档")


if __name__ == "__main__":
    init_knowledge_base()
