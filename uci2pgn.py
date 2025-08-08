import chess
import chess.pgn
from datetime import datetime
import json
from utils import uci_to_pgn,save_pgn_to_file

if __name__ == '__main__':

    uci_moves = [
        "e2e4",
        "b8c6",
        "g1f3",
        "g8f6",
        "f1b5",
        "f6h5",
        "d2d4",
        "h7h6",
        "d4d5",
        "g7g6",
        "d5c6",
        "f8g7",
        "c6d7",
        "d8d7",
        "b5d7",
        "e8d8",
        "b1c3",
        "g7f6",
        "d1d6",
        "f6g7",
        "d7e8",
        "d8e8",
        "d6d8",
        "e8d8",
        "c3d5",
        "g7f6",
        "d5f6",
        "e7f6",
        "c1g5",
        "d8e7",
        "g5f6",
        "e7f8",
        "f6d8",
        "f8g7",
        "d8e7",
        "g7h7",
        "e7f6",
        "h7g8",
        "f6g7",
        "g8h7",
        "g7h8",
        "h7g8",
        "h8g7",
        "g8h7",
        "g7h8",
        "h7g8",
        "h8g7",
        "g8h7",
        "g7h8",
        "h7g8",
        "h8g7",
        "g8h7",
        "g7h8",
        "h7g8",
        "h8g7",
        "g8h7",
        "g7h8"
    ]
    pgn_content = uci_to_pgn(uci_moves, event="我的比赛", white="我", black="对手")
    save_pgn_to_file(pgn_content, "my_game.pgn")