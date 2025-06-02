# File: backend/engine/rules.py
# Version: V15.1 - Thêm is_square_protected, sửa lỗi nhỏ trong get_raw_moves_for_piece (Horse)

import copy
from .board import XiangqiBoard, GENERAL, ADVISOR, ELEPHANT, HORSE, CHARIOT, CANNON, PAWN

class GameRules:
    def __init__(self, xiangqi_board_instance):
        self.board_instance = xiangqi_board_instance 

    def get_piece_info(self, piece_char):
        return XiangqiBoard.PIECE_INFO.get(piece_char)

    def get_opponent_color(self, color):
        return 'black' if color == 'red' else 'red'

    def is_in_board(self, r, c):
        return 0 <= r < self.board_instance.rows and 0 <= c < self.board_instance.cols

    def is_in_palace(self, r, c, color):
        if not (3 <= c <= 5): return False
        if color == 'red': return 7 <= r <= 9
        if color == 'black': return 0 <= r <= 2
        return False

    def find_king(self, color):
        king_char = 'K' if color == 'red' else 'k'
        for r_idx in range(self.board_instance.rows):
            for c_idx in range(self.board_instance.cols):
                if self.board_instance.board[r_idx][c_idx] == king_char:
                    return r_idx, c_idx
        return None

    def generals_facing(self):
        red_king_pos = self.find_king('red')
        black_king_pos = self.find_king('black')
        if not red_king_pos or not black_king_pos: return True 
        r_red, c_red = red_king_pos
        r_black, c_black = black_king_pos
        if c_red != c_black: return False
        for r_path in range(min(r_red, r_black) + 1, max(r_red, r_black)):
            if self.board_instance.board[r_path][c_red] is not None:
                return False
        return True

    def get_raw_moves_for_piece(self, r_start, c_start):
        moves = []
        piece_char = self.board_instance.get_piece_at(r_start, c_start)
        if not piece_char: return []

        piece_info = self.get_piece_info(piece_char)
        if not piece_info: return [] 
        
        color = piece_info['color']
        piece_type = piece_info['type']
        board_array = self.board_instance.board 
        current_pos_tuple = (r_start, c_start)

        if piece_type == GENERAL:
            for dr, dc in [(0, 1), (0, -1), (1, 0), (-1, 0)]:
                nr, nc = r_start + dr, c_start + dc
                if self.is_in_palace(nr, nc, color):
                    target_piece_char = board_array[nr][nc]
                    if target_piece_char is None or (self.get_piece_info(target_piece_char) and self.get_piece_info(target_piece_char)['color'] != color):
                        moves.append((current_pos_tuple, (nr, nc)))
            # Bay Tướng (chỉ khi nước đi đó là bắt Tướng đối phương trực tiếp)
            opp_king_pos = self.find_king(self.get_opponent_color(color))
            if opp_king_pos:
                r_opp_king, c_opp_king = opp_king_pos
                if c_start == c_opp_king: 
                    is_clear_path = True
                    for r_path in range(min(r_start, r_opp_king) + 1, max(r_start, r_opp_king)):
                        if board_array[r_path][c_start] is not None:
                            is_clear_path = False
                            break
                    if is_clear_path: # Nếu đường đi trống, Tướng có thể "bay" để ăn Tướng đối phương
                        moves.append((current_pos_tuple, (r_opp_king, c_opp_king))) 

        elif piece_type == ADVISOR:
            for dr, dc in [(1,1), (1,-1), (-1,1), (-1,-1)]: 
                nr, nc = r_start + dr, c_start + dc
                if self.is_in_palace(nr, nc, color): 
                    target_piece_char = board_array[nr][nc]
                    if target_piece_char is None or (self.get_piece_info(target_piece_char) and self.get_piece_info(target_piece_char)['color'] != color):
                        moves.append((current_pos_tuple, (nr,nc)))

        elif piece_type == ELEPHANT:
            for dr, dc in [(2,2), (2,-2), (-2,2), (-2,-2)]: 
                nr, nc = r_start + dr, c_start + dc
                block_r, block_c = r_start + dr//2, c_start + dc//2 
                river_crossed = (color == 'red' and nr < 5) or (color == 'black' and nr > 4)
                if self.is_in_board(nr, nc) and not river_crossed and \
                   self.is_in_board(block_r, block_c) and board_array[block_r][block_c] is None: 
                    target_piece_char = board_array[nr][nc]
                    if target_piece_char is None or (self.get_piece_info(target_piece_char) and self.get_piece_info(target_piece_char)['color'] != color):
                        moves.append((current_pos_tuple, (nr,nc)))

        elif piece_type == HORSE:
            # dr, dc: hướng di chuyển của Mã
            # lr_off, lc_off: offset để tìm ô cản chân Mã (leg)
            horse_leg_offsets = [
                ((-2, -1), (-1, 0)), ((-2, 1), (-1, 0)),  # Lên 2, trái/phải 1 (cản ở giữa theo chiều dọc)
                ((2, -1), (1, 0)),  ((2, 1), (1, 0)),   # Xuống 2, trái/phải 1
                ((-1, -2), (0, -1)), ((-1, 2), (0, 1)),  # Lên 1, trái/phải 2 (cản ở giữa theo chiều ngang)
                ((1, -2), (0, -1)),  ((1, 2), (0, 1))   # Xuống 1, trái/phải 2
            ]
            for (dr, dc), (leg_dr, leg_dc) in horse_leg_offsets:
                nr, nc = r_start + dr, c_start + dc
                leg_r, leg_c = r_start + leg_dr, c_start + leg_dc # Vị trí cản Mã
                
                if self.is_in_board(nr,nc) and self.is_in_board(leg_r, leg_c) and board_array[leg_r][leg_c] is None: 
                    target_piece_char = board_array[nr][nc]
                    if target_piece_char is None or (self.get_piece_info(target_piece_char) and self.get_piece_info(target_piece_char)['color'] != color):
                        moves.append((current_pos_tuple, (nr,nc)))
        
        elif piece_type == CHARIOT:
            for dr, dc in [(0,1), (0,-1), (1,0), (-1,0)]: 
                for i in range(1, 10): 
                    nr, nc = r_start + dr*i, c_start + dc*i
                    if not self.is_in_board(nr, nc): break 
                    target_piece_char = board_array[nr][nc]
                    if target_piece_char is None: 
                        moves.append((current_pos_tuple, (nr,nc)))
                    else: 
                        if self.get_piece_info(target_piece_char) and self.get_piece_info(target_piece_char)['color'] != color: 
                            moves.append((current_pos_tuple, (nr,nc))) 
                        break 
        
        elif piece_type == CANNON:
            for dr, dc in [(0,1), (0,-1), (1,0), (-1,0)]: 
                jumped_over_one = False 
                for i in range(1, 10):
                    nr, nc = r_start + dr*i, c_start + dc*i
                    if not self.is_in_board(nr, nc): break
                    target_piece_char_at_dest = board_array[nr][nc]
                    if target_piece_char_at_dest is None: 
                        if not jumped_over_one: 
                            moves.append((current_pos_tuple, (nr,nc))) 
                    else: 
                        if not jumped_over_one: 
                            jumped_over_one = True 
                        else: 
                            if self.get_piece_info(target_piece_char_at_dest) and self.get_piece_info(target_piece_char_at_dest)['color'] != color: 
                                moves.append((current_pos_tuple, (nr,nc)))
                            break 
        
        elif piece_type == PAWN:
            forward_dir = -1 if color == 'red' else 1 
            nr_fwd, nc_fwd = r_start + forward_dir, c_start
            if self.is_in_board(nr_fwd, nc_fwd):
                target_piece_char = board_array[nr_fwd][nc_fwd]
                if target_piece_char is None or (self.get_piece_info(target_piece_char) and self.get_piece_info(target_piece_char)['color'] != color):
                    moves.append((current_pos_tuple, (nr_fwd, nc_fwd)))
            crossed_river = (color == 'red' and r_start < 5) or (color == 'black' and r_start > 4)
            if crossed_river:
                for dc_side in [-1, 1]: 
                    nr_side, nc_side = r_start, c_start + dc_side
                    if self.is_in_board(nr_side, nc_side):
                        target_piece_char = board_array[nr_side][nc_side]
                        if target_piece_char is None or (self.get_piece_info(target_piece_char) and self.get_piece_info(target_piece_char)['color'] != color):
                            moves.append((current_pos_tuple, (nr_side, nc_side)))
        return moves

    def is_square_attacked(self, r_target, c_target, attacker_color):
        # --- Giữ nguyên logic từ V15.0 (đã có xử lý Tướng bay) ---
        for r_attacker in range(self.board_instance.rows):
            for c_attacker in range(self.board_instance.cols):
                piece_char = self.board_instance.get_piece_at(r_attacker, c_attacker)
                if piece_char:
                    piece_info = self.get_piece_info(piece_char)
                    if piece_info and piece_info['color'] == attacker_color:
                        if piece_info['type'] == GENERAL:
                            if c_attacker == c_target:
                                is_clear_path_to_target = True
                                for r_path in range(min(r_attacker, r_target) + 1, max(r_attacker, r_target)):
                                    if self.board_instance.get_piece_at(r_path, c_attacker) is not None:
                                        is_clear_path_to_target = False; break
                                if is_clear_path_to_target: return True 
                        else:
                            raw_moves = self.get_raw_moves_for_piece(r_attacker, c_attacker)
                            for _move_from_tuple, move_to_tuple in raw_moves:
                                if move_to_tuple == (r_target, c_target):
                                    return True
        return False

    def is_square_protected(self, r_target, c_target, piece_color_at_target):
        """
        Kiểm tra xem ô (r_target, c_target) có quân của piece_color_at_target
        có được bảo vệ bởi một quân khác CÙNG MÀU piece_color_at_target không.
        Lưu ý: Quân ở (r_target, c_target) không tự bảo vệ mình trong logic này.
        Hàm này hoạt động trên self.board_instance.
        """
        protector_color = piece_color_at_target
        for r_protector in range(self.board_instance.rows):
            for c_protector in range(self.board_instance.cols):
                if r_protector == r_target and c_protector == c_target:
                    continue # Bỏ qua chính quân ở ô mục tiêu

                piece_char_protector = self.board_instance.get_piece_at(r_protector, c_protector)
                if piece_char_protector:
                    protector_info = self.get_piece_info(piece_char_protector)
                    if protector_info and protector_info['color'] == protector_color:
                        # Quân bảo vệ không thể là Tướng nếu ô mục tiêu cũng là Tướng
                        # (Tướng không tự bảo vệ mình theo nghĩa này)
                        target_piece_at_r_target_c_target = self.board_instance.get_piece_at(r_target, c_target)
                        if protector_info['type'] == GENERAL and \
                           target_piece_at_r_target_c_target and \
                           self.get_piece_info(target_piece_at_r_target_c_target)['type'] == GENERAL:
                            continue
                        
                        # Lấy các nước đi thô của quân có thể là quân bảo vệ
                        # Một quân bảo vệ một ô nếu nó có thể di chuyển đến ô đó (để bắt quân địch nếu quân địch ăn quân ở ô đó)
                        raw_moves_of_protector = self.get_raw_moves_for_piece(r_protector, c_protector)
                        for _from_sq, to_sq_potential_protection in raw_moves_of_protector:
                            if to_sq_potential_protection == (r_target, c_target):
                                # Kiểm tra thêm: nước đi bảo vệ này có hợp lệ không
                                # (tức là không tự đưa Tướng của quân bảo vệ vào thế bị chiếu)
                                # Điều này quan trọng để tránh Tướng "bảo vệ" một cách tự sát
                                temp_board_for_protection_check = XiangqiBoard(copy.deepcopy(self.board_instance.board))
                                # Giả sử quân bảo vệ di chuyển đến ô mục tiêu (để bắt quân địch đã ăn)
                                temp_board_for_protection_check.make_move((r_protector, c_protector), (r_target, c_target))
                                
                                temp_rules_for_protection = GameRules(temp_board_for_protection_check)
                                if not temp_rules_for_protection.is_king_in_check(protector_color) and \
                                   not temp_rules_for_protection.generals_facing():
                                    return True
        return False

    def is_king_in_check(self, king_color):
        # --- Giữ nguyên logic từ V15.0 ---
        king_pos = self.find_king(king_color)
        if not king_pos: return True 
        return self.is_square_attacked(king_pos[0], king_pos[1], self.get_opponent_color(king_color))

    def get_all_valid_moves(self, player_color):
        # --- Giữ nguyên logic từ V15.0 ---
        # Đảm bảo rằng khi tạo temp_rules, nó sử dụng board_instance đã được cập nhật đúng
        valid_moves = []
        for r_idx in range(self.board_instance.rows):
            for c_idx in range(self.board_instance.cols):
                piece_char = self.board_instance.get_piece_at(r_idx, c_idx)
                if piece_char:
                    piece_info = self.get_piece_info(piece_char)
                    if piece_info and piece_info['color'] == player_color:
                        raw_moves_for_this_piece = self.get_raw_moves_for_piece(r_idx, c_idx)
                        for move_from_tuple, move_to_tuple in raw_moves_for_this_piece:
                            original_board_data = copy.deepcopy(self.board_instance.board)
                            temp_board_obj = XiangqiBoard(original_board_data)
                            temp_board_obj.make_move(move_from_tuple, move_to_tuple)
                            temp_rules = GameRules(temp_board_obj) # temp_rules sẽ dùng temp_board_obj
                            if not temp_rules.is_king_in_check(player_color) and \
                               not temp_rules.generals_facing():
                                valid_moves.append((move_from_tuple, move_to_tuple, piece_char))
        return valid_moves

    def is_checkmate(self, player_color):
        # --- Giữ nguyên logic từ V15.0 ---
        if not self.is_king_in_check(player_color): return False, None 
        possible_moves = self.get_all_valid_moves(player_color)
        if not possible_moves: return True, self.get_opponent_color(player_color) 
        return False, None 

    def is_stalemate(self, player_color):
        # --- Giữ nguyên logic từ V15.0 ---
        if self.is_king_in_check(player_color): return False 
        possible_moves = self.get_all_valid_moves(player_color)
        return not possible_moves 

    def check_threefold_repetition_from_history(self, current_board_tuple, player_to_move_for_current_board, full_board_history_tuples):
        # --- Giữ nguyên logic từ V14.1 ---
        if not full_board_history_tuples: return False
        current_entry_to_check = (current_board_tuple, player_to_move_for_current_board)
        count = 0
        for hist_board_tuple, hist_player_to_move in full_board_history_tuples:
            if hist_board_tuple == current_entry_to_check[0] and hist_player_to_move == current_entry_to_check[1]:
                count +=1
        return count >= 3

    @staticmethod
    def coords_to_uci(from_sq, to_sq, board_rows=10):
        # --- Giữ nguyên logic từ V15.0 ---
        r1, c1 = from_sq; r2, c2 = to_sq
        try:
            col_char_map = "abcdefghi"
            from_uci = f"{col_char_map[c1]}{r1}"
            to_uci = f"{col_char_map[c2]}{r2}"
            return f"{from_uci}{to_uci}"
        except IndexError: return None

    @staticmethod
    def uci_to_coords(uci_move_str, board_rows=10):
        # --- Giữ nguyên logic từ V15.0 ---
        if not uci_move_str or len(uci_move_str) != 4: return None
        try:
            col_char_map = "abcdefghi"
            c1 = col_char_map.index(uci_move_str[0])
            r1 = int(uci_move_str[1])
            c2 = col_char_map.index(uci_move_str[2])
            r2 = int(uci_move_str[3])
            if not (0 <= r1 < board_rows and 0 <= c1 < 9 and 0 <= r2 < board_rows and 0 <= c2 < 9):
                return None
            return ((r1, c1), (r2, c2))
        except (ValueError, IndexError): return None
