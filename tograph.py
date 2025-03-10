import csv
import json
from neo4j import GraphDatabase
from datetime import datetime, timedelta

# Neo4j连接配置（请根据您的Neo4j实例修改）
NEO4J_URI = "neo4j://localhost:7687"
NEO4J_USER = "neo4j"
NEO4J_PASSWORD = "password"  # 请替换为您的密码

# 初始化Neo4j驱动
driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))


# 将时间字符串转换为秒
def time_to_seconds(time_str):
    h, m, s = map(int, time_str.split(":"))
    return h * 3600 + m * 60 + s


# 1. 处理 stop_times.txt 文件
def process_stop_times(file_path):
    trips = {}
    with open(file_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            trip_id = row["trip_id"]
            if trip_id not in trips:
                trips[trip_id] = []
            trips[trip_id].append({
                "stop_id": row["stop_id"],
                "arrival_time": row["arrival_time"],
                "departure_time": row["departure_time"],
                "stop_sequence": int(row["stop_sequence"]),
                "shape_dist_traveled": float(row["shape_dist_traveled"])
            })

    # 按stop_sequence排序并生成关系数据
    trip_relations = []
    all_stops = set()
    for trip_id, stops in trips.items():
        stops.sort(key=lambda x: x["stop_sequence"])
        for i in range(len(stops) - 1):
            stop1 = stops[i]
            stop2 = stops[i + 1]
            all_stops.add(stop1["stop_id"])
            all_stops.add(stop2["stop_id"])
            arrival_seconds = time_to_seconds(stop2["arrival_time"])
            departure_seconds = time_to_seconds(stop1["departure_time"])
            travel_time = arrival_seconds - departure_seconds
            trip_relations.append({
                "from_stop": stop1["stop_id"],
                "to_stop": stop2["stop_id"],
                "trip_id": trip_id,
                "departure_time": stop1["departure_time"],
                "arrival_time": stop2["arrival_time"],
                "travel_time": travel_time
            })

    return list(all_stops), trip_relations


# 2. 处理 transfers.json 文件
def process_transfers(file_path):
    with open(file_path, "r", encoding="utf-8") as f:
        transfers = json.load(f)
    transfer_relations = []
    for transfer_key, transfer_time in transfers.items():
        from_stop, to_stop = transfer_key.split(" to ")
        transfer_relations.append({
            "from_stop": from_stop,
            "to_stop": to_stop,
            "transfer_time": transfer_time
        })
    return transfer_relations


# 3. 使用APOC导入数据到Neo4j
def import_to_neo4j_with_apoc(stops, trip_relations, transfer_relations):
    with driver.session() as session:
        # 批量创建站点节点
        print("正在创建站点节点...")
        session.run(
            """
            UNWIND $stops AS stop_id
            MERGE (s:Stop {stop_id: stop_id})
            """,
            stops=stops
        )

        # 创建索引以加速后续查询
        session.run("CREATE INDEX FOR (s:Stop) ON (s.stop_id)")

        # 批量创建BUS关系
        print("正在创建BUS关系...")
        session.run(
            """
            CALL apoc.periodic.iterate(
                'UNWIND $relations AS rel RETURN rel',
                'MATCH (s1:Stop {stop_id: rel.from_stop})
                 MATCH (s2:Stop {stop_id: rel.to_stop})
                 CREATE (s1)-[r:BUS {
                     trip_id: rel.trip_id,
                     departure_time: rel.departure_time,
                     arrival_time: rel.arrival_time,
                     travel_time: rel.travel_time
                 }]->(s2)',
                {batchSize: 1000, parallel: true, params: {relations: $relations}}
            )
            """,
            relations=trip_relations
        )

        # 批量创建TRANSFER关系
        print("正在创建TRANSFER关系...")
        session.run(
            """
            CALL apoc.periodic.iterate(
                'UNWIND $relations AS rel RETURN rel',
                'MATCH (s1:Stop {stop_id: rel.from_stop})
                 MATCH (s2:Stop {stop_id: rel.to_stop})
                 CREATE (s1)-[r:TRANSFER {transfer_time: rel.transfer_time}]->(s2)',
                {batchSize: 1000, parallel: true, params: {relations: $relations}}
            )
            """,
            relations=transfer_relations
        )


# 4. 查询路径规划（保持不变）
def find_path(start_stop, end_stop, start_time_str):
    start_seconds = time_to_seconds(start_time_str)

    with driver.session() as session:
        result = session.run(
            """
            MATCH path = (start:Stop {stop_id: $start_stop})-[:BUS|TRANSFER*]->(end:Stop {stop_id: $end_stop})
            WITH path, relationships(path) AS rels
            UNWIND rels AS rel
            WITH path, rels, 
                 COLLECT(CASE WHEN type(rel) = 'BUS' THEN rel.departure_time ELSE null END) AS departures,
                 COLLECT(CASE WHEN type(rel) = 'BUS' THEN rel.arrival_time ELSE null END) AS arrivals,
                 COLLECT(CASE WHEN type(rel) = 'BUS' THEN rel.trip_id ELSE null END) AS trip_ids,
                 COLLECT(CASE WHEN type(rel) = 'TRANSFER' THEN rel.transfer_time ELSE null END) AS transfers
            WHERE ALL(i IN RANGE(0, SIZE(departures)-1) WHERE 
                      (departures[i] IS NOT NULL AND time_to_seconds(departures[i]) >= $start_seconds) AND
                      (i = 0 OR time_to_seconds(arrivals[i-1]) + 
                                COALESCE(transfers[i-1], 0) <= time_to_seconds(departures[i])))
            RETURN path, trip_ids, departures, arrivals, transfers
            ORDER BY REDUCE(total_time = 0, r IN rels | 
                            total_time + CASE WHEN type(r) = 'BUS' THEN r.travel_time 
                                              WHEN type(r) = 'TRANSFER' THEN r.transfer_time 
                                              ELSE 0 END) ASC
            LIMIT 1
            """,
            start_stop=start_stop,
            end_stop=end_stop,
            start_seconds=start_seconds
        )

        record = result.single()
        if record:
            path = record["path"]
            trip_ids = record["trip_ids"]
            departures = record["departures"]
            arrivals = record["arrivals"]
            transfers = record["transfers"]

            print("路径规划结果：")
            nodes = path.nodes
            for i, node in enumerate(nodes):
                print(f"站点: {node['stop_id']}")
                if i < len(departures) and departures[i]:
                    print(f"  行程: {trip_ids[i]}, 出发时间: {departures[i]}, 到达时间: {arrivals[i]}")
                if i < len(transfers) and transfers[i]:
                    print(f"  换乘时间: {transfers[i]}秒")
        else:
            print("未找到路径")


# 主程序
if __name__ == "__main__":
    # 文件路径
    stop_times_file = "raw_file/stop_times.txt"
    transfers_file = "transfers.json"

    # 处理数据
    print("处理 stop_times.txt...")
    stops, trip_relations = process_stop_times(stop_times_file)
    print("处理 transfers.json...")
    transfer_relations = process_transfers(transfers_file)

    # 导入Neo4j
    import_to_neo4j_with_apoc(stops, trip_relations, transfer_relations)
    print("数据导入完成！")

    # 示例查询
    start_stop = "de:09162:40:51:51-Hst"
    end_stop = "de:09162:200:51:52-Hst"
    start_time = "04:33:40"
    print(f"从 {start_stop} 到 {end_stop} 于 {start_time} 出发：")
    find_path(start_stop, end_stop, start_time)

    # 关闭驱动
    driver.close()