import csv
import numpy as np
from typing import Dict, List, Set
import json

def time_to_seconds(time_str: str) -> int:
    """将 HH:MM:SS 格式的时间转换为秒"""
    h, m, s = map(int, time_str.split(':'))
    return h * 3600 + m * 60 + s

def preprocess_stop_times_to_numpy_matrix(file_path: str, npz_output_path: str, mapping_output_path: str) -> None:
    """
    预处理 stop_times.txt 文件，将数据转为 NumPy 邻接矩阵，并保存矩阵和站点映射。

    参数:
        file_path (str): stop_times.txt 文件的路径
        npz_output_path (str): 输出 NumPy 矩阵文件路径（.npz 格式）
        mapping_output_path (str): 输出站点 ID 到索引的映射文件路径（JSON 格式）
    """
    # 存储所有 trip 的站点序列
    trips: Dict[str, List[dict]] = {}
    stops_set: Set[str] = set()  # 所有唯一的 stop_id

    # 读取文件
    with open(file_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        # 修正字段名，移除可能的 BOM
        expected_headers = {'trip_id', 'arrival_time', 'departure_time', 'stop_id', 'stop_sequence'}
        actual_headers = set(reader.fieldnames)
        print(f"文件头: {actual_headers}")  # 调试：检查实际字段名
        if not expected_headers.issubset(actual_headers):
            raise ValueError(f"文件头不符合预期，缺少必要的列。预期: {expected_headers}, 实际: {actual_headers}")

        for row in reader:
            # 使用正确的 trip_id 键（移除 BOM）
            trip_id = row['trip_id']
            stop_seq = int(row['stop_sequence'])
            stop_data = {
                'stop_id': row['stop_id'],
                'arrival_time': row['arrival_time'],
                'departure_time': row['departure_time']
            }
            stops_set.add(row['stop_id'])

            if trip_id not in trips:
                trips[trip_id] = []
            while len(trips[trip_id]) < stop_seq:
                trips[trip_id].append(None)
            trips[trip_id][stop_seq - 1] = stop_data

    # 调试：检查 trips 数据
    print(f"行程数量: {len(trips)}")
    print(f"站点数量: {len(stops_set)}")
    for trip_id, stop_list in trips.items():
        print(f"Trip {trip_id}: {stop_list}")

    # 创建站点 ID 到索引的映射
    stops = sorted(list(stops_set))  # 固定顺序，确保映射一致
    stop_to_index = {stop: idx for idx, stop in enumerate(stops)}

    # 初始化邻接矩阵（用无穷大表示无连接）
    n = len(stops)
    adjacency = np.full((n, n), np.inf)  # 用 np.inf 表示不可达

    # 填充邻接矩阵
    for trip_id, stop_list in trips.items():
        for i in range(len(stop_list) - 1):
            if stop_list[i] is None or stop_list[i + 1] is None:
                continue  # 跳过空数据
            from_stop = stop_list[i]['stop_id']
            to_stop = stop_list[i + 1]['stop_id']
            from_time = stop_list[i]['departure_time']
            to_time = stop_list[i + 1]['arrival_time']
            time_diff = time_to_seconds(to_time) - time_to_seconds(from_time)

            from_idx = stop_to_index[from_stop]
            to_idx = stop_to_index[to_stop]
            adjacency[from_idx, to_idx] = min(adjacency[from_idx, to_idx], time_diff)
            print(f"连接: {from_stop} -> {to_stop}, 时间: {time_diff} 秒")  # 调试：检查填充

    # 调试：检查矩阵
    print(f"邻接矩阵:\n{adjacency}")

    # 保存邻接矩阵为 .npz 文件
    np.savez(npz_output_path, adjacency=adjacency)

    # 保存站点映射为 JSON 文件
    with open(mapping_output_path, 'w', encoding='utf-8') as f:
        json.dump(stop_to_index, f, ensure_ascii=False, indent=4)

    print(f"NumPy 邻接矩阵已保存到 {npz_output_path}")
    print(f"站点映射已保存到 {mapping_output_path}")

def load_numpy_matrix(npz_file_path: str, mapping_file_path: str) -> tuple[np.ndarray, Dict[str, int]]:
    """加载 NumPy 邻接矩阵和站点映射"""
    data = np.load(npz_file_path)
    adjacency = data['adjacency']
    with open(mapping_file_path, 'r', encoding='utf-8') as f:
        stop_to_index = json.load(f)
    return adjacency, stop_to_index

def query_travel_time(adjacency: np.ndarray, stop_to_index: Dict[str, int], from_stop: str, to_stop: str) -> float:
    """查询两个站点之间的旅行时间"""
    from_idx = stop_to_index.get(from_stop)
    to_idx = stop_to_index.get(to_stop)
    if from_idx is None or to_idx is None:
        print(f"站点不存在: from={from_stop}, to={to_stop}")
        return np.inf  # 站点不存在
    time = adjacency[from_idx, to_idx]
    print(f"查询: {from_stop} -> {to_stop}, 索引: {from_idx} -> {to_idx}, 时间: {time}")  # 调试
    return time

# 测试代码
if __name__ == "__main__":
    input_file = "stop_times.txt"
    npz_output = "stop_times_adjacency.npz"
    mapping_output = "stop_mapping.json"

    # 预处理
    # preprocess_stop_times_to_numpy_matrix(input_file, npz_output, mapping_output)

    # 加载并查询
    adjacency, stop_to_index = load_numpy_matrix(npz_output, mapping_output)
    from_stop = "de:09162:1140:51:51-Hst"
    to_stop = "de:09162:40:51:51-Hst"
    time = query_travel_time(adjacency, stop_to_index, from_stop, to_stop)
    if time != np.inf:
        print(f"从 {from_stop} 到 {to_stop} 的旅行时间: {time} 秒")
    else:
        print(f"从 {from_stop} 到 {to_stop} 无直接连接")