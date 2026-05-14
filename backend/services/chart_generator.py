"""
图表生成服务
为 LangGraph data_agent 节点提供统计图表生成能力
"""

import os
import uuid
import logging
import numpy as np

# 中文字体配置
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm

# 尝试加载中文字体
def _get_cjk_font():
    """获取可用的中文字体"""
    # Windows 系统字体
    windows_fonts = ['Microsoft YaHei', 'SimHei', 'KaiTi', 'FangSong']
    for font_name in windows_fonts:
        try:
            font_prop = fm.FontProperties(family=font_name)
            fm.FontManager().addfont(fm.findfont(font_prop))
            return font_name
        except Exception:
            continue
    return 'sans-serif'

CJK_FONT = _get_cjk_font()
plt.rcParams['font.sans-serif'] = [CJK_FONT] + plt.rcParams['font.sans-serif']
plt.rcParams['axes.unicode_minus'] = False


def generate_trend_chart(
    dates: list,
    rates: list,
    title: str = "质量趋势分析",
    save_dir: str = "./charts",
    envelope: bool = True,
) -> str:
    """生成合格率趋势图（含包络线）

    Args:
        dates: 日期字符串列表
        rates: 合格率数值列表
        title: 图表标题
        save_dir: 保存目录
        envelope: 是否绘制包络线 (mean ± 3*std)

    Returns:
        保存的文件路径
    """
    if not dates or not rates:
        logging.warning("No data for trend chart")
        return ""

    os.makedirs(save_dir, exist_ok=True)
    fig, ax = plt.subplots(figsize=(10, 5))

    x = range(len(dates))
    ax.plot(x, rates, marker='o', linewidth=2, color='#1890ff', label='合格率')
    ax.fill_between(x, rates, alpha=0.15, color='#1890ff')

    # 包络线
    if envelope and len(rates) >= 5:
        mean_val = np.mean(rates)
        std_val = np.std(rates)
        # 样本数 < 20 时使用 2*std
        multiplier = 2.0 if len(rates) < 20 else 3.0
        upper = [mean_val + multiplier * std_val] * len(rates)
        lower = [mean_val - multiplier * std_val] * len(rates)
        ax.axhline(y=mean_val, color='orange', linestyle='--', linewidth=1, label=f'均值={mean_val:.2%}')
        ax.fill_between(x, lower, upper, alpha=0.1, color='orange', label=f'包络线(mean±{multiplier}σ)')

    ax.set_xticks(list(x))
    ax.set_xticklabels([str(d) for d in dates], rotation=45, ha='right')
    ax.set_title(title, fontsize=14, fontweight='bold')
    ax.set_xlabel('日期', fontsize=12)
    ax.set_ylabel('合格率', fontsize=12)
    ax.set_ylim(0, 1.05)
    ax.legend(fontsize=10)
    ax.grid(True, alpha=0.3)

    fig.tight_layout()
    filename = f"trend_{uuid.uuid4().hex[:8]}.png"
    path = os.path.join(save_dir, filename)
    fig.savefig(path, dpi=120)
    plt.close(fig)
    logging.info(f"Trend chart saved: {path}")
    return path


def generate_distribution_chart(
    values: list,
    title: str = "数据分布分析",
    xlabel: str = "测量值",
    save_dir: str = "./charts",
) -> str:
    """生成数据分布直方图

    Args:
        values: 数值列表
        title: 图表标题
        xlabel: X 轴标签
        save_dir: 保存目录

    Returns:
        保存的文件路径
    """
    if not values:
        logging.warning("No data for distribution chart")
        return ""

    os.makedirs(save_dir, exist_ok=True)
    fig, ax = plt.subplots(figsize=(10, 5))

    ax.hist(values, bins=20, color='#52c41a', edgecolor='white', alpha=0.8)
    mean_val = np.mean(values)
    std_val = np.std(values)
    ax.axvline(x=mean_val, color='red', linestyle='--', linewidth=1.5, label=f'均值={mean_val:.2f}')
    ax.axvline(x=mean_val + 3 * std_val, color='orange', linestyle=':', linewidth=1, label=f'+3σ={mean_val + 3 * std_val:.2f}')
    ax.axvline(x=mean_val - 3 * std_val, color='orange', linestyle=':', linewidth=1, label=f'-3σ={mean_val - 3 * std_val:.2f}')

    ax.set_title(title, fontsize=14, fontweight='bold')
    ax.set_xlabel(xlabel, fontsize=12)
    ax.set_ylabel('频次', fontsize=12)
    ax.legend(fontsize=10)
    ax.grid(True, alpha=0.3, axis='y')

    fig.tight_layout()
    filename = f"distribution_{uuid.uuid4().hex[:8]}.png"
    path = os.path.join(save_dir, filename)
    fig.savefig(path, dpi=120)
    plt.close(fig)
    logging.info(f"Distribution chart saved: {path}")
    return path
