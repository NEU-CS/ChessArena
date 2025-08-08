import os
import json

def main():
    data = []
    with open("./gpt-4.1_predictions_2000.jsonl","r") as f:
        for line in f:
            data.append(json.loads(line))
    
    sft_data = []
    for i,v in enumerate(data):
        if v["pred_piece"] == v["gt_piece"]:
            if v["f1_score"] == 1:
                sft_item = {}
                sft_item["system"] = v["system"]
                sft_item["prompt"] = v["prompt"]
                sft_item["response"] = v["response"]
                sft_data.append(sft_item)
    
    with open("chess_modeling_gpt_4_1.jsonl","w") as f:
        for item in sft_data:
            f.write(json.dumps(item)+"\n")

if __name__ == '__main__':
    main()