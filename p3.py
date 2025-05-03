import pandas as pd
import numpy as np
import networkx as nx
from scipy.spatial.distance import cdist
from sklearn.cluster import KMeans
from ortools.linear_solver import pywraplp

# ===== 实际数据加载 =====
# 根据需求数据定义停车点
locations = [
    '东门', '南门', '北门', '一食堂', '二食堂', '三食堂',
    '梅苑1栋', '菊苑1栋', '教学2楼', '教学4楼', '计算机学院',
    '工程中心', '网球场', '体育馆', '校医院'
]

# 根据实际位置设置坐标
coords = np.array([
    [1200, 2300],  # 东门
    [3500, 1500],  # 南门
    [2500, 2800],  # 北门
    [1500, 800],  # 一食堂
    [1700, 1800],  # 二食堂
    [2100, 900],  # 三食堂
    [3300, 2300],  # 梅苑1栋
    [4000, 1900],  # 菊苑1栋
    [1200, 1100],  # 教学2楼
    [900, 1500],  # 教学4楼
    [1800, 500],  # 计算机学院
    [2200, 2000],  # 工程中心
    [2800, 700],  # 网球场
    [400, 1800],  # 体育馆
    [3800, 600]  # 校医院
])

# 读取需求数据（已直接转换为numpy数组）
gap_data = np.array([
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


# ===== 工具函数 =====
def compute_distance_matrix(coords):
    """生成实际道路距离矩阵"""
    # 假设实际路程是欧氏距离的1.3倍（可根据实际地图路径调整）
    euclidean_dist = cdist(coords, coords, metric='euclidean')
    return euclidean_dist * 1.3


distance_matrix = compute_distance_matrix(coords)


# ===== 节点重要性计算 =====
def compute_node_importance(d_matrix):
    G = nx.Graph()
    G.add_nodes_from(locations)

    # 添加边（仅连接距离1km内的停车点）
    for i in range(len(locations)):
        for j in range(i + 1, len(locations)):
            if d_matrix[i][j] < 1000:
                G.add_edge(locations[i], locations[j], weight=1 / d_matrix[i][j])

    # 计算介数中心性
    betweenness = nx.betweenness_centrality(G, weight='weight', normalized=True)
    return {loc: betweenness.get(loc, 0.0) for loc in locations}


node_importance = compute_node_importance(distance_matrix)


# ===== 时空效率评估 =====
class OperationEvaluator:
    def __init__(self, distance_matrix, time_windows):
        self.d_matrix = distance_matrix
        self.time_windows = time_windows
        self.time_decay = {t: np.exp(-0.1 * i) for i, t in enumerate(time_windows)}

    def compute_kde(self, gap_data):
        n_nodes = len(locations)
        n_time = len(self.time_windows)
        kde_table = np.zeros((n_nodes, n_time))

        for i in range(n_nodes):
            spatial_weights = np.exp(-self.d_matrix[i] / 800)  # 800m spatial kernel
            for ti, t in enumerate(self.time_windows):
                kde_table[i, ti] = np.dot(gap_data[:, ti], spatial_weights) * self.time_decay[t]
        return kde_table

    def evaluate_efficiency(self, gap_data):
        kde = self.compute_kde(gap_data)
        return {
            'turnover': np.abs(np.diff(gap_data, axis=1)).sum(axis=1),
            'load_var': np.var(gap_data, axis=1),
            'node_importance': np.array([node_importance[loc] for loc in locations]),
            'KDE': kde.mean(axis=1)
        }


# ===== 布局优化模型 =====
class LayoutOptimizer:
    def __init__(self, distance_matrix, demands, capacities):
        self.dist_mat = distance_matrix
        self.demands = demands
        self.capacities = capacities
        self.n = len(locations)

    def solve(self):
        solver = pywraplp.Solver.CreateSolver('SCIP')

        # 决策变量
        x = [solver.IntVar(0, 1, f'x_{i}') for i in range(self.n)]

        # 目标函数（最小化供需缺口+容量冗余）
        objective = solver.Objective()
        for i in range(self.n):
            objective.SetCoefficient(x[i], 0.6 * self.demands[i] + 0.4 * (100 - self.capacities[i]))
        objective.SetMinimization()

        # 约束1：每个点至少被一个服务站覆盖（800m内）
        for j in range(self.n):
            ct = solver.Constraint(1, solver.infinity())
            for i in range(self.n):
                if self.dist_mat[i][j] <= 800:
                    ct.SetCoefficient(x[i], 1)

        # 约束2：站点数量不超过当前配置
        ct = solver.Constraint(0, len(locations))
        for i in range(self.n):
            ct.SetCoefficient(x[i], 1)

        status = solver.Solve()

        if status == pywraplp.Solver.OPTIMAL:
            return [x[i].solution_value() for i in range(self.n)]
        else:
            print("无最优解，采用全量策略")
            return [1] * self.n


# ===== 主程序 =====
if __name__ == "__main__":
    time_windows = ['07:00', '09:00', '12:00', '14:00', '18:00', '21:00', '23:00']

    # 初始评估
    evaluator = OperationEvaluator(distance_matrix, time_windows)
    initial_eff = evaluator.evaluate_efficiency(gap_data)

    # 布局优化
    demands = gap_data.mean(axis=1)
    capacities = np.array([100] * len(locations))
    optimizer = LayoutOptimizer(distance_matrix, demands, capacities)
    solution = optimizer.solve()

    # 应用优化方案（新增/扩容站点）
    new_capacities = np.where(np.array(solution) > 0.5, 150, 100)
    optimized_gap = gap_data * np.where(new_capacities[:, None] == 150, 0.7, 1.1)

    # 优化后评估
    optimized_eff = evaluator.evaluate_efficiency(optimized_gap)

    # 打印结果
    print(f"优化前平均周转量: {initial_eff['turnover'].mean():.1f}")
    print(
        f"优化后平均周转量: {optimized_eff['turnover'].mean():.1f} (降低{(1 - optimized_eff['turnover'].mean() / initial_eff['turnover'].mean()) * 100:.1f}%)")

    # 聚类分析
    kmeans = KMeans(n_clusters=3).fit(coords)

    print("\n优化建议:")
    for c in range(3):
        cluster_points = [coords[i] for i, label in enumerate(kmeans.labels_) if label == c]
        members = [loc for i, loc in enumerate(locations) if kmeans.labels_[i] == c]

        # 正确计算实际地理位置中心
        center_x = np.mean([p[0] for p in cluster_points])
        center_y = np.mean([p[1] for p in cluster_points])

        print(f"集群{c + 1}（中心坐标: {int(center_x)},{int(center_y)}）:")
        print(f"  服务范围: {', '.join(members)}")

        # 判断集群特征生成建议
        if any('食堂' in loc for loc in members):
            print("  建议：增加就餐高峰时段调度")
        elif sum(initial_eff['node_importance'][kmeans.labels_ == c]) > 0.3:
            print("  建议：设置24小时运维站点")
        else:
            print("  建议：常规动态运力调配")