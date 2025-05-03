import matplotlib.pyplot as plt
import numpy as np

# ================== 数据准备 ==================
# 修复后的调度记录
schedules = [
    ('运维处', '菊苑1栋', 20), ('运维处', '菊苑1栋', 20), ('运维处', '菊苑1栋', 15),
    ('菊苑1栋', '梅苑1栋', 15), ('梅苑1栋', '计算机学院', 6), ('计算机学院', '东门', 7),
    ('东门', '一食堂', 5), ('一食堂', '教学2楼', 9), ('教学2楼', '工程中心', 8),
    ('教学2楼', '工程中心', 9), ('运维处', '南门', 20), ('运维处', '二食堂', 20),
    ('运维处', '二食堂', 20), ('二食堂', '教学4楼', 20), ('教学4楼', '三食堂', 5),
    ('运维处', '二食堂', 7), ('二食堂', '教学2楼', 12), ('教学2楼', '工程中心', 15),
    ('工程中心', '北门', 7), ('运维处', '网球场', 3), ('运维处', '体育馆', 4), ('体育馆', '北门', 3)
]

# 预测数据及地理分组
location_groups = {
    "生活区": ["东门", "南门", "北门", "一食堂", "二食堂", "三食堂", "梅苑1栋", "菊苑1栋", "校医院"],
    "教学区": ["教学2楼", "教学4楼", "计算机学院", "工程中心"],
    "文体区": ["网球场", "体育馆"]
}
predicted_09 = {
    "东门":31, "南门":17, "北门":39, "一食堂":13, "二食堂":13, "三食堂":12,
    "梅苑1栋":27, "菊苑1栋":21, "教学2楼":78, "教学4楼":56, "计算机学院":12,
    "工程中心":28, "网球场":15, "体育馆":7, "校医院":7
}

# ================== 计算逻辑 ==================
# 初始化流量统计
inflow = {loc:0 for loc in predicted_09}
outflow = {loc:0 for loc in predicted_09}

for start, end, amount in schedules:
    if end in inflow:
        inflow[end] += amount
    if start != '运维处' and start in outflow:
        outflow[start] += amount

net_flow = {loc: inflow[loc]-outflow[loc] for loc in predicted_09}
actual_09 = {loc: predicted_09[loc]+net_flow[loc] for loc in predicted_09}

# ================== 高级可视化设计 ==================
plt.rcParams.update({
    'font.sans-serif': 'Microsoft YaHei',
    'axes.facecolor': 'FFFFFF',    # 浅橙色背景
    'figure.facecolor': 'FFFFFF'   # 整体背景色
})

# 创建专业调色板
palette = {
    "预测值": {
        "color": "#FFB347",      # 浅橙色
        "edge": "#E67E22"        # 深橙色边框
    },
    "实际值": {
        "color": "#FF8C00",      # 鲜明橙色
        "edge": "#D35400"        # 深橙色边框
    },
    "highlight": "#E74C3C",      # 高亮红色
    "grid": "#EDBB99"            # 网格线颜色
}

# 创建带分组的坐标轴标签
sorted_locations = list(location_groups.values())[0] + list(location_groups.values())[1] + list(location_groups.values())[2]
x_labels = [f"{loc}\n({group})" for loc in sorted_locations
           for group, locs in location_groups.items() if loc in locs]

# 绘制专业图表
fig, ax = plt.subplots(figsize=(20, 10))
x = np.arange(len(sorted_locations))
width = 0.45

# 绘制带边框的柱状图
bars_pred = ax.bar(x - width/2, [predicted_09[loc] for loc in sorted_locations], width,
                  color=palette["预测值"]["color"], edgecolor=palette["预测值"]["edge"],
                  linewidth=1.5, label='预测值', zorder=2)

bars_actual = ax.bar(x + width/2, [actual_09[loc] for loc in sorted_locations], width,
                    color=palette["实际值"]["color"], edgecolor=palette["实际值"]["edge"],
                    linewidth=1.5, label='调度后实际值', zorder=2)

# 设计网格和边框
ax.grid(axis='y', color=palette["grid"], linestyle='--', alpha=0.7, zorder=1)
ax.spines['top'].set_visible(False)
ax.spines['right'].set_visible(False)
ax.spines['bottom'].set_color('#D5D8DC')
ax.spines['left'].set_color('#D5D8DC')

# 高级标签设计
ax.set_title('共享单车供需调度效果分析（09:00）\n', fontsize=20, color='#34495E', pad=20)
ax.set_xlabel('地理位置分布（按区域分组）', fontsize=14, color='#34495E', labelpad=15)
ax.set_ylabel('单车数量', fontsize=14, color='#34495E', labelpad=15)
ax.set_xticks(x)
ax.set_xticklabels(x_labels, rotation=45, ha='right', fontsize=12, color='#2C3E50')

# 自动标注数值
def format_annotation(height):
    return f'▲{height}' if height > 70 else str(height)

for bars, color in zip([bars_pred, bars_actual], ['#2C3E50', '#C0392B']):
    for bar in bars:
        height = bar.get_height()
        ax.text(bar.get_x() + bar.get_width()/2, height+1, format_annotation(height),
                ha='center', va='bottom', fontsize=10, color=color, fontweight='bold')

# 添加区域分隔线
sep_positions = [
    len(location_groups["生活区"]) - 0.5,
    len(location_groups["生活区"]) + len(location_groups["教学区"]) - 0.5
]
for pos in sep_positions:
    ax.axvline(pos, color='#EDBB99', linestyle='--', alpha=0.8)

# 添加图例和高亮标注
legend = ax.legend(frameon=True, shadow=True, fontsize=12,
                  facecolor='#FFE4CC', edgecolor='#D35400',
                  loc='upper left', bbox_to_anchor=(0.02, 0.98))
legend.get_frame().set_linewidth(2.0)

# 高亮关键数据点
ax.plot(7, 76, 'o', markersize=12, color=palette["highlight"],
        markeredgewidth=2, markeredgecolor='white')
ax.annotate('超量调度预警', xy=(7, 76), xytext=(8, 85),
           arrowprops=dict(arrowstyle="fancy", color=palette["highlight"],
                           connectionstyle="angle3,angleA=0,angleB=90"),
           fontsize=14, color=palette["highlight"], weight='bold')

# 输出最终图表
plt.tight_layout()
plt.savefig('optimized_scheduling_visualization.png', dpi=300, bbox_inches='tight')
plt.show()
