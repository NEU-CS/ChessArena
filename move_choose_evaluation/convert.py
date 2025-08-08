import os
import json

def main(file_path):
    data = []
    with open(file_path, 'r') as f:
        for line in f:
            data.append(json.loads(line))

    sft_data = []
    for i, item in enumerate(data):
        if item["success"]:
            if item["final_uci"] in item["top_moves"]:
                sft_item = {}
                sft_item["system"] = item["system"]
                sft_item["prompt"] = item["prompt"]
                sft_item["response"] = item["response"]
                sft_data.append(sft_item)
                print(f"{i}\t{len(sft_data)}")
    
    with open("./deepseek-v3-without-legal-moves-top3.jsonl","w") as f:
        for line in sft_data:
            f.write(json.dumps(line) + "\n")

if __name__ == '__main__':
    file_path = "./deepseek-v3_prediction_False_10000.jsonl"
    main(file_path)