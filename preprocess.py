import pandas as pd
import json


# 将时间字符串转换为秒数，便于比较
def time_to_seconds(time_str):
    h, m, s = map(int, time_str.split(':'))
    return h * 3600 + m * 60 + s


# ----------------------------
# 预处理部分：构建 trips 与 stop_index
# ----------------------------

# # 读取 stop_times.txt 数据
# df = pd.read_csv('raw_file/stop_times.txt', quotechar='"')
#
# # 建立字典，存储每个 trip 的所有记录（按 stop_sequence 升序排列）
# trips = {}
# # 同时建立一个索引：每个 stop_id 对应的列表 (trip_id, 在 trip 中的索引, departure_sec, arrival_sec)
# stop_index = {}
#
# # 按 trip_id 分组，并对每个分组按 stop_sequence 排序（转换为 int 类型）
# for trip_id, group in df.groupby('trip_id'):
#     group_sorted = group.sort_values('stop_sequence', key=lambda x: x.astype(int))
#     trip_list = []
#     for idx, row in group_sorted.reset_index(drop=True).iterrows():
#         record = {
#             'stop_id': row['stop_id'],
#             'arrival_time': row['arrival_time'],
#             'departure_time': row['departure_time'],
#             'stop_sequence': int(row['stop_sequence']),
#             'departure_sec': time_to_seconds(row['departure_time']),
#             'arrival_sec': time_to_seconds(row['arrival_time'])
#         }
#         trip_list.append(record)
#
#         # 更新 stop_index
#         stop = row['stop_id']
#         if stop not in stop_index:
#             stop_index[stop] = []
#         stop_index[stop].append((trip_id, idx, record['departure_sec'], record['arrival_sec']))
#     trips[trip_id] = trip_list
# with open("stop_index.json",'w') as file:
#     file.write(json.dumps(stop_index))
# with open("trips.json",'w') as file:
#     file.write(json.dumps(trips))
with open("stop_index.json", mode='r', encoding='utf-8') as file:
    stop_index = json.load(file)  # 解析 JSON 数据
with open("trips.json", mode='r', encoding='utf-8') as file:
    trips = json.load(file)  # 解析 JSON 数据


def find_segments_with_min(start_stop, end_stop, min_dep_sec):
    segments = []
    if start_stop not in stop_index:
        return segments

    for (trip_id, idx, dep_sec, _) in stop_index[start_stop]:
        if dep_sec >= min_dep_sec:
            trip_stops = trips[trip_id]
            # 从 boarding 站点后的记录中查找目标下车站
            for j in range(idx + 1, len(trip_stops)):
                if trip_stops[j]['stop_id'] == end_stop:
                    stop_count = j - idx + 1  # 包括上车和下车站
                    segments.append({
                        'trip_id': trip_id,
                        'board_stop': start_stop,
                        'alight_stop': end_stop,
                        'departure_time': trip_stops[idx]['departure_time'],
                        'arrival_time': trip_stops[j]['arrival_time'],
                        'departure_sec': dep_sec,
                        'arrival_sec': trip_stops[j]['arrival_sec'],
                        'stop_count': stop_count,
                        'start_index': idx,
                        'end_index': j
                    })
                    break  # 每趟车取最早符合的下车方案
    return segments


# ----------------------------
# 直达方案：返回距离当前时间最近的直达车段
# ----------------------------
def find_direct_trip(start_stop, end_stop, current_time):
    current_sec = time_to_seconds(current_time)
    segments = find_segments_with_min(start_stop, end_stop, current_sec)
    if segments:
        best_direct = min(segments, key=lambda x: x['departure_sec'])
        return best_direct
    return None


# ----------------------------
# 读取 transfer.json 中换乘信息
# ----------------------------
with open('transfers.json', 'r', encoding='utf-8') as f:
    transfers = json.load(f)


# ----------------------------
# 换乘方案：支持一次换乘，返回最早出发的换乘方案
# ----------------------------
def find_transfer_trips(start_stop, end_stop, current_time):
    current_sec = time_to_seconds(current_time)
    transfer_results = []

    # 遍历 transfer.json 中的换乘关系，key 格式 "A to B"
    for key, transfer_wait in transfers.items():
        parts = key.split(" to ")
        if len(parts) != 2:
            continue
        transfer_from = parts[0]  # 第一段的终点（换乘下车站）
        transfer_to = parts[1]  # 第二段的起点（换乘上车站）

        # 第一段：从起点到 transfer_from
        trip1_segments = find_segments_with_min(start_stop, transfer_from, current_sec)
        if not trip1_segments:
            continue

        for seg1 in trip1_segments:
            # 计算换乘后第二段的最早出发时间
            earliest_dep_trip2 = seg1['arrival_sec'] + transfer_wait
            # 第二段：从 transfer_to 到终点
            trip2_segments = find_segments_with_min(transfer_to, end_stop, earliest_dep_trip2)
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
                    'stop_count_trip1': seg1['stop_count'],
                    'transfer_wait': transfer_wait,
                    'departure_time_trip2': seg2['departure_time'],
                    'arrival_time_trip2': seg2['arrival_time'],
                    'stop_count_trip2': seg2['stop_count'],
                    'trip1_departure_sec': seg1['departure_sec']
                })
    if transfer_results:
        best_transfer = min(transfer_results, key=lambda x: x['trip1_departure_sec'])
        return best_transfer
    return None


# ----------------------------
# 示例调用
# ----------------------------
start_stop = "de:09162:40:51:51-Hst"
end_stop = "de:09162:1140:51:51-Hst"
current_time = "04:30:00"

print("【直达线路】")
best_direct = find_direct_trip(start_stop, end_stop, current_time)
if best_direct:
    print(f"直达线路: {best_direct['trip_id']}")
    print(f"  从 {best_direct['board_stop']} 于 {best_direct['departure_time']} 上车")
    print(f"  到 {best_direct['alight_stop']} 于 {best_direct['arrival_time']} 下车")
    print(f"  经过 {best_direct['stop_count']} 站")
    print("-" * 40)
else:
    print("未找到符合条件的直达线路。")

print("\n【换乘线路】")
best_transfer = find_transfer_trips(start_stop, end_stop, current_time)
if best_transfer:
    print(f"第一段线路: {best_transfer['trip1_id']}")
    print(f"  从 {best_transfer['board_stop']} 于 {best_transfer['departure_time_trip1']} 上车")
    print(f"  到 {best_transfer['transfer_from']} 于 {best_transfer['arrival_time_trip1']} 下车")
    print(f"  经过 {best_transfer['stop_count_trip1']} 站")
    print(f"换乘等待: {best_transfer['transfer_wait']} 秒后，在 {best_transfer['transfer_to']} 换乘")
    print(f"第二段线路: {best_transfer['trip2_id']}")
    print(f"  从 {best_transfer['transfer_to']} 于 {best_transfer['departure_time_trip2']} 上车")
    print(f"  到 {best_transfer['alight_stop']} 于 {best_transfer['arrival_time_trip2']} 下车")
    print(f"  经过 {best_transfer['stop_count_trip2']} 站")
    print("-" * 40)
else:
    print("未找到符合条件的换乘线路。")
