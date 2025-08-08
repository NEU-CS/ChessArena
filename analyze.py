import json
import chess
from stockfish import get_best_moves_and_evaluate
from utils import remove_all_empty_lines,sp_blitz as sp,sp_chess_modeling,get_random_piece_position_by_color,\
get_random_empty_position,get_piece_and_legal_moves,parse_side_to_move_from_fen

def analyze_fen_jsonl(input_file, output_file, stockfish_path="./stockfish-8-linux/Linux/stockfish_8_x64", depth=20, resume=True):
    """
    读取JSONL文件中的FEN棋盘，使用Stockfish分析并写入新的JSONL文件
    支持断点续传功能
    
    Parameters:
    - input_file: 输入JSONL文件路径
    - output_file: 输出JSONL文件路径
    - stockfish_path: Stockfish可执行文件路径
    - depth: 分析深度
    - resume: 是否启用断点续传模式
    """
    import os
    
    # 检查输出文件是否存在，确定已处理的行数
    processed_lines = 0
    processed_data = []
    
    if resume and os.path.exists(output_file):
        print("检测到输出文件已存在，启用断点续传模式...")
        with open(output_file, 'r', encoding='utf-8') as existing_file:
            for line in existing_file:
                if line.strip():
                    processed_data.append(json.loads(line.strip()))
                    processed_lines += 1
        print(f"已处理的行数: {processed_lines}")
    
    # 读取输入文件的所有数据
    input_data = []
    with open(input_file, 'r', encoding='utf-8') as infile:
        for line in infile:
            if line.strip():
                input_data.append(json.loads(line.strip()))
    
    total_lines = len(input_data)
    print(f"输入文件总行数: {total_lines}")
    
    # 如果启用断点续传，检查是否需要重新分析
    if resume and processed_lines > 0:
        # 验证已处理的数据是否完整
        for i in range(min(processed_lines, len(input_data))):
            input_item = input_data[i]
            processed_item = processed_data[i] if i < len(processed_data) else {}
            
            # 检查这一行是否已经完整分析过
            if ('legal_moves' in processed_item and 'top_moves' in processed_item and 
                processed_item.get('FEN') == input_item.get('FEN')):
                continue
            else:
                # 发现不完整的分析，从这一行重新开始
                processed_lines = i
                processed_data = processed_data[:i]
                print(f"发现第{i+1}行分析不完整，从此行重新开始分析")
                break
    
    # 以追加模式打开输出文件（如果是新文件则创建）
    mode = 'a' if (resume and processed_lines > 0) else 'w'
    with open(output_file, mode, encoding='utf-8') as outfile:
        # 如果是全新开始，需要写入已处理的数据
        if mode == 'w' and processed_data:
            for data in processed_data:
                outfile.write(json.dumps(data, ensure_ascii=False) + '\n')
        
        # 从未处理的行开始分析
        for line_num in range(processed_lines, total_lines):
            try:
                data = {}  
                fen = input_data[line_num]['FEN']
                is_white = parse_side_to_move_from_fen(fen)
                if is_white:
                    is_white = True if is_white == "white" else False
                print(f"处理第{line_num+1}行 (剩余 {total_lines-line_num-1} 行)，FEN: {fen[:50]}...")
                
                # 检查是否已经分析过（防止重复分析）
                if 'legal_moves' in data and 'top_moves' in data:
                    print(f"  - 第{line_num+1}行已分析过，跳过")
                    outfile.write(json.dumps(data, ensure_ascii=False) + '\n')
                    continue
                
                # 创建棋盘
                try:
                    board = chess.Board(fen)
                except ValueError as e:
                    print(f"错误：第{line_num+1}行FEN格式无效: {e}")
                    # 保留原数据，添加错误信息
                    data['analysis_error'] = f"Invalid FEN: {str(e)}"
                    outfile.write(json.dumps(data, ensure_ascii=False) + '\n')
                    continue
                
                # 获取所有合法走法
                legal_moves = []
                for move in board.legal_moves:
                    legal_moves.append(move.uci())
                
                # 获取前3个最佳走法及其胜率
                try:
                    top_moves_data, _ = get_best_moves_and_evaluate(
                        board=board,
                        stockfish_path=stockfish_path,
                        n=100,
                        depth=depth
                    )
                    
                    top_moves = []
                    for move, win_rate in top_moves_data:
                        top_moves.append(move.uci())
                
                except Exception as e:
                    print(f"错误：第{line_num+1}行Stockfish分析失败: {e}")
                    # 保留原数据，添加错误信息
                    data['analysis_error'] = f"Stockfish analysis failed: {str(e)}"
                    outfile.write(json.dumps(data, ensure_ascii=False) + '\n')
                    continue
                legal_moves_str = ""
                if legal_moves:
                    legal_moves_str = f"Legal moves in UCI notation: {', '.join(legal_moves)}"
                # 添加分析结果到原数据
                data["FEN"] = fen
                data["system"] = sp(is_white)
                data["prompt"] = remove_all_empty_lines(f"""
Current board position in FEN notation:
{fen}
{legal_moves_str}
""")             
                data["prompt_without_legal_moves"] = remove_all_empty_lines(f"""
Current board position in FEN notation:
{fen}
""")
                data['legal_moves'] = legal_moves
                data['top_moves'] = top_moves
                # 写入输出文件并立即刷新缓冲区
                outfile.write(json.dumps(data, ensure_ascii=False) + '\n')
                outfile.flush()  # 确保数据立即写入文件
                print(f"  ✓ 合法走法数量: {len(legal_moves)}")
                if top_moves:
                    print(f"  ✓ 最佳走法: {top_moves}")
                
                # 每处理10行显示进度
                if (line_num + 1) % 10 == 0:
                    progress = (line_num + 1) / total_lines * 100
                    print(f"进度: {line_num+1}/{total_lines} ({progress:.1f}%)")
                
            except json.JSONDecodeError as e:
                print(f"错误：第{line_num+1}行JSON格式无效: {e}")
                continue
            except Exception as e:
                print(f"错误：处理第{line_num+1}行时发生未知错误: {e}")
                continue
def get_analysis_status(input_file, output_file):
    """
    检查分析进度状态
    
    Parameters:
    - input_file: 输入文件路径
    - output_file: 输出文件路径
    
    Returns:
    - 包含进度信息的字典
    """
    import os
    
    if not os.path.exists(input_file):
        return {"error": "输入文件不存在"}
    
    # 统计输入文件行数
    input_lines = 0
    with open(input_file, 'r', encoding='utf-8') as f:
        for line in f:
            if line.strip():
                input_lines += 1
    
    # 统计输出文件行数和完成情况
    output_lines = 0
    completed_lines = 0
    error_lines = 0
    
    if os.path.exists(output_file):
        with open(output_file, 'r', encoding='utf-8') as f:
            for line in f:
                if line.strip():
                    output_lines += 1
                    try:
                        data = json.loads(line.strip())
                        if 'analysis_error' in data:
                            error_lines += 1
                        elif 'legal_moves' in data and 'top_moves' in data:
                            completed_lines += 1
                    except:
                        pass
    
    progress = (output_lines / input_lines * 100) if input_lines > 0 else 0
    
    return {
        "input_lines": input_lines,
        "output_lines": output_lines,
        "completed_lines": completed_lines,
        "error_lines": error_lines,
        "remaining_lines": input_lines - output_lines,
        "progress_percent": round(progress, 2),
        "can_resume": output_lines > 0 and output_lines < input_lines
    }

# 使用示例
if __name__ == "__main__":
    # 设置文件路径
    input_file = "puzzles_by_rating/lite/all_rating_puzzles.jsonl"  # 输入文件路径
    output_file = "puzzles_by_rating/lite/grpo_data_continue.jsonl"  # 输出文件路径
    stockfish_path = "./stockfish-8-linux/Linux/stockfish_8_x64"  # Stockfish路径
    
    # 检查分析状态
    status = get_analysis_status(input_file, output_file)
    print("=== 分析状态 ===")
    print(f"输入文件行数: {status.get('input_lines', 0)}")
    print(f"已处理行数: {status.get('output_lines', 0)}")
    print(f"成功分析行数: {status.get('completed_lines', 0)}")
    print(f"错误行数: {status.get('error_lines', 0)}")
    print(f"剩余行数: {status.get('remaining_lines', 0)}")
    print(f"进度: {status.get('progress_percent', 0)}%")
    print(f"可以断点续传: {'是' if status.get('can_resume', False) else '否'}")
    print("=" * 20)
    
    # 执行分析（启用断点续传）
    print("开始分析JSONL文件...")
    analyze_fen_jsonl(
        input_file=input_file,
        output_file=output_file,
        stockfish_path=stockfish_path,
        depth=20,  # 可以根据需要调整深度
        resume=True  # 启用断点续传
    )
    print("分析完成！")
    
    # 显示最终状态
    final_status = get_analysis_status(input_file, output_file)
    print("\n=== 最终状态 ===")
    print(f"总计处理: {final_status.get('output_lines', 0)} 行")
    print(f"成功分析: {final_status.get('completed_lines', 0)} 行")
    print(f"错误行数: {final_status.get('error_lines', 0)} 行")
    print(f"完成率: {final_status.get('progress_percent', 0)}%")