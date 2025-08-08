import json
import os
import re
import random
from utils import remove_all_empty_lines,sp_blitz

def convert():
    data = []
    with open("all_data.jsonl","r") as f:
        for line in f.readlines():
            data.append(json.loads(line))
    
    converted_data = []
    for i,v in enumerate(data):
        color = v["color"]
        model = v[f"{color}_player"]
        player = color
        x = {}
        x['model'] = model
        x["player"] = player        
        x["question"] = v["question"]
        x["answer"] = v["answer"]
        x["move_ranking"] = v["move_ranking"]
        converted_data.append(x)
    
    with open("converted_data.jsonl","w") as f:
        for line in converted_data:
            f.write(json.dumps(line) + "\n")




def combine():
    chess_game = []
    with open("converted_data.jsonl","r") as f:
        for line in f.readlines():
            x = json.loads(line)
            x["answer"] = x["answer"]["content"]
            chess_game.append(x)
    
    with open("chess_game.jsonl","r") as f:
        for i,line in enumerate(f.readlines()):
            try:
                x = json.loads(line)
                x["move_ranking"] = int(x["move_ranking"]) if x["move_ranking"] else None
                chess_game.append(x)
            except:
                pass
    
    with open("chess_game_combined.jsonl","w") as f:
        for line in chess_game:
            f.write(json.dumps(line) + "\n")
        
            
def get_blitz_data():
    data = []
    with open("chess_game_combined.jsonl","r") as f:
        for line in f.readlines():
            data.append(json.loads(line))
    
    blitz_data = []
    length = 0
    different_fen_notation = set()
    '''
    Current board position in FEN notation:\n8/8/2k5/rp6/1p2K3/3P4/P7/8 b - - 1 66
    '''
    pattern = re.compile("Current board position in FEN notation:\n.*?\n")

    existed_fen = set()
    multi_round_data = []
    top = 3
    for i,v in enumerate(data):
        sft_item = {}
        model = v["model"]
        mode = model.split("_")[-1]
        prompt = v["question"]
        multi_round_item = {}
        if mode == "blitz" or ("think and reason as much as you want" in prompt[0]["content"] and "only have" not in prompt[0]["content"] and "directly" not in prompt[0]["content"]):
            if v["move_ranking"] and int(v["move_ranking"]) in list(range(1,top+1)):
                if mode != "standard":
                    if "as White" in v["question"][0]["content"]:
                        is_white = True
                    elif "as Black" in v["question"][0]["content"]:
                        is_white = False
                    else:
                        raise Exception(f"Can't extract color information")
                    sft_item["system"] = sp_blitz(is_white) 
                    FEN_REGEX = r'Current board position in FEN notation:\s*([^\s]+(?:\s+[^\s]+){5})'
                    MOVE_HISTORY_REGEX = r'[Mm]ove history in UCI notation:\s*(.+?)\n'
                    LEGAL_MOVES_REGEX = r'Legal moves in UCI notation:\s*(.+?)\n'
                    if len(v["question"]) >= 2:
                        sft_item["prompt"] = v["question"][1]["content"]
                    else:
                        fen_match = re.search(FEN_REGEX, v["question"][0]["content"])
                        fen = fen_match.group(1).strip() if fen_match else ""
                        move_history_match = re.search(MOVE_HISTORY_REGEX, v["question"][0]["content"])
                        move_history = move_history_match.group(1).strip() if move_history_match else ""
                        legal_moves_match = re.search(LEGAL_MOVES_REGEX, v["question"][0]["content"])
                        legal_moves = legal_moves_match.group(1).strip() if legal_moves_match else ""
                        move_history_str = ""
                        if move_history:
                            move_history_str = f"Partial move history in UCI notation: {move_history}"
                        
                        legal_moves_str = ""
                        if legal_moves:
                            legal_moves_str = f"Legal moves in UCI notation: {legal_moves}"
                        user_prompt = f"""
Current board position in FEN notation:
{fen}
{move_history_str}
{legal_moves_str}
"""
                        sft_item["prompt"] = remove_all_empty_lines(user_prompt)
                    
                    fen_match = re.search(FEN_REGEX, sft_item["prompt"])
                    fen = fen_match.group(1).strip() if fen_match else ""
                    
                    if fen in existed_fen:
                        continue
                    
                    flag = False
                    for one_item in v["question"]:
                        if one_item.get("status","scucessful") != "scucessful":
                            flag = True
                            break
                    
                    if flag:
                        multi_round_item = {}
                        multi_round_item["system"] = sp_blitz(is_white)
                        multi_round_item["prompt"] = v["question"][-1]["content"]
                        multi_round_item["response"] = v["answer"]
                        history = []
                        for index in range(1,len(v["question"])-1,2):
                            mini_history = [v["question"][index]["content"],v["question"][index + 1]["content"]]
                            history.append(mini_history)
                        multi_round_item["history"] = history
                        multi_round_data.append(multi_round_item)
        
                    sft_item["response"] = v["answer"]
                    for vv in pattern.findall(sft_item["system"] + sft_item["prompt"]):
                        assert len(pattern.findall(sft_item["system"] + sft_item["prompt"])) == 1
                        different_fen_notation.add(vv)
                    blitz_data.append(sft_item)
                    existed_fen.add(fen)
                    length += len(v["answer"])
    
    print(len(different_fen_notation))
    print(length/len(blitz_data))
    print(len(blitz_data))
    with open(f"blitz_chess_top_{top}_game.jsonl","w") as f:
        for line in blitz_data:
            f.write(json.dumps(line) + '\n')
    
    with open("multi_round_fix_data.jsonl","w") as f:
        for line in multi_round_data:
            f.write(json.dumps(line) + '\n')


def get_existed_fen():
    #训练数据fen与eval数据的fen去重
    existed_fen = set()
    data = []
    with open("blitz_chess_top_1_game.jsonl") as f:
        for line in f.readlines():
            data.append(json.loads(line))
    
    with open("blitz_chess_top_3_game.jsonl") as f:
        for line in f.readlines():
            data.append(json.loads(line))
    
    with open("blitz_chess_top_1_game_no_legal.jsonl") as f:
        for line in f.readlines():
            data.append(json.loads(line))
    
    with open("blitz_chess_top_3_game_no_legal.jsonl") as f:
        for line in f.readlines():
            data.append(json.loads(line))
    
    with open("chess_modeling_gpt_4_1.jsonl") as f:
        for line in f.readlines():
            data.append(json.loads(line))
    
    FEN_REGEX = r'Current board position in FEN notation:\s*([^\s]+(?:\s+[^\s]+){5})'
    for i,v in enumerate(data):
        fen_match = re.search(FEN_REGEX, v["prompt"])
        fen = fen_match.group(1).strip() if fen_match else ""
        existed_fen.add(fen)
    
    with open("exsited_fen.json","w") as f:
        print(len(list(existed_fen)))
        f.write(json.dumps(list(existed_fen)))
    return existed_fen
    
if __name__ == '__main__':
    #convert()
    #combine()
    #get_blitz_data()
    #get_existed_fen()
        
    
    
    
    
    