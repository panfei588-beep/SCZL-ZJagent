import json
import argparse
import sys
import os

# 关键路径配置
sys.path.insert(0, "/home/ubuntu/digitalemployee")
sys.path.insert(0, "/home/ubuntu/digitalemployee/backend")

from knowledge_base.milvus_client import (
    build_diagnosis_kb,
    build_improvement_kb,
    write_to_diagnosis_kb,
    write_to_improvement_kb,
)

DATA_DIR = "/home/ubuntu/digitalemployee/backend/data/cases"
FILES = {
    "new":     os.path.join(DATA_DIR, "new_cases.json"),
    "quality": os.path.join(DATA_DIR, "quality_cases.json"),
}

def load_json(path):
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    print(f"📄 加载 {os.path.basename(path)}，共 {len(data)} 条")
    return data

def merge_cases(*file_keys):
    all_cases = []
    for key in file_keys:
        path = FILES.get(key)
        if path and os.path.exists(path):
            all_cases.extend(load_json(path))
        else:
            print(f"⚠️  文件不存在: {path}")
    return all_cases

def full_rebuild(cases):
    print("\n🔨 全量重建模式（清空旧数据）...")
    diag_cases = [c for c in cases if "root_cause" in c]
    if diag_cases:
        count = build_diagnosis_kb(diag_cases)
        print(f"✅ 诊断知识库写入: {count} 条")
    else:
        print("⚠️  无诊断案例（缺少 root_cause 字段）")
    impr_cases = [c for c in cases if "effect" in c]
    if impr_cases:
        count = build_improvement_kb(impr_cases)
        print(f"✅ 改善知识库写入: {count} 条")
    else:
        print("⚠️  无改善案例（缺少 effect 字段）")

def append_mode(cases):
    print("\n➕ 追加模式（保留旧数据）...")
    diag_ok = impr_ok = 0
    for case in cases:
        if "root_cause" in case:
            text = f"{case['title']} {case['problem']} {case['root_cause']}"
            meta = {k: case.get(k, "") for k in ["case_id","title","problem","root_cause","solution","category"]}
            if write_to_diagnosis_kb(text, meta):
                diag_ok += 1
        if "effect" in case:
            text = f"{case['title']} 解决方案:{case['solution']} 效果:{case['effect']}"
            meta = {k: case.get(k, "") for k in ["case_id","title","problem","solution","effect","category"]}
            if write_to_improvement_kb(text, meta):
                impr_ok += 1
    print(f"✅ 诊断知识库追加: {diag_ok} 条")
    print(f"✅ 改善知识库追加: {impr_ok} 条")

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=["full", "append"], default="full")
    parser.add_argument("--file", choices=["new", "quality", "all"], default="all")
    args = parser.parse_args()
    cases = merge_cases("new", "quality") if args.file == "all" else merge_cases(args.file)
    if not cases:
        print("❌ 没有可用数据，退出")
        return
    print(f"\n📦 共加载 {len(cases)} 条案例，模式: {args.mode}")
    full_rebuild(cases) if args.mode == "full" else append_mode(cases)
    print("\n🎉 知识库更新完成！")

if __name__ == "__main__":
    main()
