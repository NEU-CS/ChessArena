import chess
import chess.engine


def analyze_position(fen_string, position):
    """
    分析棋盘上指定位置的棋子和所有合法走法
    
    Args:
        fen_string: FEN字符串，表示棋盘状态
        position: 位置字符串，如"a1", "e4"等
    
    Returns:
        dict: 包含棋子信息和合法走法的字典
    """
    # 从FEN字符串创建棋盘
    board = chess.Board(fen_string)
    
    # 将位置字符串转换为chess.Square对象
    try:
        square = chess.parse_square(position)
    except ValueError:
        return {"error": f"无效的位置: {position}"}
    
    # 获取指定位置的棋子
    piece = board.piece_at(square)
    
    # 获取所有合法走法
    legal_moves = list(board.legal_moves)
    
    # 筛选出从指定位置开始的走法
    moves_from_position = [move for move in legal_moves if move.from_square == square]
    
    # 准备返回结果
    result = {
        "position": position,
        "piece": None,
        "piece_info": None,
        "moves_from_position": [],
        "all_legal_moves": [],
        "board_info": {
            "turn": "白方" if board.turn == chess.WHITE else "黑方",
            "castling_rights": str(board.castling_rights),
            "en_passant": board.is_en_passant,
            "halfmove_clock": board.halfmove_clock,
            "fullmove_number": board.fullmove_number
        }
    }
    
    # 处理棋子信息
    if piece:
        piece_names = {
            chess.PAWN: "兵",
            chess.ROOK: "车", 
            chess.KNIGHT: "马",
            chess.BISHOP: "象",
            chess.QUEEN: "后",
            chess.KING: "王"
        }
        
        color = "白" if piece.color == chess.WHITE else "黑"
        piece_type = piece_names.get(piece.piece_type, "未知")
        
        result["piece"] = str(piece)
        result["piece_info"] = {
            "color": color,
            "type": piece_type,
            "symbol": piece.symbol(),
            "unicode": piece.unicode_symbol()
        }
    
    # 处理从该位置出发的走法
    for move in moves_from_position:
        move_info = {
            "from": chess.square_name(move.from_square),
            "to": chess.square_name(move.to_square),
            "uci": move.uci(),
            "san": board.san(move)  # 标准代数记号
        }
        
        # 添加特殊走法信息
        if move.promotion:
            promotion_pieces = {
                chess.QUEEN: "后",
                chess.ROOK: "车",
                chess.BISHOP: "象", 
                chess.KNIGHT: "马"
            }
            move_info["promotion"] = promotion_pieces.get(move.promotion, "未知")
        
        result["moves_from_position"].append(move_info)
    
    # 处理所有合法走法
    for move in legal_moves:
        move_info = {
            "from": chess.square_name(move.from_square),
            "to": chess.square_name(move.to_square),
            "uci": move.uci(),
            "san": board.san(move)
        }
        result["all_legal_moves"].append(move_info)
    
    return result

# 示例使用
if __name__ == "__main__":
    # 标准开局位置
    starting_fen = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"
    
    # 测试不同位置
    test_positions = ["a1", "e2", "d4", "h8"]
    
    for pos in test_positions:
        print(f"\n=== 分析位置 {pos} ===")
        result = analyze_position(starting_fen, pos)
        
        if "error" in result:
            print(result["error"])
            continue
            
        print(f"位置: {result['position']}")
        
        if result["piece"]:
            piece_info = result["piece_info"]
            print(f"棋子: {piece_info['color']}{piece_info['type']} ({piece_info['unicode']})")
        else:
            print("棋子: 空")
        
        print(f"从此位置的合法走法数量: {len(result['moves_from_position'])}")
        for move in result["moves_from_position"][:5]:  # 只显示前5个
            print(f"  {move['san']} ({move['from']} -> {move['to']})")
        
        print(f"总合法走法数量: {len(result['all_legal_moves'])}")
        print(f"当前轮到: {result['board_info']['turn']}")

    # 测试一个复杂的中局位置
    print("\n=== 测试复杂位置 ===")
    complex_fen = "r1bqkb1r/pppp1ppp/2n2n2/4p3/2B1P3/3P1N2/PPP2PPP/RNBQK2R w KQkq - 0 4"
    
    result = analyze_position(complex_fen, "f3")
    print(f"位置 f3 的棋子: {result['piece_info']['color'] if result['piece'] else '空'}{result['piece_info']['type'] if result['piece'] else ''}")
    print(f"从 f3 的合法走法:")
    for move in result["moves_from_position"]:
        print(f"  {move['san']}")