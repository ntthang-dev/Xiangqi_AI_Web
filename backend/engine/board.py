# File: backend/engine/board.py
# Version: V15.1 - Ít thay đổi, chủ yếu đảm bảo tính nhất quán

import copy

GENERAL = 'General'
ADVISOR = 'Advisor'
ELEPHANT = 'Elephant'
HORSE = 'Horse'
CHARIOT = 'Chariot'
CANNON = 'Cannon'
PAWN = 'Pawn'

class XiangqiBoard:
    INITIAL_BOARD_DATA = [ 
        ['r', 'h', 'e', 'a', 'k', 'a', 'e', 'h', 'r'], 
        [None,None,None,None,None,None,None,None,None], 
        [None,'c',None,None,None,None,None,'c',None], 
        ['p',None,'p',None,'p',None,'p',None,'p'],    
        [None,None,None,None,None,None,None,None,None], 
        [None,None,None,None,None,None,None,None,None], 
        ['P',None,'P',None,'P',None,'P',None,'P'],    
        [None,'C',None,None,None,None,None,'C',None], 
        [None,None,None,None,None,None,None,None,None], 
        ['R', 'H', 'E', 'A', 'K', 'A', 'E', 'H', 'R']  
    ]
    PIECE_INFO = { 
        'K': {'type': GENERAL, 'color': 'red'}, 'A': {'type': ADVISOR, 'color': 'red'},
        'E': {'type': ELEPHANT, 'color': 'red'}, 'H': {'type': HORSE, 'color': 'red'},
        'R': {'type': CHARIOT, 'color': 'red'}, 'C': {'type': CANNON, 'color': 'red'},
        'P': {'type': PAWN, 'color': 'red'},
        'k': {'type': GENERAL, 'color': 'black'}, 'a': {'type': ADVISOR, 'color': 'black'},
        'e': {'type': ELEPHANT, 'color': 'black'}, 'h': {'type': HORSE, 'color': 'black'},
        'r': {'type': CHARIOT, 'color': 'black'}, 'c': {'type': CANNON, 'color': 'black'},
        'p': {'type': PAWN, 'color': 'black'}
    }
    PIECE_ORDER_FOR_COUNT = ['K', 'A', 'E', 'H', 'R', 'C', 'P', 'k', 'a', 'e', 'h', 'r', 'c', 'p']


    def __init__(self, board_state_list_of_lists=None):
        self.rows = 10
        self.cols = 9
        # Thêm thuộc tính để AIPlayer có thể lưu số nước đi hiện tại của ván cờ vào board
        # Điều này hữu ích cho hàm get_game_progress_score trong Evaluation
        self.current_half_move_count = 0 
        
        if board_state_list_of_lists:
            self.set_board_state(copy.deepcopy(board_state_list_of_lists))
        else:
            self.board = copy.deepcopy(self.INITIAL_BOARD_DATA)

    def set_board_state(self, board_state_list_of_lists):
        # --- Giữ nguyên logic từ V14.1 ---
        if not isinstance(board_state_list_of_lists, list) or \
           len(board_state_list_of_lists) != self.rows:
            self.board = copy.deepcopy(self.INITIAL_BOARD_DATA)
            return

        processed_board = []
        for r_idx, row_data in enumerate(board_state_list_of_lists):
            if not isinstance(row_data, list) or len(row_data) != self.cols:
                self.board = copy.deepcopy(self.INITIAL_BOARD_DATA)
                return
            processed_row = [None if piece == 'null' or piece is None or str(piece).strip() == "" else str(piece) for piece in row_data]
            processed_board.append(processed_row)
        self.board = processed_board


    def get_piece_at(self, r, c):
        # --- Giữ nguyên logic từ V14.1 ---
        if 0 <= r < self.rows and 0 <= c < self.cols:
            return self.board[r][c]
        return None 

    def get_piece_color(self, piece_char): # Ít dùng, thường dùng PIECE_INFO
        info = self.PIECE_INFO.get(piece_char)
        return info['color'] if info else None

    def get_piece_type(self, piece_char): # Ít dùng, thường dùng PIECE_INFO
        info = self.PIECE_INFO.get(piece_char)
        return info['type'] if info else None

    def make_move(self, from_sq, to_sq): 
        # --- Giữ nguyên logic từ V14.1 ---
        r1, c1 = from_sq; r2, c2 = to_sq
        if not (0 <= r1 < self.rows and 0 <= c1 < self.cols and \
                0 <= r2 < self.rows and 0 <= c2 < self.cols):
            # print(f"Lỗi make_move: Tọa độ không hợp lệ from {from_sq} to {to_sq}")
            return "Error: Invalid coordinates" 
        
        piece_to_move = self.board[r1][c1]
        if not piece_to_move: 
            # print(f"Lỗi make_move: Không có quân ở {from_sq}")
            return "Error: No piece at source"
            
        captured_piece = self.board[r2][c2]
        self.board[r2][c2] = piece_to_move
        self.board[r1][c1] = None
        return captured_piece 

    def unmake_move(self, from_sq, to_sq, moved_piece_char, captured_piece_char):
        # --- Giữ nguyên logic từ V14.1 ---
        r1, c1 = from_sq; r2, c2 = to_sq
        self.board[r1][c1] = moved_piece_char  
        self.board[r2][c2] = captured_piece_char 

    def __str__(self):
        # --- Giữ nguyên logic từ V14.1 ---
        board_str = ""
        for r_idx, row in enumerate(self.board):
            row_str = []
            for piece in row:
                row_str.append(piece if piece else ".")
            board_str += " ".join(row_str) + f"  # Hàng {r_idx}\n"
        return board_str

    def to_tuple(self, board_data=None):
        # --- Giữ nguyên logic từ V14.1 ---
        target_board = board_data if board_data is not None else self.board
        return tuple(map(tuple, target_board))

    def convert_to_fen(self, player_to_move_color, fullmove_number=1, halfmove_clock=0):
        # --- Giữ nguyên logic từ V14.1 ---
        fen_rows = []
        for r in range(self.rows): 
            empty_count = 0
            fen_row_str = ""
            for c in range(self.cols): 
                piece = self.board[r][c]
                if piece is None:
                    empty_count += 1
                else:
                    if empty_count > 0:
                        fen_row_str += str(empty_count)
                        empty_count = 0
                    fen_row_str += piece 
            if empty_count > 0: 
                fen_row_str += str(empty_count)
            fen_rows.append(fen_row_str)
        
        board_fen_part = "/".join(fen_rows)
        player_char = 'w' if player_to_move_color == 'red' else 'b' 
        castling_availability = "-" # Cờ tướng không có nhập thành
        en_passant_target = "-"   # Cờ tướng không có bắt tốt qua đường
        return f"{board_fen_part} {player_char} {castling_availability} {en_passant_target} {halfmove_clock} {fullmove_number}"


    @staticmethod
    def fen_to_board_array(fen_string):
        # --- Giữ nguyên logic từ V14.1 ---
        try:
            parts = fen_string.split(' ')
            board_fen_part = parts[0]
            fen_rows = board_fen_part.split('/')

            if len(fen_rows) != 10: 
                raise ValueError("FEN không hợp lệ: Sai số hàng.")

            board_array = []
            for fen_row_str in fen_rows:
                current_row = []
                for char_in_fen_row in fen_row_str:
                    if char_in_fen_row.isdigit():
                        current_row.extend([None] * int(char_in_fen_row))
                    else:
                        if char_in_fen_row not in XiangqiBoard.PIECE_INFO:
                             raise ValueError(f"FEN không hợp lệ: Ký tự quân không xác định '{char_in_fen_row}'")
                        current_row.append(char_in_fen_row)
                
                if len(current_row) != 9: 
                    raise ValueError(f"FEN không hợp lệ: Sai số cột trong hàng '{fen_row_str}'")
                board_array.append(current_row)
            
            player_to_move = 'red' if parts[1] == 'w' else 'black'
            # halfmove_clock và fullmove_number có thể không quan trọng bằng FEN cờ vua
            halfmove = int(parts[4]) if len(parts) > 4 and parts[4].isdigit() else 0
            fullmove = int(parts[5]) if len(parts) > 5 and parts[5].isdigit() else 1

            return board_array, player_to_move, halfmove, fullmove
        except Exception as e:
            # print(f"Lỗi khi parse FEN: {e}, FEN: {fen_string}")
            return None, None, 0, 1

    def get_piece_counts(self):
        # --- Giữ nguyên logic từ V14.1 ---
        counts = {color: {ptype: 0 for ptype in [GENERAL, ADVISOR, ELEPHANT, HORSE, CHARIOT, CANNON, PAWN]} for color in ['red', 'black']}
        for r in range(self.rows):
            for c in range(self.cols):
                piece_char = self.board[r][c]
                if piece_char:
                    info = self.PIECE_INFO.get(piece_char)
                    if info:
                        counts[info['color']][info['type']] += 1
        return counts

    def check_piece_count_legality(self):
        # --- Giữ nguyên logic từ V14.1 ---
        counts = self.get_piece_counts()
        expected_max = {
            GENERAL: 1, ADVISOR: 2, ELEPHANT: 2,
            HORSE: 2, CHARIOT: 2, CANNON: 2, PAWN: 5
        }
        for color in ['red', 'black']:
            for piece_type, count in counts[color].items():
                if count > expected_max[piece_type]:
                    return False, f"Lỗi số lượng quân: {color} có {count} {piece_type} (tối đa {expected_max[piece_type]})"
        return True, "Số lượng quân hợp lệ."

