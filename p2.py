import pandas as pd
import numpy as np
from sklearn.ensemble import GradientBoostingRegressor
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline

# 初始化数据
data = {
    '位置': ['东门', '南门', '北门', '一食堂', '二食堂', '三食堂', '梅苑1栋', '菊苑1栋',
             '教学2楼', '教学4楼', '计算机学院', '工程中心', '网球场', '体育馆', '校医院'],
    '07:00': [28, 38, 15, 16, 63, 16, 30, 78, 13, 23, 3, 5, 9, 7, 2],
    '09:00': [31, 17, 39, 13, 13, 12, 27, 21, 78, 56, 12, 28, 15, 7, 7],
    '12:00': [23, 24, 48, 33, 103, 13, 29, 46, 22, 0, 7, 9, 0, 3, 1],
    '14:00': [45, 16, 30, 9, 8, 11, 19, 40, 16, 84, 34, 24, 10, 10, 7],
    '18:00': [7, 86, 54, 0, 41, 35, 18, 0, 15, 1, 22, 6, 17, 34, 2],
    '21:00': [75, 0, 26, 21, 25, 21, 29, 37, 72, 22, 11, 51, 0, 3, 2],
    '23:00': [28, 26, 10, 53, 88, 31, 89, 56, 15, 15, 6, 34, 8, 1, 8]
}

# 转换为时序特征矩阵
df = pd.DataFrame(data)
melted = df.melt(id_vars=['位置'], var_name='时间', value_name='车辆数')

# 生成空间类别特征
location_types = {
    '东门': 'gate', '南门': 'gate', '北门': 'gate',
    '一食堂': 'canteen', '二食堂': 'canteen', '三食堂': 'canteen',
    '梅苑1栋': 'dorm', '菊苑1栋': 'dorm',
    '教学2楼': 'academic', '教学4楼': 'academic',  # 补全类型定义
    '计算机学院': 'academic', '工程中心': 'academic',
    '网球场': 'sports', '体育馆': 'sports', '校医院': 'hospital'
}
melted['位置类型'] = melted['位置'].map(location_types)


# 生成时间特征
def time_features(time_str):
    h, m = map(int, time_str.split(':'))
    return {
        'hour': h,
        'minute': m,
        'course_period': int(any(
            abs((h + m / 60) - course) <= 0.5
            for course in [8, 8.92, 10.33, 11.25, 14, 15.92, 16.83, 19.5, 20.42]
        ))
    }


time_feats = melted['时间'].apply(lambda x: pd.Series(time_features(x)))
melted = pd.concat([melted, time_feats], axis=1)

# 生成滞后特征
melted['prev_count'] = melted.groupby('位置')['车辆数'].shift(1)
melted = melted.dropna()

# 构建特征矩阵
features = melted[['位置类型', 'hour', 'course_period', 'prev_count']]
labels = melted['车辆数']

# 创建预处理管道
preprocessor = ColumnTransformer([
    ('cat', OneHotEncoder(), ['位置类型']),
    ('num', StandardScaler(), ['hour', 'course_period', 'prev_count'])
])

model = Pipeline([
    ('preprocessor', preprocessor),
    ('regressor', GradientBoostingRegressor(
        n_estimators=150,
        learning_rate=0.1,
        max_depth=5
    ))
])

# 训练模型
model.fit(features, labels)


# 需求预测函数
def predict_demand(current_time, current_counts):
    """预测下一时段需求
    Args:
        current_time (str): 当前时间 HH:MM 格式
        current_counts (dict): 各点位当前车辆数 {位置: 数量}
    Returns:
        demand (dict): 预测的各点位需求 {位置: 需求数}
    """
    h, m = map(int, current_time.split(':'))
    next_h = h + 2 if h < 22 else 23  # 简单时序处理

    input_data = []
    for loc in data['位置']:
        input_data.append({
            '位置类型': location_types[loc],
            'hour': next_h,
            'course_period': int(any(
                abs((next_h + 30 / 60) - course) <= 0.5
                for course in [8, 8.92, 10.33, 11.25, 14, 15.92, 16.83, 19.5, 20.42]
            )),
            'prev_count': current_counts[loc]
        })

    X_pred = pd.DataFrame(input_data)
    return dict(zip(data['位置'], model.predict(X_pred).round().astype(int)))


# 多目标调度优化算法
class BikeScheduler:
    def __init__(self, nodes, distance_matrix):
        self.nodes = nodes  # 节点位置信息
        self.dist_mat = distance_matrix  # 距离矩阵

    def optimize(self, supply, demand, trucks=3, capacity=20):
        """调度优化核心算法
        Args:
            supply (dict): 供大于求的点位 {位置: 盈余数量}
            demand (dict): 需要补充的点位 {位置: 需求数量}
            trucks (int): 调度车数量
            capacity (int): 单车载量

        Returns:
            list: 调度路径 ["起点->终点(数量)", ...]
        """
        routes = []
        truck_loads = [0] * trucks
        truck_positions = ['运维处'] * trucks

        while sum(supply.values()) > 0 and sum(demand.values()) > 0:
            for t in range(trucks):
                if truck_loads[t] == 0:  # 车辆空载，寻找供应点
                    closest_supply = self._find_closest(truck_positions[t], supply)
                    if not closest_supply:
                        continue
                    pickup = min(supply[closest_supply], capacity)

                    supply[closest_supply] -= pickup
                    if supply[closest_supply] == 0:
                        del supply[closest_supply]

                    truck_loads[t] = pickup
                    truck_positions[t] = closest_supply
                    routes.append(f"运维处->{closest_supply}(载取{pickup})")

                else:  # 车辆满载，寻找需求点
                    closest_demand = self._find_closest(truck_positions[t], demand)
                    if not closest_demand:
                        continue
                    delivery = min(demand[closest_demand], truck_loads[t])

                    demand[closest_demand] -= delivery
                    if demand[closest_demand] == 0:
                        del demand[closest_demand]

                    truck_loads[t] -= delivery
                    truck_positions[t] = closest_demand
                    routes.append(f"{routes[-1].split('->')[-1]}->{closest_demand}(运送{delivery})")

        return routes

    def _find_closest(self, current_pos, targets):
        """根据距离矩阵寻找最近目标"""
        available = [loc for loc in targets if loc in self.nodes]
        if not available:
            return None
        return min(available, key=lambda x: self.dist_mat.get((current_pos, x), float('inf')))


# 示例调度配置
demo_distance = {
    ('运维处', '东门'): 1420, ('东门', '运维处'): 1420,
    ('运维处', '南门'): 1180, ('南门', '运维处'): 1180,
    ('运维处', '北门'): 1670, ('北门', '运维处'): 1670,
    ('运维处', '一食堂'): 850, ('一食堂', '运维处'): 850,
    ('运维处', '二食堂'): 720, ('二食堂', '运维处'): 720,
    ('运维处', '三食堂'): 930, ('三食堂', '运维处'): 930,
    ('运维处', '梅苑1栋'): 680, ('梅苑1栋', '运维处'): 680,
    ('运维处', '菊苑1栋'): 650, ('菊苑1栋', '运维处'): 650,
    ('运维处', '教学2楼'): 420, ('教学2楼', '运维处'): 420,
    ('运维处', '教学4楼'): 610, ('教学4楼', '运维处'): 610,
    ('运维处', '计算机学院'): 890, ('计算机学院', '运维处'): 890,
    ('运维处', '工程中心'): 920, ('工程中心', '运维处'): 920,
    ('运维处', '网球场'): 1300, ('网球场', '运维处'): 1300,
    ('运维处', '体育馆'): 1250, ('体育馆', '运维处'): 1250,
    ('运维处', '校医院'): 1110, ('校医院', '运维处'): 1110,
    # 校门到核心区域
    ('东门', '南门'): 2450, ('南门', '东门'): 2450,
    ('东门', '北门'): 1980, ('北门', '东门'): 1980,
    ('南门', '北门'): 2620, ('北门', '南门'): 2620,
    # 宿舍区域内部
    ('梅苑1栋', '菊苑1栋'): 380, ('菊苑1栋', '梅苑1栋'): 380,
    ('梅苑1栋', '一食堂'): 270, ('一食堂', '梅苑1栋'): 270,
    ('菊苑1栋', '二食堂'): 410, ('二食堂', '菊苑1栋'): 410,
    # 食堂之间
    ('一食堂', '二食堂'): 890, ('二食堂', '一食堂'): 890,
    ('二食堂', '三食堂'): 640, ('三食堂', '二食堂'): 640,
    # 教学区域
    ('教学2楼', '教学4楼'): 220, ('教学4楼', '教学2楼'): 220,
    ('教学2楼', '计算机学院'): 170, ('计算机学院', '教学2楼'): 170,
    ('教学4楼', '工程中心'): 310, ('工程中心', '教学4楼'): 310,
    # 运动场馆集群
    ('网球场', '体育馆'): 150, ('体育馆', '网球场'): 150,
    ('体育馆', '校医院'): 430, ('校医院', '体育馆'): 430,
    # 跨区域主要连接
    ('东门', '教学2楼'): 680, ('教学2楼', '东门'): 680,
    ('南门', '教学4楼'): 820, ('教学4楼', '南门'): 820,
    ('北门', '校医院'): 1050, ('校医院', '北门'): 1050,
    ('三食堂', '工程中心'): 730, ('工程中心', '三食堂'): 730,
    ('计算机学院', '体育馆'): 920, ('体育馆', '计算机学院'): 920,
    ('一食堂', '工程中心'): 610, ('工程中心', '一食堂'): 610,
    # 补充其他相邻路径（假设对称性）
    ('梅苑1栋', '网球场'): 890, ('网球场', '梅苑1栋'): 890,
    ('菊苑1栋', '计算机学院'): 570, ('计算机学院', '菊苑1栋'): 570,
    ('二食堂', '教学4楼'): 450, ('教学4楼', '二食堂'): 450,
    ('三食堂', '体育馆'): 1100, ('体育馆', '三食堂'): 1100,
    ('校医院', '工程中心'): 390, ('工程中心', '校医院'): 390
}

# 执行示例
if __name__ == "__main__":
    # 获取当前车辆分布
    current_status = {row['位置']: row['07:00'] for _, row in df.iterrows()}

    # 预测09:00需求
    predicted_demand = predict_demand('07:00', current_status)

    # 计算供需缺口
    supply = {}
    demand = {}
    for loc in current_status:
        gap = predicted_demand[loc] - current_status[loc]
        if gap < 0:
            supply[loc] = abs(gap)
        elif gap > 0:
            demand[loc] = gap

    # 初始化调度器
    scheduler = BikeScheduler(
        nodes=data['位置'] + ['运维处'],
        distance_matrix=demo_distance
    )

    # 生成调度方案
    routes = scheduler.optimize(supply, demand)

    print("\n优化调度方案：")
    print(*routes[:100], sep="\n")  # 显示前100条调度指令
