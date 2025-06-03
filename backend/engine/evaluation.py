# File: backend/engine/evaluation.py
# Version: V17.0 - Hoàn thiện đầy đủ, tích hợp chiến lược

from .board import GENERAL, PAWN, ADVISOR, ELEPHANT, HORSE, CHARIOT, CANNON 
from .rules import GameRules # GameRules giờ đã có is_square_protected

class Evaluation:
    def __init__(self, game_rules_instance, book_knowledge_instance=None):
        self.rules = game_rules_instance 
        self.board_instance = self.rules.board_instance # Sẽ được cập nhật bởi AIPlayer
        self.book_knowledge = book_knowledge_instance
        
        self.CHECKMATE_SCORE = 100000 
        self.STALEMATE_SCORE = 0 

        # Giá trị quân cờ CƠ BẢN (điểm neo cho nội suy)
        self.PIECE_BASE_VALUES_OPENING = {
            'R': 1000, 'H': 400, 'C': 500, 'A': 200, 'E': 200, 'P': 100 
        }
        self.PIECE_BASE_VALUES_MIDGAME = {
            'R': 1000, 'H': 450, 'C': 500, 'A': 250, 'E': 250, 'P': 150 
        }
        self.PIECE_BASE_VALUES_ENDGAME = {
            'R': 1000, 'H': 500, 'C': 450, 'A': 250, 'E': 250, 'P': 200 
        }
        
        self.PAWN_ADVANCEMENT_MODIFIERS = { 
            'crossed_river_shallow': 2.0, 
            'crossed_river_middle': 2.5,  
            'crossed_river_deep': 3.0,    
            'at_baseline': 3.5            
        }


        # # Giá trị quân cờ CƠ BẢN (điểm neo cho nội suy) - Updated for better balance
        # self.PIECE_BASE_VALUES_OPENING = {
        #     'R': 1000, 'H': 380, 'C': 520, 'A': 200, 'E': 210, 'P': 100 
        # }
        # self.PIECE_BASE_VALUES_MIDGAME = {
        #     'R': 1000, 'H': 450, 'C': 510, 'A': 240, 'E': 260, 'P': 150 
        # }
        # self.PIECE_BASE_VALUES_ENDGAME = {
        #     'R': 1050, 'H': 520, 'C': 430, 'A': 260, 'E': 270, 'P': 220 
        # }
        
        # self.PAWN_ADVANCEMENT_MODIFIERS = { 
        #     'crossed_river_shallow': 2.0, 
        #     'crossed_river_middle': 2.5,  
        #     'crossed_river_deep': 3.0,    
        #     'at_baseline': 3.5            
        # }


        # # CẬP NHẬT QUAN TRỌNG: Điều chỉnh giá trị quân theo giai đoạn
        # self.PIECE_BASE_VALUES_OPENING = {
        #     'R': 900,  # Xe: giảm nhẹ do chưa phát huy hết sức mạnh
        #     'H': 380,  # Mã: giảm nhẹ
        #     'C': 480,  # Pháo: tăng trong khai cuộc
        #     'A': 220,  # Sĩ: tăng để khuyến khích bảo vệ tướng
        #     'E': 210,  # Tượng: tăng
        #     'P': 90    # Tốt: giảm
        # }
        # self.PIECE_BASE_VALUES_MIDGAME = {
        #     'R': 1000, # Xe: giá trị cao nhất
        #     'H': 450,  # Mã: tăng
        #     'C': 460,  # Pháo: giảm nhẹ
        #     'A': 180,  # Sĩ: giảm
        #     'E': 170,  # Tượng: giảm
        #     'P': 130   # Tốt: tăng
        # }
        # self.PIECE_BASE_VALUES_ENDGAME = {
        #     'R': 1100, # Xe: rất quan trọng
        #     'H': 500,  # Mã: tăng mạnh
        #     'C': 400,  # Pháo: giảm do ít ngòi
        #     'A': 150,  # Sĩ: ít quan trọng
        #     'E': 140,  # Tượng: ít quan trọng
        #     'P': 250   # Tốt: cực kỳ quan trọng
        # }
        
        # # Hệ số tiến triển cho Tốt
        # self.PAWN_ADVANCEMENT_MODIFIERS = { 
        #     'crossed_river_shallow': 1.5,  # Giảm hệ số
        #     'crossed_river_middle': 2.0,  
        #     'crossed_river_deep': 2.5,    
        #     'at_baseline': 3.0            
        # }


        # PSTs - Đây là các giá trị ví dụ, cần tinh chỉnh kỹ lưỡng!
        # Giá trị dương tốt cho Đỏ.
        self.CHARIOT_PST_RED = [
            [10, 12, 15, 25, 30, 25, 15, 12, 10], [10, 15, 18, 28, 33, 28, 18, 15, 10],
            [ 8, 10, 12, 20, 25, 20, 12, 10,  8], [ 5,  8, 10, 15, 18, 15, 10,  8,  5],
            [ 0,  2,  5, 10, 12, 10,  5,  2,  0], [-2,  0,  2,  5,  8,  5,  2,  0, -2],
            [ 0,  0,  0,  0,  0,  0,  0,  0,  0], [ 0,  0,  0,  0,  0,  0,  0,  0,  0],
            [-2, -2, -2, -5, -5, -5, -2, -2, -2], [-5, -5, -5, -8, -8, -8, -5, -5, -5]
        ]
        self.CHARIOT_PST_BLACK = [[-x for x in row] for row in reversed(self.CHARIOT_PST_RED)]

        self.CANNON_PST_RED = [
            [  0,   0,   5,  10,  15,  10,   5,   0,   0], [  0,   2,   8,  12,  18,  12,   8,   2,   0],
            [  0,   5,  10,  15,  20,  15,  10,   5,   0], [  5,   8,  12,  18,  22,  18,  12,   8,   5],
            [  2,   5,  10,  15,  18,  15,  10,   5,   2], [  0,   0,   5,  10,  12,  10,   5,   0,   0], 
            [  0,   0,   2,   8,  10,   8,   2,   0,   0], [  0,   0,   0,   5,   5,   5,   0,   0,   0],
            [ -5,  -5,  -2,   0,   0,   0,  -2,  -5,  -5], [-10, -10,  -5,  -5,  -5,  -5,  -5, -10, -10]  
        ]
        self.CANNON_PST_BLACK = [[-x for x in row] for row in reversed(self.CANNON_PST_RED)]

        self.HORSE_PST_RED = [
            [ -5,  0, 10, 20, 25, 20, 10,  0, -5], [  0,  8, 18, 28, 33, 28, 18,  8,  0],
            [  5, 15, 25, 30, 35, 30, 25, 15,  5], [  2, 10, 20, 25, 30, 25, 20, 10,  2], 
            [  0,  5, 12, 18, 22, 18, 12,  5,  0], [ -5,  0,  8, 12, 15, 12,  8,  0, -5],
            [-10, -2,  5,  8, 10,  8,  5, -2,-10], [-15, -8,  0,  2,  5,  2,  0, -8,-15], 
            [-20,-15,-10, -5, -5, -5,-10,-15,-20], [-25,-20,-15,-10,-10,-10,-15,-20,-25] 
        ]
        self.HORSE_PST_BLACK = [[-x for x in row] for row in reversed(self.HORSE_PST_RED)]
        
        self.ADVISOR_PST_RED = [
            [0,0,0,0,0,0,0,0,0],[0,0,0,0,0,0,0,0,0],[0,0,0,0,0,0,0,0,0],
            [0,0,0,0,0,0,0,0,0],[0,0,0,0,0,0,0,0,0],[0,0,0,0,0,0,0,0,0],
            [0,0,0,0,0,0,0,0,0],
            [0,0,0, 8, 0, 8,0,0,0], [0,0,0, 0,20, 0,0,0,0], [0,0,0,10, 0,10,0,0,0]
        ]
        self.ADVISOR_PST_BLACK = [[-x for x in row] for row in reversed(self.ADVISOR_PST_RED)]

        self.ELEPHANT_PST_RED = [
            [0,0,0,0,0,0,0,0,0],[0,0,0,0,0,0,0,0,0],[0,0,0,0,0,0,0,0,0],
            [0,0,0,0,0,0,0,0,0],[0,0,0,0,0,0,0,0,0], [0,0,0,0,0,0,0,0,0], 
            [0,0, 8,0,15,0, 8,0,0], [0,0, 0,0, 0,0, 0,0,0],
            [8,0,12,0,18,0,12,0,8], [0,0, 0,0, 0,0, 0,0,0]
        ]
        self.ELEPHANT_PST_BLACK = [[-x for x in row] for row in reversed(self.ELEPHANT_PST_RED)]

        self.PAWN_PST_RED = [ 
            [100,110,120,130,130,130,120,110,100], [ 90,100,110,120,125,120,110,100, 90], 
            [ 70, 80, 85, 90, 95, 90, 85, 80, 70], [ 50, 60, 65, 70, 75, 70, 65, 60, 50], 
            [ 30, 35, 40, 45, 50, 45, 40, 35, 30], [ 10, 15, 18, 20, 25, 20, 18, 15, 10], 
            [  0,  5,  8, 10, 12, 10,  8,  5,  0], [  0,  2,  5,  8, 10,  8,  5,  2,  0], 
            [  0,  0,  0,  0,  0,  0,  0,  0,  0], [  0,  0,  0,  0,  0,  0,  0,  0,  0]  
        ]
        self.PAWN_PST_BLACK = [[-x for x in row] for row in reversed(self.PAWN_PST_RED)]

        self.KING_PST_RED = [ 
            [0,0,0,0,0,0,0,0,0],[0,0,0,0,0,0,0,0,0],[0,0,0,0,0,0,0,0,0],
            [0,0,0,0,0,0,0,0,0],[0,0,0,0,0,0,0,0,0], 
            [0,0,0,10,15,10,0,0,0], [0,0,0, 5,10, 5,0,0,0], 
            [0,0,0,  2, 8,  2,0,0,0], [0,0,0,  0, 5,  0,0,0,0], 
            [0,0,0, -2, 0, -2,0,0,0] 
        ]
        self.KING_PST_BLACK = [[-x for x in row] for row in reversed(self.KING_PST_RED)]

        self.MOBILITY_WEIGHT = 2.5 
        self.PIECE_SAFETY_PENALTY_FACTOR = 0.75 
        self.STRATEGIC_FORMATION_BONUS = 45
        self.TERRITORY_CONTROL_PENALTY = 35 
        self.TERRITORY_PRESENCE_BONUS = 20  
        self.PAWN_STRUCTURE_BONUS = 10 
        self.RIVER_CONTROL_BONUS = 8 
        self.CANNON_MOUNT_BONUS = 15
        self.CONNECTED_PAWNS_BONUS = 5 # Điểm thưởng cho mỗi cặp Tốt liên hoàn


        # # CẬP NHẬT HỆ SỐ ĐÁNH GIÁ
        # self.MOBILITY_WEIGHT = 1.8  # Giảm trọng số di chuyển
        # self.PIECE_SAFETY_PENALTY_FACTOR = 0.85  # Tăng phạt mất quân
        # self.STRATEGIC_FORMATION_BONUS = 35  # Giảm bonus thế trận
        # self.TERRITORY_CONTROL_PENALTY = 30  # Giảm phạt kiểm soát lãnh thổ
        # self.TERRITORY_PRESENCE_BONUS = 20  # Giảm bonus hiện diện lãnh thổ
        # self.PAWN_STRUCTURE_BONUS = 15  # Tăng bonus cấu trúc tốt
        # self.RIVER_CONTROL_BONUS = 12  # Tăng bonus kiểm soát sông
        # self.CANNON_MOUNT_BONUS = 18  # Tăng bonus pháo có ngòi
        # self.CONNECTED_PAWNS_BONUS = 7  # Tăng bonus tốt liên hoàn

    def get_game_progress_score(self, move_count_half_moves=0):
        if not self.board_instance or not self.board_instance.board:
            return 1.0 
            
        current_board_array = self.board_instance.board
        num_major_pieces = 0; total_pieces_on_board = 0
        for r in range(self.board_instance.rows):
            for c in range(self.board_instance.cols):
                piece = current_board_array[r][c]
                if piece:
                    total_pieces_on_board += 1
                    if piece.upper() in ['R', 'H', 'C']: num_major_pieces += 1
        
        score = 0.0
        if num_major_pieces <= 4 or total_pieces_on_board <= 12 : 
            score = 2.2 + max(0, (12 - total_pieces_on_board)) / 10.0 * 0.3 + min(move_count_half_moves, 80)/160.0 * 0.2
        elif num_major_pieces <= 7 or total_pieces_on_board <= 16: 
            score = 1.8 + max(0, (16 - total_pieces_on_board)) / 10.0 * 0.4 + min(move_count_half_moves, 60)/120.0 * 0.2
        elif move_count_half_moves < 10: 
            score = (move_count_half_moves / 20.0) 
        elif move_count_half_moves < 24: 
             score = 0.5 + ((move_count_half_moves - 10) / 28.0) 
        else: 
            score = 1.0 + min( (move_count_half_moves-24) / 80.0, 0.5) + \
                    min(max(0, (28 - total_pieces_on_board)) / 20.0, 0.4) 
        return min(score, 2.5)

    def get_piece_value_at_pos(self, piece_char, r, c, game_progress_score, color_context):
        piece_char_upper = piece_char.upper()
        base_opening = self.PIECE_BASE_VALUES_OPENING.get(piece_char_upper, 0)
        base_midgame = self.PIECE_BASE_VALUES_MIDGAME.get(piece_char_upper, 0)
        base_endgame = self.PIECE_BASE_VALUES_ENDGAME.get(piece_char_upper, 0)
        current_base_value = 0

        if game_progress_score < 1.0:
            current_base_value = base_opening + game_progress_score * (base_midgame - base_opening)
        elif game_progress_score < 2.0:
            progress_to_endgame = game_progress_score - 1.0
            current_base_value = base_midgame + progress_to_endgame * (base_endgame - base_midgame)
        else: 
            current_base_value = base_endgame

        positional_bonus = 0
        if piece_char_upper == 'P':
            is_red_pawn = (color_context == 'red')
            crossed_river = (is_red_pawn and r < 5) or (not is_red_pawn and r > 4)
            if crossed_river:
                mod_key = 'crossed_river_shallow'
                if (is_red_pawn and r == 0) or (not is_red_pawn and r == 9): mod_key = 'at_baseline'
                elif (is_red_pawn and r <= 1) or (not is_red_pawn and r >= 8): mod_key = 'crossed_river_deep'
                elif (is_red_pawn and r <= 3) or (not is_red_pawn and r >= 6): mod_key = 'crossed_river_middle'
                current_base_value *= self.PAWN_ADVANCEMENT_MODIFIERS.get(mod_key, 1.0)
            pst_pawn = self.PAWN_PST_RED if color_context == 'red' else self.PAWN_PST_BLACK
            if 0 <= r < len(pst_pawn) and 0 <= c < len(pst_pawn[0]): positional_bonus += pst_pawn[r][c]
        elif piece_char_upper == 'K':
            pst_king = self.KING_PST_RED if color_context == 'red' else self.KING_PST_BLACK
            if 0 <= r < len(pst_king) and 0 <= c < len(pst_king[0]): positional_bonus += pst_king[r][c]
            current_base_value = 0 
        else:
            pst_map = {'R': (self.CHARIOT_PST_RED, self.CHARIOT_PST_BLACK),
                       'H': (self.HORSE_PST_RED, self.HORSE_PST_BLACK),
                       'C': (self.CANNON_PST_RED, self.CANNON_PST_BLACK),
                       'A': (self.ADVISOR_PST_RED, self.ADVISOR_PST_BLACK),
                       'E': (self.ELEPHANT_PST_RED, self.ELEPHANT_PST_BLACK)}
            pst_red, pst_black = pst_map.get(piece_char_upper, (None, None))
            pst = pst_red if color_context == 'red' else pst_black
            if pst and 0 <= r < len(pst) and 0 <= c < len(pst[0]): positional_bonus += pst[r][c]
        
        if piece_char_upper == 'C':
            num_effective_mounts = self._count_effective_cannon_mounts(r, c, color_context)
            positional_bonus += num_effective_mounts * self.CANNON_MOUNT_BONUS
        
        final_value = current_base_value + positional_bonus
        return final_value if color_context == 'red' else -final_value

    def _count_effective_cannon_mounts(self, r_cannon, c_cannon, cannon_color):
        if not self.board_instance or not self.rules: return 0
        count = 0
        opponent_color = self.rules.get_opponent_color(cannon_color)
        for dr, dc in [(0,1), (0,-1), (1,0), (-1,0)]:
            mount_found = False
            for i in range(1,10):
                nr, nc = r_cannon + dr*i, c_cannon + dc*i
                if not self.rules.is_in_board(nr,nc): break
                piece_at_curr = self.board_instance.get_piece_at(nr,nc)
                if piece_at_curr:
                    if not mount_found: 
                        mount_found = True
                    else: 
                        if self.rules.get_piece_info(piece_at_curr)['color'] == opponent_color:
                            target_type = self.rules.get_piece_info(piece_at_curr)['type']
                            if target_type == GENERAL: count += 2.5 
                            elif target_type in [CHARIOT, CANNON, HORSE]: count += 1.5
                            elif target_type in [ADVISOR, ELEPHANT]: count += 0.8
                            else: count += 0.5 
                        break 
        return count

    def evaluate_king_safety(self, king_color, current_board_obj, game_progress_score):
        original_rules_board = self.rules.board_instance
        self.rules.board_instance = current_board_obj
        safety_score = 0.0 
        king_pos = self.rules.find_king(king_color)
        if not king_pos: 
            self.rules.board_instance = original_rules_board
            return -self.CHECKMATE_SCORE    
        
        r_king, c_king = king_pos
        opponent_color = self.rules.get_opponent_color(king_color)
        advisor_char = 'A' if king_color == 'red' else 'a'
        elephant_char = 'E' if king_color == 'red' else 'e'
        num_advisors = 0; num_elephants = 0

        if king_color == 'red':
            if current_board_obj.get_piece_at(8,3) == advisor_char: num_advisors +=1
            if current_board_obj.get_piece_at(8,5) == advisor_char: num_advisors +=1
            if current_board_obj.get_piece_at(9,2) == elephant_char: num_elephants +=1
            if current_board_obj.get_piece_at(9,6) == elephant_char: num_elephants +=1
        else: 
            if current_board_obj.get_piece_at(1,3) == advisor_char: num_advisors +=1
            if current_board_obj.get_piece_at(1,5) == advisor_char: num_advisors +=1
            if current_board_obj.get_piece_at(0,2) == elephant_char: num_elephants +=1
            if current_board_obj.get_piece_at(0,6) == elephant_char: num_elephants +=1
        
        safety_score += num_advisors * 40 
        safety_score += num_elephants * 35
        if num_advisors < 2: safety_score -= (2 - num_advisors) * 70 
        if num_elephants < 2: safety_score -= (2 - num_elephants) * 60

        # # TĂNG QUAN TRỌNG CỦA BẢO VỆ TƯỚNG
        # safety_score += num_advisors * 45  # Tăng giá trị Sĩ
        # safety_score += num_elephants * 40  # Tăng giá trị Tượng
        
        # Phạt nặng hơn khi thiếu quân phòng thủ
        if num_advisors < 2: 
            safety_score -= (2 - num_advisors) * 100  # Tăng mức phạt
        if num_elephants < 2: 
            safety_score -= (2 - num_elephants) * 90  # Tăng mức phạt

        attack_threat_penalty = 0
        palace_squares_to_check = [(r_king, c_king)] 
        for dr_k in [-1, 0, 1]:
            for dc_k in [-1, 0, 1]:
                if dr_k == 0 and dc_k == 0: continue
                nr, nc = r_king + dr_k, c_king + dc_k
                if self.rules.is_in_palace(nr, nc, king_color): 
                     palace_squares_to_check.append((nr,nc))
        
        for r_target, c_target in palace_squares_to_check:
            if self.rules.is_square_attacked(r_target, c_target, opponent_color):
                attack_threat_penalty += 50 
                if r_target == r_king and c_target == c_king: 
                    attack_threat_penalty += 200 
        safety_score -= attack_threat_penalty
        
        self.rules.board_instance = original_rules_board
        return safety_score 

    def evaluate_mobility(self, player_color, current_board_obj, game_progress_score):
        original_rules_board = self.rules.board_instance
        self.rules.board_instance = current_board_obj
        mobility_score = 0.0
        mobility_piece_weights = {
            CHARIOT: 3.0 if game_progress_score < 2.0 else 3.5, 
            HORSE: 2.2, CANNON: 2.0, PAWN: 0.7,
            GENERAL: 0.5, ADVISOR: 0.4, ELEPHANT: 0.4
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
                            actual_moves = 0
                            for move_from, move_to in raw_moves:
                                target_char = current_board_obj.get_piece_at(move_to[0], move_to[1])
                                if target_char is None or self.rules.get_piece_info(target_char)['color'] != player_color:
                                    actual_moves +=1
                            mobility_score += actual_moves * mobility_piece_weights[piece_type]
        self.rules.board_instance = original_rules_board
        return mobility_score * self.MOBILITY_WEIGHT

    def evaluate_territorial_control_and_pawn_structure(self, player_color, board_obj, game_progress_score):
        score = 0
        current_board_array = board_obj.board
        for r in range(board_obj.rows):
            for c in range(board_obj.cols):
                piece_char = current_board_array[r][c]
                if piece_char:
                    piece_info = self.rules.get_piece_info(piece_char)
                    p_color = piece_info['color']
                    p_type = piece_info['type']
                    is_player_home_territory = (player_color == 'red' and r >= 5) or (player_color == 'black' and r < 5)
                    is_player_enemy_territory = (player_color == 'red' and r < 5) or (player_color == 'black' and r >= 5)

                    if p_color != player_color and is_player_home_territory and p_type in [CHARIOT, CANNON, HORSE]:
                        penalty = self.TERRITORY_CONTROL_PENALTY
                        if (player_color == 'red' and r >= 7) or (player_color == 'black' and r <= 2): penalty += 25
                        if not self.rules.is_square_attacked(r, c, player_color): penalty *= 1.5
                        score -= penalty 
                    elif p_color == player_color and is_player_enemy_territory and p_type in [CHARIOT, CANNON, HORSE, PAWN]:
                        bonus = self.TERRITORY_PRESENCE_BONUS
                        if p_type == PAWN and ((player_color == 'red' and r <=1) or (player_color == 'black' and r >=8)): bonus += 25
                        elif p_type != PAWN and ((player_color == 'red' and r <=2) or (player_color == 'black' and r >=7)): bonus += 30
                        score += bonus
        
        pawn_char_player = 'P' if player_color == 'red' else 'p'
        if game_progress_score < 1.5: 
            row_pawn_start = 6 if player_color == 'red' else 3
            if current_board_array[row_pawn_start][0] == pawn_char_player: score += self.PAWN_STRUCTURE_BONUS
            if current_board_array[row_pawn_start][8] == pawn_char_player: score += self.PAWN_STRUCTURE_BONUS
            if current_board_array[row_pawn_start][4] == pawn_char_player: score += self.PAWN_STRUCTURE_BONUS * 0.7
        
        # Tốt liên hoàn
        for r_pawn in range(10):
            for c_pawn in range(8): # Check đến cột 7 để tránh index out of bounds cho c_pawn+1
                if current_board_array[r_pawn][c_pawn] == pawn_char_player and \
                   current_board_array[r_pawn][c_pawn+1] == pawn_char_player:
                    score += self.CONNECTED_PAWNS_BONUS
        
        river_row_player_side = 4 if player_color == 'red' else 5 
        for c_river in range(9):
            p_on_river = current_board_array[river_row_player_side][c_river]
            if p_on_river and self.rules.get_piece_info(p_on_river)['color'] == player_color and \
               self.rules.get_piece_info(p_on_river)['type'] in [CHARIOT, CANNON]:
                score += self.RIVER_CONTROL_BONUS
        return score 

    def evaluate_strategic_formations(self, player_color, board_array, game_progress_score):
        formation_score = 0
        cannons = []; horses = []; chariots = []
        for r_idx in range(self.board_instance.rows):
            for c_idx in range(self.board_instance.cols):
                p = board_array[r_idx][c_idx]
                if p and self.rules.get_piece_info(p)['color'] == player_color:
                    p_type = self.rules.get_piece_info(p)['type']
                    if p_type == CANNON: cannons.append((r_idx, c_idx))
                    elif p_type == HORSE: horses.append((r_idx, c_idx))
                    elif p_type == CHARIOT: chariots.append((r_idx, c_idx))
        
        # Song Pháo
        if len(cannons) >= 2:
            formation_score += self.STRATEGIC_FORMATION_BONUS * 0.3 # Điểm cơ bản
            # (Thêm logic kiểm tra vị trí cụ thể của Song Pháo, ví dụ: Pháo lồng, Pháo gánh)
            # Ví dụ: nếu 2 Pháo cùng cột/hàng và có ngòi tốt
            if len(cannons) ==2:
                r1,c1 = cannons[0]; r2,c2 = cannons[1]
                if r1 == r2 or c1 == c2: # Cùng hàng hoặc cột
                    # Kiểm tra có ngòi giữa chúng hoặc có thể tấn công mạnh
                    formation_score += self.STRATEGIC_FORMATION_BONUS * 0.4


        # Pháo Mã
        if len(cannons) >= 1 and len(horses) >= 1:
            formation_score += self.STRATEGIC_FORMATION_BONUS * 0.2
            # (Thêm logic kiểm tra sự phối hợp tốt, ví dụ Mã làm ngòi cho Pháo, hoặc Mã ở vị trí tấn công được Pháo yểm trợ)
            
        # Xe Pháo, Xe Mã (tương tự)
        if len(chariots) >=1 and len(cannons) >=1: formation_score += self.STRATEGIC_FORMATION_BONUS * 0.25
        if len(chariots) >=1 and len(horses) >=1: formation_score += self.STRATEGIC_FORMATION_BONUS * 0.25
        
        return formation_score

    def evaluate_board(self, player_to_maximize, move_count_half_moves=0):
        if not self.board_instance or not self.rules: return 0
        if self.rules.board_instance != self.board_instance:
             self.rules.board_instance = self.board_instance

        is_checkmated_player_to_maximize, _ = self.rules.is_checkmate(player_to_maximize)
        if is_checkmated_player_to_maximize: return -self.CHECKMATE_SCORE 
        opponent_color = self.rules.get_opponent_color(player_to_maximize)
        is_checkmated_opponent, _ = self.rules.is_checkmate(opponent_color)
        if is_checkmated_opponent: return self.CHECKMATE_SCORE
        if self.rules.is_stalemate(player_to_maximize) or self.rules.is_stalemate(opponent_color):
            return self.STALEMATE_SCORE 

        current_game_progress = self.get_game_progress_score(move_count_half_moves)
        current_board_array = self.board_instance.board
        
        material_and_positional_score_red_perspective = 0
        for r_idx in range(self.board_instance.rows):
            for c_idx in range(self.board_instance.cols):
                piece_char = current_board_array[r_idx][c_idx]
                if piece_char:
                    piece_color = self.rules.get_piece_info(piece_char)['color']
                    material_and_positional_score_red_perspective += self.get_piece_value_at_pos(
                        piece_char, r_idx, c_idx, current_game_progress, piece_color
                    )
        
        king_safety_red = self.evaluate_king_safety('red', self.board_instance, current_game_progress)
        king_safety_black = self.evaluate_king_safety('black', self.board_instance, current_game_progress)
        
        mobility_red = self.evaluate_mobility('red', self.board_instance, current_game_progress)
        mobility_black = self.evaluate_mobility('black', self.board_instance, current_game_progress)
        
        territory_pawns_red = self.evaluate_territorial_control_and_pawn_structure('red', self.board_instance, current_game_progress)
        territory_pawns_black = self.evaluate_territorial_control_and_pawn_structure('black', self.board_instance, current_game_progress)

        formations_red = self.evaluate_strategic_formations('red', current_board_array, current_game_progress)
        formations_black = self.evaluate_strategic_formations('black', current_board_array, current_game_progress)

        total_score_red_perspective = material_and_positional_score_red_perspective + \
                                     (king_safety_red + king_safety_black) + \
                                     (mobility_red - mobility_black) + \
                                     (territory_pawns_red + territory_pawns_black) + \
                                     (formations_red - formations_black)

        if self.rules.is_king_in_check('red'): total_score_red_perspective -= 300 
        if self.rules.is_king_in_check('black'): total_score_red_perspective += 300

        piece_safety_score_red_pov = 0
        valuable_types_safety = ['R', 'H', 'C'] 
        for r_s in range(self.board_instance.rows):
            for c_s in range(self.board_instance.cols):
                p_s_char = self.board_instance.get_piece_at(r_s,c_s)
                if p_s_char:
                    p_s_info = self.rules.get_piece_info(p_s_char)
                    if p_s_info['type'].upper() in valuable_types_safety:
                        p_s_color = p_s_info['color']
                        opp_s_color = self.rules.get_opponent_color(p_s_color)
                        if self.rules.is_square_attacked(r_s, c_s, opp_s_color) and \
                           not self.rules.is_square_protected(r_s, c_s, p_s_color):
                            base_val_s = 0
                            if current_game_progress < 1.0: base_val_s = self.PIECE_BASE_VALUES_OPENING.get(p_s_char.upper(),0)
                            elif current_game_progress < 2.0: base_val_s = self.PIECE_BASE_VALUES_MIDGAME.get(p_s_char.upper(),0)
                            else: base_val_s = self.PIECE_BASE_VALUES_ENDGAME.get(p_s_char.upper(),0)
                            penalty_s = base_val_s * self.PIECE_SAFETY_PENALTY_FACTOR
                            if p_s_color == 'red': piece_safety_score_red_pov -= penalty_s
                            else: piece_safety_score_red_pov += penalty_s 
        total_score_red_perspective += piece_safety_score_red_pov
            
        if self.book_knowledge:
            known_endgame_eval_for_maximizer = self.book_knowledge.get_evaluation_for_known_endgame(
                self.board_instance, player_to_maximize, current_game_progress
            )
            if known_endgame_eval_for_maximizer is not None:
                return known_endgame_eval_for_maximizer
            
        return total_score_red_perspective if player_to_maximize == 'red' else -total_score_red_perspective
