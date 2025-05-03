
import numpy as np
from ortools.constraint_solver import routing_enums_pb2
from ortools.constraint_solver import pywrapcp
import matplotlib.pyplot as plt

# ============== 全局配置优化 ==============
plt.rcParams['font.family'] = 'SimHei'
plt.rcParams['axes.unicode_minus'] = False

# ============== 地理信息数据 ==============
maintenance_depot = [3800, 2800]

optimized_coords = {
    '东门': (1200, 2300), '教学4楼': (900, 1500), '体育馆': (400, 1800),
    '南门': (3500, 1500), '北门': (2500, 2800), '梅苑1栋': (3300, 2300),
    '菊苑1栋': (4000, 1900), '校医院': (3800, 600), '一食堂': (1500, 800),
    '二食堂': (1700, 1800), '三食堂': (2100, 900), '教学2楼': (1200, 1100),
    '计算机学院': (1800, 500), '工程中心': (2200, 2000), '网球场': (2800, 700)
}


# ============== 智能车辆配置系统 ==============
class VehicleConfig:
    def __init__(self):
        self.base_config = {
            'num_vehicles': 4,
            'capacity': 28,
            'max_time': 720,
            'base_factor': 0.08,
            'overload_allowance': 150
        }

    def smart_adjust(self, total_demand):
        min_vehicles = max(3, int(total_demand * 1.1 / 30))
        req_capacity = min(35, max(20, int(total_demand / min_vehicles * 1.3)))

        self.base_config.update({
            'num_vehicles': min_vehicles,
            'capacity': req_capacity
        })
        return self.base_config


# ============== 可视化配置 ==============
visual_config = {
    'node_style': {
        'service_node': {'color': '#2F4554', 's': 80, 'marker': 'o'},
        'depot_node': {'color': '#1A1A1A', 's': 200, 'marker': '*'}
    },
    'route_style': [
        {'color': '#61A0A8', 'linewidth': 2, 'linestyle': '-', 'alpha': 0.8},
        {'color': '#D48265', 'linewidth': 2, 'linestyle': '--', 'alpha': 0.8},
        {'color': '#91C7AE', 'linewidth': 2, 'linestyle': '-.', 'alpha': 0.8}
    ],
    'peak_style': {'color': '#C23531', 'linestyle': ':'}
}

# ============== 动态时段参数 ==============
time_windows = ['07:00', '09:00', '12:00', '14:00', '18:00', '21:00', '23:00']
peak_factors = {'07:00': 1.5, '09:00': 2.0, '18:00': 1.8}


# ============== 核心优化引擎 ==============
class CampusFaultOptimizer:
    def __init__(self):
        self.locations = [maintenance_depot] + [list(optimized_coords[k]) for k in optimized_coords]
        self.location_names = ['运维处'] + list(optimized_coords.keys())
        self.vehicle_cfg = VehicleConfig()
        self._verify_data_integrity()

    def _verify_data_integrity(self):
        if len(optimized_coords) != 15:
            raise ValueError("地图坐标数据缺失，应包含15个区域")

    def _dynamic_time_matrix(self, time_slot):
        time_factor = peak_factors.get(time_slot, 1.0)
        return np.array([[int((abs(x1 - x2) + abs(y1 - y2)) / 1000 * 5.5 * time_factor)
                          for x2, y2 in self.locations]
                         for x1, y1 in self.locations])

    def _compute_distance_matrix(self):
        return np.array([[abs(x1 - x2) + abs(y1 - y2)
                          for x2, y2 in self.locations]
                         for x1, y1 in self.locations])

    def demand_prediction(self, time_slot):
        slot_idx = time_windows.index(time_slot)
        demands = []
        weekend_factor = 1.2 if time_slot in ['09:00', '18:00'] else 1.0

        for name in optimized_coords:
            base = turnover_data[name][slot_idx]
            dynamic_factor = min(0.22,
                                 self.vehicle_cfg.base_config['base_factor'] * weekend_factor + 0.02 * (slot_idx % 2))
            demands.append(int(base * dynamic_factor))

        total = sum(demands)
        feasible_capacity = (self.vehicle_cfg.base_config['capacity']
                             * self.vehicle_cfg.base_config['num_vehicles'])
        safe_capacity = feasible_capacity * 0.95

        if total > safe_capacity:
            scale = safe_capacity / total
            return [max(1, int(d * scale)) for d in demands]
        return demands

    def auto_configure(self, demands):
        total = sum(demands)
        return {
            'recommended_vehicles': max(3, int(total // 30) + 1),
            'recommended_capacity': int(total / max(1, total // 30) * 1.3)
        }

    def optimize_routes(self, time_slot):
        # 动态配置更新
        demands = [0] + self.demand_prediction(time_slot)
        if sum(demands) == 0:
            return {}

        cfg = self.vehicle_cfg.smart_adjust(sum(demands))
        print(f"当前配置：{cfg['num_vehicles']}辆车 | 单车容量:{cfg['capacity']} | 最长工时:{cfg['max_time']}分钟")

        # OR-Tools模型初始化
        manager = pywrapcp.RoutingIndexManager(
            len(self.locations), cfg['num_vehicles'], 0)
        routing = pywrapcp.RoutingModel(manager)

        # 注册双回调函数
        distance_matrix = self._compute_distance_matrix()
        time_matrix = self._dynamic_time_matrix(time_slot)

        transit_callback = lambda i, j: distance_matrix[manager.IndexToNode(i)][manager.IndexToNode(j)]
        time_callback = lambda i, j: time_matrix[manager.IndexToNode(i)][manager.IndexToNode(j)]

        transit_idx = routing.RegisterTransitCallback(transit_callback)
        time_idx = routing.RegisterTransitCallback(time_callback)

        # 维度约束
        routing.SetArcCostEvaluatorOfAllVehicles(transit_idx)

        # 容量约束（关键修订点）
        demand_callback = lambda i: demands[manager.IndexToNode(i)]
        demand_idx = routing.RegisterUnaryTransitCallback(demand_callback)
        routing.AddDimensionWithVehicleCapacity(
            demand_idx,
            cfg['overload_allowance'],
            [cfg['capacity']] * cfg['num_vehicles'],
            True,
            'Capacity'
        )

        # 时间窗约束
        routing.AddDimension(
            time_idx, 30, cfg['max_time'],
            False, 'Time'
        )

        # 强化求解策略
        search_params = pywrapcp.DefaultRoutingSearchParameters()
        search_params.first_solution_strategy = (
            routing_enums_pb2.FirstSolutionStrategy.PARALLEL_CHEAPEST_INSERTION)
        search_params.local_search_metaheuristic = (
            routing_enums_pb2.LocalSearchMetaheuristic.AUTOMATIC)
        search_params.time_limit.seconds = 60

        solution = routing.SolveWithParameters(search_params)
        return self._parse_solution(manager, routing, solution) if solution else {}

    def _parse_solution(self, manager, routing, solution):
        routes = {}
        for vid in range(routing.vehicles()):
            index = routing.Start(vid)
            route = []
            while not routing.IsEnd(index):
                node = manager.IndexToNode(index)
                route.append(self.location_names[node])
                index = solution.Value(routing.NextVar(index))
            route.append('运维处')

            if len(route) > 1:
                routes[f'巡检车-{vid + 1}'] = route
        return routes

    def visualize(self, routes, time_slot):
        plt.figure(figsize=(16, 10), dpi=100, facecolor='#F3F4F6')
        ax = plt.gca()
        ax.set_facecolor('#FFFFFF')

        for name, (x, y) in optimized_coords.items():
            ax.scatter(x, y, **visual_config['node_style']['service_node'])
            plt.text(x + 50, y + 50, name, fontsize=8, color='#444')
        ax.scatter(*maintenance_depot, **visual_config['node_style']['depot_node'])

        for vid, (vname, path) in enumerate(routes.items()):
            coords = []
            for p in path:
                coords.append(maintenance_depot if p == '运维处' else optimized_coords[p])
            coords = np.array(coords)

            style = visual_config['route_style'][vid % len(visual_config['route_style'])]
            if time_slot in peak_factors:
                style = {**style, **visual_config['peak_style']}

            ax.plot(coords[:, 0], coords[:, 1],
                    marker='o', markersize=6,
                    markerfacecolor='white',
                    label=f'{vname}路线',
                    **style)

        plt.title(f'校园智能巡检路径优化 - {time_slot}时段\n'
                  f'高峰期优化策略：{"是" if time_slot in peak_factors else "否"} | 总节点数：{len(optimized_coords)}',
                  fontsize=12, pad=15)
        plt.legend(loc='upper left', frameon=True)
        plt.grid(True, color='#EEEEEE')
        plt.tight_layout()
        plt.show()


# ============== 数据加载 ==============
turnover_data = {
    '东门': [48, 70, 56, 36, 84, 60, 30], '教学4楼': [30, 44, 38, 24, 50, 36, 20],
    '体育馆': [20, 36, 30, 16, 40, 24, 14], '南门': [60, 90, 76, 50, 100, 70, 40],
    '北门': [40, 60, 50, 30, 70, 50, 24], '梅苑1栋': [50, 70, 60, 36, 80, 56, 30],
    '菊苑1栋': [56, 80, 64, 40, 90, 60, 36], '校医院': [24, 30, 20, 16, 36, 24, 12],
    '一食堂': [36, 50, 40, 24, 60, 40, 20], '二食堂': [44, 60, 50, 30, 70, 48, 24],
    '三食堂': [40, 56, 44, 28, 64, 44, 22], '教学2楼': [32, 40, 36, 20, 48, 32, 16],
    '计算机学院': [20, 30, 24, 14, 36, 24, 12], '工程中心': [30, 40, 34, 20, 44, 30, 16],
    '网球场': [16, 24, 20, 10, 30, 20, 8]
}

# ============== 主程序入口 ==============
if __name__ == "__main__":
    try:
        engine = CampusFaultOptimizer()
        time_point = '09:00'  # 可测试不同时段

        print(f"⚙️ 正在处理【{time_point}】时段的动态优化...")
        demands = engine.demand_prediction(time_point)
        recommendation = engine.auto_configure(demands)
        print(
            f"💡 智能推荐配置：{recommendation['recommended_vehicles']}辆车 | 单车容量{recommendation['recommended_capacity']}")

        routes = engine.optimize_routes(time_point)

        print("\n▼▼▼ 优化结果 ▼▼▼")
        print(
            f"总需求预测：{sum(demands)} | 可用总容量：{engine.vehicle_cfg.base_config['num_vehicles'] * engine.vehicle_cfg.base_config['capacity']}")

        if routes:
            for vname, path in routes.items():
                # 重要修正点：正确计算负载
                load_indices = [i for i, n in enumerate(engine.location_names) if n in path]
                load = sum(demands[i] for i in load_indices if i < len(demands))

                print(f"{vname}：负载({load}/{engine.vehicle_cfg.base_config['capacity']}) → {' → '.join(path)}")
            engine.visualize(routes, time_point)
        else:
            print("\n⚠️ 未找到可行解，建议措施：")
            print("  1. 检查车辆配置参数")
            print("  2. 确认预测需求合理性")
            print("  3. 延长求解时间限制")

    except Exception as e:
        print(f"\n❌ 系统异常：{str(e)}")
