import os
import json
import matplotlib.pyplot as plt

def main():
    # 1. 获取当前目录下的模型文件夹（子目录）
    model_dirs = [d for d in os.listdir('.') if os.path.isdir(d)]
    if not model_dirs:
        print("当前目录下没有找到模型文件夹，请检查目录结构。")
        return

    # 存储数据：{模型名称: {Elo分段: 准确率(%)}}
    model_data = {}
    all_elo_segments = set()

    # 遍历每个模型文件夹
    for model_name in model_dirs:
        model_path = os.path.join('.', model_name)
        elo_dirs = [d for d in os.listdir(model_path) if os.path.isdir(os.path.join(model_path, d))]
        model_data[model_name] = {}
        
        # 遍历每个Elo分段文件夹
        for elo_segment in elo_dirs:
            elo_path = os.path.join(model_path, elo_segment)
            # 查找final_metrics开头的JSON文件
            json_files = [f for f in os.listdir(elo_path) 
                          if f.startswith('final_metrics') and f.endswith('.json')]
            if not json_files:
                continue  # 没有找到对应的JSON文件，跳过
                
            # 读取JSON文件中的accuracy
            with open(os.path.join(elo_path, json_files[0]), 'r') as f:
                metrics = json.load(f)
            accuracy = metrics.get('accuracy', 0.0)
            # 转换为百分比（如果原始数据是小数）
            if 0 <= accuracy <= 1:
                accuracy *= 100
            model_data[model_name][elo_segment] = accuracy
            all_elo_segments.add(elo_segment)

    # 2. 处理Elo分段的排序（按起始值升序）
    def sort_elo(segment):
        start = int(segment.split('-')[0])
        return start

    sorted_elo = sorted(all_elo_segments, key=sort_elo)
    num_elo = len(sorted_elo)
    num_models = len(model_data)

    # 3. 绘制分组柱状图
    plt.figure(figsize=(14, 7))
    bar_width = 0.8 / num_models  # 每个模型柱子的宽度

    for i, model in enumerate(model_data.keys()):
        # 计算每个柱子的X坐标（分组内的偏移）
        x_pos = [j + i * bar_width for j in range(num_elo)]
        # 获取该模型在每个Elo分段的准确率（无数据则填0）
        y_vals = [model_data[model].get(elo, 0) for elo in sorted_elo]
        plt.bar(x_pos, y_vals, width=bar_width, label=model)

    # 设置X轴刻度和标签
    plt.xticks(
        [j + bar_width * (num_models - 1) / 2 for j in range(num_elo)],
        sorted_elo,
        rotation=45,
        ha='right'
    )
    plt.xlabel('Puzzle Rating (Elo)')
    plt.ylabel('Accuracy (%)')
    plt.legend()
    plt.tight_layout()  # 自动调整布局
    plt.savefig("puzzles_rating_vs_accuaracy.png")
    #plt.show()

if __name__ == "__main__":
    main()