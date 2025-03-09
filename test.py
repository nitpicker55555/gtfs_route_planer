import pandas as pd

# 读取txt文件
# 假设文件名为'stop_times.txt'
df = pd.read_csv('stop_times.txt',
                 dtype={
                     'trip_id': str,
                     'arrival_time': str,
                     'departure_time': str,
                     'stop_id': str,
                     'stop_sequence': int,
                     'pickup_type': int,
                     'drop_off_type': int,
                     'shape_dist_traveled': float
                 })

# 筛选包含'U6'的trip_id
u6_trips = df[df['trip_id'].str.contains('U6')]

# 选择需要的列
result = u6_trips[['trip_id', 'arrival_time', 'departure_time']]
# 从arrival_time提取小时:分钟
# 假设时间格式都是 HH:MM:SS，我们只取前5个字符 HH:MM
hours_minutes = u6_trips['arrival_time'].str[:2]

# 获取不重复的小时:分钟组合
unique_times = hours_minutes.drop_duplicates()

# 打印结果
print(unique_times)



# 如果需要保存到文件
# result.to_csv('u6_trips.csv', index=False)