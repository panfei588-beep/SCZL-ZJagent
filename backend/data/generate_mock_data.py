"""
生成模拟质量检测数据
模拟3号精密磨床最近7天的内径检测数据，呈现合格率逐渐下降的趋势
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta


def generate_mock_data(output_path: str = "data/mock_data/quality_records.xlsx"):
    np.random.seed(42)

    start_date = datetime(2026, 5, 1)
    days = 7
    records_per_day = 100

    data = []
    product_prefix = "AX"
    product_counter = 2001

    for day in range(days):
        current_date = start_date + timedelta(days=day)
        degradation = day * 0.0015

        for i in range(records_per_day):
            product_no = f"{product_prefix}{product_counter}"
            product_counter += 1

            standard_value = 20.0
            tolerance = 0.005

            base_offset = degradation
            noise = np.random.normal(0, 0.002)
            measured = standard_value + base_offset + noise

            if day >= 3 and np.random.random() < 0.05 * (day - 2):
                measured += np.random.uniform(0.003, 0.008)

            is_pass = abs(measured - standard_value) <= tolerance
            result = "合格" if is_pass else "不合格"

            operators = ["张伟", "李四", "王强", "赵明"]
            if day >= 4:
                operator = np.random.choice(operators, p=[0.3, 0.4, 0.2, 0.1])
            else:
                operator = np.random.choice(operators, p=[0.3, 0.3, 0.25, 0.15])

            record = {
                "日期": current_date.strftime("%Y-%m-%d"),
                "产品编号": product_no,
                "检测项": "内径",
                "标准值": f"{standard_value}±{tolerance}",
                "实测值": round(measured, 4),
                "偏差": round(measured - standard_value, 4),
                "判定": result,
                "设备": "3号精密磨床",
                "操作员": operator,
                "班次": "A班" if i < 50 else "B班",
            }
            data.append(record)

    df = pd.DataFrame(data)

    import os
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    df.to_excel(output_path, index=False, engine="openpyxl")

    stats = df.groupby("日期")["判定"].apply(
        lambda x: round((x == "合格").sum() / len(x) * 100, 1)
    )
    print("每日合格率：")
    for date, rate in stats.items():
        print(f"  {date}: {rate}%")
    print(f"\n总记录数: {len(df)}")
    print(f"总合格率: {round((df['判定'] == '合格').sum() / len(df) * 100, 1)}%")
    print(f"文件已保存至: {output_path}")

    return output_path


if __name__ == "__main__":
    generate_mock_data()
