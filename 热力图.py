import pandas as pd
import numpy as np
import seaborn as sns
import matplotlib.pyplot as plt

# 数据定义（来自论文表3）
locations = [
    "东门", "南门", "北门", "一食堂", "二食堂", "三食堂",
    "梅苑1栋", "菊苑1栋", "教学2楼", "教学4楼", "计算机学院",
    "工程中心", "网球场", "体育馆", "校医院"
]
time_windows = ["07:00", "09:00", "12:00", "14:00", "18:00", "21:00", "23:00"]

# 优化前后的供需缺口数据（示例数据）
gap_before = np.array([
    [28, 31, 23, 45, 7, 75, 28],  # 东门
    [38, 17, 24, 16, 86, 0, 26],  # 南门
    [15, 39, 48, 30, 54, 26, 10],  # 北门
    [16, 13, 33, 9, 0, 21, 53],  # 一食堂
    [63, 13, 103, 8, 41, 25, 88],  # 二食堂
    [16, 12, 13, 11, 35, 21, 31],  # 三食堂
    [30, 27, 29, 19, 18, 29, 89],  # 梅苑1栋
    [78, 21, 46, 40, 0, 37, 56],  # 菊苑1栋
    [13, 78, 22, 16, 15, 72, 15],  # 教学2楼
    [23, 56, 0, 84, 1, 22, 15],  # 教学4楼
    [3, 12, 7, 34, 22, 11, 6],  # 计算机学院
    [5, 28, 9, 24, 6, 51, 34],  # 工程中心
    [9, 15, 0, 10, 17, 0, 8],  # 网球场
    [7, 7, 3, 10, 34, 3, 1],  # 体育馆
    [2, 7, 1, 7, 2, 2, 8]  # 校医院
])

gap_after = gap_before * 0.3  # 假设优化后缺口减少70%

# 绘制热力图
def plot_gap_heatmap(data, title):
    df = pd.DataFrame(data, index=locations, columns=time_windows)
    plt.figure(figsize=(12,8))
    sns.heatmap(df, annot=True, fmt="d", cmap="coolwarm", center=0,
                linewidths=0.5, linecolor="grey")
    plt.title(title, fontsize=14)
    plt.xlabel("时间", fontsize=12)
    plt.ylabel("停车点", fontsize=12)
    plt.xticks(rotation=45)
    plt.tight_layout()
    plt.show()

# 绘制优化前后的对比
plot_gap_heatmap(gap_before, "优化前供需缺口热力图")
plot_gap_heatmap(gap_after, "优化后供需缺口热力图")