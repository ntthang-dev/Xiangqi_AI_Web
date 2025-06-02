# File: backend/engine/book_knowledge.py
# Version: V15.0 - Tích hợp Sát Pháp, Chiến Thuật, Mirroring, Cải thiện Cờ Tàn

import json
import os
import glob
from .board import XiangqiBoard # Cần XiangqiBoard để thao tác với board khi nhận diện
from .rules import GameRules    # Có thể cần rules để kiểm tra một số điều kiện

class BookKnowledge:
    def __init__(self, data_directory="engine/book_data"):
        self.all_endgame_studies = []  # Lưu tất cả các study cờ tàn
        self.endgame_studies_by_fen = {} # Index theo FEN (có thể giữ lại cho khớp nhanh)
        self.endgame_studies_by_id = {}

        self.opening_book_lines = []
        self.kill_patterns = [] # Sát Pháp
        self.midgame_tactics = [] # Chiến thuật trung cuộc

        self.STANDARD_INITIAL_FEN_BOARD_PART = "rnbakabnr/9/1c5c1/p1p1p1p1p/9/9/P1P1P1P1P/1C5C1/9/RNBAKABNR"

        base_dir = os.path.dirname(os.path.abspath(__file__))
        full_data_directory = os.path.join(base_dir, data_directory)

        if not os.path.isdir(full_data_directory):
            print(f"LỖI BOOK: Không tìm thấy thư mục dữ liệu sách tại {full_data_directory}")
            return

        # --- Tải Sách Khai Cuộc (Chapter 4) ---
        opening_file_path = os.path.join(full_data_directory, "chapter4_openings.json")
        if os.path.exists(opening_file_path):
            try:
                with open(opening_file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.opening_book_lines = data.get("openings", [])
                    print(f"INFO BOOK: Đã tải {len(self.opening_book_lines)} dòng khai cuộc từ {opening_file_path}")
            except Exception as e:
                print(f"LỖI BOOK: Xảy ra lỗi khi tải sách khai cuộc {opening_file_path}: {e}")
        else:
            print(f"CẢNH BÁO BOOK: Không tìm thấy tệp sách khai cuộc: {opening_file_path}")

        # --- Tải Sách Cờ Tàn (Chapter 2) ---
        endgame_file_path = os.path.join(full_data_directory, "chapter2_endgames.json")
        if os.path.exists(endgame_file_path):
            try:
                with open(endgame_file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    for section in data.get("sections", []):
                        for study in section.get("studies", []):
                            self.all_endgame_studies.append(study)
                            self.endgame_studies_by_id[study["study_id"]] = study
                            if "initial_fen" in study and "player_to_move_in_fen" in study:
                                fen_board_part = study['initial_fen'].split(' ')[0]
                                player_char = 'w' if study['player_to_move_in_fen'] == 'red' else 'b'
                                fen_key = f"{fen_board_part}_{player_char}"
                                self.endgame_studies_by_fen[fen_key] = study # Vẫn giữ để khớp FEN nhanh
                    print(f"INFO BOOK: Đã tải {len(self.all_endgame_studies)} thế cờ tàn từ {endgame_file_path}")
            except Exception as e:
                print(f"LỖI BOOK: Xảy ra lỗi khi tải sách cờ tàn {endgame_file_path}: {e}")
        else:
            print(f"CẢNH BÁO BOOK: Không tìm thấy tệp sách cờ tàn: {endgame_file_path}")

        # --- Tải Sách Sát Pháp (Chapter 3) ---
        kill_patterns_file_path = os.path.join(full_data_directory, "chapter3_kill_patterns.json")
        if os.path.exists(kill_patterns_file_path):
            try:
                with open(kill_patterns_file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.kill_patterns = data.get("kill_patterns", [])
                    print(f"INFO BOOK: Đã tải {len(self.kill_patterns)} sát pháp từ {kill_patterns_file_path}")
            except Exception as e:
                print(f"LỖI BOOK: Xảy ra lỗi khi tải sách sát pháp {kill_patterns_file_path}: {e}")
        else:
            print(f"CẢNH BÁO BOOK: Không tìm thấy tệp sách sát pháp: {kill_patterns_file_path}")
            # Tạo file mẫu nếu không có
            self._create_sample_kill_patterns_file(kill_patterns_file_path)


        # --- Tải Sách Chiến Thuật Trung Cuộc (Chapter 5) ---
        midgame_tactics_file_path = os.path.join(full_data_directory, "chapter5_midgame_tactics.json")
        if os.path.exists(midgame_tactics_file_path):
            try:
                with open(midgame_tactics_file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.midgame_tactics = data.get("midgame_tactics", [])
                    print(f"INFO BOOK: Đã tải {len(self.midgame_tactics)} chiến thuật trung cuộc từ {midgame_tactics_file_path}")
            except Exception as e:
                print(f"LỖI BOOK: Xảy ra lỗi khi tải sách chiến thuật trung cuộc {midgame_tactics_file_path}: {e}")
        else:
            print(f"CẢNH BÁO BOOK: Không tìm thấy tệp sách chiến thuật trung cuộc: {midgame_tactics_file_path}")
            self._create_sample_midgame_tactics_file(midgame_tactics_file_path)

    def _create_sample_kill_patterns_file(self, file_path):
        sample_data = {
            "kill_patterns": [
                {
                    "pattern_id": "KP_THIET_MON_THUYEN_EXAMPLE",
                    "name": "Thiết Môn Thuyên (Ví dụ)",
                    "description": "Pháo Xe phối hợp chiếu bí Tướng ở đáy.",
                    "recognition_logic_description": "Red Chariot on file X, Red Cannon on file Y aiming at king, opponent king on baseline, limited escapes.",
                    "key_pieces_red": {"R": ["on_enemy_baseline_open_file"], "C": ["controls_king_escape_route_or_supports_chariot"]},
                    "key_pieces_black_king_pos": "baseline_limited_advisor",
                    "solution_uci_sequence_for_red": ["h2e2", "e2e0"], # Ví dụ
                    "priority": 100 # Độ ưu tiên cao
                }
            ]
        }
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(sample_data, f, indent=2, ensure_ascii=False)
            print(f"INFO BOOK: Đã tạo tệp mẫu sách sát pháp: {file_path}")
        except Exception as e:
            print(f"LỖI BOOK: Không thể tạo tệp mẫu sách sát pháp: {e}")

    def _create_sample_midgame_tactics_file(self, file_path):
        sample_data = {
            "midgame_tactics": [
                {
                    "tactic_id": "MT_DOUBLE_CANNON_ATTACK",
                    "name": "Song Pháo Công Phá (Ví dụ)",
                    "description": "Sử dụng hai Pháo để tấn công mạnh vào một cánh hoặc trung lộ.",
                    "conditions_description": "Hai Pháo của người chơi còn trên bàn, có không gian hoạt động, đối phương có điểm yếu ở một khu vực.",
                    "general_objectives": ["break_defense_line", "attack_king_flank"],
                    "prioritized_move_types_for_player": ["cannon_attack", "cannon_positioning_for_attack"],
                    "piece_requirements": {"C": 2} # Cần ít nhất 2 Pháo
                }
            ]
        }
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(sample_data, f, indent=2, ensure_ascii=False)
            print(f"INFO BOOK: Đã tạo tệp mẫu sách chiến thuật trung cuộc: {file_path}")
        except Exception as e:
            print(f"LỖI BOOK: Không thể tạo tệp mẫu sách chiến thuật trung cuộc: {e}")


    # --- Mirroring Logic ---
    def _mirror_row_col(self, r, c):
        """ Lật tọa độ (r,c) từ góc nhìn Đỏ sang Đen và ngược lại. """
        return 9 - r, 8 - c

    def _mirror_piece_char(self, piece_char):
        """ Đổi màu quân cờ. """
        if not piece_char: return None
        return piece_char.lower() if 'A' <= piece_char <= 'Z' else piece_char.upper()

    def get_mirrored_board_tuple(self, board_tuple_original_perspective):
        """
        Lật toàn bộ bàn cờ (dạng tuple) sang góc nhìn của đối phương.
        Quân Đỏ thành Đen, Đen thành Đỏ, và vị trí bị lật.
        """
        mirrored_board_list = [[None for _ in range(9)] for _ in range(10)]
        for r_orig in range(10):
            for c_orig in range(9):
                piece_orig = board_tuple_original_perspective[r_orig][c_orig]
                if piece_orig:
                    mr, mc = self._mirror_row_col(r_orig, c_orig)
                    mirrored_board_list[mr][mc] = self._mirror_piece_char(piece_orig)
        return tuple(map(tuple, mirrored_board_list))

    def mirror_uci_move(self, uci_move_str_original_perspective):
        """
        Lật một nước đi UCI sang góc nhìn của đối phương.
        Ví dụ: Đỏ đi b7e7 (Pháo (7,1) -> (7,4))
        Nếu lật sang Đen, thì Pháo Đen ở vị trí tương ứng (2,1) sẽ đi đến (2,4)
        Tọa độ (r,c) của Đỏ: (7,1) -> (7,4)
        Tọa độ lật (9-r, 8-c): (2,7) -> (2,4)
        UCI của Đen: h2e2
        """
        if not uci_move_str_original_perspective or len(uci_move_str_original_perspective) != 4:
            return None
        
        coords = GameRules.uci_to_coords(uci_move_str_original_perspective)
        if not coords: return None
        (r1_orig, c1_orig), (r2_orig, c2_orig) = coords

        r1_mir, c1_mir = self._mirror_row_col(r1_orig, c1_orig)
        r2_mir, c2_mir = self._mirror_row_col(r2_orig, c2_orig)
        
        return GameRules.coords_to_uci((r1_mir, c1_mir), (r2_mir, c2_mir))


    # --- Tra Cứu Sách ---
    def get_book_move_for_position(self, current_board_obj, player_to_move_color, game_kifu_uci_list=None):
        """
        Lấy nước đi khai cuộc từ sách.
        Nếu player_to_move_color là Đen, bàn cờ và kifu sẽ được lật trước khi tra cứu.
        """
        if game_kifu_uci_list is None: game_kifu_uci_list = []

        board_to_check = current_board_obj
        kifu_to_check = game_kifu_uci_list
        is_mirrored_query = False

        if player_to_move_color == 'black':
            # Tạo board lật để tra cứu (sách thường theo góc nhìn Đỏ đi trước)
            mirrored_board_tuple = self.get_mirrored_board_tuple(current_board_obj.to_tuple())
            board_to_check = XiangqiBoard() # Tạo instance mới
            board_to_check.board = [list(row) for row in mirrored_board_tuple]
            
            kifu_to_check = [self.mirror_uci_move(uci) for uci in game_kifu_uci_list if uci] # Lật kifu
            is_mirrored_query = True
            # print(f"DEBUG BOOK (Black Query): Original Kifu: {game_kifu_uci_list}, Mirrored Kifu: {kifu_to_check}")


        num_game_moves_made = len(kifu_to_check)
        # Sách khai cuộc thường giả định Đỏ đi trước trên board chuẩn
        # Nếu is_mirrored_query là True, nghĩa là Đen đang tìm nước,
        # thì lượt đi trong sách sẽ là của Đỏ (nếu num_game_moves_made chẵn) hoặc Đen (nếu lẻ)
        # trên bàn cờ đã lật.

        for opening_line in self.opening_book_lines:
            book_fen_board_part = opening_line.get("applies_to_fen_board", self.STANDARD_INITIAL_FEN_BOARD_PART)
            # Sách khai cuộc của chúng ta luôn bắt đầu từ thế chuẩn cho Đỏ
            if board_to_check.convert_to_fen('red').split(' ')[0] != book_fen_board_part and num_game_moves_made == 0:
                 # Chỉ kiểm tra FEN ban đầu nếu chưa có nước nào được đi
                 # Hoặc, nếu sách của bạn có các dòng bắt đầu từ FEN khác, logic này cần thay đổi
                continue
            
            book_uci_sequence = opening_line.get("uci_sequence", [])
            if num_game_moves_made >= len(book_uci_sequence): continue # Game đã đi nhiều hơn sách

            match = True
            for i in range(num_game_moves_made):
                if kifu_to_check[i] != book_uci_sequence[i]:
                    match = False
                    break
            
            if match: # Kifu hiện tại khớp với phần đầu của dòng sách này
                # Nước đi tiếp theo trong sách là book_uci_sequence[num_game_moves_made]
                # Cần xác định xem lượt đi này có phải của player_to_move_color không
                # Trên board_to_check (có thể đã lật), ai là người đi nước book_uci_sequence[num_game_moves_made]?
                # Sách khai cuộc thường theo thứ tự Đỏ, Đen, Đỏ, Đen...
                # Nếu num_game_moves_made là chẵn (0, 2, 4...), thì là lượt Đỏ trên board_to_check
                # Nếu num_game_moves_made là lẻ (1, 3, 5...), thì là lượt Đen trên board_to_check
                
                is_red_turn_on_board_to_check = (num_game_moves_made % 2 == 0)
                
                correct_turn_for_book_move = False
                if is_mirrored_query: # AI là Đen, board_to_check là lật (Đen của AI là Đỏ trên board lật)
                    if is_red_turn_on_board_to_check: correct_turn_for_book_move = True
                else: # AI là Đỏ, board_to_check là gốc
                    if is_red_turn_on_board_to_check: correct_turn_for_book_move = True
                
                if correct_turn_for_book_move:
                    book_move_uci_for_red_on_current_board_to_check = book_uci_sequence[num_game_moves_made]
                    if is_mirrored_query:
                        # Nước này là cho Đỏ trên board lật, cần lật lại cho Đen trên board gốc
                        actual_move_for_black_ai = self.mirror_uci_move(book_move_uci_for_red_on_current_board_to_check)
                        # print(f"DEBUG BOOK (Black): Found opening '{opening_line.get('name')}', book move (Red on mirrored): {book_move_uci_for_red_on_current_board_to_check}, actual for Black: {actual_move_for_black_ai}")
                        return actual_move_for_black_ai
                    else:
                        # print(f"DEBUG BOOK (Red): Found opening '{opening_line.get('name')}', next move: {book_move_uci_for_red_on_current_board_to_check}")
                        return book_move_uci_for_red_on_current_board_to_check
        return None

    def _check_endgame_study_features(self, board_obj, player_to_move, study_features):
        """
        Kiểm tra xem các 'key_recognition_features' của một study cờ tàn có khớp với board hiện tại không.
        board_obj: XiangqiBoard instance của thế cờ hiện tại (đã được lật nếu cần).
        player_to_move: Ai là người đi trên board_obj ('red' hoặc 'black').
        study_features: List các feature string từ JSON, ví dụ ["red_one_pawn_crossed_river", "black_king_restricted"]
        """
        if not study_features: return True # Nếu không có feature nào thì coi như khớp
        
        # Cần các hàm helper để trích xuất thông tin từ board_obj
        # Ví dụ: count_pieces(board_obj, piece_type, color), is_pawn_crossed(board_obj, pawn_pos, pawn_color), ...
        # Tạm thời để trống, cần triển khai chi tiết
        # for feature in study_features:
        #     if feature == "red_one_pawn_crossed_river":
        #         # logic kiểm tra
        #         pass
        #     elif feature == "black_king_restricted":
        #         # logic kiểm tra
        #         pass
        #     # ... các feature khác
        #     else: # Feature không xác định hoặc chưa hỗ trợ
        #         return False 
        return False # Tạm thời trả về False nếu chưa có logic kiểm tra feature

    def find_endgame_study_flexibly(self, current_board_obj, player_to_move_color):
        """
        Tìm study cờ tàn phù hợp dựa trên key_recognition_features.
        """
        board_to_check = current_board_obj
        player_on_board_to_check = player_to_move_color
        is_mirrored = False

        if player_to_move_color == 'black':
            mirrored_board_tuple = self.get_mirrored_board_tuple(current_board_obj.to_tuple())
            board_to_check = XiangqiBoard()
            board_to_check.board = [list(row) for row in mirrored_board_tuple]
            player_on_board_to_check = 'red' # Trên board lật, AI (Đen) giờ là Đỏ
            is_mirrored = True

        for study in self.all_endgame_studies:
            # Study luôn được định nghĩa theo góc nhìn Đỏ đi (player_to_move_in_fen == 'red')
            if study.get("player_to_move_in_fen") != player_on_board_to_check:
                continue # Chỉ xét study mà lượt đi khớp với player trên board_to_check

            # So sánh FEN nhanh nếu có
            if "initial_fen" in study:
                study_fen_board_part = study['initial_fen'].split(' ')[0]
                current_fen_to_check_part = board_to_check.convert_to_fen(player_on_board_to_check).split(' ')[0]
                if study_fen_board_part == current_fen_to_check_part:
                    return study, is_mirrored # Khớp FEN chính xác

            # Nếu không khớp FEN, thử khớp features
            # if self._check_endgame_study_features(board_to_check, player_on_board_to_check, study.get("key_recognition_features", [])):
            #     return study, is_mirrored
        
        return None, is_mirrored # Không tìm thấy study nào

    def get_endgame_study_move_uci(self, current_board_obj, player_to_move_color, game_kifu_uci_list=None):
        """
        Lấy nước đi từ sách cờ tàn nếu thế cờ hiện tại khớp với một study.
        """
        study, was_mirrored = self.find_endgame_study_flexibly(current_board_obj, player_to_move_color)
        if not study: return None

        # Logic để xác định nước đi tiếp theo trong study dựa trên game_kifu_uci_list
        # (Cần lật kifu nếu was_mirrored)
        # Tạm thời, nếu khớp study, trả về nước đầu tiên của study nếu chưa có nước nào trong study được đi
        
        # kifu_for_study_check = []
        # if was_mirrored and game_kifu_uci_list:
        #     # Cần xác định điểm bắt đầu của endgame trong kifu và lật phần đó
        #     # Đây là phần phức tạp, tạm thời bỏ qua
        #     pass
        # else:
        #     kifu_for_study_check = game_kifu_uci_list
        
        # Giả sử nếu khớp study, và kifu của study chưa được đi, thì lấy nước đầu tiên
        if study.get("main_line_kifu") and len(study["main_line_kifu"]) > 0:
            book_move_entry = study["main_line_kifu"][0] # Lấy nước đầu tiên
            
            # Nước trong study.main_line_kifu là cho player_to_move_in_fen của study (thường là Đỏ)
            # trên FEN gốc của study.
            if book_move_entry.get("player") == study.get("player_to_move_in_fen"):
                move_uci_from_study = book_move_entry.get("move_uci")
                if move_uci_from_study:
                    if was_mirrored:
                        return self.mirror_uci_move(move_uci_from_study) # Lật lại cho Đen
                    return move_uci_from_study
        return None

    def get_kill_pattern_solution_uci(self, current_board_obj, player_color):
        """
        Nhận diện và trả về chuỗi nước đi của sát pháp nếu có.
        """
        board_to_check = current_board_obj
        player_on_board_to_check = player_color
        is_mirrored_query = False

        if player_color == 'black':
            mirrored_board_tuple = self.get_mirrored_board_tuple(current_board_obj.to_tuple())
            board_to_check = XiangqiBoard()
            board_to_check.board = [list(row) for row in mirrored_board_tuple]
            player_on_board_to_check = 'red'
            is_mirrored_query = True
        
        for pattern in self.kill_patterns:
            # Logic nhận diện pattern (Cần triển khai chi tiết)
            # Ví dụ: self._recognize_pattern(board_to_check, player_on_board_to_check, pattern.get("recognition_logic_description"), pattern.get("key_pieces_red"))
            # Tạm thời giả sử có hàm _recognize_kill_pattern
            if self._recognize_kill_pattern(board_to_check, player_on_board_to_check, pattern):
                solution_uci_for_red_on_board_to_check = pattern.get("solution_uci_sequence_for_red", [])
                if solution_uci_for_red_on_board_to_check:
                    if is_mirrored_query:
                        return [self.mirror_uci_move(uci) for uci in solution_uci_for_red_on_board_to_check if uci]
                    return solution_uci_for_red_on_board_to_check
        return None
        
    def _recognize_kill_pattern(self, board_obj, player_color_on_board, pattern_data):
        """ Hàm phụ trợ để nhận diện một sát pháp cụ thể. Cần triển khai chi tiết. """
        # Dựa vào pattern_data["recognition_logic_description"], 
        # pattern_data["key_pieces_red"], pattern_data["key_pieces_black_king_pos"]
        # Trả về True nếu khớp, False nếu không.
        # Đây là phần phức tạp, cần logic nhận diện mẫu hình.
        return False # Placeholder

    def get_midgame_tactic_guidance(self, current_board_obj, player_color):
        """
        Nhận diện chiến thuật trung cuộc và trả về gợi ý.
        """
        # (Tương tự như get_kill_pattern_solution, cần logic nhận diện và mirroring)
        # Trả về ví dụ: {"tactic_id": "MT_XYZ", "prioritized_move_types": ["cannon_attack"]}
        return None # Placeholder

    def get_mcts_expansion_priority_move_uci(self, board_obj, player_color):
        """
        Gợi ý nước đi ưu tiên cho MCTS expansion.
        Thứ tự ưu tiên: Sát pháp -> Chiến thuật trung cuộc.
        """
        # 1. Kiểm tra Sát pháp
        kill_solution_seq = self.get_kill_pattern_solution_uci(board_obj, player_color)
        if kill_solution_seq and len(kill_solution_seq) > 0:
            return kill_solution_seq[0] # Trả về nước đầu tiên của sát pháp

        # 2. Kiểm tra Chiến thuật trung cuộc (nếu có nước đi cụ thể được gợi ý)
        # tactic_guidance = self.get_midgame_tactic_guidance(board_obj, player_color)
        # if tactic_guidance and tactic_guidance.get("suggested_next_best_move_uci"):
        #    return tactic_guidance["suggested_next_best_move_uci"]
        
        return None

    def get_evaluation_for_known_endgame(self, board_obj, player_to_move_color):
        """
        Nếu là thế cờ tàn đã biết kết quả, trả về điểm đánh giá tương ứng.
        """
        study, _ = self.find_endgame_study_flexibly(board_obj, player_to_move_color)
        if study:
            goal = study.get("goal_for_player_to_move", "").lower()
            # Giả sử study được định nghĩa theo góc nhìn của player_to_move_in_fen (thường là Đỏ)
            # Nếu player_to_move_color khớp với player_to_move_in_fen của study (sau khi đã mirror nếu cần)
            
            # Đây là cách đơn giản, cần logic phức tạp hơn để xác định ai thắng/thua/hòa
            # dựa trên goal và player_to_move_color hiện tại
            if "thắng" in goal or "win" in goal:
                return 10000 # Điểm thắng (cần khớp với CHECKMATE_SCORE trong evaluation)
            elif "hòa" in goal or "draw" in goal:
                return 0 # Điểm hòa
            # "Thua" thường không được định nghĩa trực tiếp trong goal, mà là đối thủ thắng
        return None


    def get_study_info_for_fen(self, fen_string_full, player_to_move_color):
        # Hàm này có thể được giữ lại hoặc tích hợp vào find_endgame_study_flexibly
        # ... (logic cũ, có thể cần điều chỉnh với find_endgame_study_flexibly) ...
        study, _ = self.find_endgame_study_flexibly(XiangqiBoard.fen_to_board_array(fen_string_full)[0], player_to_move_color)
        if study:
            return {
                "study_id": study.get("study_id"),
                "name": study.get("name"),
                # ... các thông tin khác
            }
        return None

