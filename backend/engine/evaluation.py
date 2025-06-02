# File: backend/engine/evaluation.py
# Version: V15.0 - Giá trị quân liên tục, an toàn quân, gợi ý tích hợp sách

from .board import GENERAL, PAWN, ADVISOR, ELEPHANT, HORSE, CHARIOT, CANNON 
from .rules import GameRules # Giả sử GameRules sẽ có thêm is_square_protected

class Evaluation:
    def __init__(self, game_rules_instance, book_knowledge_instance=None): # Thêm book_knowledge
        self.rules = game_rules_instance 
        self.board_instance = self.rules.board_instance 
        self.book_knowledge = book_knowledge_instance # Lưu trữ tham chiếu
        self.CHECKMATE_SCORE = 100000 
        self.STALEMATE_SCORE = 0 

        # Giá trị quân cờ CƠ BẢN (điểm neo)
        self.PIECE_BASE_VALUES_OPENING = {
            'R': 900, 'H': 400, 'C': 500, 'A': 200, 'E': 200, 'P': 100 
        }
        self.PIECE_BASE_VALUES_MIDGAME = {
            'R': 900, 'H': 450, 'C': 500, 'A': 250, 'E': 250, 'P': 150 # Giá trị Tốt ở trung cuộc (chưa qua sông)
        }
        self.PIECE_BASE_VALUES_ENDGAME = {
            'R': 1000, 'H': 500, 'C': 450, 'A': 250, 'E': 250, 'P': 200 # Giá trị Tốt ở tàn cuộc (chưa qua sông)
        }
        
        # Hệ số cho Tốt đã qua sông và tiến sâu (nhân với giá trị Tốt cơ bản của giai đoạn đó)
        self.PAWN_ADVANCEMENT_MODIFIERS = { 
            'crossed_river_shallow': 1.5, # Mới qua sông
            'crossed_river_middle': 2.0,  # Giữa lãnh thổ địch
            'crossed_river_deep': 2.8,    # Gần cung
            'promotion_threat': 4.0     # Sát đáy, đe dọa phong cấp (nếu có luật phong cấp)
                                        # Trong cờ tướng không có phong cấp, nhưng Tốt đáy rất mạnh
        }

        # --- Piece-Square Tables (PST) ---
        # Cần rà soát và tinh chỉnh kỹ các PST này để phản ánh vai trò quân
        # Giá trị dương tốt cho Đỏ.
        self.CHARIOT_PST_RED = [ # Xe Đỏ
            [10, 10, 12, 20, 20, 20, 12, 10, 10], # Hàng 0 (đáy Đen) - Xe Đỏ ở đây rất mạnh
            [ 8, 12, 15, 25, 25, 25, 15, 12,  8],
            [ 5,  8, 10, 20, 20, 20, 10,  8,  5],
            [ 0,  5,  8, 15, 15, 15,  8,  5,  0], # Qua sông
            [-2,  0,  5, 10, 10, 10,  5,  0, -2], # Sông
            [-5, -2,  0,  5,  5,  5,  0, -2, -5],
            [-5,  0,  0,  0,  0,  0,  0,  0, -5],
            [ 0,  0,  0,  0,  0,  0,  0,  0,  0], # Hàng nhà
            [ 0,  0,  0, -2, -2, -2,  0,  0,  0], # Tránh Xe ở vị trí xuất phát quá lâu
            [-2,  0,  0,  0,  0,  0,  0,  0, -2] 
        ]
        self.CHARIOT_PST_BLACK = [[-x for x in row] for row in reversed(self.CHARIOT_PST_RED)]

        self.CANNON_PST_RED = [ # Pháo Đỏ
            [  0,   0,  -5,  -5, -10,  -5,  -5,   0,   0], 
            [  0,   2,   0,   5,   8,   5,   0,   2,   0],
            [  0,   0,   5,  10,  15,  10,   5,   0,   0], # Tuyến cung thành địch
            [  5,   5,  10,  20,  25,  20,  10,   5,   5], # Hàng Tốt địch
            [ 10,  10,  15,  25,  30,  25,  15,  10,  10], # Trung tâm, có ngòi tốt
            [  5,   8,  12,  20,  25,  20,  12,   8,   5], 
            [  0,   0,   0,  10,  15,  10,   0,   0,   0], # Tuyến Tốt nhà
            [  0,   0,   0,   5,   5,   5,   0,   0,   0], # Tuyến Pháo nhà (cần có ngòi)
            [ -5,  -5,   0,   0,   0,   0,   0,  -5,  -5], 
            [-10, -10,  -5,  -5,  -5,  -5,  -5, -10, -10]  
        ]
        self.CANNON_PST_BLACK = [[-x for x in row] for row in reversed(self.CANNON_PST_RED)]

        self.HORSE_PST_RED = [ # Mã Đỏ
            [-10, -5,  5, 15, 10, 15,  5, -5,-10], 
            [ -5,  5, 10, 20, 25, 20, 10,  5, -5], # Vị trí tốt để tấn công
            [  5, 10, 20, 25, 30, 25, 20, 10,  5], # Ngoạ tào, quải giác tiềm năng
            [  0,  8, 15, 20, 25, 20, 15,  8,  0], 
            [ -5,  5, 10, 15, 20, 15, 10,  5, -5], 
            [ -8,  0,  5, 10, 15, 10,  5,  0, -8],
            [-10, -5,  0,  5, 10,  5,  0, -5,-10],
            [-15, -8, -2,  0,  5,  0, -2, -8,-15], # Chân nhà
            [-20,-15,-10, -5, -5, -5,-10,-15,-20], 
            [-25,-20,-15,-10,-10,-10,-15,-20,-25]  # Tránh Mã ở đáy
        ]
        self.HORSE_PST_BLACK = [[-x for x in row] for row in reversed(self.HORSE_PST_RED)]
        
        self.ADVISOR_PST_RED = [ # Sĩ Đỏ
            [0,0,0,0,0,0,0,0,0],[0,0,0,0,0,0,0,0,0],[0,0,0,0,0,0,0,0,0],
            [0,0,0,0,0,0,0,0,0],[0,0,0,0,0,0,0,0,0],[0,0,0,0,0,0,0,0,0],
            [0,0,0,0,0,0,0,0,0],
            [0,0,0, 5, 0, 5,0,0,0], # Hàng 7 (index)
            [0,0,0, 0,15, 0,0,0,0], # Hàng 8 (Sĩ trung tâm rất quan trọng)
            [0,0,0, 8, 0, 8,0,0,0]  # Hàng 9
        ]
        self.ADVISOR_PST_BLACK = [[-x for x in row] for row in reversed(self.ADVISOR_PST_RED)]

        self.ELEPHANT_PST_RED = [ # Tượng Đỏ
            [0,0,0,0,0,0,0,0,0],[0,0,0,0,0,0,0,0,0],[0,0,0,0,0,0,0,0,0],
            [0,0,0,0,0,0,0,0,0],[0,0,0,0,0,0,0,0,0], # Không qua sông
            [0,0,0,0,0,0,0,0,0], # Hàng 5
            [0,0, 5,0,10,0, 5,0,0], # Hàng 6 (index) - Tượng điền
            [0,0, 0,0, 0,0, 0,0,0],
            [5,0,10,0,15,0,10,0,5], # Hàng 8 (index) - Tượng biên và Tượng tâm liên kết Sĩ
            [0,0, 0,0, 0,0, 0,0,0]  # Hàng 9
        ]
        self.ELEPHANT_PST_BLACK = [[-x for x in row] for row in reversed(self.ELEPHANT_PST_RED)]

        self.PAWN_PST_RED = [ # Tốt Đỏ
            [90,100,110,120,120,120,110,100, 90], # Hàng 0 (đáy Đen, Tốt Đỏ ở đây cực mạnh)
            [85, 95,100,110,115,110,100, 95, 85], 
            [70, 80, 85, 90, 95, 90, 85, 80, 70], 
            [50, 60, 65, 70, 75, 70, 65, 60, 50], # Qua sông, bắt đầu có giá trị tấn công
            [30, 35, 40, 45, 50, 45, 40, 35, 30], # Vừa qua sông
            [10, 15, 18, 20, 25, 20, 18, 15, 10], # Chuẩn bị qua sông
            [ 0,  5,  8, 10, 12, 10,  8,  5,  0], # Hàng Tốt nhà
            [ 0,  0,  0,  0,  0,  0,  0,  0,  0], 
            [ 0,  0,  0,  0,  0,  0,  0,  0,  0], 
            [ 0,  0,  0,  0,  0,  0,  0,  0,  0]  
        ]
        self.PAWN_PST_BLACK = [[-x for x in row] for row in reversed(self.PAWN_PST_RED)]

        self.KING_PST_RED = [ # Tướng Đỏ - chủ yếu là giữ an toàn, không nên di chuyển nhiều trừ tàn cuộc
            [0,0,0, -1000, -5000, -1000,0,0,0], # Tướng Đỏ không bao giờ ở đây
            [0,0,0, -1000, -5000, -1000,0,0,0],
            [0,0,0, -1000, -5000, -1000,0,0,0],
            [0,0,0,0,0,0,0,0,0], 
            [0,0,0,0,0,0,0,0,0], 
            [0,0,0,0,0,0,0,0,0], 
            [0,0,0,0,0,0,0,0,0], 
            [0,0,0,  5,  10,  5,0,0,0], # Hàng 7
            [0,0,0,  0,  15,  0,0,0,0], # Hàng 8
            [0,0,0, -5,   5, -5,0,0,0]  # Hàng 9 (tránh Tướng ở biên khi không cần thiết)
        ]
        self.KING_PST_BLACK = [[-x for x in row] for row in reversed(self.KING_PST_RED)]

        self.MOBILITY_WEIGHT = 2 # Tăng nhẹ trọng số cơ động
        self.PIECE_SAFETY_PENALTY_FACTOR = 0.6 # Phạt 60% giá trị quân nếu bị tấn công mà không được bảo vệ
        self.STRATEGIC_FORMATION_BONUS = 50 # Điểm thưởng cho các bộ quân chiến lược

    def get_game_progress_score(self, move_count_half_moves=0):
        # Hàm này cần self.board_instance đã được cập nhật
        current_board_array = self.board_instance.board
        num_major_pieces = 0
        total_pieces_on_board = 0
        
        # Đếm số quân mạnh và tổng số quân
        for r in range(self.board_instance.rows):
            for c in range(self.board_instance.cols):
                piece = current_board_array[r][c]
                if piece:
                    total_pieces_on_board += 1
                    piece_type = piece.upper()
                    if piece_type in ['R', 'H', 'C']: # Xe, Mã, Pháo
                        num_major_pieces += 1
        
        # Logic xác định giai đoạn (cần tinh chỉnh thêm)
        # Thang điểm: 0.0 (đầu khai cuộc) -> 1.0 (cuối khai cuộc/đầu trung cuộc) 
        # -> 2.0 (cuối trung cuộc/đầu tàn cuộc) -> >2.0 (tàn cuộc sâu)
        
        # Ngưỡng dựa trên số quân mạnh (ví dụ)
        # 12+ quân mạnh: chắc chắn khai cuộc hoặc đầu trung cuộc
        # 7-11 quân mạnh: trung cuộc
        # <=6 quân mạnh: chắc chắn tàn cuộc hoặc cuối trung cuộc

        # Ngưỡng dựa trên tổng số quân (ví dụ)
        # >22 quân: khai cuộc
        # 15-22 quân: trung cuộc
        # <15 quân: tàn cuộc

        # Ngưỡng dựa trên số nước đi
        # < 20 nửa nước: thường là khai cuộc
        # 20-60 nửa nước: thường là trung cuộc
        # > 60 nửa nước: thường là tàn cuộc

        # Kết hợp các yếu tố
        score = 0.0
        # Ưu tiên số quân mạnh để xác định tàn cuộc
        if num_major_pieces <= 4 or total_pieces_on_board <= 12 : # Tàn cuộc sâu
            score = 2.2 + ( (12 - total_pieces_on_board) / 10.0) * 0.3 # Càng ít quân, điểm càng cao
        elif num_major_pieces <= 7 or total_pieces_on_board <= 16: # Đầu tàn cuộc / cuối trung cuộc
            score = 1.8 + ( (16 - total_pieces_on_board) / 10.0) * 0.4 
        # Khai cuộc
        elif move_count_half_moves < 15 and num_major_pieces >= 10:
            score = (move_count_half_moves / 30.0) # Từ 0.0 đến 0.5
        elif move_count_half_moves < 30 and num_major_pieces >= 8:
             score = 0.5 + ((move_count_half_moves - 15) / 30.0) # Từ 0.5 đến 1.0
        # Trung cuộc
        else:
            # Dựa vào số quân và số nước để ước lượng trong khoảng 1.0 -> 1.8
            score = 1.0 + min(move_count_half_moves / 100.0, 0.5) + \
                    min((28 - total_pieces_on_board) / 20.0, 0.3)
        
        return min(score, 2.5) # Giới hạn trên để tránh số quá lớn

    def get_piece_value_at_pos(self, piece_char, r, c, game_progress_score, color_context):
        piece_char_upper = piece_char.upper()
        base_value_opening = self.PIECE_BASE_VALUES_OPENING.get(piece_char_upper, 0)
        base_value_midgame = self.PIECE_BASE_VALUES_MIDGAME.get(piece_char_upper, 0)
        base_value_endgame = self.PIECE_BASE_VALUES_ENDGAME.get(piece_char_upper, 0)
        
        current_base_value = 0
        # Nội suy giá trị cơ bản
        if game_progress_score < 1.0: # Từ Khai cuộc (0.0) -> Trung cuộc (1.0)
            current_base_value = base_value_opening + game_progress_score * (base_value_midgame - base_value_opening)
        elif game_progress_score < 2.0: # Từ Trung cuộc (1.0) -> Tàn cuộc (2.0)
            progress_to_endgame = game_progress_score - 1.0
            current_base_value = base_value_midgame + progress_to_endgame * (base_value_endgame - base_value_midgame)
        else: # Tàn cuộc sâu (>=2.0)
            current_base_value = base_value_endgame

        positional_bonus = 0
        
        if piece_char_upper == 'P': # Tốt
            is_red_pawn = 'A' <= piece_char <= 'Z' # Hoặc dùng color_context
            crossed_river = (is_red_pawn and r < 5) or (not is_red_pawn and r > 4)
            advancement_modifier = 1.0
            if crossed_river:
                if (is_red_pawn and r <= 1) or (not is_red_pawn and r >= 8): # Gần cung
                    advancement_modifier = self.PAWN_ADVANCEMENT_MODIFIERS['crossed_river_deep']
                    if (is_red_pawn and r == 0) or (not is_red_pawn and r == 9): # Sát đáy
                         advancement_modifier = self.PAWN_ADVANCEMENT_MODIFIERS['promotion_threat']
                elif (is_red_pawn and r <= 3) or (not is_red_pawn and r >= 6): # Giữa sân địch
                    advancement_modifier = self.PAWN_ADVANCEMENT_MODIFIERS['crossed_river_middle']
                else: # Mới qua sông
                    advancement_modifier = self.PAWN_ADVANCEMENT_MODIFIERS['crossed_river_shallow']
            current_base_value *= advancement_modifier
            
            pst_pawn = self.PAWN_PST_RED if color_context == 'red' else self.PAWN_PST_BLACK
            if 0 <= r < len(pst_pawn) and 0 <= c < len(pst_pawn[0]):
                 positional_bonus += pst_pawn[r][c]
        
        elif piece_char_upper == 'K': 
            pst_king = self.KING_PST_RED if color_context == 'red' else self.KING_PST_BLACK
            if 0 <= r < len(pst_king) and 0 <= c < len(pst_king[0]):
                positional_bonus += pst_king[r][c]
            current_base_value = 0 # Giá trị Tướng không tính vào vật chất, chỉ tính an toàn và vị trí
        
        else: # Các quân khác (R, H, C, A, E)
            pst = None
            if piece_char_upper == 'R':
                pst = self.CHARIOT_PST_RED if color_context == 'red' else self.CHARIOT_PST_BLACK
            elif piece_char_upper == 'C':
                pst = self.CANNON_PST_RED if color_context == 'red' else self.CANNON_PST_BLACK
                # Thêm logic thưởng/phạt cho Pháo dựa trên có ngòi hoặc bị kẹt
                # (Cần self.board_instance để kiểm tra)
            elif piece_char_upper == 'H':
                pst = self.HORSE_PST_RED if color_context == 'red' else self.HORSE_PST_BLACK
            elif piece_char_upper == 'A':
                pst = self.ADVISOR_PST_RED if color_context == 'red' else self.ADVISOR_PST_BLACK
            elif piece_char_upper == 'E':
                pst = self.ELEPHANT_PST_RED if color_context == 'red' else self.ELEPHANT_PST_BLACK
            
            if pst and 0 <= r < len(pst) and 0 <= c < len(pst[0]):
                 positional_bonus += pst[r][c]
            
        final_value_for_piece = current_base_value + positional_bonus
        return final_value_for_piece if color_context == 'red' else -final_value_for_piece

    def evaluate_king_safety(self, king_color, current_board_obj, game_progress_score):
        # Hàm này cần current_board_obj (là self.board_instance khi gọi từ evaluate_board)
        # và self.rules cũng phải dùng board_obj này
        original_rules_board = self.rules.board_instance # Lưu lại board gốc của rules
        self.rules.board_instance = current_board_obj    # Set board cho rules để dùng các hàm is_square_attacked,...
        
        safety_score = 0.0 
        king_pos = self.rules.find_king(king_color)
        if not king_pos: 
            self.rules.board_instance = original_rules_board # Khôi phục
            return -self.CHECKMATE_SCORE * 2 # Tướng mất là thua ngay

        r_king, c_king = king_pos
        opponent_color = self.rules.get_opponent_color(king_color)
        
        # 1. Số lượng Sĩ Tượng bảo vệ
        advisor_char = 'A' if king_color == 'red' else 'a'
        elephant_char = 'E' if king_color == 'red' else 'e'
        num_advisors = 0
        num_elephants = 0

        # Đếm Sĩ (ví dụ cho Đỏ)
        if king_color == 'red':
            if current_board_obj.get_piece_at(8,3) == advisor_char: num_advisors +=1
            if current_board_obj.get_piece_at(8,5) == advisor_char: num_advisors +=1
            if current_board_obj.get_piece_at(7,4) == advisor_char: num_advisors +=0.5 # Sĩ lên cao có thể yếu hơn
            # Đếm Tượng
            if current_board_obj.get_piece_at(9,2) == elephant_char: num_elephants +=1
            if current_board_obj.get_piece_at(9,6) == elephant_char: num_elephants +=1
            if current_board_obj.get_piece_at(7,0) == elephant_char or \
               current_board_obj.get_piece_at(7,4) == elephant_char or \
               current_board_obj.get_piece_at(7,8) == elephant_char : num_elephants +=0.5 # Tượng biên hoặc lên cao
        else: # Đen
            if current_board_obj.get_piece_at(1,3) == advisor_char: num_advisors +=1
            if current_board_obj.get_piece_at(1,5) == advisor_char: num_advisors +=1
            if current_board_obj.get_piece_at(2,4) == advisor_char: num_advisors +=0.5
            # Đếm Tượng
            if current_board_obj.get_piece_at(0,2) == elephant_char: num_elephants +=1
            if current_board_obj.get_piece_at(0,6) == elephant_char: num_elephants +=1
            if current_board_obj.get_piece_at(2,0) == elephant_char or \
               current_board_obj.get_piece_at(2,4) == elephant_char or \
               current_board_obj.get_piece_at(2,8) == elephant_char : num_elephants +=0.5

        safety_score += num_advisors * 30 # Giảm nhẹ điểm Sĩ, vì PST đã tính
        safety_score += num_elephants * 25 # Giảm nhẹ điểm Tượng
        
        if num_advisors < 2: safety_score -= (2 - num_advisors) * 50 # Phạt nếu thiếu Sĩ
        if num_elephants < 2: safety_score -= (2 - num_elephants) * 40 # Phạt nếu thiếu Tượng

        # 2. Mối đe dọa trực tiếp đến Tướng và các ô lân cận trong cung
        attack_threat_penalty = 0
        # Kiểm tra Tướng có bị chiếu không (đã có trong evaluate_board chính)
        # Các ô lân cận Tướng trong cung
        palace_squares_to_check = []
        for dr_k in [-1, 0, 1]:
            for dc_k in [-1, 0, 1]:
                # if dr_k == 0 and dc_k == 0: continue # Bỏ qua ô Tướng đứng
                nr, nc = r_king + dr_k, c_king + dc_k
                if self.rules.is_in_palace(nr, nc, king_color): 
                     palace_squares_to_check.append((nr,nc))
        
        for r_target, c_target in palace_squares_to_check:
            if self.rules.is_square_attacked(r_target, c_target, opponent_color):
                attack_threat_penalty += 30 # Phạt cho mỗi ô quan trọng bị tấn công
                if r_target == r_king and c_target == c_king: # Nếu Tướng bị chiếu
                    attack_threat_penalty += 100 # Phạt nặng hơn nữa
        safety_score -= attack_threat_penalty
        
        # 3. Cấu trúc phòng thủ (ví dụ: Sĩ Tượng có liên kết không)
        # (Logic này có thể phức tạp, tạm thời bỏ qua hoặc tích hợp vào PST)

        self.rules.board_instance = original_rules_board # Khôi phục board gốc cho rules
        return safety_score 

    def evaluate_mobility(self, player_color, current_board_obj, game_progress_score):
        original_rules_board = self.rules.board_instance
        self.rules.board_instance = current_board_obj
        mobility_score = 0
        # Trọng số cơ động cho từng loại quân, có thể thay đổi theo giai đoạn
        mobility_piece_weights = {
            CHARIOT: 2.5 if game_progress_score < 2.0 else 3.0, # Xe cơ động hơn ở tàn cuộc
            HORSE: 1.8,
            CANNON: 1.5, # Pháo cần ngòi, cơ động thuần túy ít giá trị hơn
            # PAWN: 0.5, # Tốt cơ động cũng có giá trị
            # GENERAL: 0.2, ADVISOR: 0.2, ELEPHANT: 0.2 # Ít quan trọng hơn
        }

        for r_idx in range(current_board_obj.rows):
            for c_idx in range(current_board_obj.cols):
                piece_char = current_board_obj.get_piece_at(r_idx, c_idx)
                if piece_char:
                    piece_info = self.rules.get_piece_info(piece_char)
                    if piece_info and piece_info['color'] == player_color:
                        piece_type = piece_info['type']
                        if piece_type in mobility_piece_weights:
                            raw_moves = self.rules.get_raw_moves_for_piece(r_idx, c_idx)
                            # Đếm số nước đi không bị cản bởi quân nhà (trừ khi là bắt quân địch)
                            actual_moves = 0
                            for move_from, move_to in raw_moves:
                                target_char = current_board_obj.get_piece_at(move_to[0], move_to[1])
                                if target_char is None or self.rules.get_piece_info(target_char)['color'] != player_color:
                                    actual_moves +=1
                            mobility_score += actual_moves * mobility_piece_weights[piece_type]
        
        self.rules.board_instance = original_rules_board
        return mobility_score * self.MOBILITY_WEIGHT

    def evaluate_center_control(self, player_color, board_obj, game_progress_score):
        # Các ô trung tâm quan trọng
        # Hàng 3,4,5,6 (index) và cột 3,4,5 (index)
        center_squares_main = [(r,c) for r in range(3,7) for c in range(3,6)]
        # Các ô gần trung tâm
        center_squares_secondary = [(2,3),(2,4),(2,5), (7,3),(7,4),(7,5), 
                                    (3,2),(4,2),(5,2),(6,2), (3,6),(4,6),(5,6),(6,6)]
        control_score = 0
        for r, c in center_squares_main:
            piece = board_obj.get_piece_at(r,c)
            if piece:
                info = self.rules.get_piece_info(piece)
                if info and info['color'] == player_color:
                    control_score += 20 # Điểm cho quân ở trung tâm chính
        for r, c in center_squares_secondary:
            piece = board_obj.get_piece_at(r,c)
            if piece:
                info = self.rules.get_piece_info(piece)
                if info and info['color'] == player_color:
                    control_score += 10 # Điểm cho quân ở trung tâm phụ
        
        # Giảm tầm quan trọng của kiểm soát trung tâm ở tàn cuộc sâu
        control_weight = 1.0
        if game_progress_score > 1.5: # Nửa sau trung cuộc trở đi
            control_weight = max(0.2, 1.0 - (game_progress_score - 1.5) * 0.8) # Giảm dần về 0.2
        
        return control_score * control_weight

    def evaluate_strategic_formations(self, player_color, board_array, game_progress_score):
        """
        Đánh giá các cấu trúc quân chiến lược (ví dụ: Song Pháo, Pháo Mã).
        Cần self.board_instance được set đúng.
        """
        formation_score = 0
        # Ví dụ: Kiểm tra Song Pháo
        cannons = []
        chariots = []
        horses = []
        for r in range(self.board_instance.rows):
            for c in range(self.board_instance.cols):
                piece_char = board_array[r][c]
                if piece_char:
                    info = self.rules.get_piece_info(piece_char)
                    if info and info['color'] == player_color:
                        if info['type'] == CANNON: cannons.append((r,c))
                        elif info['type'] == CHARIOT: chariots.append((r,c))
                        elif info['type'] == HORSE: horses.append((r,c))
        
        # Song Pháo Kẹp Nách/Song Pháo Quá Hà (ví dụ đơn giản)
        if len(cannons) == 2:
            c1_r, c1_c = cannons[0]
            c2_r, c2_c = cannons[1]
            # Kiểm tra xem 2 Pháo có ở vị trí tấn công tốt không (ví dụ cùng hàng/cột gần Tướng địch)
            # Đây là logic ví dụ, cần chi tiết hơn
            if (player_color == 'red' and (c1_r < 5 and c2_r < 5)) or \
               (player_color == 'black' and (c1_r > 4 and c2_r > 4)): # Cả 2 Pháo qua sông
                formation_score += self.STRATEGIC_FORMATION_BONUS * 0.8
                # Kiểm tra thêm vị trí cụ thể
        
        # Pháo Mã phối hợp
        if len(cannons) >= 1 and len(horses) >= 1:
            # Kiểm tra xem Pháo và Mã có ở gần nhau và có thể hỗ trợ tấn công không
            # Ví dụ: Mã ở vị trí tốt, Pháo có thể làm ngòi
            formation_score += self.STRATEGIC_FORMATION_BONUS * 0.5

        # Cần thêm nhiều logic nhận diện cấu trúc khác từ sách
        return formation_score

    def evaluate_board(self, player_to_maximize, move_count_half_moves=0):
        # 0. Cập nhật board_instance cho self.rules và self.evaluator (quan trọng!)
        # Hàm gọi evaluate_board (ví dụ từ AIPlayer) phải đảm bảo điều này.
        # Hoặc truyền board_obj vào đây và set nó cho self.rules.board_instance
        
        # 1. Kiểm tra chiếu bí hoặc hết nước đi (trạng thái kết thúc)
        is_checkmated_player_to_maximize, _ = self.rules.is_checkmate(player_to_maximize)
        if is_checkmated_player_to_maximize: return -self.CHECKMATE_SCORE 
        
        opponent_color = self.rules.get_opponent_color(player_to_maximize)
        is_checkmated_opponent, _ = self.rules.is_checkmate(opponent_color)
        if is_checkmated_opponent: return self.CHECKMATE_SCORE
        
        if self.rules.is_stalemate(player_to_maximize) or self.rules.is_stalemate(opponent_color):
            return self.STALEMATE_SCORE 

        # 2. Xác định giai đoạn ván cờ (dưới dạng số thực)
        current_game_progress = self.get_game_progress_score(move_count_half_moves)
        current_board_array = self.board_instance.board # Đảm bảo board_instance là đúng
        
        # 3. Tính điểm vật chất và vị trí
        material_and_positional_score_red_perspective = 0
        for r_idx in range(self.board_instance.rows):
            for c_idx in range(self.board_instance.cols):
                piece_char = current_board_array[r_idx][c_idx]
                if piece_char:
                    piece_color_of_this_piece = self.rules.get_piece_info(piece_char)['color']
                    # Truyền game_progress_score vào get_piece_value_at_pos
                    material_and_positional_score_red_perspective += self.get_piece_value_at_pos(
                        piece_char, r_idx, c_idx, current_game_progress, piece_color_of_this_piece
                    )
        
        # 4. An toàn Tướng
        king_safety_red_val = self.evaluate_king_safety('red', self.board_instance, current_game_progress)
        king_safety_black_val = self.evaluate_king_safety('black', self.board_instance, current_game_progress) 
        material_and_positional_score_red_perspective += (king_safety_red_val - king_safety_black_val) 
        
        # 5. Độ linh hoạt của quân (Mobility)
        mobility_red = self.evaluate_mobility('red', self.board_instance, current_game_progress)
        mobility_black = self.evaluate_mobility('black', self.board_instance, current_game_progress)
        material_and_positional_score_red_perspective += (mobility_red - mobility_black)

        # 6. Kiểm soát trung tâm
        center_control_red = self.evaluate_center_control('red', self.board_instance, current_game_progress)
        center_control_black = self.evaluate_center_control('black', self.board_instance, current_game_progress)
        material_and_positional_score_red_perspective += (center_control_red - center_control_black)

        # 7. An toàn quân cờ (trừ điểm nếu quân bị tấn công mà không được bảo vệ)
        piece_safety_penalty_score = 0
        valuable_piece_types_for_safety = ['R', 'H', 'C'] # Xe, Pháo, Mã
        for r_idx_safety in range(self.board_instance.rows):
            for c_idx_safety in range(self.board_instance.cols):
                piece_char_safety = self.board_instance.get_piece_at(r_idx_safety, c_idx_safety)
                if piece_char_safety:
                    piece_info_safety = self.rules.get_piece_info(piece_char_safety)
                    # Chỉ xét các quân giá trị
                    if piece_info_safety['type'].upper() in valuable_piece_types_for_safety:
                        current_piece_color = piece_info_safety['color']
                        opponent = self.rules.get_opponent_color(current_piece_color)
                        is_attacked = self.rules.is_square_attacked(r_idx_safety, c_idx_safety, opponent)
                        
                        # is_square_protected cần được triển khai trong rules.py
                        is_protected = self.rules.is_square_protected(r_idx_safety, c_idx_safety, current_piece_color)
                        
                        if is_attacked and not is_protected:
                            base_val_op = self.PIECE_BASE_VALUES_OPENING.get(piece_char_safety.upper(),0) # Lấy tạm giá trị khai cuộc
                            penalty = base_val_op * self.PIECE_SAFETY_PENALTY_FACTOR
                            if current_piece_color == 'red':
                                piece_safety_penalty_score -= penalty
                            else:
                                piece_safety_penalty_score += penalty # Cộng vào điểm Đỏ nếu quân Đen bị nguy hiểm
        material_and_positional_score_red_perspective += piece_safety_penalty_score

        # 8. Điểm thưởng cho các cấu trúc quân chiến lược
        strategic_formation_red = self.evaluate_strategic_formations('red', current_board_array, current_game_progress)
        strategic_formation_black = self.evaluate_strategic_formations('black', current_board_array, current_game_progress)
        material_and_positional_score_red_perspective += (strategic_formation_red - strategic_formation_black)

        # 9. Phạt/Thưởng khi bị chiếu/chiếu được
        if self.rules.is_king_in_check('red'): 
            material_and_positional_score_red_perspective -= 150 # Giảm hình phạt chiếu một chút
        if self.rules.is_king_in_check('black'): 
            material_and_positional_score_red_perspective += 150 
        
        # 10. (TODO - Nâng cao) Tích hợp đánh giá từ Sát Pháp, Chiến Thuật, Cờ Tàn đã biết
        # if self.book_knowledge:
        #     # Ví dụ:
        #     known_endgame_eval = self.book_knowledge.get_evaluation_for_known_endgame(self.board_instance, player_to_maximize)
        #     if known_endgame_eval is not None: # Nếu là thế cờ tàn đã biết kết quả
        #         return known_endgame_eval 
            
        #     recognized_kill_pattern_score = self.book_knowledge.evaluate_kill_pattern_threat(self.board_instance, player_to_maximize)
        #     # ... (cộng/trừ vào điểm tổng) ...

        # Trả về điểm theo góc nhìn của player_to_maximize
        return material_and_positional_score_red_perspective if player_to_maximize == 'red' else -material_and_positional_score_red_perspective

