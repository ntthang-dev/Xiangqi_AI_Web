# File: backend/engine/referee.py (V14 - Rà soát logic cấm lặp lại)
import copy
from .board import XiangqiBoard, GENERAL, PAWN 
from .rules import GameRules   

ACTION_TYPE_CHECK = "check"                 # Chiếu Tướng
ACTION_TYPE_CHASE_UNPROTECTED = "chase_unprotected" # Đuổi quân không được bảo vệ
ACTION_TYPE_CHASE_PROTECTED = "chase_protected"     # Đuổi quân được bảo vệ (dọa bắt)
ACTION_TYPE_THREATEN_MATE = "threaten_mate"         # Dọa chiếu bí (chưa dùng nhiều)
ACTION_TYPE_OTHER = "other"                 # Nước đi khác

REPETITION_COUNT_FOR_FORBIDDEN_ACTION = 3 # Số lần lặp lại hành động để coi là bị cấm (vd: 3 lần chiếu cùng một kiểu)
MAX_ACTION_HISTORY_LENGTH = 60 # Giới hạn độ dài lịch sử hành động để tránh quá lớn

class Referee:
    def __init__(self, main_game_rules_instance):
        # main_game_rules_instance phải có board_instance được set đúng với trạng thái hiện tại
        self.rules = main_game_rules_instance 
        self.board_instance = main_game_rules_instance.board_instance # Tham chiếu đến board của rules
        self.action_history = [] # [{player, action_type, target_key, board_tuple_after_action, move_tuple}, ...]

    def reset_history(self):
        """Reset lịch sử hành động."""
        self.action_history = []

    def _generate_target_key(self, action_type, target_info, piece_char_moved=None, acting_piece_original_pos=None):
        """
        Tạo một "khóa mục tiêu" duy nhất cho một hành động để so sánh.
        target_info: Phụ thuộc vào action_type.
            - CHECK: (king_r, king_c) của Tướng bị chiếu.
            - CHASE: ((target_r, target_c), target_piece_char) của quân bị đuổi.
        piece_char_moved: Ký tự quân vừa di chuyển.
        acting_piece_original_pos: Vị trí (r,c) ban đầu của quân vừa di chuyển.
        """
        if action_type == ACTION_TYPE_CHECK and target_info: # target_info là (r_king, c_king)
            return f"check_king_at_{target_info[0]}_{target_info[1]}"
        
        if (action_type == ACTION_TYPE_CHASE_UNPROTECTED or action_type == ACTION_TYPE_CHASE_PROTECTED) and target_info:
            target_pos, target_char = target_info # target_pos là (r,c), target_char là ký tự quân bị đuổi
            if acting_piece_original_pos and piece_char_moved:
                 # Khóa chi tiết hơn: bao gồm cả quân đuổi và vị trí gốc của nó
                 return f"chase_{target_char}_at_{target_pos[0]}_{target_pos[1]}_by_{piece_char_moved}_from_{acting_piece_original_pos[0]}_{acting_piece_original_pos[1]}"
            else: 
                 return f"chase_{target_char}_at_{target_pos[0]}_{target_pos[1]}" # Khóa ít chi tiết hơn
        
        return "no_specific_target" # Cho các hành động khác

    def record_action_in_history(self, player_color, move_tuple, action_type, target_info, board_data_after_action, piece_char_moved):
        """
        Ghi lại một hành động vào lịch sử.
        player_color: 'red' hoặc 'black' - người thực hiện hành động.
        move_tuple: ((r_from, c_from), (r_to, c_to)).
        action_type: Loại hành động (vd: ACTION_TYPE_CHECK).
        target_info: Thông tin về mục tiêu của hành động.
        board_data_after_action: Dữ liệu bàn cờ (list of lists) SAU KHI hành động được thực hiện.
        piece_char_moved: Ký tự của quân đã di chuyển.
        """
        # Chuyển đổi board_data_after_action thành tuple để có thể so sánh và hash
        board_tuple_after_action = self.board_instance.to_tuple(board_data_after_action) 
        
        action_entry = {
            "player": player_color, 
            "action_type": action_type,
            "target_key": self._generate_target_key(action_type, target_info, piece_char_moved, move_tuple[0]),
            "board_tuple_after_action": board_tuple_after_action, 
            "move_tuple": move_tuple # ((r1,c1),(r2,c2))
        }
        self.action_history.append(action_entry)

        # Giới hạn kích thước lịch sử
        if len(self.action_history) > MAX_ACTION_HISTORY_LENGTH: 
            self.action_history = self.action_history[-MAX_ACTION_HISTORY_LENGTH:]

    def check_forbidden_perpetual_action(self, offending_player_color, current_move_tuple, 
                                         current_action_type, current_target_info, 
                                         current_board_tuple_after_action, piece_char_moved,
                                         full_action_history_to_check):
        """
        Kiểm tra xem hành động hiện tại có phải là một hành động lặp lại bị cấm không.
        offending_player_color: Người chơi thực hiện hành động hiện tại.
        current_move_tuple: Nước đi hiện tại ((r_from, c_from), (r_to, c_to)).
        current_action_type: Loại hành động hiện tại.
        current_target_info: Thông tin mục tiêu của hành động hiện tại.
        current_board_tuple_after_action: Tuple bàn cờ SAU KHI thực hiện hành động hiện tại.
        piece_char_moved: Quân cờ đã di chuyển.
        full_action_history_to_check: Toàn bộ lịch sử hành động DẪN ĐẾN trạng thái này (BAO GỒM cả hành động hiện tại đang được kiểm tra).
        """
        # Luật cấm lặp lại thường cần ít nhất vài nước đi lặp lại.
        # Ví dụ, lặp lại 3 lần một hành động (chiếu, đuổi) với cùng mục tiêu và cùng thế cờ sau đó.
        # full_action_history_to_check đã bao gồm hành động hiện tại.
        # Nếu cần lặp 3 lần, thì cần ít nhất 3 entry giống nhau trong history.
        # (A đi X -> B đi Y -> A đi X -> B đi Y -> A đi X) -> A lặp X 3 lần.
        # Lịch sử cần ít nhất (3 * 2 - 1) = 5 entry nếu tính cả nước của đối thủ.
        # Hoặc đơn giản là đếm số lần xuất hiện của (hành động, thế cờ sau đó) của offending_player.
        
        if len(full_action_history_to_check) < (REPETITION_COUNT_FOR_FORBIDDEN_ACTION): # Cần ít nhất 3 hành động để xét lặp 3 lần
            return False

        # Tướng và Tốt được phép đuổi mãi (theo luật cờ tướng một số giải)
        # Tuy nhiên, luật "chiếu mãi" vẫn áp dụng cho Tướng.
        # "Đuổi mãi" (chase) bởi Tướng/Tốt không bị cấm.
        if current_action_type == ACTION_TYPE_CHASE_UNPROTECTED or current_action_type == ACTION_TYPE_CHASE_PROTECTED:
            if piece_char_moved and piece_char_moved.upper() in ['K', 'P']:
                # print(f"DEBUG Referee: Hành động đuổi bởi Tướng/Tốt ({piece_char_moved}) không bị cấm lặp lại.")
                return False # Tướng/Tốt đuổi không bị cấm (trừ khi là chiếu Tướng)

        current_target_key_for_check = self._generate_target_key(current_action_type, current_target_info, piece_char_moved, current_move_tuple[0])
        
        count = 0
        # Duyệt qua lịch sử để đếm số lần hành động này (bởi offending_player) đã xảy ra
        # và dẫn đến cùng một thế cờ (current_board_tuple_after_action)
        for hist_action in full_action_history_to_check:
            if hist_action["player"] == offending_player_color and \
               hist_action["action_type"] == current_action_type and \
               hist_action["target_key"] == current_target_key_for_check and \
               hist_action["board_tuple_after_action"] == current_board_tuple_after_action:
                count += 1
        
        # print(f"DEBUG Referee Check Forbidden: Player {offending_player_color}, Action {current_action_type}, TargetKey {current_target_key_for_check}, BoardAfter {current_board_tuple_after_action}, Count {count}")

        if count >= REPETITION_COUNT_FOR_FORBIDDEN_ACTION:
            # print(f"DEBUG Referee: Hành động bị cấm do lặp lại {count} lần!")
            return True # Bị cấm nếu lặp lại đủ số lần quy định
            
        return False

    def get_action_details(self, board_before_move_obj, move_from_tuple, move_to_tuple, piece_char_moved):
        """
        Phân tích một nước đi để xác định loại hành động (chiếu, đuổi, ...) và mục tiêu.
        board_before_move_obj: Đối tượng XiangqiBoard TRƯỚC KHI thực hiện nước đi.
        move_from_tuple: (r_from, c_from)
        move_to_tuple: (r_to, c_to)
        piece_char_moved: Ký tự quân cờ di chuyển.
        Trả về: (action_type, target_info, board_data_after_move)
                 board_data_after_move là list of lists.
        """
        r_from, c_from = move_from_tuple
        r_to, c_to = move_to_tuple
        
        action_type = ACTION_TYPE_OTHER
        target_info = None 
        
        # Tạo một bản sao của board TRƯỚC KHI đi để thử nước đi
        temp_board_after_move_obj = XiangqiBoard(copy.deepcopy(board_before_move_obj.board))
        # Thực hiện nước đi trên board tạm để lấy captured_piece và trạng thái sau nước đi
        captured_piece_char_on_target = temp_board_after_move_obj.make_move(move_from_tuple, move_to_tuple)
        
        # Tạo rules tạm thời cho board SAU KHI đi
        temp_rules_after_move = GameRules(temp_board_after_move_obj)
        
        moving_piece_info = self.rules.get_piece_info(piece_char_moved)
        if not moving_piece_info: # Không thể xảy ra nếu piece_char_moved hợp lệ
            return ACTION_TYPE_OTHER, None, temp_board_after_move_obj.board

        moving_piece_color = moving_piece_info['color']
        opponent_color = self.rules.get_opponent_color(moving_piece_color)

        # 1. Kiểm tra có phải là nước CHIẾU Tướng không?
        if temp_rules_after_move.is_king_in_check(opponent_color):
            action_type = ACTION_TYPE_CHECK
            king_pos_opponent = temp_rules_after_move.find_king(opponent_color)
            target_info = king_pos_opponent # Mục tiêu là Tướng đối phương
            return action_type, target_info, temp_board_after_move_obj.board # Trả về board sau khi đi

        # 2. Kiểm tra có phải là nước ĐUỔI quân không?
        # Lấy các nước đi thô của quân vừa di chuyển TỪ VỊ TRÍ MỚI của nó
        # trên temp_board_after_move_obj
        raw_moves_of_moved_piece_from_new_pos = temp_rules_after_move.get_raw_moves_for_piece(r_to, c_to)
        
        potential_chase_targets = [] # List các ((pos), char) mà quân vừa đi có thể bắt ở nước tiếp theo
        if raw_moves_of_moved_piece_from_new_pos:
            for _f_ignored, to_potential_target_sq_tuple in raw_moves_of_moved_piece_from_new_pos:
                # Xem quân gì ở ô đích của những nước đi thô này trên temp_board_after_move_obj
                char_at_potential_target = temp_board_after_move_obj.get_piece_at(to_potential_target_sq_tuple[0], to_potential_target_sq_tuple[1])
                if char_at_potential_target:
                    info_potential_target = self.rules.get_piece_info(char_at_potential_target)
                    # Nếu là quân đối phương và không phải Tướng (Tướng không bị "đuổi" theo nghĩa thông thường)
                    if info_potential_target and info_potential_target['color'] == opponent_color and info_potential_target['type'] != GENERAL:
                        potential_chase_targets.append((to_potential_target_sq_tuple, char_at_potential_target))
        
        if potential_chase_targets:
            # Ưu tiên mục tiêu giá trị nhất hoặc một logic nào đó nếu có nhiều mục tiêu đuổi
            # Tạm thời lấy mục tiêu đầu tiên tìm thấy
            chased_target_pos_tuple, chased_target_char = potential_chase_targets[0]
            target_info = (chased_target_pos_tuple, chased_target_char) # Mục tiêu là (vị trí quân bị đuổi, ký tự quân bị đuổi)

            # Phân biệt đuổi quân được bảo vệ hay không
            # Kiểm tra xem ô chased_target_pos_tuple có được đối phương bảo vệ không
            # TRÊN temp_board_after_move_obj (board SAU KHI quân của ta đã di chuyển đến (r_to, c_to))
            if temp_rules_after_move.is_square_attacked(chased_target_pos_tuple[0], chased_target_pos_tuple[1], moving_piece_color):
                action_type = ACTION_TYPE_CHASE_PROTECTED # Quân bị đuổi đang được BẢO VỆ bởi quân CÙNG MÀU với nó
            else:
                action_type = ACTION_TYPE_CHASE_UNPROTECTED # Quân bị đuổi KHÔNG được bảo vệ
        
        # Nếu không phải chiếu hoặc đuổi, thì là ACTION_TYPE_OTHER
        return action_type, target_info, temp_board_after_move_obj.board
