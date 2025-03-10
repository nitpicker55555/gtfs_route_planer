import pandas as pd
import json
from datetime import datetime


# 将时间字符串转换为秒数，方便时间比较
def time_to_seconds(time_str):
    h, m, s = map(int, time_str.split(':'))
    return h * 3600 + m * 60 + s


# 读取 stop_times.txt 数据（确保文件编码、分隔符等与实际一致）
df = pd.read_csv('raw_file/stop_times.txt', quotechar='"')

# 将 stop_times 按 trip_id 分组
grouped = df.groupby('trip_id')


# 查找直达方案（无需换乘）的函数
def find_direct_trip(start_stop, end_stop, current_time):
    current_sec = time_to_seconds(current_time)
    direct_results = []
    for trip_id, group in grouped:
        # 根据 stop_sequence 排序（此处假定 stop_sequence 为数字，可能需要转换类型）
        group_sorted = group.sort_values('stop_sequence', key=lambda x: x.astype(int))
        stops = group_sorted['stop_id'].tolist()
        if start_stop in stops and end_stop in stops:
            index_start = stops.index(start_stop)
            index_end = stops.index(end_stop)
            if index_start < index_end:
                departure_time = group_sorted.iloc[index_start]['departure_time']
                dep_sec = time_to_seconds(departure_time)
                if dep_sec >= current_sec:
                    arrival_time = group_sorted.iloc[index_end]['arrival_time']
                    direct_results.append({
                        'trip_id': trip_id,
                        'board_stop': start_stop,
                        'alight_stop': end_stop,
                        'departure_time': departure_time,
                        'arrival_time': arrival_time
                    })
    return direct_results


# 辅助函数：查找从 start_stop 到 end_stop 的车段，要求出发时间 >= min_dep_sec
def find_segments_with_min(start_stop, end_stop, min_dep_sec):
    segments = []
    for trip_id, group in grouped:
        group_sorted = group.sort_values('stop_sequence', key=lambda x: x.astype(int))
        stops = group_sorted['stop_id'].tolist()
        if start_stop in stops and end_stop in stops:
            index_start = stops.index(start_stop)
            index_end = stops.index(end_stop)
            if index_start < index_end:
                departure_time = group_sorted.iloc[index_start]['departure_time']
                departure_sec = time_to_seconds(departure_time)
                if departure_sec >= min_dep_sec:
                    arrival_time = group_sorted.iloc[index_end]['arrival_time']
                    arrival_sec = time_to_seconds(arrival_time)
                    segments.append({
                        'trip_id': trip_id,
                        'board_stop': start_stop,
                        'alight_stop': end_stop,
                        'departure_time': departure_time,
                        'arrival_time': arrival_time,
                        'departure_sec': departure_sec,
                        'arrival_sec': arrival_sec
                    })
    return segments


# 读取 transfer.json 换乘信息文件
with open('transfers.json', 'r', encoding='utf-8') as f:
    transfers = json.load(f)


# 查找换乘方案的函数（支持一处换乘）
def find_transfer_trips(start_stop, end_stop, current_time):
    current_sec = time_to_seconds(current_time)
    transfer_results = []
    # 遍历 transfer.json 中的所有换乘关系，key 格式为 "A to B"
    for key, transfer_wait in transfers.items():
        parts = key.split(" to ")
        if len(parts) != 2:
            continue
        transfer_from = parts[0]  # 第一段的终点
        transfer_to = parts[1]  # 第二段的起点

        # 第一段：从起点到 transfer_from，要求出发时间不早于当前时间
        trip1_segments = find_segments_with_min(start_stop, transfer_from, current_sec)
        if not trip1_segments:
            continue
        # 对每个第一段方案，计算到达 transfer_from 后加上换乘等待时间，
        # 得到第二段可接受的最早出发时间
        for seg1 in trip1_segments:
            earliest_departure_trip2 = seg1['arrival_sec'] + transfer_wait
            # 第二段：从 transfer_to 到终点，要求出发时间 >= earliest_departure_trip2
            trip2_segments = find_segments_with_min(transfer_to, end_stop, earliest_departure_trip2)
            for seg2 in trip2_segments:
                transfer_results.append({
                    'trip1_id': seg1['trip_id'],
                    'trip2_id': seg2['trip_id'],
                    'board_stop': start_stop,
                    'transfer_from': transfer_from,
                    'transfer_to': transfer_to,
                    'alight_stop': end_stop,
                    'departure_time_trip1': seg1['departure_time'],
                    'arrival_time_trip1': seg1['arrival_time'],
                    'transfer_wait': transfer_wait,
                    'departure_time_trip2': seg2['departure_time'],
                    'arrival_time_trip2': seg2['arrival_time']
                })
    return transfer_results


# 示例调用
start_stop = "de:09162:540:1:1-Hst"
end_stop = "de:09162:120:51:51-Hst"
current_time = "08:30:00"

print("【直达线路】")
direct_trips = find_direct_trip(start_stop, end_stop, current_time)
if direct_trips:
    for trip in direct_trips:
        print(f"线路: {trip['trip_id']}")
        print(f"  从 {trip['board_stop']} 于 {trip['departure_time']} 上车")
        print(f"  到 {trip['alight_stop']} 于 {trip['arrival_time']} 下车")
        print("-" * 40)
else:
    print("未找到符合条件的直达线路。")

print("\n【换乘线路】")
transfer_trips = find_transfer_trips(start_stop, end_stop, current_time)
if transfer_trips:
    for route in transfer_trips:
        print(
            f"第一段线路: {route['trip1_id']} 从 {route['board_stop']} 于 {route['departure_time_trip1']} 上车，到 {route['transfer_from']} 于 {route['arrival_time_trip1']} 下车")
        print(f"换乘等待: {route['transfer_wait']} 秒后，在 {route['transfer_to']} 换乘")
        print(
            f"第二段线路: {route['trip2_id']} 从 {route['transfer_to']} 于 {route['departure_time_trip2']} 上车，到 {route['alight_stop']} 于 {route['arrival_time_trip2']} 下车")
        print("-" * 40)
else:
    print("未找到符合条件的换乘线路。")
