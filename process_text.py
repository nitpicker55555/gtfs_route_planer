import csv
import json
from typing import Dict, Tuple, Optional

# 定义一个字典来存储换乘时间，键为 (\ufefffrom_stop_id, to_stop_id)，值为 min_transfer_time
TransferDict = Dict[Tuple[str, str], int]


def preprocess_transfers(file_path: str, json_output_path: str) -> None:
    """
    预处理 transfers.txt 文件，将换乘数据存入字典并保存为 JSON 文件。

    参数:
        file_path (str): transfers.txt 文件的路径
        json_output_path (str): 输出 JSON 文件的路径
    """
    transfer_dict: TransferDict = {}

    # 打开并读取文件
    with open(file_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        print(reader.fieldnames)
        # 确保字段名正确
        expected_headers = {'\ufefffrom_stop_id', 'to_stop_id', 'transfer_type', 'min_transfer_time'}
        if not expected_headers.issubset(reader.fieldnames):
            raise ValueError("文件头不符合预期，缺少必要的列")

        # 遍历每一行
        for row in reader:
            from_stop = row['\ufefffrom_stop_id']
            to_stop = row['to_stop_id']
            # 只处理 transfer_type 为 "2" 的情况（需要固定换乘时间）
            if row['transfer_type'] == '2':
                try:
                    min_time = int(row['min_transfer_time'])  # 转换为整数
                    transfer_dict[(from_stop, to_stop)] = min_time
                except ValueError:
                    print(f"警告: 无效的 min_transfer_time 在行: {row}")

    # 将字典保存为 JSON 文件
    # JSON 不支持元组作为键，因此将 (\ufefffrom_stop_id, to_stop_id) 转换为字符串 "\ufefffrom_stop_id:to_stop_id"
    json_compatible_dict = {f"{from_stop} to {to_stop}": time for (from_stop, to_stop), time in transfer_dict.items()}

    with open(json_output_path, 'w', encoding='utf-8') as json_file:
        json.dump(json_compatible_dict, json_file, ensure_ascii=False, indent=4)

    print(f"预处理完成，数据已保存到 {json_output_path}")


def load_transfer_dict(json_file_path: str) -> Dict[str, int]:
    """
    从 JSON 文件加载换乘时间数据。

    参数:
        json_file_path (str): JSON 文件的路径

    返回:
        Dict[str, int]: 换乘时间字典，键为 "\ufefffrom_stop_id:to_stop_id" 格式的字符串
    """
    with open(json_file_path, 'r', encoding='utf-8') as json_file:
        return json.load(json_file)


def query_transfer_time(transfer_dict: Dict[str, int], from_stop: str, to_stop: str) -> Optional[int]:
    """
    查询两个站点之间的最小换乘时间。

    参数:
        transfer_dict (Dict[str, int]): 从 JSON 加载的换乘时间字典
        from_stop (str): 起始站点 ID
        to_stop (str): 目标站点 ID

    返回:
        Optional[int]: 最小换乘时间（秒），如果不存在则返回 None
    """
    key = f"{from_stop}:{to_stop}"
    return transfer_dict.get(key)


# 示例用法
if __name__ == "__main__":
    # 文件路径
    input_file = "raw_file/transfers.txt"
    output_json = "transfers.json"

    # 预处理并保存为 JSON
    preprocess_transfers(input_file, output_json)

    # # 加载 JSON 数据
    # transfer_dict = load_transfer_dict(output_json)
    # print("从 JSON 文件加载数据完成")
    #
    # # 示例查询
    # test_cases = [
    #     ("de:09162:1:1:1-Hst", "de:09162:1:1:91-Hst"),  # 预期返回 60
    #     ("de:09162:1:1:1-Hst", "de:09162:1:2:2-Hst"),  # 预期返回 96
    #     ("de:09162:1:1:1-Hst", "de:09162:999"),  # 预期返回 None
    # ]
    #
    # for from_stop, to_stop in test_cases:
    #     result = query_transfer_time(transfer_dict, from_stop, to_stop)
    #     if result is not None:
    #         print(f"从 {from_stop} 到 {to_stop} 的最小换乘时间: {result} 秒")
    #     else:
    #         print(f"从 {from_stop} 到 {to_stop} 无换乘信息")