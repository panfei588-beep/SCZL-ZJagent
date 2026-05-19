import pandas as pd
import sys
sys.path.insert(0, '/home/ubuntu/digitalemployee/backend')

from knowledge_base.milvus_client import (
    write_to_diagnosis_kb,
    write_to_improvement_kb
)

def import_valve_kb():
    # 从第4行读取列名，第5行起读取数据
    df = pd.read_excel(
        'data/cases/阀门电磁铁性能质量异常诊断知识库2026517.xlsx',
        header=4       # 第4行作为列名
    )
    df = df.fillna("")

    print(f"读取到 {len(df)} 条数据")
    print(f"列名：{df.columns.tolist()}")

    stats = {"diagnosis": 0, "improvement": 0, "skip": 0}

    for idx, row in df.iterrows():

        # 合并三个根因字段
        root_cause_parts = []
        for field in ['根本原因①', '根本原因②', '根本原因③']:
            val = str(row.get(field, "")).strip()
            if val and val != "nan":
                root_cause_parts.append(val)
        root_cause = "；".join(root_cause_parts)

        # 合并关键信息为检索文本
        problem    = str(row.get('异常现象/发验条件', "")).strip()
        title      = str(row.get('关键问题定性', "")).strip()
        keywords   = str(row.get('触发关键词', "")).strip()
        dimension  = str(row.get('检测维度', "")).strip()
        solution   = str(row.get('处置步骤', "")).strip()
        prevention = str(row.get('预防措施', "")).strip()
        severity   = str(row.get('严重等级', "")).strip()
        confirm    = str(row.get('快速确认方法', "")).strip()
        accept     = str(row.get('合格判定', "")).strip()
        case_id    = str(row.get('知识编号', f"VALVE-{idx:03d}")).strip()

        # 跳过空行
        if not problem and not title:
            stats["skip"] += 1
            continue

        # -------- 构建诊断库检索文本 --------
        diagnosis_text = (
            f"设备:阀门电磁铁 "
            f"维度:{dimension} "
            f"关键词:{keywords} "
            f"异常:{title} "
            f"现象:{problem} "
            f"根因:{root_cause} "
            f"确认方法:{confirm}"
        )

        diagnosis_metadata = {
            "case_id":      case_id,
            "title":        title,
            "problem":      problem,
            "root_cause":   root_cause,
            "solution":     solution,
            "category":     dimension,
            "equipment":    "阀门电磁铁",
            "severity":     severity,
            "keywords":     keywords,
            "confirm_method": confirm,
            "acceptance":   accept,
            "source_file":  "阀门电磁铁性能质量异常诊断知识库2026517.xlsx",
        }

        write_to_diagnosis_kb(diagnosis_text, diagnosis_metadata)
        stats["diagnosis"] += 1

        # -------- 有预防措施的同时写入改善库 --------
        if prevention.strip():
            improvement_text = (
                f"设备:阀门电磁铁 "
                f"维度:{dimension} "
                f"问题:{title} "
                f"现象:{problem} "
                f"处置:{solution} "
                f"预防:{prevention}"
            )
            improvement_metadata = {
                "case_id":   case_id,
                "title":     title,
                "problem":   problem,
                "solution":  solution,
                "effect":    prevention,
                "category":  dimension,
                "equipment": "阀门电磁铁",
                "source_file": "阀门电磁铁性能质量异常诊断知识库2026517.xlsx",
            }
            write_to_improvement_kb(improvement_text, improvement_metadata)
            stats["improvement"] += 1

    print(f"\n✅ 导入完成！")
    print(f"   诊断库写入：{stats['diagnosis']} 条")
    print(f"   改善库写入：{stats['improvement']} 条")
    print(f"   跳过空行：  {stats['skip']} 条")

if __name__ == "__main__":
    import_valve_kb()
