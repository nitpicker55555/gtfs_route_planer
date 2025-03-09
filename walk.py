from flask import Flask, request, jsonify,render_template
import osmnx as ox
import networkx as nx

app = Flask(__name__)

# 在应用启动时加载保存的慕尼黑步行路网
G = ox.load_graphml(filepath="munich_walk_network.graphml")
print("已加载慕尼黑步行路网")


# 提供前端页面

@app.route('/')
def index():

    return render_template('index.html')


# 计算路径的 API 端点
@app.route('/calculate_route', methods=['POST'])
def calculate_route():
    data = request.json
    start = data['start']  # [纬度, 经度]
    end = data['end']  # [纬度, 经度]

    # 找到最近的路网节点
    start_node = ox.distance.nearest_nodes(G, start[1], start[0])
    end_node = ox.distance.nearest_nodes(G, end[1], end[0])

    # 计算最短路径
    try:
        path = ox.routing.shortest_path(G, start_node, end_node, weight='length')
        if not path:
            raise nx.NetworkXNoPath("无法找到路径")

        # 提取路径的坐标
        coordinates = []
        for node in path:
            node_data = G.nodes[node]
            coordinates.append([node_data['x'], node_data['y']])  # [经度, 纬度]

        # 构造 GeoJSON
        geojson = {
            "type": "Feature",
            "geometry": {
                "type": "LineString",
                "coordinates": coordinates
            },
            "properties": {}
        }
        return jsonify(geojson)
    except nx.NetworkXNoPath:
        return jsonify({'error': '无法找到路径'}), 404


if __name__ == '__main__':
    app.run(debug=True)