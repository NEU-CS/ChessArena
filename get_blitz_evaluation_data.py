import json
import os
import random
import re
from utils import remove_all_empty_lines,sp_blitz as sp,sp_chess_modeling,get_random_piece_position_by_color,\
get_random_empty_position,get_piece_and_legal_moves

#拿到chess_game_combined.jsonl中的所有数据，并提取其中的blitz对弈的数据
#构建两个测试数据集:1. 给定当前FEN，以及所有legal moves，预测下一步走法，legal move率，optimal move率；
#2. 给定当前FEN，预测下一步走法，legal move率，optimal move率；
FEN_REGEX = r'Current board position in FEN notation:\s*([^\s]+(?:\s+[^\s]+){5})'
LEGAL_MOVES_REGEX = r'Legal moves in UCI notation:\s*(.+?)\n'
MOVE_HISTORY_REGEX = r'(Partial)?\s*[Mm]ove history in UCI notation:\s*.+?\n'

def get_blitz_evaluation_data():
    data = []
    with open("all_data.jsonl","r") as f:
        for line in f:
            line = json.loads(line)
            data.append(line)

    question = []
    existed_fen = set()
    with open("exsited_fen.json","r") as f:
        existed_fen = set(json.load(f))

    for i,v in enumerate(data):
        model = v["white_player"] if v["color"] == "white" else v["black_player"]
        mode = model.split("_")[-1]
        prompt = v["question"]
        eval_item = {}
        if mode == "blitz" or ("think and reason as much as you want" in prompt[0]["content"] and "only have" not in prompt[0]["content"] and "directly" not in prompt[0]["content"]):
            if v["move_ranking"] in [1,2,3]:#评测数据不在训练数据中
                continue
            if "as White" in v["question"][0]["content"]:
                is_white = True
            elif "as Black" in v["question"][0]["content"]:
                is_white = False           
            eval_item["system"] = sp(is_white)
            
            if len(v["question"]) >= 2:
                fen_match = re.search(FEN_REGEX, v["question"][1]["content"])
                fen = fen_match.group(1).strip() if fen_match else ""
                
                eval_item["prompt"] = re.sub(MOVE_HISTORY_REGEX, "",v["question"][1]["content"])
                legal_moves_match = re.search(LEGAL_MOVES_REGEX, v["question"][1]["content"])
                legal_moves = legal_moves_match.group(1).strip() if legal_moves_match else ""
            else:
                fen_match = re.search(FEN_REGEX, v["question"][0]["content"])
                fen = fen_match.group(1).strip() if fen_match else ""
                legal_moves_match = re.search(LEGAL_MOVES_REGEX, v["question"][0]["content"])
                legal_moves = legal_moves_match.group(1).strip() if legal_moves_match else ""
                legal_moves_str = ""
                if legal_moves:
                    legal_moves_str = f"Legal moves in UCI notation: {legal_moves}"
                user_prompt = f"""
Current board position in FEN notation:
{fen}
{legal_moves_str}
What is the best move to make out of the list of legal moves? Think it step by step.
""" 
                eval_item["prompt"] = user_prompt
            eval_item["prompt"] = remove_all_empty_lines(eval_item["prompt"].strip())
            fen_match = re.search(FEN_REGEX, eval_item["prompt"])
            fen = fen_match.group(1).strip() if fen_match else ""
            legal_move_ground_truth = legal_moves.split(",")
            if not legal_move_ground_truth or not legal_moves or fen in existed_fen:
                continue
            existed_fen.add(fen)
            eval_item["fen"] = fen
            eval_item["top_moves"] = v["top_moves"]
            eval_item["prompt_without_legal_moves"] = re.sub("Legal moves in UCI notation:", "", eval_item["prompt"])
            eval_item["prompt_without_legal_moves"] = re.sub("list of ", "", eval_item["prompt"])
            eval_item["prompt_without_legal_moves"] = remove_all_empty_lines(re.sub(legal_moves,"",eval_item["prompt_without_legal_moves"]))
            eval_item["legal_moves"] = [x.strip() for x in legal_move_ground_truth]
            question.append(eval_item)
            
    
    random.shuffle(question)
    with open("move_choose_evaluation/blitz_legal_evaluation.jsonl","w") as f:
        for line in question:
            f.write(json.dumps(line) + "\n")


def get_chess_modeling_data():
    data = []
    with open("all_data.jsonl","r") as f:
        for line in f:
            line = json.loads(line)
            data.append(line)

    question = []
    existed_fen = set()
    with open("exsited_fen.json","r") as f:
        existed_fen = set(json.load(f))
    for i,v in enumerate(data):
        eval_item = {}
        if v["move_ranking"] in [1,2,3]:#评测数据不在训练数据中
            continue
        color = v["color"]
        verse_color = "white" if color == "black" else "black"
        eval_item["system"] = sp_chess_modeling()
        fen = v["fen_before"]
        if fen in existed_fen:
            continue
        prob = random.random()
        try:
            if prob <= 0.85:
                position = get_random_piece_position_by_color(fen,color)
            elif 0.85 < prob <= 0.92:
                position = get_random_piece_position_by_color(fen,verse_color)
            else:
                position = get_random_empty_position(fen)
            prompt = f"""
Current board position in FEN notation:
{fen}
Position:{position}
"""         

            eval_item["prompt"] = prompt
            eval_item["ground_truth"] = get_piece_and_legal_moves(fen,position)
            eval_item["fen"] = fen
            existed_fen.add(fen)
            question.append(eval_item)
        except:
            pass
        
    random.shuffle(question)
    with open("chess_modeling_evaluation/chess_modeling_evaluation.jsonl","w") as f:
        for line in question:
            f.write(json.dumps(line) + "\n")
            
if __name__ == '__main__':
    get_blitz_evaluation_data()
    #get_chess_modeling_data()
                