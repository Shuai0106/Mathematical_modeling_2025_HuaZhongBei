import numpy as np
import matplotlib.pyplot as plt
from matplotlib.font_manager import FontProperties
from matplotlib.colors import LinearSegmentedColormap

# ======================
# 1. 中文环境强制配置
# ======================
try:
    # Windows系统首选方案
    font_path = 'C:/Windows/Fonts/simhei.ttf'
    chinese_font = FontProperties(fname=font_path, size=12)
    plt.rcParams['font.sans-serif'] = [chinese_font.get_name()]
except:
    # Mac/Linux备选方案
    plt.rcParams['font.sans-serif'] = ['Heiti TC', 'Songti SC', 'WenQuanYi Zen Hei']

plt.rcParams['axes.unicode_minus'] = False  # 修复负号显示

# ======================
# 2. 校园地理参数设置
# ======================
map_width, map_height = 2000, 2000  # 地图尺寸
zones_config = {
    "学生生活区": {"x_range": (700, 1700), "y_range": (1600, 2000), "color": "#FFEECC"},
    "核心教学区": {"x_range": (200, 900), "y_range": (800, 1600), "color": "#DDFFDD"},
    "科研实验区": {"x_range": (100, 400), "y_range": (100, 700), "color": "#DDEEFF"},
    "运动场馆区": {"x_range": (1200, 1900), "y_range": (200, 800), "color": "#FFDDDD"}
}

# ======================
# 3. 生成专业级模拟数据
# ======================
np.random.seed(2023)
locations = {}

# 生成区域特征点
for zone, cfg in zones_config.items():
    num_points = 10 if zone=="学生生活区" else 6  # 生活区更高密度
    x = np.random.uniform(*cfg["x_range"], num_points)
    y = np.random.uniform(*cfg["y_range"], num_points)
    gammas = np.clip(
        np.random.normal(loc=1.1 if "教学" in zone else 0.9, scale=0.15, size=num_points),
        0.6, 1.5  # γ值限制范围
    )
    for i in range(num_points):
        loc_name = f"{zone}_{i+1}" if i>0 else zone
        locations[loc_name] = (x[i], y[i], gammas[i])

# 添加关键地标
special_landmarks = {
    '东校门': (1950, 100, 1.38),
    '运维中心': (150, 150, 0.72),
    '共享中台': (np.random.choice([300, 1600]), 800, 1.22),
    '国重实验室': (280, 650, 1.52)
}
locations.update(special_landmarks)

# ======================
# 4. 构建专业可视化系统
# ======================
fig, ax = plt.subplots(figsize=(20, 16), dpi=200)
fig.patch.set_facecolor('#FFFFFF')  # 纯白背景

# ----------------------
# 4.1 绘制地理特征基底
# ----------------------
for zone, cfg in zones_config.items():
    # 区域底色块
    ax.add_patch(plt.Rectangle(
        (cfg["x_range"][0], cfg["y_range"][0]),
        cfg["x_range"][1]-cfg["x_range"][0],
        cfg["y_range"][1]-cfg["y_range"][0],
        facecolor=cfg["color"],
        alpha=0.15,
        edgecolor='none',
        zorder=0
    ))
    # 区域文字标注
    ax.text(
        np.mean(cfg["x_range"]), np.mean(cfg["y_range"]),
        zone,
        ha='center', va='center',
        fontsize=14, color=cfg["color"].replace('#','#60'),
        alpha=0.8
    )

# 绘制主干道
ax.plot([0, map_width], [1200, 1200], color='#666666', lw=12, alpha=0.2, zorder=1)
ax.plot([1500, 1500], [0, map_height], color='#666666', lw=12, alpha=0.2, zorder=1)

# ----------------------
# 4.2 热力点高级渲染
# ----------------------
x = np.array([v[0] for v in locations.values()])
y = np.array([v[1] for v in locations.values()])
gammas = np.array([v[2] for v in locations.values()])

# 创建定制色阶
cmap = LinearSegmentedColormap.from_list("gamma_map", [
    (0.0, '#2E86C1'),   # 低值区：深蓝
    (0.5, '#F4D03F'),   # 中值区：明黄
    (1.0, '#E74C3C')    # 高值区：红色
])

sc = ax.scatter(
    x, y,
    c=gammas,
    s=np.interp(gammas, [0.6, 1.5], [80, 350]),  # 动态尺寸映射
    cmap=cmap,
    edgecolor='white',
    linewidths=1.2,
    alpha=0.95,
    zorder=20,
    vmin=0.6,
    vmax=1.5
)

# ----------------------
# 4.3 智能标签布局系统
# ----------------------
def smart_label_position(xi, yi):
    if xi > 1600: return (xi-50, yi+30)  # 右侧向左标注
    if yi > 1800: return (xi+20, yi-40)  # 顶部向下标注
    return (xi+25, yi+25)  # 默认右上标注

for name, (xi, yi, gi) in locations.items():
    tx, ty = smart_label_position(xi, yi)
    ax.annotate(
        f'{name}\nγ={gi:.2f}',
        (xi, yi),
        (tx, ty),
        ha='left' if tx > xi else 'right',
        va='bottom',
        fontsize=9,
        color='#34495E',
        linespacing=1.2,
        arrowprops=dict(
            arrowstyle="->",
            color='#7F8C8D',
            lw=0.8,
            connectionstyle="arc3,rad=0.2"
        ),
        bbox=dict(
            boxstyle="round,pad=0.2",
            facecolor='#FFFFFF88',  # 半透明白底
            edgecolor='none'
        )
    )

# ----------------------
# 4.4 辅助元素配置
# ----------------------
# 专业级颜色条
cbar = plt.colorbar(sc, ax=ax, shrink=0.45, pad=0.02)
cbar.outline.set_visible(False)
cbar.set_label('区位补偿系数 γ', labelpad=10)

# 比例尺
scale_params = [(1800, 180, 2000, 180, '200m'),
                (1700, 1700, 1700, 1850, '150m')]
for x1, y1, x2, y2, text in scale_params:
    ax.plot([x1, x2], [y1, y2], color='#333333', lw=2, solid_capstyle='butt')
    ax.text(np.mean([x1,x2]), np.mean([y1,y2])+5, text,
           ha='center', va='bottom', fontsize=10)

# ======================
# 5. 渲染输出
# ======================
ax.set_xlim(0, map_width)
ax.set_ylim(0, map_height)
ax.axis('off')  # 隐藏坐标轴

plt.title(
    "大学城共享单车服务半径补偿因子地理分布\n",
    fontsize=20,
    pad=30,
    color='#2C3E50'
)

plt.savefig(
    'Campus_GammaDistribution_Final.png',
    bbox_inches='tight',
    pad_inches=0.1,
    dpi=300,
    facecolor=fig.get_facecolor()
)
plt.close()
