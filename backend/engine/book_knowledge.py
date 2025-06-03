# File: backend/engine/book_knowledge.py
# Version: V17.4 - Tinh chỉnh logic Khai Cuộc

import json
import os
import copy 
from .board import XiangqiBoard, GENERAL, ADVISOR, ELEPHANT, HORSE, CHARIOT, CANNON, PAWN
from .rules import GameRules 

class BookKnowledge:
    def __init__(self, data_directory_name="book_data"):
        self.all_endgame_studies = []
        self.opening_book_lines = [] # Sẽ chứa các dictionary khai cuộc
        self.kill_patterns = [] 
        self.midgame_tactics = [] 

        self.STANDARD_INITIAL_FEN_BOARD_PART = "rnbakabnr/9/1c5c1/p1p1p1p1p/9/9/P1P1P1P1P/1C5C1/9/RNBAKABNR"
        self.current_rules_instance = None 
        self.current_board_for_feature_check = None # Board (đã lật về Red POV nếu cần)

        base_dir_of_this_file = os.path.dirname(os.path.abspath(__file__))
        full_data_directory = os.path.join(base_dir_of_this_file, data_directory_name)

        if not os.path.isdir(full_data_directory):
            print(f"LỖI BOOK: Không tìm thấy thư mục dữ liệu sách tại {full_data_directory}")
            return
        self._load_data(full_data_directory)

    def set_current_context_for_feature_checking(self, board_obj_red_pov, rules_obj_red_pov):
        self.current_board_for_feature_check = board_obj_red_pov
        self.current_rules_instance = rules_obj_red_pov
        if self.current_rules_instance and self.current_board_for_feature_check:
            self.current_rules_instance.board_instance = self.current_board_for_feature_check

    def _load_data(self, data_dir):
        openings_path = os.path.join(data_dir, "chapter4_openings.json")
        if os.path.exists(openings_path):
            try:
                with open(openings_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.book_chapter_info_opening = data.get("book_chapter_info", {})
                    self.opening_book_lines = data.get("openings", []) # Lưu toàn bộ danh sách các dictionary
                print(f"INFO BOOK: Đã tải {len(self.opening_book_lines)} khai cuộc. Thông tin chương: {self.book_chapter_info_opening.get('title_vi')}")
            except Exception as e: print(f"LỖI BOOK (Khai cuộc): {e}")
        else: print(f"CẢNH BÁO BOOK: Không tìm thấy tệp sách khai cuộc: {openings_path}")

        endgames_path = os.path.join(data_dir, "chapter2_endgames.json")
        if os.path.exists(endgames_path):
            try:
                with open(endgames_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.book_chapter_info_endgame = data.get("book_chapter_info", {}) 
                    self.all_endgame_studies = data.get("endgame_studies", [])
                print(f"INFO BOOK: Đã tải {len(self.all_endgame_studies)} thế cờ tàn. Thông tin chương: {self.book_chapter_info_endgame.get('title_vi')}")
            except Exception as e: print(f"LỖI BOOK (Cờ Tàn): {e}")
        else: print(f"CẢNH BÁO BOOK: Không tìm thấy tệp sách cờ tàn: {endgames_path}")
        
        kill_patterns_path = os.path.join(data_dir, "chapter3_kill_patterns.json")
        if os.path.exists(kill_patterns_path):
            try:
                with open(kill_patterns_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.book_chapter_info_kill = data.get("book_chapter_info", {})
                    self.kill_patterns = data.get("kill_patterns", [])
                print(f"INFO BOOK: Đã tải {len(self.kill_patterns)} sát pháp. Thông tin chương: {self.book_chapter_info_kill.get('title_vi')}")
            except Exception as e: print(f"LỖI BOOK (Sát Pháp): {e}")
        else: print(f"CẢNH BÁO BOOK: Không tìm thấy tệp sách sát pháp: {kill_patterns_path}")

        midgame_tactics_path = os.path.join(data_dir, "chapter5_midgame_tactics.json")
        if os.path.exists(midgame_tactics_path):
            try:
                with open(midgame_tactics_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.book_chapter_info_midgame = data.get("book_chapter_info", {})
                    self.midgame_tactics = data.get("midgame_tactics", [])
                print(f"INFO BOOK: Đã tải {len(self.midgame_tactics)} chiến thuật trung cuộc. Thông tin chương: {self.book_chapter_info_midgame.get('title_vi')}")
            except Exception as e: print(f"LỖI BOOK (Trung Cuộc): {e}")
        else: print(f"CẢNH BÁO BOOK: Không tìm thấy tệp sách chiến thuật trung cuộc: {midgame_tactics_path}")

    def _mirror_row_col(self, r, c): return 9 - r, 8 - c
    def _mirror_piece_char(self, p): return p.lower() if p and 'A' <= p <= 'Z' else (p.upper() if p else None)

    def get_mirrored_board_tuple(self, board_tuple_orig):
        mir_list = [[None for _ in range(9)] for _ in range(10)]
        for r_o in range(10):
            for c_o in range(9):
                p_o = board_tuple_orig[r_o][c_o]
                if p_o: mr, mc = self._mirror_row_col(r_o, c_o); mir_list[mr][mc] = self._mirror_piece_char(p_o)
        return tuple(map(tuple, mir_list))

    def mirror_uci_move(self, uci_orig):
        if not uci_orig or len(uci_orig) != 4: return None
        coords = GameRules.uci_to_coords(uci_orig)
        if not coords: return None
        (r1_o, c1_o), (r2_o, c2_o) = coords
        r1_m, c1_m = self._mirror_row_col(r1_o, c1_o); r2_m, c2_m = self._mirror_row_col(r2_o, c2_o)
        return GameRules.coords_to_uci((r1_m, c1_m), (r2_m, c2_m))

    def _get_piece_enum_from_char(self, piece_char_upper):
        # Chuyển ký tự quân cờ (in hoa) sang hằng số Enum
        if piece_char_upper == "P": return PAWN
        elif piece_char_upper == "R": return CHARIOT
        elif piece_char_upper == "H": return HORSE
        elif piece_char_upper == "C": return CANNON
        elif piece_char_upper == "A": return ADVISOR
        elif piece_char_upper == "E": return ELEPHANT
        elif piece_char_upper == "K": return GENERAL
        return None

    def _check_single_feature(self, feature_def):
        # Hàm này kiểm tra một đặc điểm (feature) cụ thể trên bàn cờ hiện tại (self.current_board_for_feature_check)
        # self.current_board_for_feature_check luôn là góc nhìn của Đỏ.
        # feature_def["player"] = "self" (Đỏ) hoặc "opponent" (Đen trên board Red POV)
        if not self.current_board_for_feature_check or not self.current_rules_instance:
            return False
        board = self.current_board_for_feature_check 
        rules = self.current_rules_instance      
        f_type = feature_def.get("type")
        f_player_role = feature_def.get("player") 
        actual_player_color = 'red' if f_player_role == "self" else 'black'

        if f_type == "piece_count_exact":
            piece_counts_def = feature_def.get("piece_counts", {})
            current_counts_on_board = {ptype: 0 for ptype in [GENERAL, ADVISOR, ELEPHANT, HORSE, CHARIOT, CANNON, PAWN]}
            for r_iter in range(10):
                for c_iter in range(9):
                    p = board.get_piece_at(r_iter, c_iter)
                    if p:
                        p_info = rules.get_piece_info(p) 
                        if p_info and p_info['color'] == actual_player_color:
                            current_counts_on_board[p_info['type']] +=1
            for piece_char_key_def, expected_count_def in piece_counts_def.items():
                piece_enum_def = self._get_piece_enum_from_char(piece_char_key_def.upper())
                if piece_enum_def is None: return False 
                if current_counts_on_board.get(piece_enum_def, 0) != expected_count_def: return False 
            return True
        elif f_type == "pawn_status":
            pawn_char_upper_def = feature_def.get("pawn_char_upper") 
            if not pawn_char_upper_def : return False
            pawn_char_to_find = pawn_char_upper_def if actual_player_color == 'red' else pawn_char_upper_def.lower()
            status_any_of = feature_def.get("status_any_of", [])
            on_which_pawns_def = feature_def.get("on_which_pawns", "any")
            if not status_any_of: return True 
            found_pawns_matching_status = 0
            total_pawns_of_player = 0
            for r_iter in range(10):
                for c_iter in range(9):
                    if board.get_piece_at(r_iter, c_iter) == pawn_char_to_find:
                        total_pawns_of_player += 1
                        is_red_pawn_on_red_pov_board = (actual_player_color == 'red')
                        crossed = (is_red_pawn_on_red_pov_board and r_iter < 5) or (not is_red_pawn_on_red_pov_board and r_iter > 4) 
                        current_pawn_status_str = ""
                        if crossed:
                            if (is_red_pawn_on_red_pov_board and r_iter == 0) or (not is_red_pawn_on_red_pov_board and r_iter == 9): current_pawn_status_str = "at_baseline"
                            elif (is_red_pawn_on_red_pov_board and r_iter <= 1) or (not is_red_pawn_on_red_pov_board and r_iter >= 8): current_pawn_status_str = "crossed_river_deep"
                            elif (is_red_pawn_on_red_pov_board and r_iter <= 2) or (not is_red_pawn_on_red_pov_board and r_iter >= 7): current_pawn_status_str = "crossed_river_middle"
                            else: current_pawn_status_str = "just_crossed_river" 
                        else: current_pawn_status_str = "not_crossed_river"
                        if current_pawn_status_str in status_any_of:
                            if on_which_pawns_def == "any": return True 
                            found_pawns_matching_status += 1
            if on_which_pawns_def == "all": return total_pawns_of_player > 0 and found_pawns_matching_status == total_pawns_of_player
            return False 
        elif f_type == "king_attribute":
            king_char_upper_def = feature_def.get("king_char_upper") 
            if not king_char_upper_def : return False
            king_color_to_check = actual_player_color
            king_pos = rules.find_king(king_color_to_check) 
            if not king_pos: return False
            attribute_def = feature_def.get("attribute")
            if attribute_def == "can_oppose_pawn_advancement_or_centralized":
                if 3 <= king_pos[1] <= 5: return True 
            elif attribute_def == "restricted_by_self_pawn_and_king": pass
            elif attribute_def == "has_limited_escape_squares":
                valid_king_moves = rules.get_all_valid_moves(king_color_to_check)
                king_moves_count = sum(1 for fm, tm, pc in valid_king_moves if pc.upper() == king_char_upper_def)
                if king_moves_count <= feature_def.get("max_escape_moves", 1): return True
        elif f_type == "advisor_attribute" or f_type == "elephant_attribute":
            piece_char_upper_def = feature_def.get("advisor_char_upper") or feature_def.get("elephant_char_upper")
            if not piece_char_upper_def: return False
            piece_char_on_board = piece_char_upper_def if actual_player_color == 'red' else piece_char_upper_def.lower()
            attribute_def = feature_def.get("attribute")
            if attribute_def == "misplaced_or_vulnerable":
                for r_iter in range(10):
                    for c_iter in range(9):
                        if board.get_piece_at(r_iter, c_iter) == piece_char_on_board:
                            if rules.is_square_attacked(r_iter, c_iter, rules.get_opponent_color(actual_player_color)): return True 
                return False 
            elif attribute_def == "well_positioned_for_defense_vs_pawn": pass
        
        # --- Logic cho Sát Pháp ---
        elif f_type == "can_force_generals_facing_and_checkmate":
            # player: "self" (actual_player_color)
            checking_piece_types_def = feature_def.get("checking_piece_types", [])
            checking_piece_enums = [self._get_piece_enum_from_char(pt.upper()) for pt in checking_piece_types_def if self._get_piece_enum_from_char(pt.upper())]
            
            self_king_pos = rules.find_king(actual_player_color)
            opponent_king_pos = rules.find_king(rules.get_opponent_color(actual_player_color))
            if not self_king_pos or not opponent_king_pos: return False

            # Thử tất cả các nước đi hợp lệ của "self"
            all_self_moves = rules.get_all_valid_moves(actual_player_color)
            for move_from, move_to, piece_moved_char in all_self_moves:
                temp_board_after_self_move = XiangqiBoard(copy.deepcopy(board.board))
                captured = temp_board_after_self_move.make_move(move_from, move_to)
                temp_rules_after_self_move = GameRules(temp_board_after_self_move)

                # Kiểm tra xem sau nước đi này, Tướng đối phương có bị ép vào thế đối mặt không
                # và có quân chiếu hết trên đường đó không.
                # Đây là logic phức tạp, cần mô phỏng nước đỡ của đối phương.
                # Tạm thời, kiểm tra xem có thể tạo ra tình huống đối mặt và có quân chiếu không.
                
                # Nếu Tướng đối phương bị chiếu bởi nước đi này
                if temp_rules_after_self_move.is_king_in_check(rules.get_opponent_color(actual_player_color)):
                    # Lấy các nước đỡ chiếu của Tướng đối phương
                    opponent_escape_moves = temp_rules_after_self_move.get_all_valid_moves(rules.get_opponent_color(actual_player_color))
                    if not opponent_escape_moves: # Nếu không có nước đỡ -> chiếu bí (không phải đối mặt cười)
                        continue 
                    
                    can_force_facing_and_mate = False
                    for opp_esc_from, opp_esc_to, opp_esc_piece in opponent_escape_moves:
                        board_after_opp_escape = XiangqiBoard(copy.deepcopy(temp_board_after_self_move.board))
                        board_after_opp_escape.make_move(opp_esc_from, opp_esc_to)
                        rules_after_opp_escape = GameRules(board_after_opp_escape)
                        
                        # Kiểm tra Tướng đối mặt sau khi đối phương đỡ chiếu
                        if rules_after_opp_escape.generals_facing():
                            # Kiểm tra xem "self" có quân chiếu trên đường Tướng đối mặt không
                            # (Cần xác định cột đối mặt)
                            facing_col = rules_after_opp_escape.find_king(actual_player_color)[1] # Cột của Tướng self
                            
                            # Tìm quân của "self" có thể chiếu trên cột đó
                            for r_checker in range(10):
                                for c_checker in range(9):
                                    checker_char = board_after_opp_escape.get_piece_at(r_checker, c_checker)
                                    if checker_char:
                                        checker_info = rules_after_opp_escape.get_piece_info(checker_char)
                                        if checker_info['color'] == actual_player_color and checker_info['type'] in checking_piece_enums:
                                            # Kiểm tra xem quân này có thể chiếu Tướng đối phương trên cột facing_col không
                                            # (Logic này cần chi tiết hơn, ví dụ Pháo cần ngòi)
                                            # Tạm thời giả định nếu là Pháo/Tốt và trên đường đó thì có thể
                                            if c_checker == facing_col or (checker_info['type'] == CANNON and c_checker != facing_col): # Rất đơn giản hóa
                                                # Kiểm tra xem Tướng đối phương có bị chiếu bí không sau nước chiếu này
                                                # (Thêm một lớp mô phỏng nữa)
                                                # print(f"DEBUG BOOK: Potential 'Doi Mat Cuoi' via {piece_moved_char} {move_from}->{move_to} leading to general facing on col {facing_col} with {checker_char}")
                                                # Đây là phần khó, cần đảm bảo nước chiếu cuối cùng là chiếu bí
                                                # Tạm thời, nếu có thể tạo đối mặt và có quân trên đường đó -> True
                                                return True 
                    if can_force_facing_and_mate: return True
            return False

        elif f_type == "opponent_king_escape_limited_by_facing_rule":
            # Logic này tương tự như phần trên, kiểm tra các nước thoát của Tướng đối phương
            # có dẫn đến vi phạm luật đối mặt và bị chiếu bí không.
            return False # Placeholder

        elif f_type == "can_sacrifice_chariot_on_center_advisor":
            # player: "self"
            # Logic: Tìm Xe của "self" có thể ăn Sĩ trung lộ của đối phương không (Sĩ ở (1,4) hoặc (8,4) trên board Red POV)
            # và sau khi ăn, Tướng đối phương có bị chiếu bí hoặc mất quân lớn không.
            opponent_color = rules.get_opponent_color(actual_player_color)
            center_advisor_pos_opp = (1,4) if opponent_color == 'black' else (8,4) # Trên board Red POV
            
            if board.get_piece_at(center_advisor_pos_opp[0], center_advisor_pos_opp[1]) and \
               rules.get_piece_info(board.get_piece_at(center_advisor_pos_opp[0], center_advisor_pos_opp[1]))['type'] == ADVISOR and \
               rules.get_piece_info(board.get_piece_at(center_advisor_pos_opp[0], center_advisor_pos_opp[1]))['color'] == opponent_color:
                # Tìm Xe của "self" có thể ăn Sĩ này không
                all_self_moves = rules.get_all_valid_moves(actual_player_color)
                for move_from, move_to, piece_moved_char in all_self_moves:
                    if rules.get_piece_info(piece_moved_char)['type'] == CHARIOT and move_to == center_advisor_pos_opp:
                        # Mô phỏng nước ăn Sĩ
                        # temp_board_after_sac = XiangqiBoard(copy.deepcopy(board.board))
                        # temp_board_after_sac.make_move(move_from, move_to)
                        # temp_rules_after_sac = GameRules(temp_board_after_sac)
                        # Kiểm tra xem có chiếu bí hoặc lợi thế lớn không
                        # if temp_rules_after_sac.is_checkmate(opponent_color)[0]: return True
                        # (Thêm đánh giá lợi thế)
                        return True # Tạm thời nếu có thể ăn Sĩ trung lộ bằng Xe
            return False

        elif f_type == "supporting_piece_can_deliver_mate_after_sacrifice":
            # player: "self"
            # supporting_piece_types: ["CHARIOT", "CANNON"]
            # Logic này cần được gọi sau khi một nước thí quân (ví dụ: Xe ăn Sĩ) được mô phỏng.
            # Kiểm tra xem các quân hỗ trợ còn lại có thể chiếu bí không.
            return False # Placeholder

        print(f"WARN BOOK: Feature type '{f_type}' chưa được triển khai đầy đủ trong _check_single_feature.")
        return False 

    def _check_all_features(self, feature_list_red_pov):
        if not self.current_board_for_feature_check or not self.current_rules_instance:
            return False
        if not feature_list_red_pov: return True 
        for feature_def in feature_list_red_pov:
            if not self._check_single_feature(feature_def):
                return False 
        return True

    def get_book_move_for_opening(self, current_board_obj, player_to_move_color, game_kifu_uci_list=None):
        if game_kifu_uci_list is None: game_kifu_uci_list = []
        board_to_check_tuple = current_board_obj.to_tuple()
        kifu_to_check = list(game_kifu_uci_list)
        is_mirrored_query = False

        if player_to_move_color == 'black':
            board_to_check_tuple = self.get_mirrored_board_tuple(board_to_check_tuple)
            kifu_to_check = [self.mirror_uci_move(uci) for uci in kifu_to_check if uci]
            is_mirrored_query = True
        
        num_moves_made_in_kifu_to_check = len(kifu_to_check)

        for opening_line in self.opening_book_lines:
            book_uci_sequence = opening_line.get("uci_sequence_from_initial_fen", []) 
            if num_moves_made_in_kifu_to_check >= len(book_uci_sequence): continue
            
            if num_moves_made_in_kifu_to_check == 0:
                fen_to_apply_from_book = opening_line.get("applies_to_initial_fen_red_perspective", self.STANDARD_INITIAL_FEN_BOARD_PART + " w - - 0 1")
                board_obj_for_fen_check = XiangqiBoard(); board_obj_for_fen_check.board = [list(row) for row in board_to_check_tuple]
                current_fen_for_check = board_obj_for_fen_check.convert_to_fen('red').split(' ')[0] 
                if current_fen_for_check != fen_to_apply_from_book.split(' ')[0]:
                    continue

            match = True
            for i in range(num_moves_made_in_kifu_to_check):
                if kifu_to_check[i] != book_uci_sequence[i]: match = False; break
            
            if match:
                is_red_turn_for_next_book_move = (num_moves_made_in_kifu_to_check % 2 == 0) 
                if is_red_turn_for_next_book_move: 
                    book_move_uci = book_uci_sequence[num_moves_made_in_kifu_to_check]
                    final_move = self.mirror_uci_move(book_move_uci) if is_mirrored_query else book_move_uci
                    if final_move:
                        print(f"INFO BOOK (Opening): Matched '{opening_line.get('name_vi', 'Unknown Opening')}'. Player: {player_to_move_color}. Suggests: {final_move}. Desc: {opening_line.get('description_vi','')}")
                        return final_move
        return None

    def find_and_get_endgame_move(self, current_board_obj, player_to_move_color, game_kifu_uci_list=None):
        is_mirrored_context = (player_to_move_color == 'black')
        player_on_fen_in_study_to_match = 'red' 
        
        # AIPlayer đã gọi set_current_context_for_feature_checking với board đã lật về Red POV
        # self.current_board_for_feature_check là board Red POV
        if not self.current_board_for_feature_check or not self.current_rules_instance:
            print("ERROR BOOK: Context for endgame feature checking not set by AIPlayer.")
            return None

        matched_study_obj = None
        for study in self.all_endgame_studies:
            if study.get("player_to_move_on_fen") != player_on_fen_in_study_to_match: 
                continue

            study_fen_red_pov = study.get("initial_fen_red_perspective", "").split(' ')[0]
            current_fen_to_check_red_pov = self.current_board_for_feature_check.convert_to_fen(player_on_fen_in_study_to_match).split(' ')[0]
            
            is_match_by_fen = False
            if study_fen_red_pov and study_fen_red_pov == current_fen_to_check_red_pov:
                is_match_by_fen = True
            
            if is_match_by_fen or self._check_all_features(study.get("key_recognition_features_red_pov", [])):
                matched_study_obj = study
                match_type = "FEN" if is_match_by_fen else "Features"
                print(f"INFO BOOK (Endgame): {match_type} match for study '{matched_study_obj.get('study_id')}: {matched_study_obj.get('name_vi')}'. Goal for Red (on study FEN): {matched_study_obj.get('goal_for_red')}")
                
                if is_match_by_fen: 
                    kifu_for_red_in_study = matched_study_obj.get("main_line_kifu_uci_for_red", [])
                    if kifu_for_red_in_study:
                        # TODO: Logic so sánh kifu game với kifu study để lấy nước tiếp theo
                        next_move_uci_for_red = kifu_for_red_in_study[0] 
                        final_move_for_ai = self.mirror_uci_move(next_move_uci_for_red) if is_mirrored_context else next_move_uci_for_red
                        if final_move_for_ai:
                            print(f"INFO BOOK (Endgame): Following study (FEN match, 1st move). AI ({player_to_move_color}) plays: {final_move_for_ai}. Analysis: {matched_study_obj.get('analysis_and_comments_vi','')}")
                            return final_move_for_ai
                break 
        return None

    def get_evaluation_for_known_endgame(self, board_obj_current_perspective, player_to_evaluate_for, game_progress_score):
        # AIPlayer đã gọi set_current_context_for_feature_checking
        if not self.current_board_for_feature_check or not self.current_rules_instance: return None
        player_on_red_pov_board_to_check = 'red' 

        matched_study = None
        for study in self.all_endgame_studies:
            study_fen_red_pov = study.get("initial_fen_red_perspective", "").split(' ')[0]
            current_fen_red_pov_to_check = self.current_board_for_feature_check.convert_to_fen(player_on_red_pov_board_to_check).split(' ')[0] 
            is_match = False
            if study_fen_red_pov and study_fen_red_pov == current_fen_red_pov_to_check: is_match = True
            elif self._check_all_features(study.get("key_recognition_features_red_pov", [])): is_match = True
            if is_match: matched_study = study; break

        if matched_study:
            expected_score_for_red = matched_study.get("expected_outcome_score_for_red")
            if expected_score_for_red is not None:
                print(f"INFO BOOK (Endgame Eval): Matched study '{matched_study.get('study_id')}' for player {player_to_evaluate_for}. Expected score (Red POV): {expected_score_for_red}")
                return expected_score_for_red if player_to_evaluate_for == 'red' else -expected_score_for_red
        return None

    def get_kill_pattern_move(self, current_board_obj, player_to_move_color):
        # AIPlayer sẽ gọi set_current_context_for_feature_checking
        if not self.current_board_for_feature_check or not self.current_rules_instance: return None
        is_mirrored = (player_to_move_color == 'black')
        
        for pattern in self.kill_patterns:
            # Giả sử pattern được định nghĩa cho Đỏ (player_on_red_pov_board_to_check là 'red')
            if self._check_all_features(pattern.get("recognition_conditions_red_pov", [])): 
                solution_uci_for_red = pattern.get("solution_uci_sequence_for_player_to_move_red_pov", [])
                if solution_uci_for_red:
                    next_move_uci_for_red = solution_uci_for_red[0] 
                    final_move_for_ai = self.mirror_uci_move(next_move_uci_for_red) if is_mirrored else next_move_uci_for_red
                    if final_move_for_ai:
                        print(f"INFO BOOK (Kill Pattern): Matched '{pattern.get('pattern_id')}: {pattern.get('name_vi')}'. AI ({player_to_move_color}) plays: {final_move_for_ai}. Desc: {pattern.get('description_vi','')}")
                        return final_move_for_ai 
        return None 

    def get_midgame_tactic_info(self, current_board_obj, player_to_move_color):
        # AIPlayer sẽ gọi set_current_context_for_feature_checking
        if not self.current_board_for_feature_check or not self.current_rules_instance: return None
        # (Logic nhận diện chiến thuật chi tiết và lật bàn cờ)
        # print(f"INFO BOOK (Midgame Tactic): Recognized '{tactic.get('name_vi')}'.")
        return None 

    def get_mcts_expansion_priority_move(self, board_obj_current_perspective, player_to_move_color):
        # AIPlayer sẽ gọi set_current_context_for_feature_checking
        if not self.current_board_for_feature_check or not self.current_rules_instance: return None
        
        kill_move_uci = self.get_kill_pattern_move(board_obj_current_perspective, player_to_move_color)
        if kill_move_uci: 
            return kill_move_uci 
        
        # (Thêm gợi ý từ chiến thuật trung cuộc nếu có)
        # tactic_info = self.get_midgame_tactic_info(board_obj_current_perspective, player_to_move_color)
        # if tactic_info and tactic_info.get("suggested_priority_move_uci"):
        #    return tactic_info["suggested_priority_move_uci"]
        return None