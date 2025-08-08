import re
import json
import os
from datetime import datetime
from typing import Dict, List, Optional

def catch_data():
    first_layer = os.path.join('./')
    all_datas = []
    top_1_cnt = 0
    top_2_cnt = 0
    top_3_cnt = 0
    all_cnt = 0
    answer = set()
    not_include_path = []
    for onedir in os.listdir(first_layer):
        second_layer = os.path.join(first_layer,onedir)
        if not os.path.isdir(second_layer):
            continue
        
        for twodir in os.listdir(second_layer):
            third_layer = os.path.join(second_layer,twodir)
            if not os.path.isdir(third_layer):
                continue
            
            for threedir in os.listdir(third_layer):
                fourth_layer = os.path.join(third_layer,threedir)
                if not os.path.isdir(fourth_layer):
                    continue
                
                for fourdir in os.listdir(fourth_layer):
                    fifth_layer = os.path.join(fourth_layer,fourdir)
                    if not os.path.isdir(fifth_layer):
                        continue
                    

                    
                    flag = False
                    for fivedir in os.listdir(fifth_layer):
                        sixth_layer = os.path.join(fifth_layer,fivedir)
                        if sixth_layer.endswith('json'):
                            #print(sixth_layer)
                            all_cnt += 1
                            with open(sixth_layer,"r") as f:
                                game_json = json.loads(f.read())
                                move_detailes = game_json["move_details"]
                                for onemove in move_detailes:
                                    if onemove.get("chat_history",None) and onemove.get("fen_after",None):
                                        flag = True
                                        one_item = {}
                                        one_item["white_player"] = game_json["white_player"]
                                        one_item["black_player"] = game_json["black_player"]
                                        one_item["fen_before"] = onemove["fen_before"]
                                        one_item["fen_after"] = onemove["fen_after"]
                                        one_item["color"] = onemove["color"]
                                        if "random" in onemove["player"] or "maia" in onemove["player"]:
                                            continue
                                        one_item["move_ranking"] = int(onemove["move_ranking"]) if onemove["move_ranking"] is not None else -1
                                        one_item["question"] = onemove["chat_history"][0][:-1]
                                        one_item["answer"] = onemove["chat_history"][0][-1]
                                        #print(onemove["chat_history"][0][-1])
                                        one_item["top_moves"] = [x[0] for x in onemove["top_moves"]]
                                        if onemove["chat_history"][0][-1]["status"] == "successful move":
                                            question_plus_answer = ''.join([x['content'] for x in [one_item["answer"]]])
                                            if question_plus_answer in answer:
                                                continue
                                            answer.add(question_plus_answer)
                                            all_datas.append(one_item)
                                            if one_item["move_ranking"] == 1:
                                                top_1_cnt += 1
                                            elif one_item["move_ranking"] == 2:
                                                top_2_cnt += 1
                                            elif one_item["move_ranking"] == 3:
                                                top_3_cnt += 1
                    
                    if not flag:
                        for fivedir in os.listdir(fifth_layer):
                            sixth_layer = os.path.join(fifth_layer,fivedir)
                            if sixth_layer.endswith('log'):
                                not_include_path.append(sixth_layer)
                    
    print(top_1_cnt,top_2_cnt,top_3_cnt,all_cnt)
    print(len(all_datas))
    with open("all_data.jsonl","w") as f:
        for data in all_datas:
            f.write(json.dumps(data))
            f.write("\n")
    
    with open("not_include_path.json","w") as f:
        json.dump(not_include_path,f,indent=2)


class ChessLogParser:
    def __init__(self):
        self.parsed_data = []
        self.top_1_ranking = 0
        self.top_2_ranking = 0
        self.top_3_ranking = 0
        self.all_cnt = 0
    
    def clean_logger_info(self, text: str) -> str:
        """移除文本中的logger相关信息"""
        # 移除时间戳和INFO标记
        text = re.sub(r'\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2},\d{3} - INFO - ', '', text)
        return text.strip()
    
    def load_logcontent(self,filepath:str):
        with open(filepath,'r',encoding='utf-8') as f:
            self.log_content = f.read()
        self.parsed_data = self.parse_prompt_response_pairs()

    
    def parse_prompt_response_pairs(self) -> List[Dict]:
        """解析Prompt-Response配对"""
        # 查找所有prompt到response的完整段落
        #prompt_response_pattern = r'(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2},\d{3}) - INFO - Prompt to (?P<color>.+?) \((?P<player>.+?)\):(?P<prompt>.*?)(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2},\d{3}) - INFO - Raw response from (.+?)(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2},\d{3}) - INFO - Valid move found: [a-h][1-8][a-h][1-8](?:[qrbnQRBN]).*(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2},\d{3}) - INFO - (Move .+ is Stockfish\'s recommendation #(?P<ranking>\d+)|Move .+ is (?P<not_ranking>not among) Stockfish\'s top 3 recommendations)'
        prompt_response_pattern = r'(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2},\d{3}) - INFO - Prompt to (?P<color>.+?) \((?P<player>.+?)\):(?P<prompt>.*?)(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2},\d{3}) - INFO - Raw response from (.+?) \((.+?)\) \(took ([\d.]+)s\):\n(?P<response>.*?)(?=\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2},\d{3}.*?INFO.*?(?:Valid move).*?)(?=\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2},\d{3}.*?INFO.*?(Move .+? is Stockfish\'s recommendation #(?P<ranking>\d)|Move .+? is (?P<not_ranking>not among) Stockfish\'s top 3 recommendations))'
        matches = re.finditer(prompt_response_pattern, self.log_content, re.MULTILINE | re.DOTALL)
        pairs = []
        for match in matches:
            prompt_player = match.group('color')
            prompt_model = match.group('player')
            prompt_content = match.group('prompt')
            response_content = match.group('response')
            move_ranking  = match.group('ranking')
            #print(response_content)
            if len(response_content) < 20:
                continue
            if "maia" in prompt_model or "random" in prompt_model:
                continue
            # 清理prompt内容
            #prompt_content = self.clean_logger_info(prompt_content)
            
            # 解析prompt - 检查是否有多轮对话
            prompt_parts = self.parse_multi_turn_prompt(prompt_content)
            
            # 清理response内容
            response_content = self.clean_logger_info(response_content)        
            pair = {
                'player': prompt_player,
                'model': prompt_model,
                'question': prompt_parts,
                'answer': response_content,
                'move_ranking': move_ranking
            }
            
            if move_ranking:
                if int(move_ranking) == 1:
                    self.top_1_ranking += 1
                elif int(move_ranking) == 2:
                    self.top_2_ranking += 1
                elif int(move_ranking) == 3:
                    self.top_3_ranking += 1
            pairs.append(pair)
        
        return pairs
    
    def parse_multi_turn_prompt(self, prompt_content: str) -> List[Dict]:
        """解析多轮对话prompt"""
        # 按空行分割prompt内容
        sections = [section.strip() for section in re.split(r'\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2},\d{3} - INFO - ',prompt_content) if section.strip()]
        prompt_parts = []
        count = 0
        for i, section in enumerate(sections):
            # 跳过logger相关的行
            if 'INFO -' in section or 'Attempt' in section:
                continue
            
            # 第一段通常是system prompt
            if count == 0:
                prompt_parts.append({
                    'role': 'system',
                    'content': section
                })
            else:
                if (count - 1) % 2 == 0:
                    prompt_parts.append({
                        'role': 'user',
                        'content': section
                    })
                else:
                    prompt_parts.append({
                        'role': 'assistant',
                        'content': section
                    })
            count += 1
        
        return prompt_parts
    
    def save_to_jsonl(self, filename: str):
        """保存结果为JSONL格式"""
        with open(filename, 'w', encoding='utf-8') as f:
            for item in self.parsed_data:
                f.write(json.dumps(item, ensure_ascii=False) + '\n')
    
    def add_to_jsonl(self, filename: str):
        """保存结果为JSONL格式"""
        with open(filename, 'a+', encoding='utf-8') as f:
            for item in self.parsed_data:
                f.write(json.dumps(item, ensure_ascii=False) + '\n')
    
        

def catch_log():
    parser = ChessLogParser()
    with open("not_include_path.json","r") as f:
        path_list = json.loads(f.read())
    for sixth_layer in path_list:
        print(sixth_layer)
        parser.load_logcontent(sixth_layer)
        parser.add_to_jsonl("chess_game.jsonl")
        print(parser.top_1_ranking,parser.top_2_ranking,parser.top_3_ranking)

if __name__ == '__main__':
    catch_data()
    #catch_log()