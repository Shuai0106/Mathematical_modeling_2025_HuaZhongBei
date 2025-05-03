import pandas as pd
import numpy as np
from datetime import datetime, time

#禁用未来警告的静默向下转型
pd.set_option('future.no_silent_downcasting', True)

# 读取数据
df = pd.read_excel('附件1.xlsx', header=0)

#显式设置列名
columns = ['Day', 'Time'] + [
    '东门', '南门', '北门', '一食堂', '二食堂', '三食堂',
    '梅苑1栋', '菊苑1栋', '教学2楼', '教学4楼',
    '计算机学院', '工程中心', '网球场', '体育馆', '校医院'
]
df.columns = columns

#使用ffill方法填充日期
df['Day'] = df['Day'].ffill()

#安全处理时间和日期格式
base_date = datetime(2024, 5, 1)  # 起始基准日期
day_count = 0
date_sequence = []

for idx, row in df.iterrows():
    if idx == 0 or row['Day'] != df.at[idx - 1, 'Day']:
        day_count += 1
    date_sequence.append(base_date + pd.DateOffset(days=day_count - 1))

df['Date'] = date_sequence


# 正确解析时间列
def parse_time(t):
    if isinstance(t, str):
        return datetime.strptime(t.split(' ')[-1], '%H:%M').time()
    elif isinstance(t, time):
        return t
    return datetime.strptime(str(t), '%H:%M:%S').time()


df['Time'] = df['Time'].apply(parse_time)
df['DateTime'] = df.apply(lambda x: datetime.combine(x['Date'], x['Time']), axis=1)

# 数值处理
for col in columns[2:]:
    df[col] = pd.to_numeric(df[col].replace('200+', 200, regex=False), errors='coerce')

df[columns[2:]] = df[columns[2:]].fillna(0)

# 重新计算夜间总量
night_mask = df['Time'].apply(lambda t: t.hour == 23 and t.minute == 0)
night_data = df[night_mask][columns[2:]].sum(axis=1)
total_vehicles = int(night_data.max() / 0.95595)  # 根据原文beta参数计算

# 时空插值预处理
df = df.set_index('DateTime')
full_index = pd.date_range(df.index.min(), df.index.max(), freq='30T')

# 重建结果表
time_points = [time(7, 0), time(9, 0), time(12, 0),
               time(14, 0), time(18, 0), time(21, 0), time(23, 0)]

result = {}
for loc in columns[2:]:
    ts = df[loc].resample('30T').mean()
    ts = ts.reindex(full_index).interpolate(method='linear')

    # 按星期分组求平均
    grouped = ts.groupby([ts.index.time, ts.index.dayofweek]).mean()

    # 构建最终结果
    loc_values = []
    for t in time_points:
        # 取所有周数的均值
        mask = grouped.index.get_level_values(0) == t
        if mask.any():
            loc_values.append(int(round(grouped[mask].mean())))
        else:
            loc_values.append(0)
    result[loc] = loc_values

# 输出结果
result_df = pd.DataFrame(result, index=time_points).T.reset_index()
result_df.columns = ['位置'] + [t.strftime('%H:%M') for t in time_points]

print(f"校园共享单车总量估计为：{total_vehicles}")
result_df.to_excel('表1-结果.xlsx', index=False)
