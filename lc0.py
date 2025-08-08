import chess
import chess.engine
import math
import os

class lc0_engine:
    def __init__(self,engine_path="./lc0/release/lc0",weights_path="./lc0/release/maia_weights/maia-1100.pb.gz"):
        # 配置路径
        # 启动引擎
        self.engine = chess.engine.SimpleEngine.popen_uci(engine_path)
        # 配置 CPU 优化参数
        config = {
            "WeightsFile": weights_path,
            "Backend": "eigen",  # 或 "eigen" 如果 BLAS 有问题
            "Threads": "4",     # 根据 CPU 核心数调整
            "NNCacheSize": "200000"
        }
        self.engine.configure(config)
    
    def predict_move(self, board, time_limit = 2.0):
        result = self.engine.play(board, chess.engine.Limit(time=time_limit))
        return result.move.uci()
        
    def quit_engine(self):
        self.engine.quit()

if __name__ == '__main__':
    e = lc0_engine()
    board = chess.Board()
    print(e.predict_move(board))
    e.quit_engine()