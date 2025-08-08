import re
import chess
import random
import json
import requests
import time
import copy
import datetime
def parse_json(content):
    """Parse json data from LLM response."""
    pattern = re.compile(r"```json(.*?)```",re.DOTALL)
    jsons = pattern.findall(content)
    try:
        if jsons:
            return json.loads(jsons[-1])
    except:
        pass
    return {}
def parse_uci_move(content,static_eval=False):
    """Parse UCI chess move from LLM response."""
    # 找到所有匹配项，取最后一个
    moves = re.findall(r'```\s*([a-h][1-8][a-h][1-8](?:[qrbnQRBN])?)\s*```', content, re.DOTALL)
    if moves:
        return moves[-1]  # 返回最后一个匹配项
    if static_eval:
        moves = re.findall(r'\s*([a-h][1-8][a-h][1-8](?:[qrbnQRBN])?)\s*', content, re.DOTALL) #去除```的影响
        if moves:
            return moves[-1]

def parse_san_move(content,static_eval=False):
    """Parse SAN chess move from LLM response."""
    pattern = r'```\s*(?P<move>O-O-O|O-O|[KQRBN]?[a-h]?[1-8]?x?[a-h][1-8](?:=[KQRBN])?[+#]?)\s*```'
    move_match = re.findall(pattern, content, re.DOTALL)
    if move_match:
        return move_match[-1]
    if static_eval:
        move_match = re.findall(r'\s*(?P<move>O-O-O|O-O|[KQRBN]?[a-h]?[1-8]?x?[a-h][1-8](?:=[KQRBN])?[+#]?)\s*', content, re.DOTALL)
        if move_match:
            return move_match[-1]


def san_to_uci(san_move, board_position=None):
    """
    将SAN格式转换为UCI格式
    
    Args:
        san_move: SAN格式的走法，如 "Nf3", "exd5", "O-O"
        board_position: 棋盘位置，如果None则使用初始位置
    
    Returns:
        UCI格式的走法，如 "g1f3", "e5d5", "e1g1"
    """
    if type(san_move) != str:
        san_move = str(san_move)
    if board_position is None:
        board = chess.Board()  # 使用初始位置
    else:
        board = chess.Board(fen=board_position)  # 使用指定位置
    
    try:
        # 解析SAN走法
        move = board.parse_san(san_move)
        # 转换为UCI格式
        return move.uci()
    except Exception as e:
        raise Exception(f"Error parsing SAN move: {san_move}") from e

def uci_to_san(uci_move, board_position=None):
    """
    将UCI格式转换为SAN格式
    
    Args:
        uci_move: UCI格式的走法，如 "g1f3", "e2e4"
        board_position: 棋盘位置，如果None则使用初始位置
    
    Returns:
        SAN格式的走法，如 "Nf3", "e4"
    """
    if type(uci_move) != str:
        uci_move = str(uci_move)
    if board_position is None:
        board = chess.Board()  # 使用初始位置
    else:
        board = chess.Board(fen=board_position)  # 使用指定位置
    
    try:
        # 解析UCI走法
        move = chess.Move.from_uci(uci_move)
        # 转换为SAN格式
        return board.san(move)
    except Exception as e:
        raise Exception(f"Error parsing UCI move: {uci_move}") from e