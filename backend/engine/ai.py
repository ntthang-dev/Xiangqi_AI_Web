# File: backend/engine/ai.py
# Version: V17.4 - Sử dụng Khai Cuộc hiệu quả, hoàn thiện logic

import copy
import time
import random
import math 

from .board import XiangqiBoard, GENERAL, PAWN, CHARIOT, HORSE, CANNON 
from .rules import GameRules 
from .evaluation import Evaluation 
from .referee import Referee 
from .book_knowledge import BookKnowledge # Đảm bảo import BookKnowledge

# --- Cấu hình cho MCTS ---
MCTS_SIMULATION_BUDGET_SECONDS_RATIO = 0.60
MCTS_MIN_SIMULATIONS_FOR_RELIABLE_MOVE = 300 # Tăng nhẹ lên 300 để đảm bảo độ tin cậy cao hơn
MCTS_UCT_C = 1.414 
MCTS_ROLLOUT_DEPTH_LIMIT = 10 
MCTS_SHALLOW_AB_DEPTH_FOR_ROLLOUT = 0 

# --- Cấu hình cho Alpha-Beta và Quiescence Search ---
# Giá trị cũ 3,4,5,6 đã được điều chỉnh để phù hợp với MCTS
QUIESCENCE_MAX_DEPTH = 2 
AB_DEFAULT_MAX_DEPTH_OPENING = 4
AB_DEFAULT_MAX_DEPTH_MIDGAME = 5 
AB_DEFAULT_MAX_DEPTH_ENDGAME = 6 # Giảm nhẹ để dành thời gian cho MCTS nếu cần
AB_ABSOLUTE_MAX_DEPTH = 7    

class MCTSNode:
    """ Lớp đại diện cho một node trong cây MCTS. """
    def __init__(self, board_state_tuple, player_to_move, p_move_leading_to_node=None, parent=None, 
                 book_knowledge=None, rules_instance=None, eval_instance=None, ai_player_instance=None):
        self.board_state_tuple = board_state_tuple
        self.player_to_move = player_to_move 
        self.move_leading_to_this_node = p_move_leading_to_node 
        self.parent = parent
        self.children = [] 
        self.wins = 0.0 
        self.visits = 0
        self.rules = rules_instance
        self.evaluator = eval_instance
        self.book_knowledge = book_knowledge # BookKnowledge instance
        self.ai_player = ai_player_instance 
        self._untried_moves = None 
        self.is_terminal, self.terminal_value = self._check_terminal_and_value()

    def _get_all_possible_moves(self):
        # Trả về danh sách các nước đi (from_sq, to_sq, piece_char) chưa được thử từ node này
        # Các nước đi được sắp xếp theo một heuristic cơ bản
        if self._untried_moves is None:
            temp_board = XiangqiBoard()
            temp_board.board = [list(row) for row in self.board_state_tuple]
            
            original_rules_board = self.rules.board_instance # Lưu lại board gốc của Rules
            self.rules.board_instance = temp_board # Gán board hiện tại cho Rules để lấy nước đi
            
            raw_moves = self.rules.get_all_valid_moves(self.player_to_move)
            
            if self.ai_player and self.ai_player.evaluator: # Sắp xếp nếu có evaluator
                 original_eval_board_for_ordering = self.ai_player.evaluator.board_instance
                 self.ai_player.evaluator.board_instance = temp_board # Gán board cho evaluator để tính điểm
                 
                 raw_moves.sort(key=lambda m: self.ai_player._get_move_score_for_ordering(temp_board, m[0], m[1], m[2], 0, self.player_to_move), reverse=True)
                 
                 self.ai_player.evaluator.board_instance = original_eval_board_for_ordering # Khôi phục board cho evaluator
            
            self._untried_moves = raw_moves
            self.rules.board_instance = original_rules_board # Khôi phục board gốc cho Rules
            
        return self._untried_moves

    def is_fully_expanded(self):
        # Kiểm tra xem tất cả các nước đi từ node này đã được expand chưa
        return not self._get_all_possible_moves() # True nếu _untried_moves rỗng

    def best_child_uct(self):
        # Chọn node con tốt nhất dựa trên công thức UCT (Upper Confidence Bound 1 applied to Trees)
        if not self.children: return None
        
        # Ưu tiên node con chưa được visit
        for child in self.children:
            if child.visits == 0: return child
            
        log_total_visits = math.log(self.visits) if self.visits > 0 else 0
        
        best_child_node = None
        max_uct_value = -float('inf')

        for child_node in self.children:
            if child_node.visits == 0: return child_node # Nên được xử lý ở trên, nhưng để chắc chắn
            
            # UCT = (wins / visits) + C * sqrt(log(total_visits) / visits)
            # Vì self.wins là theo góc nhìn của self.player_to_move,
            # còn child_node.wins là theo góc nhìn của child_node.player_to_move (đối thủ của self)
            # nên cần đảo dấu exploitation_term
            exploitation_term = - (child_node.wins / child_node.visits)
            exploration_term = MCTS_UCT_C * math.sqrt(log_total_visits / child_node.visits)
            current_uct_value = exploitation_term + exploration_term
            
            if current_uct_value > max_uct_value:
                max_uct_value = current_uct_value
                best_child_node = child_node
                
        return best_child_node

    def expand(self):
        # Mở rộng node hiện tại bằng cách thêm một node con mới từ một nước đi chưa được thử
        possible_moves_to_try = self._get_all_possible_moves() 
        if not possible_moves_to_try: return None # Không còn nước đi nào để expand
        
        priority_move_uci_from_book = None
        if self.book_knowledge and self.ai_player:
            temp_board_for_book_expansion = XiangqiBoard()
            temp_board_for_book_expansion.board = [list(row) for row in self.board_state_tuple]
            
            # AIPlayer.find_best_move đã set context cho book_knowledge bằng board Red POV.
            # Nếu board_state_tuple của node này (sau khi lật về Red POV nếu cần) khớp với
            # current_board_for_feature_check của book_knowledge, thì mới gọi get_mcts_expansion_priority_move.
            # Điều này phức tạp vì MCTS tree có thể không ở Red POV.
            # Tạm thời, giả sử book_knowledge.set_current_context_for_feature_checking được gọi đúng
            # cho từng node MCTS nếu cần, hoặc get_mcts_expansion_priority_move xử lý lật bàn cờ nội bộ.
            # Cách đơn giản hơn: chỉ ưu tiên ở root node (đã xử lý trong AIPlayer.find_best_move)
            # Tuy nhiên, nếu muốn ưu tiên sâu hơn trong cây, cần logic phức tạp hơn.
            # Ở đây, ta đang ở trong 1 node con, có thể không phải Red POV.
            # AIPlayer sẽ cần set context cho BookKnowledge trước khi gọi _perform_mcts_search
            # và get_mcts_expansion_priority_move sẽ cần nhận board hiện tại của node.
            
            # Để đơn giản, MCTS expansion priority sẽ chỉ áp dụng cho root hoặc các node được set context đúng.
            # Trong hàm này, ta đang ở 1 node bất kỳ, có thể không phải là Red POV.
            # Ta cần board hiện tại của node này để lấy gợi ý.
            
            # Cần đảm bảo book_knowledge.current_board_for_feature_check được cập nhật đúng
            # với self.board_state_tuple (sau khi lật nếu cần)
            # Đây là một điểm cần xem xét kỹ lưỡng về kiến trúc.
            # Tạm thời, để MCTS chạy mà không có gợi ý sâu từ sách ở các node con,
            # trừ khi có cơ chế set context phức tạp hơn.

            # Logic đơn giản: get_mcts_expansion_priority_move phải có khả năng xử lý
            # board hiện tại (self.board_state_tuple) và player_to_move.
            # AIPlayer sẽ truyền self.book_knowledge cho root node.
            # if self.book_knowledge.current_board_for_feature_check and \
            #    self.book_knowledge.current_board_for_feature_check.to_tuple() == self.board_state_tuple:

            # AIPlayer.find_best_move đã gọi set_current_context_for_feature_checking rồi.
            # Hàm get_mcts_expansion_priority_move nên nhận board_obj và player_color
            # và tự xử lý lật bàn cờ nếu cần.
            board_for_mcts_expansion_suggestion = XiangqiBoard()
            board_for_mcts_expansion_suggestion.board = [list(r) for r in self.board_state_tuple]
            priority_move_uci_from_book = self.book_knowledge.get_mcts_expansion_priority_move(
                board_for_mcts_expansion_suggestion, self.player_to_move
            )


        move_to_expand_tuple = None 
        if priority_move_uci_from_book and self.ai_player:
            # Chuyển UCI sang tuple (from_sq, to_sq, piece_char)
            # Cần board_obj để xác định piece_char từ from_sq
            board_obj_for_uci_parse = XiangqiBoard(list(map(list,self.board_state_tuple)))
            parsed_priority_move = self.ai_player._uci_to_coords_tuple(
                priority_move_uci_from_book, self.player_to_move, board_obj_for_uci_parse
            )
            if parsed_priority_move:
                # Tìm nước đi ưu tiên trong danh sách _untried_moves
                for i, move_tuple_valid in enumerate(possible_moves_to_try):
                    if move_tuple_valid[0] == parsed_priority_move[0] and \
                       move_tuple_valid[1] == parsed_priority_move[1] and \
                       move_tuple_valid[2] == parsed_priority_move[2]: 
                        move_to_expand_tuple = possible_moves_to_try.pop(i)
                        break # Tìm thấy nước ưu tiên
        
        if not move_to_expand_tuple and possible_moves_to_try: # Nếu không có nước ưu tiên hoặc không tìm thấy
            move_to_expand_tuple = possible_moves_to_try.pop(0) # Lấy nước đầu tiên (đã được sắp xếp)
        
        if not move_to_expand_tuple: return None # Thực sự không còn nước nào

        # Tạo node con mới
        temp_board_after_move = XiangqiBoard()
        temp_board_after_move.board = [list(row) for row in self.board_state_tuple]
        temp_board_after_move.make_move(move_to_expand_tuple[0], move_to_expand_tuple[1])
        new_board_state_tuple = temp_board_after_move.to_tuple()
        next_player = self.rules.get_opponent_color(self.player_to_move)
        
        child_node = MCTSNode(new_board_state_tuple, next_player, 
                              p_move_leading_to_node=move_to_expand_tuple, 
                              parent=self,
                              book_knowledge=self.book_knowledge, rules_instance=self.rules, 
                              eval_instance=self.evaluator, ai_player_instance=self.ai_player)
        self.children.append(child_node)
        return child_node

    def _check_terminal_and_value(self):
        # Kiểm tra xem node có phải là trạng thái kết thúc (thắng/thua/hòa) không
        temp_board = XiangqiBoard()
        temp_board.board = [list(row) for row in self.board_state_tuple]
        
        original_rules_board = self.rules.board_instance # Lưu
        self.rules.board_instance = temp_board # Gán
        
        is_mate_current_player, _ = self.rules.is_checkmate(self.player_to_move)
        if is_mate_current_player: # Nếu người chơi hiện tại của node này bị chiếu bí
            self.rules.board_instance = original_rules_board # Khôi phục
            return True, -1.0 # Node này là thua cho player_to_move
            
        is_stalemate_current = self.rules.is_stalemate(self.player_to_move)
        if is_stalemate_current: # Hòa cờ
            self.rules.board_instance = original_rules_board # Khôi phục
            return True, 0.0
            
        self.rules.board_instance = original_rules_board # Khôi phục
        return False, None # Chưa kết thúc

class AIPlayer:
    def __init__(self, game_rules_instance, evaluation_instance, referee_instance, book_knowledge_instance=None):
        self.rules = game_rules_instance 
        self.evaluator = evaluation_instance 
        # Đảm bảo evaluator cũng có tham chiếu đến book_knowledge nếu cần
        if hasattr(self.evaluator, 'book_knowledge') and self.evaluator.book_knowledge is None and book_knowledge_instance:
            self.evaluator.book_knowledge = book_knowledge_instance
        if hasattr(self.evaluator, 'rules') and self.evaluator.rules is None: # Và cả rules
            self.evaluator.rules = game_rules_instance

        self.referee = referee_instance 
        self.book_knowledge = book_knowledge_instance # BookKnowledge instance
        # Đảm bảo book_knowledge có tham chiếu đến rules (rules của game hiện tại)
        if self.book_knowledge : 
             self.book_knowledge.current_rules_instance = game_rules_instance # Gán rules gốc cho book

        self.transposition_table = {} 
        self.move_count_for_eval = 0 # Số nửa nước đi đã thực hiện trong ván cờ
        self.current_search_start_time = 0
        self.time_limit_for_move = 10.0 # Giây
        self.actual_depth_reached_in_last_search = 0
        self.mcts_simulations_performed = 0
        self.initial_max_depth_for_this_call = 0 # Cho Iterative Deepening của Alpha-Beta
        self.killer_moves = {} # {depth: [(move1_tuple), (move2_tuple)]}
        self.history_heuristic_table = {} # {(piece_char, to_sq_tuple): score}
        # Gợi ý một số nước đi mở đầu tốt để tăng tốc heuristic sắp xếp
        self.PREFERRED_OPENING_MOVES_RED_UCI = { "h2e2", "b2c2", "b0b1", "h0g2", "c0c1", "g0f0", "e0d0" }
        self.PREFERRED_OPENING_MOVES_BLACK_UCI = { "h9g7", "b9c7", "a9b9", "h0g2", "c9e7", "g9f7", "e9d9" }


    def _reset_search_helpers(self):
        # Reset các cấu trúc dữ liệu phụ trợ trước mỗi lần tìm nước mới
        self.transposition_table.clear()
        self.killer_moves = {} # Killer moves thường được reset cho mỗi search mới
        # self.history_heuristic_table có thể giữ lại qua nhiều search hoặc reset tùy chiến lược
        self.actual_depth_reached_in_last_search = 0
        self.mcts_simulations_performed = 0
    
    def _uci_to_coords_tuple(self, uci_move_str, player_color_making_move, board_obj):
        # Chuyển đổi nước đi UCI (ví dụ "h2e2") sang tuple ((row_from, col_from), (row_to, col_to), piece_char_moved)
        if not uci_move_str or not board_obj: return None
        coords = GameRules.uci_to_coords(uci_move_str)
        if not coords: return None
        from_sq, to_sq = coords
        
        piece_char = board_obj.get_piece_at(from_sq[0], from_sq[1])
        if not piece_char: 
            print(f"DEBUG UCI_PARSE: Không có quân tại {from_sq} trên board_obj cho UCI {uci_move_str}")
            return None
            
        # Phải dùng rules instance phù hợp với board_obj để lấy piece_info
        rules_to_use = self.rules 
        if rules_to_use.board_instance.to_tuple() != board_obj.to_tuple():
            # Nếu board_obj khác với board hiện tại của self.rules, tạo rules tạm
            print(f"DEBUG UCI_PARSE: Tạo rules tạm cho board_obj khác với self.rules.board_instance")
            rules_to_use = GameRules(board_obj) # Khởi tạo rules mới với board_obj đó

        piece_info = rules_to_use.get_piece_info(piece_char)
        if not piece_info or piece_info['color'] != player_color_making_move:
            print(f"DEBUG UCI_PARSE: Quân {piece_char} tại {from_sq} không phải của {player_color_making_move}. Info: {piece_info}")
            return None
            
        return (from_sq, to_sq, piece_char)

    def _coords_to_uci_str(self, from_sq, to_sq):
        # Chuyển đổi tọa độ ((r1,c1), (r2,c2)) sang chuỗi UCI
        return GameRules.coords_to_uci(from_sq, to_sq)

    def _get_move_score_for_ordering(self, board_obj_before_move, move_from, move_to, piece_char_moved, current_search_ply_depth, player_color):
        # Heuristic để sắp xếp các nước đi, giúp Alpha-Beta cắt tỉa hiệu quả hơn
        original_eval_board = self.evaluator.board_instance # Lưu
        self.evaluator.board_instance = board_obj_before_move # Gán
        
        score = 0.0
        # 1. Ưu tiên nước bắt quân giá trị cao bằng quân giá trị thấp (MVV-LVA)
        piece_at_target_sq = board_obj_before_move.get_piece_at(move_to[0], move_to[1]) 
        
        game_ply_at_root = self.move_count_for_eval # Số nửa nước đi của ván cờ (không phải độ sâu tìm kiếm)

        # 1.5 Ưu tiên các nước khai cuộc thường gặp ở những nước đầu
        if game_ply_at_root < 8: # Ví dụ: trong 4 nước đầu tiên của mỗi bên
            move_uci_str = self._coords_to_uci_str(move_from, move_to)
            if move_uci_str:
                preferred_set = self.PREFERRED_OPENING_MOVES_RED_UCI if player_color == 'red' else self.PREFERRED_OPENING_MOVES_BLACK_UCI
                if move_uci_str in preferred_set:
                    score += 500 # Điểm thưởng lớn cho nước đi khai cuộc ưa thích

            # Phạt nhẹ nếu Pháo di chuyển quá sớm mà không ăn quân (để tránh Pháo lạng)
            if piece_char_moved.upper() == 'C' and not piece_at_target_sq:
                if player_color == 'red' and move_from[0] >=7 and move_to[0] < 5 and move_from[0] - move_to[0] > 2 : # Pháo đỏ từ nhà qua sông xa
                    score -= 200 
                elif player_color == 'black' and move_from[0] <=2 and move_to[0] > 4 and move_to[0] - move_from[0] > 2: # Pháo đen từ nhà qua sông xa
                    score -= 200


        # 2. Killer Moves (nếu có)
        if current_search_ply_depth in self.killer_moves: # current_search_ply_depth là độ sâu hiện tại trong cây tìm kiếm
            if (move_from, move_to) in self.killer_moves[current_search_ply_depth]:
                score += 200 # Ưu tiên cao thứ hai
        
        if piece_at_target_sq: # Nếu là nước bắt quân
            victim_val = self.evaluator.PIECE_BASE_VALUES_MIDGAME.get(piece_at_target_sq.upper(), 0)
            aggressor_val = self.evaluator.PIECE_BASE_VALUES_MIDGAME.get(piece_char_moved.upper(), 1) # Tránh chia cho 0
            score += (victim_val - aggressor_val / 10.0) * 10 # MVV/LVA
        
        # 3. Nước chiếu Tướng (có thể nguy hiểm hoặc tốt)
        # Tạo bàn cờ tạm sau khi thực hiện nước đi
        temp_board_after_move_ordering = XiangqiBoard(copy.deepcopy(board_obj_before_move.board))
        temp_board_after_move_ordering.make_move(move_from, move_to)
        
        original_rules_board_ordering = self.rules.board_instance # Lưu
        self.rules.board_instance = temp_board_after_move_ordering # Gán
        if self.rules.is_king_in_check(self.rules.get_opponent_color(player_color)): # Nếu chiếu Tướng đối phương
            score += 80 
        self.rules.board_instance = original_rules_board_ordering # Khôi phục

        # 4. History Heuristic
        history_score = self.history_heuristic_table.get((piece_char_moved, move_to), 0)
        score += history_score 

        # 5. Ưu tiên phát triển các quân mạnh ở đầu game nếu chưa có điểm cao
        if game_ply_at_root < 12 and score < 100: # Nếu điểm còn thấp và đang ở khai cuộc
            piece_type = self.rules.get_piece_info(piece_char_moved)['type']
            if piece_type in [HORSE, CHARIOT, CANNON]:
                # Ưu tiên đưa các quân này ra khỏi vị trí ban đầu
                if player_color == 'red' and move_from[0] >= 7 : # Quân đỏ còn ở nhà
                    score += 30 
                elif player_color == 'black' and move_from[0] <= 2: # Quân đen còn ở nhà
                    score += 30
        
        self.evaluator.board_instance = original_eval_board # Khôi phục
        return score

    def _update_killer_move(self, depth, move_tuple):
        # Cập nhật Killer Moves: lưu 2 nước tốt nhất không bắt quân gây beta-cutoff ở mỗi độ sâu
        if depth not in self.killer_moves:
            self.killer_moves[depth] = []
        if move_tuple not in self.killer_moves[depth]:
            self.killer_moves[depth].insert(0, move_tuple) # Thêm vào đầu
            if len(self.killer_moves[depth]) > 2: # Giữ tối đa 2 killer moves
                self.killer_moves[depth].pop()

    def _update_history_heuristic(self, piece_char, to_sq_tuple, bonus):
        # Tăng điểm cho nước đi (quân, ô tới) đã dẫn đến beta-cutoff
        current_score = self.history_heuristic_table.get((piece_char, to_sq_tuple), 0)
        self.history_heuristic_table[(piece_char, to_sq_tuple)] = current_score + bonus

    def _quiescence_search(self, current_board_obj, alpha, beta, player_to_optimize_for, 
                           current_total_half_moves, depth_remaining, is_maximizing_turn_qs):
        # Tìm kiếm tĩnh lặng: chỉ xét các nước bắt quân hoặc nước chiếu quan trọng
        original_rules_board_qs = self.rules.board_instance
        original_eval_board_qs = self.evaluator.board_instance
        self.rules.board_instance = current_board_obj
        self.evaluator.board_instance = current_board_obj

        # Đánh giá "stand-pat" (không làm gì cả)
        stand_pat_score = self.evaluator.evaluate_board(player_to_optimize_for, current_total_half_moves)
        
        current_player_for_qs_node = player_to_optimize_for if is_maximizing_turn_qs else self.rules.get_opponent_color(player_to_optimize_for)

        if is_maximizing_turn_qs:
            alpha = max(alpha, stand_pat_score)
        else:
            beta = min(beta, stand_pat_score)

        if alpha >= beta or depth_remaining == 0:
            self.rules.board_instance = original_rules_board_qs; self.evaluator.board_instance = original_eval_board_qs
            return stand_pat_score

        all_valid_moves_qs = self.rules.get_all_valid_moves(current_player_for_qs_node)
        
        # Chỉ xét các nước bắt quân (tactical moves)
        tactical_moves = []
        for move_from, move_to, piece_moved in all_valid_moves_qs:
            if current_board_obj.get_piece_at(move_to[0], move_to[1]) is not None: # Là nước bắt quân
                tactical_moves.append((move_from, move_to, piece_moved))
            # TODO: Có thể thêm cả các nước chiếu Tướng vào đây
        
        tactical_moves.sort(key=lambda m: self._get_move_score_for_ordering(current_board_obj, m[0], m[1], m[2], 0, current_player_for_qs_node), reverse=True)

        if not tactical_moves: # Nếu không có nước bắt quân nào
            self.rules.board_instance = original_rules_board_qs; self.evaluator.board_instance = original_eval_board_qs
            return stand_pat_score # Trả về điểm stand-pat

        best_val_qs = stand_pat_score # Khởi tạo với stand_pat, nếu không có nước tactical nào tốt hơn
        if not is_maximizing_turn_qs and len(tactical_moves) > 0 : best_val_qs = float('inf') 
        elif is_maximizing_turn_qs and len(tactical_moves) > 0 : best_val_qs = float('-inf')


        for move_from, move_to, piece_char_moved in tactical_moves:
            new_board_obj_qs = XiangqiBoard(copy.deepcopy(current_board_obj.board))
            new_board_obj_qs.make_move(move_from, move_to)
            
            score = self._quiescence_search(new_board_obj_qs, alpha, beta, player_to_optimize_for,
                                           current_total_half_moves + 1, depth_remaining - 1,
                                           not is_maximizing_turn_qs) # Đổi lượt
            
            if is_maximizing_turn_qs: 
                best_val_qs = max(best_val_qs, score)
                alpha = max(alpha, score)
            else: 
                best_val_qs = min(best_val_qs, score)
                beta = min(beta, score)
            
            if alpha >= beta: # Cắt tỉa
                break
        
        self.rules.board_instance = original_rules_board_qs; self.evaluator.board_instance = original_eval_board_qs
        return best_val_qs

    def _minimax_alpha_beta_recursive(self, current_board_obj, depth, alpha, beta, is_maximizing_player_turn, player_to_optimize_for, 
                                      board_history_tuples_for_repetition, action_history_for_referee, current_ply_from_root):
        # Hàm đệ quy Alpha-Beta
        self.actual_depth_reached_in_last_search = max(self.actual_depth_reached_in_last_search, self.initial_max_depth_for_this_call - depth)
        
        # Kiểm tra giới hạn thời gian
        if time.time() - self.current_search_start_time > self.time_limit_for_move:
            raise TimeoutError("AI search time limit exceeded")

        # Transposition Table Lookup
        board_tuple_for_tt = current_board_obj.to_tuple()
        tt_key = (board_tuple_for_tt, depth, is_maximizing_player_turn, player_to_optimize_for)
        if tt_key in self.transposition_table:
            tt_entry = self.transposition_table[tt_key]
            if tt_entry['depth'] >= depth: # Chỉ dùng nếu entry có độ sâu bằng hoặc lớn hơn
                if tt_entry['type'] == 'exact': return tt_entry['score']
                if tt_entry['type'] == 'lower_bound': alpha = max(alpha, tt_entry['score'])
                elif tt_entry['type'] == 'upper_bound': beta = min(beta, tt_entry['score'])
                if alpha >= beta: return tt_entry['score']

        # Lưu và thiết lập board hiện tại cho Rules, Evaluator, Referee
        original_rules_board = self.rules.board_instance
        original_eval_board = self.evaluator.board_instance
        original_referee_board = self.referee.board_instance
        self.rules.board_instance = current_board_obj
        self.evaluator.board_instance = current_board_obj
        self.referee.board_instance = current_board_obj 
        
        current_player_for_this_node = player_to_optimize_for if is_maximizing_player_turn else self.rules.get_opponent_color(player_to_optimize_for)
        
        # Kiểm tra điều kiện kết thúc đệ quy (node lá)
        is_checkmate_current, _ = self.rules.is_checkmate(current_player_for_this_node)
        is_stalemate_current = self.rules.is_stalemate(current_player_for_this_node)
        current_total_half_moves_at_node = self.move_count_for_eval + current_ply_from_root

        if depth <= 0 or is_checkmate_current or is_stalemate_current: 
            eval_score = self._quiescence_search(current_board_obj, alpha, beta, 
                                                 player_to_optimize_for, 
                                                 current_total_half_moves_at_node, 
                                                 QUIESCENCE_MAX_DEPTH,
                                                 is_maximizing_player_turn # Lượt của node hiện tại trong Alpha-Beta
                                                 )
            # Khôi phục board cho các instance
            self.rules.board_instance = original_rules_board
            self.evaluator.board_instance = original_eval_board
            self.referee.board_instance = original_referee_board
            # Lưu vào Transposition Table
            self.transposition_table[tt_key] = {'score': eval_score, 'type': 'exact', 'depth': depth}
            return eval_score

        # Kiểm tra lặp 3 lần
        current_board_tuple_for_hist = current_board_obj.to_tuple() 
        history_to_check_3fold = board_history_tuples_for_repetition + [(current_board_tuple_for_hist, current_player_for_this_node)]
        if self.rules.check_threefold_repetition_from_history(current_board_tuple_for_hist, current_player_for_this_node, history_to_check_3fold):
            self.rules.board_instance = original_rules_board
            self.evaluator.board_instance = original_eval_board
            self.referee.board_instance = original_referee_board
            self.transposition_table[tt_key] = {'score': self.evaluator.STALEMATE_SCORE, 'type': 'exact', 'depth': depth}
            return self.evaluator.STALEMATE_SCORE
        
        possible_moves_tuples = self.rules.get_all_valid_moves(current_player_for_this_node)
        if not possible_moves_tuples: # Hết nước đi hợp lệ (có thể là stalemate hoặc checkmate đã bị miss ở trên)
            eval_score = self.evaluator.evaluate_board(player_to_optimize_for, current_total_half_moves_at_node)
            self.rules.board_instance = original_rules_board
            self.evaluator.board_instance = original_eval_board
            self.referee.board_instance = original_referee_board
            self.transposition_table[tt_key] = {'score': eval_score, 'type': 'exact', 'depth': depth}
            return eval_score

        # Sắp xếp nước đi
        possible_moves_tuples.sort(key=lambda move_tuple: self._get_move_score_for_ordering(current_board_obj, move_tuple[0], move_tuple[1], move_tuple[2], depth, current_player_for_this_node), reverse=True)
        
        best_val = float('-inf') if is_maximizing_player_turn else float('inf')
        original_alpha_for_tt = alpha # Cần để xác định loại TT entry (exact, lower, upper)
        best_move_found_in_node = None # Nước đi tốt nhất tìm được ở node này

        for i, (move_from, move_to, piece_char_moved) in enumerate(possible_moves_tuples):
            # Kiểm tra luật cấm của Referee
            action_type, target_info, board_data_after_action = self.referee.get_action_details(current_board_obj, move_from, move_to, piece_char_moved)
            board_tuple_after_action = XiangqiBoard(board_data_after_action).to_tuple() # Convert sang tuple để hash
            
            current_action_entry = {"player": current_player_for_this_node, "action_type": action_type, "target_key": self.referee._generate_target_key(action_type, target_info, piece_char_moved, move_from), "board_tuple_after_action": board_tuple_after_action, "move_tuple": (move_from, move_to)}
            history_for_referee_check_this_node = action_history_for_referee + [current_action_entry]
            
            is_forbidden = self.referee.check_forbidden_perpetual_action(current_player_for_this_node, (move_from, move_to), action_type, target_info, board_tuple_after_action, piece_char_moved, history_for_referee_check_this_node )
            
            if is_forbidden:
                # Phạt nặng nếu nước đi bị cấm (thường là xử thua)
                eval_for_forbidden = -self.evaluator.CHECKMATE_SCORE * 0.95 if is_maximizing_player_turn else self.evaluator.CHECKMATE_SCORE * 0.95
                if is_maximizing_player_turn: best_val = max(best_val, eval_for_forbidden); alpha = max(alpha, eval_for_forbidden) 
                else: best_val = min(best_val, eval_for_forbidden); beta = min(beta, eval_for_forbidden)
                if alpha >= beta: break # Cắt tỉa
                continue # Bỏ qua nước đi bị cấm này

            # Tạo board mới cho node con
            new_board_hist_tuples_for_child = board_history_tuples_for_repetition + [(board_tuple_after_action, self.rules.get_opponent_color(current_player_for_this_node))]
            new_action_hist_for_child = history_for_referee_check_this_node
            new_board_obj_for_recursive_call = XiangqiBoard(board_data_after_action) # Tạo từ board_data_after_action
            
            new_depth = depth - 1 
            
            # Gọi đệ quy
            evaluation = self._minimax_alpha_beta_recursive(new_board_obj_for_recursive_call, new_depth, alpha, beta, 
                                                            not is_maximizing_player_turn, player_to_optimize_for, 
                                                            new_board_hist_tuples_for_child, new_action_hist_for_child,
                                                            current_ply_from_root + 1) 
            
            if is_maximizing_player_turn:
                if evaluation > best_val: best_val = evaluation; best_move_found_in_node = (move_from, move_to, piece_char_moved)
                alpha = max(alpha, evaluation)
            else: # Minimizing player
                if evaluation < best_val: best_val = evaluation; best_move_found_in_node = (move_from, move_to, piece_char_moved)
                beta = min(beta, evaluation)
            
            if alpha >= beta: # Cắt tỉa Alpha-Beta
                # Nếu là nước không bắt quân gây ra cắt tỉa, lưu vào Killer Moves và History Heuristic
                if not current_board_obj.get_piece_at(move_to[0], move_to[1]): # Không phải nước bắt quân
                    self._update_killer_move(depth, (move_from, move_to))
                    self._update_history_heuristic(piece_char_moved, move_to, depth * depth) # Thưởng bằng bình phương độ sâu còn lại
                break 
        
        # Khôi phục board cho các instance
        self.rules.board_instance = original_rules_board
        self.evaluator.board_instance = original_eval_board
        self.referee.board_instance = original_referee_board

        # Lưu vào Transposition Table
        tt_store_type = 'exact'
        if best_val <= original_alpha_for_tt: tt_store_type = 'upper_bound' # Giá trị thực có thể thấp hơn
        elif best_val >= beta: tt_store_type = 'lower_bound' # Giá trị thực có thể cao hơn
        self.transposition_table[tt_key] = {'score': best_val, 'type': tt_store_type, 'depth': depth, 'best_move': best_move_found_in_node if tt_store_type != 'upper_bound' else None}
        
        return best_val

    def _mcts_simulation_phase(self, node_to_simulate_from):
        # Giai đoạn mô phỏng của MCTS (Rollout)
        # Từ node lá của giai đoạn Expansion, mô phỏng ván cờ đến hết hoặc đến độ sâu giới hạn
        current_board_sim_obj = XiangqiBoard()
        current_board_sim_obj.board = [list(row) for row in node_to_simulate_from.board_state_tuple]
        current_player_sim = node_to_simulate_from.player_to_move
        
        original_ai_rules_board = self.rules.board_instance # Lưu lại board gốc của AIPlayer.rules
        original_ai_eval_board = self.evaluator.board_instance # Lưu lại board gốc của AIPlayer.evaluator
        
        # Tính toán số nước đi đã thực hiện để đến được node này từ gốc của MCTS tree
        ply_offset_mcts = 0 
        temp_node_for_ply = node_to_simulate_from
        while temp_node_for_ply.parent:
            ply_offset_mcts += 1
            temp_node_for_ply = temp_node_for_ply.parent
        rollout_move_count_start = self.move_count_for_eval + ply_offset_mcts
        
        for i_rollout in range(MCTS_ROLLOUT_DEPTH_LIMIT):
            self.rules.board_instance = current_board_sim_obj # Gán board sim cho AIPlayer.rules
            self.evaluator.board_instance = current_board_sim_obj # Gán board sim cho AIPlayer.evaluator

            is_mate_sim, _ = self.rules.is_checkmate(current_player_sim)
            if is_mate_sim:
                self.rules.board_instance = original_ai_rules_board # Khôi phục
                self.evaluator.board_instance = original_ai_eval_board # Khôi phục
                return -1.0 # Người chơi hiện tại của node mô phỏng bị chiếu bí -> thua

            if self.rules.is_stalemate(current_player_sim):
                self.rules.board_instance = original_ai_rules_board # Khôi phục
                self.evaluator.board_instance = original_ai_eval_board # Khôi phục
                return 0.0 # Hòa

            possible_moves_sim = self.rules.get_all_valid_moves(current_player_sim)
            if not possible_moves_sim: # Hết nước đi (có thể là hòa do hết nước)
                self.rules.board_instance = original_ai_rules_board # Khôi phục
                self.evaluator.board_instance = original_ai_eval_board # Khôi phục
                return 0.0 

            chosen_move_sim_tuple = None
            # Sử dụng Alpha-Beta nông để chọn nước đi trong rollout (Hybrid MCTS-AB)
            if MCTS_SHALLOW_AB_DEPTH_FOR_ROLLOUT >= 0 and i_rollout < 1: # Chỉ dùng AB cho vài nước đầu của rollout
                best_val_for_rollout_move = -float('inf') 
                alpha_r, beta_r = float('-inf'), float('inf')
                
                # Sắp xếp các nước đi đầu tiên của rollout
                possible_moves_sim.sort(key=lambda m: self._get_move_score_for_ordering(current_board_sim_obj, m[0],m[1],m[2],0,current_player_sim), reverse=True)

                # Chỉ xét vài nước đầu tiên (ví dụ 3 nước) để tiết kiệm thời gian
                for r_move_from, r_move_to, r_piece_moved in possible_moves_sim[:3]: 
                    temp_board_rollout = XiangqiBoard(copy.deepcopy(current_board_sim_obj.board))
                    temp_board_rollout.make_move(r_move_from, r_move_to)
                    
                    # Gọi Alpha-Beta cho đối thủ của current_player_sim
                    val = self._minimax_alpha_beta_recursive(
                        temp_board_rollout, MCTS_SHALLOW_AB_DEPTH_FOR_ROLLOUT, 
                        alpha_r, beta_r, False, current_player_sim, # False vì giờ là lượt đối thủ của current_player_sim
                        [], [], # Lịch sử board và action rỗng cho AB nông này
                        rollout_move_count_start + i_rollout + 1 # Số nước đi tổng cộng
                    )
                    current_move_score = -val # Vì val là điểm của đối thủ, ta muốn điểm của current_player_sim
                    if current_move_score > best_val_for_rollout_move:
                        best_val_for_rollout_move = current_move_score
                        chosen_move_sim_tuple = (r_move_from, r_move_to, r_piece_moved)
                
                if not chosen_move_sim_tuple and possible_moves_sim : # Nếu AB không tìm được, chọn nước đầu (đã sắp xếp)
                    chosen_move_sim_tuple = possible_moves_sim[0]
            
            if not chosen_move_sim_tuple: # Nếu vẫn không có (ví dụ AB sâu = -1), chọn ngẫu nhiên
                 if not possible_moves_sim: # Double check, đã có ở trên
                    self.rules.board_instance = original_ai_rules_board
                    self.evaluator.board_instance = original_ai_eval_board
                    return 0.0 
                 chosen_move_sim_tuple = random.choice(possible_moves_sim)

            current_board_sim_obj.make_move(chosen_move_sim_tuple[0], chosen_move_sim_tuple[1])
            current_player_sim = self.rules.get_opponent_color(current_player_sim)
        
        # Sau MCTS_ROLLOUT_DEPTH_LIMIT nước, đánh giá bàn cờ
        self.evaluator.board_instance = current_board_sim_obj # Gán board cuối cùng của rollout cho evaluator
        # Đánh giá từ góc nhìn của người chơi ở node_to_simulate_from (cha của chuỗi rollout này)
        final_eval_score = self.evaluator.evaluate_board(node_to_simulate_from.player_to_move, 
                                                           rollout_move_count_start + MCTS_ROLLOUT_DEPTH_LIMIT)
        
        self.rules.board_instance = original_ai_rules_board # Khôi phục board gốc cho AIPlayer.rules
        self.evaluator.board_instance = original_ai_eval_board # Khôi phục board gốc cho AIPlayer.evaluator
        
        # Chuẩn hóa kết quả về -1 (thua), 0 (hòa), 1 (thắng) cho backpropagation
        if final_eval_score > 150: return 1.0 # Thắng cho node_to_simulate_from.player_to_move
        elif final_eval_score < -150: return -1.0 # Thua
        return 0.0 # Hòa

    def _mcts_backpropagate_refined(self, path_of_nodes, final_rollout_value, player_of_rollout_leaf_node):
        # Cập nhật số lần visit và wins cho các node trên đường đi từ root đến node lá đã mô phỏng
        for node_in_path in reversed(path_of_nodes):
            node_in_path.visits += 1
            # final_rollout_value là theo góc nhìn của player_of_rollout_leaf_node
            # Nếu player_to_move của node_in_path trùng với player_of_rollout_leaf_node, thì win cộng dồn
            # Nếu khác, thì win trừ đi (vì đó là thắng/thua của đối thủ)
            if node_in_path.player_to_move == player_of_rollout_leaf_node:
                node_in_path.wins += final_rollout_value
            else:
                node_in_path.wins -= final_rollout_value # Vì rollout_value là của đối thủ node này

    def _perform_mcts_search(self, root_board_obj, player_color_ai, time_budget_seconds):
        # Thực hiện tìm kiếm MCTS
        # player_color_ai là người chơi mà AI đang tìm nước đi cho (ở root_node)
        root_node = MCTSNode(root_board_obj.to_tuple(), player_color_ai, 
                             book_knowledge=self.book_knowledge, rules_instance=self.rules, 
                             eval_instance=self.evaluator, ai_player_instance=self)
        start_mcts_time = time.time()
        sims_count = 0
        
        # Lấy và sao lưu danh sách nước đi ban đầu của gốc, phòng trường hợp MCTS không tìm được con nào
        root_node_all_moves = root_node._get_all_possible_moves() # Khởi tạo _untried_moves
        initial_root_moves_backup = list(root_node_all_moves or []) 

        if not initial_root_moves_backup: # Nếu gốc không có nước đi nào
            print(f"MCTS WARN: Root node cho {player_color_ai} không có nước đi hợp lệ nào ban đầu.")
            return None

        # Giới hạn số simulation dựa trên thời gian
        max_sims_for_budget = MCTS_MIN_SIMULATIONS_FOR_RELIABLE_MOVE * 10 # Con số lớn tùy ý ban đầu
        if time_budget_seconds < 1.0: max_sims_for_budget = MCTS_MIN_SIMULATIONS_FOR_RELIABLE_MOVE 
        elif time_budget_seconds < 0.5: max_sims_for_budget = MCTS_MIN_SIMULATIONS_FOR_RELIABLE_MOVE // 2
        max_sims_for_budget = max(10, max_sims_for_budget) # Ít nhất cũng chạy vài sim

        # Vòng lặp chính của MCTS
        while time.time() - start_mcts_time < time_budget_seconds - 0.05 and sims_count < max_sims_for_budget : # Trừ hao 0.05s
            sims_count += 1
            node_to_explore = root_node
            path = [root_node] # Đường đi từ root đến node lá được chọn
            
            # 1. Selection: Chọn node lá tốt nhất để expand
            while not node_to_explore.is_terminal:
                if not node_to_explore.is_fully_expanded(): # Nếu còn nước chưa thử
                    break # Đi đến Expansion
                selected_child = node_to_explore.best_child_uct()
                if selected_child is None: # Không có con nào (hiếm khi xảy ra nếu is_fully_expanded là False)
                    break 
                node_to_explore = selected_child
                path.append(node_to_explore)
            
            # 2. Expansion: Mở rộng node lá đã chọn (nếu chưa phải terminal và chưa fully expanded)
            if not node_to_explore.is_terminal and not node_to_explore.is_fully_expanded():
                expanded_child = node_to_explore.expand()
                if expanded_child: # Nếu expand thành công
                    node_to_explore = expanded_child # Chuyển sang node con mới để mô phỏng
                    path.append(node_to_explore)
            
            # 3. Simulation (Rollout): Từ node_to_explore, mô phỏng ván cờ
            rollout_val = 0.0
            if node_to_explore.is_terminal: # Nếu node đã là terminal (ví dụ: do expand ra node checkmate)
                rollout_val = node_to_explore.terminal_value
            else: # Nếu không phải terminal, thực hiện rollout
                rollout_val = self._mcts_simulation_phase(node_to_explore) # Kết quả là theo góc nhìn của node_to_explore.player_to_move

            # 4. Backpropagation: Cập nhật kết quả rollout ngược lên cây
            self._mcts_backpropagate_refined(path, rollout_val, node_to_explore.player_to_move)
        
        self.mcts_simulations_performed = sims_count
        print(f"INFO MCTS: Hoàn thành {self.mcts_simulations_performed} simulations trong {time.time() - start_mcts_time:.2f}s")
        
        # Chọn nước đi tốt nhất từ root node (thường là node con có số lần visit cao nhất)
        if not root_node.children:
            print(f"MCTS WARN: Root node cho {player_color_ai} không có con nào sau simulations.")
            if initial_root_moves_backup:
                print(f"MCTS FALLBACK (no children): Chọn nước ngẫu nhiên từ gốc ({len(initial_root_moves_backup)} moves).")
                return random.choice(initial_root_moves_backup)
            return None 
        
        best_child_for_move = None
        # Chọn con có số visit cao nhất, nếu không có visit thì chọn con có win/loss tốt nhất (hiếm)
        if any(c.visits > 0 for c in root_node.children):
            best_child_for_move = max(root_node.children, key=lambda node: node.visits)
        elif root_node.children: # Nếu tất cả children đều có 0 visit (ví dụ budget quá thấp)
            print(f"MCTS WARN: Tất cả các con của root cho {player_color_ai} có 0 visits. Chọn con đầu tiên (đã được sắp xếp).")
            # Sắp xếp lại các con của gốc theo một tiêu chí nào đó nếu visits = 0, ví dụ prior_value (nếu có)
            # Hoặc đơn giản là lấy con đầu tiên từ danh sách đã được sắp xếp ở _get_all_possible_moves
            # (Hàm expand đã pop từ _untried_moves, nên children[0] là một lựa chọn hợp lý)
            best_child_for_move = root_node.children[0] 
        
        if best_child_for_move and best_child_for_move.move_leading_to_this_node:
            return best_child_for_move.move_leading_to_this_node
        else:
            print(f"MCTS ERROR: Không thể chọn best_child_for_move.")
            if initial_root_moves_backup:
                print(f"MCTS FALLBACK (no best_child): Chọn nước ngẫu nhiên từ gốc ({len(initial_root_moves_backup)} moves).")
                return random.choice(initial_root_moves_backup)
            print(f"MCTS CRITICAL ERROR: Không có nước đi nào từ gốc và không có fallback.")
            return None

    def find_best_move(self, initial_max_depth_suggestion_ignored, player_color_ai, 
                       current_board_history_tuples_param=None, current_action_history_param=None, 
                       current_move_count_from_game=0, game_kifu_uci_list_param=None,
                       time_limit_seconds=10):
        
        self.current_search_start_time = time.time()
        self.time_limit_for_move = float(time_limit_seconds) 
        self._reset_search_helpers() # Reset TT, killer moves, etc.
        self.move_count_for_eval = current_move_count_from_game # Số nửa nước đi
        
        current_game_board_obj = self.rules.board_instance # Board hiện tại của game
        self.evaluator.board_instance = current_game_board_obj # Gán board cho evaluator
        
        # Thiết lập context cho BookKnowledge (board phải là Red POV)
        if self.book_knowledge:
            self.book_knowledge.current_rules_instance = self.rules # Gán rules của game cho book
            # Lấy board Red POV để BookKnowledge kiểm tra features
            board_red_pov_for_book_tuple = self.book_knowledge.get_mirrored_board_tuple(current_game_board_obj.to_tuple()) if player_color_ai == 'black' else current_game_board_obj.to_tuple()
            board_red_pov_for_book_obj = XiangqiBoard() # Tạo instance mới
            board_red_pov_for_book_obj.board = [list(row) for row in board_red_pov_for_book_tuple]
            # Tạo rules mới cho board đã lật này, vì self.rules đang dùng board gốc
            rules_red_pov_for_book = GameRules(board_red_pov_for_book_obj) 
            self.book_knowledge.set_current_context_for_feature_checking(board_red_pov_for_book_obj, rules_red_pov_for_book)

        print(f"INFO AI ({player_color_ai}): Tìm nước. Tổng nước đi: {self.move_count_for_eval}. TimeLimit: {self.time_limit_for_move:.1f}s.")

        # --- Thứ tự ưu tiên tìm nước ---
        # 1. Sách Khai Cuộc
        if self.book_knowledge and self.move_count_for_eval < 12: # Giới hạn tra cứu khai cuộc, ví dụ 6 nước đầu của mỗi bên
            # game_kifu_uci_list_param là kỳ phổ của ván cờ hiện tại
            book_opening_move_uci = self.book_knowledge.get_book_move_for_opening(current_game_board_obj, player_color_ai, game_kifu_uci_list_param)
            if book_opening_move_uci:
                parsed_move = self._uci_to_coords_tuple(book_opening_move_uci, player_color_ai, current_game_board_obj)
                if parsed_move: 
                    # Kiểm tra nước đi từ sách có hợp lệ không (phòng trường hợp sách có lỗi hoặc không tương thích)
                    temp_board_check = XiangqiBoard(copy.deepcopy(current_game_board_obj.board))
                    temp_board_check.make_move(parsed_move[0], parsed_move[1])
                    # Tạo rules tạm cho board sau nước đi từ sách
                    temp_rules_check = GameRules(temp_board_check)
                    if not temp_rules_check.is_king_in_check(player_color_ai) and not temp_rules_check.generals_facing():
                        print(f"INFO AI: Chơi từ Sách Khai Cuộc: {book_opening_move_uci} ({parsed_move[2]})")
                        return parsed_move
                    else:
                        print(f"WARN AI: Nước đi từ sách khai cuộc {book_opening_move_uci} không hợp lệ. Bỏ qua.")
        
        game_progress = self.evaluator.get_game_progress_score(self.move_count_for_eval)
        
        # 2. Sách Sát Pháp (Ưu tiên cao, có thể xảy ra bất cứ lúc nào)
        if self.book_knowledge:
            # Context cho book_knowledge đã được set ở đầu hàm find_best_move
            # get_kill_pattern_move cần board hiện tại (chưa lật) và màu quân AI
            kill_move_uci = self.book_knowledge.get_kill_pattern_move(current_game_board_obj, player_color_ai)
            if kill_move_uci: # Giả sử get_kill_pattern_move trả về một nước UCI hoặc None
                parsed_move = self._uci_to_coords_tuple(kill_move_uci, player_color_ai, current_game_board_obj)
                if parsed_move:
                    temp_board_check = XiangqiBoard(copy.deepcopy(current_game_board_obj.board))
                    temp_board_check.make_move(parsed_move[0], parsed_move[1])
                    temp_rules_check = GameRules(temp_board_check)
                    if not temp_rules_check.is_king_in_check(player_color_ai) and not temp_rules_check.generals_facing():
                        print(f"INFO AI: Thực hiện Sát Pháp! Nước: {kill_move_uci} ({parsed_move[2]})")
                        return parsed_move
                    else:
                        print(f"WARN AI: Nước đi từ sách sát pháp {kill_move_uci} không hợp lệ. Bỏ qua.")
        
        # 3. Sách Cờ Tàn (Chỉ kiểm tra nếu thực sự vào tàn cuộc và sau một số nước nhất định)
        # Ngưỡng game_progress và move_count_for_eval cần được tinh chỉnh
        if self.book_knowledge and game_progress >= 1.8 and self.move_count_for_eval >= 20: # Ví dụ: sau 10 hiệp
            print(f"INFO AI ({player_color_ai}): Giai đoạn cờ tàn (prog: {game_progress:.2f}), kiểm tra sách cờ tàn.")
            # Context cho book_knowledge đã được set
            book_endgame_move_uci = self.book_knowledge.find_and_get_endgame_move(current_game_board_obj, player_color_ai, game_kifu_uci_list_param)
            if book_endgame_move_uci:
                parsed_move = self._uci_to_coords_tuple(book_endgame_move_uci, player_color_ai, current_game_board_obj)
                if parsed_move:
                    temp_board_check = XiangqiBoard(copy.deepcopy(current_game_board_obj.board))
                    temp_board_check.make_move(parsed_move[0], parsed_move[1])
                    temp_rules_check = GameRules(temp_board_check)
                    if not temp_rules_check.is_king_in_check(player_color_ai) and not temp_rules_check.generals_facing():
                        print(f"INFO AI: Chơi từ Sách Cờ Tàn: {book_endgame_move_uci} ({parsed_move[2]})")
                        return parsed_move
                    else:
                        print(f"WARN AI: Nước đi từ sách cờ tàn {book_endgame_move_uci} không hợp lệ. Bỏ qua.")
        
        # 4. Lựa chọn thuật toán tìm kiếm chính (MCTS-AB hoặc Alpha-Beta)
        best_move_found = None
        use_mcts_primary = False # Mặc định không dùng MCTS trừ khi điều kiện thỏa mãn
        # Điều kiện sử dụng MCTS (ví dụ: đầu/giữa game, đủ thời gian)
        if game_progress < 1.0 and self.time_limit_for_move > 0.8: # Khai cuộc (ngoài sách)
            use_mcts_primary = True
            print(f"INFO AI: Giai đoạn Khai cuộc (ngoài sách), sử dụng MCTS-AB.")
        elif game_progress < 1.9 and self.time_limit_for_move > 1.5: # Trung cuộc
            use_mcts_primary = True
            print(f"INFO AI: Giai đoạn Trung cuộc, sử dụng MCTS-AB.")
        
        if use_mcts_primary:
            mcts_time_budget = self.time_limit_for_move * MCTS_SIMULATION_BUDGET_SECONDS_RATIO
            if self.move_count_for_eval < 6 : mcts_time_budget = self.time_limit_for_move * 0.70 # Ít thời gian hơn cho những nước đầu
            
            print(f"INFO AI: MCTS-AB budget: {mcts_time_budget:.2f}s")
            best_move_found_mcts = self._perform_mcts_search(current_game_board_obj, player_color_ai, mcts_time_budget)
            if best_move_found_mcts:
                self.actual_depth_reached_in_last_search = self.mcts_simulations_performed # Lưu số sims thay cho depth
                print(f"INFO AI: MCTS-AB chọn nước: {self._coords_to_uci_str(best_move_found_mcts[0], best_move_found_mcts[1])} ({best_move_found_mcts[2]}). Sims: {self.mcts_simulations_performed}.")
                return best_move_found_mcts
            else:
                print(f"WARN AI: MCTS-AB không tìm thấy nước đi, chuyển sang Alpha-Beta.")
        
        # Fallback hoặc nếu là Tàn cuộc / không đủ thời gian cho MCTS / MCTS không tìm được nước
        print(f"INFO AI: Sử dụng Alpha-Beta với Quiescence. Game Prog: {game_progress:.2f}")
        
        time_spent_so_far = time.time() - self.current_search_start_time
        remaining_time_for_ab = self.time_limit_for_move - time_spent_so_far - 0.05 # Trừ hao
        
        # Xác định độ sâu hiệu quả cho Alpha-Beta dựa trên giai đoạn và thời gian còn lại
        effective_ab_depth = AB_DEFAULT_MAX_DEPTH_ENDGAME
        if game_progress < 0.8: effective_ab_depth = AB_DEFAULT_MAX_DEPTH_OPENING
        elif game_progress < 1.8: effective_ab_depth = AB_DEFAULT_MAX_DEPTH_MIDGAME
        
        # Điều chỉnh độ sâu dựa trên thời gian còn lại
        if remaining_time_for_ab < 0.3: effective_ab_depth = min(effective_ab_depth, 1) 
        elif remaining_time_for_ab < 1.0: effective_ab_depth = min(effective_ab_depth, 2)
        elif remaining_time_for_ab < 2.5: effective_ab_depth = min(effective_ab_depth, 3)
        elif game_progress < 1.8 : # Nếu là trung cuộc
             effective_ab_depth = min(effective_ab_depth, AB_DEFAULT_MAX_DEPTH_MIDGAME) 
        
        if game_progress >= 1.8 : # Nếu là tàn cuộc
            if remaining_time_for_ab > 5.0: effective_ab_depth = min(AB_ABSOLUTE_MAX_DEPTH, AB_DEFAULT_MAX_DEPTH_ENDGAME + 1)
            elif remaining_time_for_ab > 2.5: effective_ab_depth = min(AB_ABSOLUTE_MAX_DEPTH, AB_DEFAULT_MAX_DEPTH_ENDGAME)
        
        effective_ab_depth = max(1, effective_ab_depth) # Ít nhất là 1

        print(f"INFO AI: Alpha-Beta. Max Depth (Iterative): {effective_ab_depth}. Time left for AB: {remaining_time_for_ab:.2f}s")
        
        best_move_ab = None
        # Khởi tạo best_eval_ab đúng cho người chơi hiện tại
        best_eval_ab = -float('inf') if player_color_ai == 'red' else float('inf') 
        
        if remaining_time_for_ab < 0.05: # Nếu gần như không còn thời gian
            print(f"WARN AI: Không đủ thời gian cho Alpha-Beta ({remaining_time_for_ab:.2f}s).")
        else:
            # Iterative Deepening Alpha-Beta
            for current_search_depth_iter in range(1, effective_ab_depth + 1):
                iter_start_time = time.time()
                # Kiểm tra thời gian trước khi bắt đầu một độ sâu mới
                time_budget_for_this_iter = (self.current_search_start_time + self.time_limit_for_move) - time.time() - 0.02 # Trừ hao
                if time_budget_for_this_iter < 0.01 and current_search_depth_iter > 1 : # Nếu không đủ thời gian cho iter tiếp theo
                    print(f"INFO AI: Alpha-Beta: Hết giờ trước khi bắt đầu depth {current_search_depth_iter}.")
                    break

                self.initial_max_depth_for_this_call = current_search_depth_iter # Độ sâu tối đa cho lần gọi _minimax_alpha_beta_recursive này
                self.actual_depth_reached_in_last_search = 0 # Reset cho mỗi lần lặp ID
                
                current_iter_best_move = None
                # Khởi tạo current_iter_eval đúng
                current_iter_eval = -float('inf') if player_color_ai == 'red' else float('inf')
                alpha, beta = float('-inf'), float('inf')

                # Đảm bảo board cho rules, evaluator, referee là board hiện tại của game
                self.rules.board_instance = current_game_board_obj
                self.evaluator.board_instance = current_game_board_obj
                self.referee.board_instance = current_game_board_obj 

                possible_moves_ab = self.rules.get_all_valid_moves(player_color_ai)
                if not possible_moves_ab: break # Không còn nước đi

                # Sắp xếp nước đi cho Alpha-Beta
                possible_moves_ab.sort(key=lambda m: self._get_move_score_for_ordering(current_game_board_obj, m[0], m[1], m[2], current_search_depth_iter, player_color_ai), reverse=True)
                
                try:
                    for i_move, (move_from, move_to, piece_char_moved) in enumerate(possible_moves_ab):
                        # Kiểm tra luật cấm của Referee cho nước đi này
                        action_type, target_info, board_data_after_action = self.referee.get_action_details(current_game_board_obj, move_from, move_to, piece_char_moved)
                        board_tuple_after_action = XiangqiBoard(board_data_after_action).to_tuple()
                        current_action_entry = {"player": player_color_ai, "action_type": action_type, "target_key": self.referee._generate_target_key(action_type, target_info, piece_char_moved, move_from), "board_tuple_after_action": board_tuple_after_action, "move_tuple": (move_from, move_to)}
                        history_for_referee_check_node = (current_action_history_param or []) + [current_action_entry]
                        
                        is_forbidden = self.referee.check_forbidden_perpetual_action(player_color_ai, (move_from, move_to), action_type, target_info, board_tuple_after_action, piece_char_moved, history_for_referee_check_node)
                        if is_forbidden:
                            # print(f"DEBUG AI: Nước đi {self._coords_to_uci_str(move_from, move_to)} bị cấm bởi Referee.")
                            continue # Bỏ qua nước đi bị cấm

                        temp_board_obj_ab = XiangqiBoard(copy.deepcopy(board_data_after_action)) # Tạo board mới từ board_data_after_action
                        
                        # Lịch sử board cho kiểm tra lặp 3 lần
                        board_hist_child = (current_board_history_tuples_param or []) + [(temp_board_obj_ab.to_tuple(), self.rules.get_opponent_color(player_color_ai))]
                        
                        # Gọi đệ quy Alpha-Beta cho đối thủ
                        evaluation = self._minimax_alpha_beta_recursive(
                            temp_board_obj_ab, current_search_depth_iter - 1, # Giảm độ sâu
                            alpha, beta, False, player_color_ai, # False vì giờ là lượt của đối thủ (minimizing)
                            board_hist_child, history_for_referee_check_node, # Truyền lịch sử
                            self.move_count_for_eval + 1 # Ply_from_root cho minimax, bắt đầu từ 1 cho nước đi đầu tiên của AI
                        )
                        
                        if player_color_ai == 'red': # AI là Đỏ (Maximizing player ở root)
                            if evaluation > current_iter_eval:
                                current_iter_eval = evaluation
                                current_iter_best_move = (move_from, move_to, piece_char_moved)
                            alpha = max(alpha, evaluation)
                        else: # AI là Đen (Minimizing player ở root, nhưng hàm minimax vẫn tìm max cho Đỏ, nên cần đảo dấu hoặc so sánh ngược lại)
                              # Thực ra, player_to_optimize_for luôn là player_color_ai.
                              # is_maximizing_player_turn thay đổi ở mỗi độ sâu.
                              # Ở root, is_maximizing_player_turn là True.
                              # Vậy logic cập nhật best_eval và alpha/beta là đúng.
                            if evaluation < current_iter_eval: # Nếu AI là Đen (Minimizing ở root, nhưng _minimax... luôn tối ưu cho player_to_optimize_for)
                                                              # Đoạn này cần xem lại. player_to_optimize_for là player_color_ai.
                                                              # Nên logic if player_color_ai == 'red' là đủ.
                                                              # Nếu AI là Đen, thì giá trị trả về từ _minimax... là điểm của Đen (nếu is_maximizing_player_turn là True cho Đen).
                                                              # Không, player_to_optimize_for là cố định.
                                                              # is_maximizing_player_turn là cho lượt của node đó.
                                                              # Ở root, AI (player_color_ai) là maximizing.
                                # Sửa lại cho đúng:
                                current_iter_eval = evaluation # Vì giá trị trả về là theo góc nhìn của player_color_ai
                                if current_iter_best_move is None: # Gán nước đầu tiên
                                     current_iter_best_move = (move_from, move_to, piece_char_moved)
                                
                                # Cập nhật alpha/beta dựa trên is_maximizing_player_turn của root (luôn là True cho AI)
                                # Đoạn này là ở root, AI luôn là maximizing
                                if current_iter_eval > best_eval_ab : # So sánh với best_eval_ab toàn cục của root
                                     best_eval_ab = current_iter_eval
                                     current_iter_best_move = (move_from, move_to, piece_char_moved)
                                alpha = max(alpha, current_iter_eval)


                        if alpha >= beta: # Cắt tỉa
                            break 

                    if current_iter_best_move:
                        best_move_ab = current_iter_best_move
                        best_eval_ab = current_iter_eval # Lưu lại eval của iter này
                        print(f"INFO AI: Alpha-Beta depth {current_search_depth_iter}. Nước: {self._coords_to_uci_str(best_move_ab[0], best_move_ab[1])} ({best_move_ab[2]}), Đ.giá ({player_color_ai}): {best_eval_ab:.0f}, T.gian ID: {time.time() - iter_start_time:.2f}s, Tổng T.gian: {time.time() - self.current_search_start_time:.2f}s, Độ sâu TT: {self.actual_depth_reached_in_last_search}")
                
                except TimeoutError:
                    print(f"WARN AI: Alpha-Beta hết thời gian ở độ sâu lặp {current_search_depth_iter}.")
                    break # Thoát vòng lặp Iterative Deepening
                
                # Kiểm tra thời gian sau mỗi lần hoàn thành một độ sâu
                if time.time() - self.current_search_start_time >= self.time_limit_for_move - 0.02: # Để lại một chút thời gian
                    print(f"INFO AI: Alpha-Beta gần hết thời gian sau depth {current_search_depth_iter}.")
                    break
            best_move_found = best_move_ab
        
        # Fallback: Nếu không tìm thấy nước đi nào (rất hiếm)
        final_time_taken = time.time() - self.current_search_start_time
        if best_move_found:
             print(f"INFO AI: Tìm kiếm hoàn tất. Nước cuối: {self._coords_to_uci_str(best_move_found[0], best_move_found[1])} ({best_move_found[2]}). T.gian: {final_time_taken:.2f}s")
        else:
             print(f"ERROR AI: Không thể tìm thấy bất kỳ nước đi hợp lệ nào cho {player_color_ai}! T.gian: {final_time_taken:.2f}s")
             # Cố gắng chọn một nước ngẫu nhiên nếu có thể
             self.rules.board_instance = current_game_board_obj # Đảm bảo rules dùng board hiện tại
             all_valid_at_end = self.rules.get_all_valid_moves(player_color_ai) 
             if all_valid_at_end: 
                 print(f"WARN AI: Chọn nước ngẫu nhiên từ {len(all_valid_at_end)} nước hợp lệ.")
                 best_move_found = random.choice(all_valid_at_end)
        
        return best_move_found

