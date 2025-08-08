import os
import sys
import json
import argparse
import concurrent.futures
import requests
from concurrent.futures import ThreadPoolExecutor
import threading
from utils import parse_uci_move,parse_san_move,san_to_uci,parse_json,evaluate_sets,connect_gpt
import time
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from chess_agent import Chess_Agent
import logging
from datetime import datetime

def setup_logger(model_name, rating, log_level=logging.INFO):
    """设置主logger和文件日志"""
    # 创建主logger
    logger = logging.getLogger(f"PuzzleEval_{model_name}_{rating}")
    logger.setLevel(log_level)
    
    # 避免重复添加handler
    if logger.handlers:
        return logger
    
    # 创建格式化器
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - [%(threadName)s] - %(message)s'
    )
    
    # 控制台处理器
    console_handler = logging.StreamHandler()
    console_handler.setLevel(log_level)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    # 文件处理器
    log_dir = f"puzzles_by_rating/lite/evaluation_results/{model_name}/{rating}_{rating+400}/logs"
    os.makedirs(log_dir, exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = f"{log_dir}/puzzle_eval_{timestamp}.log"
    
    file_handler = logging.FileHandler(log_file, encoding='utf-8')
    file_handler.setLevel(logging.DEBUG)  # 文件记录所有级别的日志
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    
    logger.info(f"Logger initialized. Log file: {log_file}")
    return logger

def collect_response_from_gpt(question_list,args):
    '''
    :param db_path: str
    :param question_list: []
    :return: dict of responses collected from openai
    '''
    count = 0
    def call_api_once(i,question):
        nonlocal count
        messages = [
            {'role':'system','content':question_list[i]["system"]},
            {'role':'user','content':question_list[i]["prompt"] if args.with_legal_move else question_list[i]["prompt_without_legal_moves"]}
        ]
        plain_result = connect_gpt(model=args.model_id, url=args.url, messages=messages, max_tokens=args.max_tokens, temperature=args.temperature, top_p=args.top_p, api_key=args.api_key,enable_thinking=args.enable_thinking)
        #print("the response is: \n",plain_result,"\n")
        count += 1
        print(f"processing:{count}/{len(question_list)}")
        return plain_result
    
    response_list = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=args.concurrency) as executor:
        # 使用 tqdm 显示进度
        response_list = list(executor.map(call_api_once, range(len(question_list)), question_list))

    return response_list

def move_choose_metric(question_list,response_list,args):
    result = []
    legal_nums = 0
    top_nums = 0
    uci_nums = 0
    san_nums = 0
    for i,v in enumerate(question_list):
        r = {}
        r['response'] = response_list[i]
        parsed_uci = parse_uci_move(r['response'],args.parse_any_move)
        converted_uci = None
        r['success'] = False
        if not parsed_uci:
            parsed_san = parse_san_move(r['response'],args.parse_any_move)
            if parsed_san:
                converted_uci = san_to_uci(parsed_san,v["fen"].strip())
                
        if parsed_uci in v['legal_moves']:
            legal_nums += 1
            uci_nums += 1
            r['success'] = True
            if parsed_uci in v["top_moves"]:
                top_nums += 1
                
        elif converted_uci in v['legal_moves']:
            legal_nums += 1
            san_nums += 1
            r['success'] = True
            if converted_uci in v["top_moves"]:
                top_nums += 1
        
        r['final_uci'] = parsed_uci if parsed_uci else converted_uci
        r['top_moves'] = v['top_moves']
        r['legal_moves'] = v['legal_moves']
        r['system'] = v["system"]
        r["prompt"] = v["prompt"] if args.with_legal_move else v["prompt_without_legal_moves"]
        result.append(r)
    final_metrics = {"legal_rate":legal_nums/len(question_list),"optimal_rate":top_nums/(legal_nums + 0.0001),\
            "total_nums":len(question_list),"uci_nums":uci_nums,"san_nums":san_nums}
    return result,final_metrics

def eval_move_choose(args):
    if not args.only_compute_metric:
        question_list = []
        with open("move_choose_evaluation/blitz_legal_evaluation.jsonl","r") as f:
            for line in f.readlines():
                question_list.append(json.loads(line))
        question_list = question_list[:args.eval_nums]
        response_list = collect_response_from_gpt(question_list,args)
    else:
        question_list = []
        with open("move_choose_evaluation/blitz_legal_evaluation.jsonl","r") as f:
            for line in f.readlines():
                question_list.append(json.loads(line))
        response_list = []
        with open(f"move_choose_evaluation/{args.model_name}_prediction_{args.with_legal_move}.jsonl") as f:
            for line in f.readlines():
                response_list.append(json.loads(line)["response"])
        args.eval_nums = len(response_list)
        question_list = question_list[:args.eval_nums]
        
    result,final_metrics = move_choose_metric(question_list,response_list,args)
    print(final_metrics)
    with open(f"move_choose_evaluation/{args.model_name}_final_metrics_{args.with_legal_move}_{args.eval_nums}.json","w") as f:
        json.dump(final_metrics,f,indent = 2)
        
    with open(f"move_choose_evaluation/{args.model_name}_prediction_{args.with_legal_move}_{args.eval_nums}.jsonl","w") as f:
        for line in result:
            f.write(json.dumps(line) + "\n")
    
def chess_modeling_metric(question_list,response_list):
    piece_match_num = 0
    result = []
    for i,v in enumerate(question_list):
        r = {}
        r['response'] = response_list[i]
        r['ground_truth'] = v['ground_truth']
        r['system'] = v["system"]
        r["prompt"] = v["prompt"]
        parsed_json = parse_json(r['response'])
        if parsed_json is None:
            continue
        
        pred_piece = parsed_json.get('piece',"unknown")
        pred_legal_moves = parsed_json.get("legal_moves","unknown")
        r['pred_piece'] = pred_piece.strip() if pred_piece else None
        r['gt_piece'] = v['ground_truth']['piece'].strip() if v['ground_truth']['piece'] else None
        r['pred_legal_moves'] = pred_legal_moves if pred_legal_moves else []
        r['gt_legal_moves'] = v['ground_truth']['legal_moves'] if pred_legal_moves else []
        if r['pred_legal_moves'] and r['pred_legal_moves'] != "unknown":
            for i,m in enumerate(r['pred_legal_moves']):
                r['pred_legal_moves'][i] = san_to_uci(m,v['fen'])
                
        if  r['pred_piece'] == r['gt_piece']:
            piece_match_num += 1
            set_compare = evaluate_sets(set(r['pred_legal_moves']),set(r['gt_legal_moves']))
        else:
            set_compare = {'f1_score':0,'precision':0,'recall':0}
        r['f1_score'] = set_compare['f1_score']
        r['precision'] = set_compare['precision']
        r['recall'] = set_compare['recall']
        result.append(r)
    

    final_metrics = {"piece_match_rate":piece_match_num/len(question_list),\
        "f1":sum(x['f1_score'] for x in result)/len(result),\
        "precision":sum(x['precision'] for x in result)/len(result),\
        "recall":sum(x['recall'] for x in result)/len(result),\
        "total_num":len(question_list)}

    return final_metrics,result 
            
def eval_chess_modeling(args):
    if not args.only_compute_metric:
        question_list = []
        with open("chess_modeling_evaluation/chess_modeling_evaluation.jsonl","r") as f:
            for line in f.readlines():
                question_list.append(json.loads(line))
        question_list = question_list[:args.eval_nums]
        args.with_legal_move = True
        response_list = collect_response_from_gpt(question_list,args)
    else:
        question_list = []
        with open("chess_modeling_evaluation/chess_modeling_evaluation.jsonl","r") as f:
            for line in f.readlines():
                question_list.append(json.loads(line))
        response_list = []
        with open(f"chess_modeling_evaluation/{args.model_name}_predictions_{args.eval_nums}.jsonl") as f:
            for line in f.readlines():
                response_list.append(json.loads(line)["response"])
        args.eval_nums = len(response_list)
        question_list = question_list[:args.eval_nums]
        
    final_metrics,result = chess_modeling_metric(question_list,response_list)
    print(final_metrics)
    with open(f"chess_modeling_evaluation/{args.model_name}_final_metrics_{args.eval_nums}.json","w") as f:
        json.dump(final_metrics,f,indent=2)
    with open(f"chess_modeling_evaluation/{args.model_name}_predictions_{args.eval_nums}.jsonl","w") as f:
        for line in result:
            f.write(json.dumps(line) + "\n")



import json


def eval_single_puzzle(puzzle_data, args, main_logger):
    fen = puzzle_data["FEN"]
    agent = Chess_Agent(
        fen, args.url, args.api_key, args.model_id,
        args.model_name, args.temperature, args.top_p,
        args.max_tokens, args.enable_thinking, args.is_san,
        args.max_retry,args.with_legal_move
    )
    ground_truth_moves = puzzle_data["Moves"]
    puzzle_id = puzzle_data["PuzzleId"]
    # 为每个谜题创建子logger
    puzzle_logger = logging.getLogger(f"Puzzle_{puzzle_id}")
    puzzle_logger.setLevel(main_logger.level)
    
    # 避免重复添加handler，直接使用parent logger的handler
    puzzle_logger.parent = main_logger
    puzzle_logger.propagate = True
    
    print(f"Evaluating Puzzle {puzzle_id}...")
    
    success = True
    for index in range(0, len(ground_truth_moves), 2):
        move = agent.step()
        if not move:
            puzzle_logger.error(f"Puzzle {puzzle_id} Failed.")
            success = False
            break
        
        if move == ground_truth_moves[index]:
            agent.get_opponent_move(ground_truth_moves[index+1])
        else:
            puzzle_logger.error(f"Move {move} wrong, ground truth is {ground_truth_moves[index]}")
            success = False
            break
        
    if success:
        puzzle_logger.info(f"Puzzle {puzzle_id} Solved")
    
    model_path = f"puzzles_by_rating/lite/evaluation_results/{args.model_name}/{args.rating}_{args.rating+400}/generation"
    if not os.path.exists(model_path):
        os.makedirs(model_path, exist_ok=True)
    agent.record_messages_and_response(f"{model_path}/puzzles_{puzzle_id}_san({args.is_san}_sccuess({success})).json")
    return success

def eval_puzzle_accuracy(args):
    # Load data
    with open(f"puzzles_by_rating/lite/puzzles_{args.rating}_{args.rating+400}.jsonl") as f:
        data = [json.loads(line) for line in f.readlines()][:args.eval_nums]
    # Thread-safe print lock
    # Process puzzles concurrently
    
    main_logger = setup_logger(args.model_name, args.rating)
    main_logger.info("Starting concurrent puzzle evaluation...")
    with ThreadPoolExecutor(max_workers=args.concurrency) as executor:
        futures = [
            executor.submit(eval_single_puzzle, puzzle, args, main_logger)
            for puzzle in data
        ]
        right_count = sum(future.result() for future in futures)
    accuracy = right_count / len(data)
    with open(f"puzzles_by_rating/lite/evaluation_results/{args.model_name}/{args.rating}_{args.rating+400}/final_metrics_issan({args.is_san}).json.json","w") as f:
        json.dump({"accuracy":accuracy,"right_count":right_count},f,indent=2)
    main_logger.info(f"\nFinal Accuracy: {accuracy:.2%} ({right_count}/{len(data)})")
    return accuracy
        
        
if __name__ == '__main__':
    args_parser = argparse.ArgumentParser()
    args_parser.add_argument('--max_tokens', type=int,default=2048)
    args_parser.add_argument("--eval_nums", type=int, default=200)
    args_parser.add_argument('--temperature', type=float,default=0.2)
    args_parser.add_argument('--top_p',type=float,default=1)
    args_parser.add_argument('--api_key', type=str,default="sk-va1zl4RPpU2XC43VnVfSB3marxgoTtyrUzcN5q7Pdtb9zAa5")
    args_parser.add_argument('--model_id', type=str,default="gemini-2.5-pro")
    args_parser.add_argument('--model_name', type=str,default="gemini-2.5-pro")
    args_parser.add_argument('--url', type=str,default="http://yy.dbh.baidu-int.com/v1/")
    args_parser.add_argument('--enable_thinking',action="store_true",default=False)
    args_parser.add_argument('--concurrency',type=int,default=20)
    args_parser.add_argument('--with_legal_move',action="store_true",default=False)
    args_parser.add_argument('--task',type=str,default="puzzle")
    args_parser.add_argument('--only_compute_metric',action="store_true",default=False)
    args_parser.add_argument('--parse_any_move',action="store_true",default=False)
    args_parser.add_argument('--rating',type=int,default=200)
    args_parser.add_argument('--is_san',action="store_true",default=False)
    args_parser.add_argument('--max_retry',type=int,default=5)
    args = args_parser.parse_args()
    if args.task == "chess_modeling":
        eval_chess_modeling(args)
    elif args.task == "move_choose":
        eval_move_choose(args)
    elif args.task == "puzzle":
        eval_puzzle_accuracy(args)
    else:
        print("task not supported")