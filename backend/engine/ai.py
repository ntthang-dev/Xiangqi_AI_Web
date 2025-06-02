# File: backend/engine/ai.py
# Version: V15.1 - Sửa lỗi MCTS return, logging chi tiết hơn

import copy
import time
import random
import math 

from .board import XiangqiBoard, GENERAL, PAWN, CHARIOT, HORSE, CANNON 
from .rules import GameRules 
from .evaluation import Evaluation 
from .referee import Referee, ACTION_TYPE_CHECK, ACTION_TYPE_CHASE_PROTECTED, ACTION_TYPE_CHASE_UNPROTECTED, ACTION_TYPE_OTHER

MCTS_SIMULATION_COUNT_PER_MOVE = 1000 
MCTS_TIME_LIMIT_PER_MOVE_SECONDS = 5.0 
MCTS_UCT_C = 1.414 
MCTS_ROLLOUT_DEPTH_LIMIT = 30 

QUIESCENCE_MAX_DEPTH = 3
TACTICAL_MOVE_SCORE_THRESHOLD = 50

class MCTSNode:
    def __init__(self, board_state_tuple, player_to_move, move_leading_to_node=None, parent=None, book_knowledge=None, rules_instance=None, eval_instance=None):
        self.board_state_tuple = board_state_tuple
        self.player_to_move = player_to_move
        self.move_leading_to_this_node = move_leading_to_node
        self.parent = parent
        self.children = []
        self.wins = 0.0
        self.visits = 0
        self.rules = rules_instance
        self.evaluator = eval_instance
        self.book_knowledge = book_knowledge
        self._untried_moves = None
        self.is_terminal, self.terminal_value = self._check_terminal_and_value()

    def _get_all_possible_moves(self):
        if self._untried_moves is None:
            temp_board = XiangqiBoard()
            temp_board.board = [list(row) for row in self.board_state_tuple]
            original_rules_board = self.rules.board_instance
            self.rules.board_instance = temp_board
            self._untried_moves = self.rules.get_all_valid_moves(self.player_to_move)
            self.rules.board_instance = original_rules_board
        return self._untried_moves

    def is_fully_expanded(self):
        return not self._get_all_possible_moves()

    def best_child_uct(self):
        if not self.children: return None
        for child in self.children:
            if child.visits == 0: return child
        log_total_visits = math.log(self.visits) if self.visits > 0 else 0 # Tránh math domain error
        def uct_value(node):
            if node.visits == 0: return float('inf')
            exploitation_term = node.wins / node.visits
            exploration_term = MCTS_UCT_C * math.sqrt(log_total_visits / node.visits)
            return exploitation_term + exploration_term
        return max(self.children, key=uct_value)

    def expand(self):
        possible_moves = self._get_all_possible_moves()
        if not possible_moves: return None
        
        # (Logic ưu tiên nước đi chiến lược từ sách có thể thêm ở đây)
        move_to_expand_tuple = possible_moves.pop(random.randrange(len(possible_moves)))
        
        temp_board = XiangqiBoard()
        temp_board.board = [list(row) for row in self.board_state_tuple]
        temp_board.make_move(move_to_expand_tuple[0], move_to_expand_tuple[1])
        
        new_board_state_tuple = temp_board.to_tuple()
        next_player = self.rules.get_opponent_color(self.player_to_move)
        
        child_node = MCTSNode(new_board_state_tuple, next_player, 
                              move_leading_to_node=move_to_expand_tuple, parent=self,
                              book_knowledge=self.book_knowledge, 
                              rules_instance=self.rules, 
                              eval_instance=self.evaluator)
        self.children.append(child_node)
        return child_node

    def _check_terminal_and_value(self):
        temp_board = XiangqiBoard()
        temp_board.board = [list(row) for row in self.board_state_tuple]
        original_rules_board = self.rules.board_instance
        self.rules.board_instance = temp_board
        is_mate_current_player, winner_if_mate = self.rules.is_checkmate(self.player_to_move)
        if is_mate_current_player:
            self.rules.board_instance = original_rules_board
            return True, -1.0 
        is_stalemate_current = self.rules.is_stalemate(self.player_to_move)
        if is_stalemate_current:
            self.rules.board_instance = original_rules_board
            return True, 0.0
        self.rules.board_instance = original_rules_board
        return False, None

class AIPlayer:
    def __init__(self, game_rules_instance, evaluation_instance, referee_instance, book_knowledge_instance=None):
        self.rules = game_rules_instance 
        self.evaluator = evaluation_instance 
        if hasattr(self.evaluator, 'book_knowledge') and self.evaluator.book_knowledge is None:
            self.evaluator.book_knowledge = book_knowledge_instance
        self.referee = referee_instance 
        self.book_knowledge = book_knowledge_instance
        self.transposition_table = {} 
        self.move_count_for_eval = 0 
        self.current_search_start_time = 0
        self.time_limit_for_move = 10.0 
        self.actual_depth_reached_in_last_search = 0 # Sẽ được set bởi AlphaBeta
        self.mcts_simulations_performed = 0 # Thêm để lưu số sim MCTS
        self.initial_max_depth_for_this_call = 0
        self.killer_moves = {} 
        self.history_heuristic_table = {}
        self.PREFERRED_OPENING_MOVES_RED_UCI = { "b7e7", "h7e7", "b9c7", "h9g7", "c6c5", "g6g5", "e6e5" }
        self.PREFERRED_OPENING_MOVES_BLACK_UCI = { "b2e2", "h2e2", "h0g2", "b0c2", "c3c4", "g3g4", "e3e4" }

    def _reset_search_helpers(self):
        self.transposition_table.clear()
        self.killer_moves = {}
        # self.history_heuristic_table.clear() # Cân nhắc giữ lại history table
        self.actual_depth_reached_in_last_search = 0
        self.mcts_simulations_performed = 0


    def _uci_to_coords_tuple(self, uci_move_str, player_color_making_move, board_obj):
        coords = GameRules.uci_to_coords(uci_move_str)
        if not coords: return None
        from_sq, to_sq = coords
        piece_char = board_obj.get_piece_at(from_sq[0], from_sq[1])
        if not piece_char: return None
        piece_info = self.rules.get_piece_info(piece_char)
        if not piece_info or piece_info['color'] != player_color_making_move: return None
        return (from_sq, to_sq, piece_char)

    def _coords_to_uci_str(self, from_sq, to_sq):
        return GameRules.coords_to_uci(from_sq, to_sq)

    def _get_move_score_for_ordering(self, board_obj_before_move, move_from, move_to, piece_char_moved, current_search_ply_depth, player_color):
        # --- Giữ nguyên logic từ V15.0, có thể đã được tinh chỉnh ---
        score = 0.0
        piece_at_target_sq = board_obj_before_move.get_piece_at(move_to[0], move_to[1]) 
        game_ply_at_root = self.move_count_for_eval
        if game_ply_at_root < 8:
            move_uci_str = self._coords_to_uci_str(move_from, move_to)
            if move_uci_str:
                preferred_set = self.PREFERRED_OPENING_MOVES_RED_UCI if player_color == 'red' else self.PREFERRED_OPENING_MOVES_BLACK_UCI
                if move_uci_str in preferred_set: score += 500
            if piece_char_moved.upper() == 'C' and not piece_at_target_sq:
                if player_color == 'red' and move_from[0] == 7 and move_to[0] < 5: score -= 300
                elif player_color == 'black' and move_from[0] == 2 and move_to[0] > 4: score -= 300
        if current_search_ply_depth in self.killer_moves: 
            if (move_from, move_to) in self.killer_moves[current_search_ply_depth]: score += 200  
        if piece_at_target_sq: 
            victim_val = self.evaluator.PIECE_BASE_VALUES_MIDGAME.get(piece_at_target_sq.upper(), 0)
            aggressor_val = self.evaluator.PIECE_BASE_VALUES_MIDGAME.get(piece_char_moved.upper(), 1) 
            score += (victim_val / (aggressor_val if aggressor_val > 0 else 1) ) * 100 
        history_score = self.history_heuristic_table.get((piece_char_moved, move_to), 0)
        score += history_score 
        if game_ply_at_root < 12 and score < 100: 
            piece_type = self.rules.get_piece_info(piece_char_moved)['type']
            if piece_type in [HORSE, CHARIOT, CANNON]:
                if player_color == 'red' and move_from[0] >= 7 : score += 30 
                elif player_color == 'black' and move_from[0] <= 2: score += 30
        return score

    def _update_killer_move(self, depth, move_tuple):
        if depth not in self.killer_moves: self.killer_moves[depth] = []
        if move_tuple not in self.killer_moves[depth]:
            self.killer_moves[depth].insert(0, move_tuple) 
            if len(self.killer_moves[depth]) > 2: self.killer_moves[depth].pop()

    def _update_history_heuristic(self, piece_char, to_sq_tuple, bonus):
        current_score = self.history_heuristic_table.get((piece_char, to_sq_tuple), 0)
        self.history_heuristic_table[(piece_char, to_sq_tuple)] = current_score + bonus

    def _quiescence_search(self, current_board_obj, alpha, beta, player_to_optimize_for, 
                           current_total_half_moves, depth_remaining, 
                           board_history_tuples_for_rep, action_history_for_referee, current_ply_from_root_qs):
        # --- Giữ nguyên logic Quiescence Search từ V15.0 ---
        # Đảm bảo self.rules.board_instance và self.evaluator.board_instance được set đúng
        original_rules_board_qs = self.rules.board_instance
        original_eval_board_qs = self.evaluator.board_instance
        self.rules.board_instance = current_board_obj
        self.evaluator.board_instance = current_board_obj

        stand_pat_score = self.evaluator.evaluate_board(player_to_optimize_for, current_total_half_moves)
        
        # Xác định lượt đi cho node quiescence này một cách cẩn thận
        # player_to_move_at_this_qs_node là người sẽ thực hiện nước đi từ current_board_obj
        # Nếu current_ply_from_root_qs là 0, thì player_to_move_at_this_qs_node là người chơi
        # mà _minimax_alpha_beta_recursive đang tìm nước đi cho (tức là current_player_for_this_node trong minimax)
        # Tuy nhiên, is_maximizing_turn_qs phải dựa trên player_to_optimize_for
        # Ví dụ: nếu player_to_optimize_for là 'red', thì khi current_player_for_qs_node là 'red', is_maximizing_turn_qs là True.
        
        # Lấy player sẽ đi từ current_board_obj
        # Điều này phụ thuộc vào việc minimax gọi quiescence cho lượt của ai
        # Giả sử minimax gọi quiescence khi đến lượt của current_player_for_this_node (trong minimax)
        # Vậy, is_maximizing_turn_qs sẽ là True nếu current_player_for_this_node == player_to_optimize_for
        
        # Lấy player hiện tại của node quiescence này:
        # Nếu current_ply_from_root_qs là chẵn (0, 2, ...), thì đó là lượt của người chơi bắt đầu nhánh quiescence.
        # Nếu là lẻ (1, 3, ...), thì là lượt của đối thủ.
        # Người chơi bắt đầu nhánh quiescence là current_player_for_this_node từ hàm minimax.
        # Hàm minimax truyền is_maximizing_player_turn.
        # Nếu is_maximizing_player_turn (trong minimax) là True, thì current_player_for_this_node (trong minimax) là player_to_optimize_for.
        # Nếu is_maximizing_player_turn (trong minimax) là False, thì current_player_for_this_node (trong minimax) là đối thủ của player_to_optimize_for.
        
        # Đơn giản hóa: is_maximizing_turn_qs nên được truyền vào từ minimax, hoặc tính lại dựa trên player_to_optimize_for và current_player_for_qs_node
        # Giả sử current_board_obj là trạng thái mà current_player_for_this_node (từ minimax) sẽ đi.
        player_making_move_in_qs = self.rules.get_opponent_color(player_to_optimize_for) if (current_total_half_moves - self.move_count_for_eval) % 2 != 0 else player_to_optimize_for
        # ^^^ Logic này có thể không hoàn toàn đúng, cần xem xét is_maximizing_player_turn từ minimax

        # Cách đúng hơn: người gọi _quiescence_search phải biết ai là người đi ở current_board_obj
        # và is_maximizing_turn_qs phải dựa trên đó và player_to_optimize_for.
        # Trong _minimax_alpha_beta_recursive, khi gọi _quiescence_search:
        # current_player_for_this_node là người sẽ đi.
        # is_maximizing_turn_qs = (current_player_for_this_node == player_to_optimize_for)
        # Ta sẽ sửa ở hàm gọi. Ở đây giả sử is_maximizing_turn_qs được truyền đúng.

        # Tạm thời dùng logic cũ của bạn cho is_maximizing_turn_qs, nhưng nó cần xem lại:
        is_maximizing_turn_qs = (self.rules.get_piece_info(current_board_obj.get_piece_at(0,0) or 'k')['color'] == player_to_optimize_for if current_ply_from_root_qs % 2 == 0 else \
                                self.rules.get_opponent_color(player_to_optimize_for) == player_to_optimize_for)
        current_player_for_qs_node = player_to_optimize_for if is_maximizing_turn_qs else self.rules.get_opponent_color(player_to_optimize_for)


        if is_maximizing_turn_qs: alpha = max(alpha, stand_pat_score)
        else: beta = min(beta, stand_pat_score)
        
        if alpha >= beta or depth_remaining == 0:
            self.rules.board_instance = original_rules_board_qs
            self.evaluator.board_instance = original_eval_board_qs
            return stand_pat_score

        all_valid_moves_qs = self.rules.get_all_valid_moves(current_player_for_qs_node)
        tactical_moves = []
        for move_from, move_to, piece_moved in all_valid_moves_qs:
            if current_board_obj.get_piece_at(move_to[0], move_to[1]) is not None: # Chỉ bắt quân
                tactical_moves.append((move_from, move_to, piece_moved))
        
        tactical_moves.sort(key=lambda m: self._get_move_score_for_ordering(current_board_obj, m[0], m[1], m[2], 0, current_player_for_qs_node), reverse=True)

        if not tactical_moves:
            self.rules.board_instance = original_rules_board_qs
            self.evaluator.board_instance = original_eval_board_qs
            return stand_pat_score

        for move_from, move_to, piece_char_moved in tactical_moves:
            new_board_obj_qs = XiangqiBoard(copy.deepcopy(current_board_obj.board))
            new_board_obj_qs.make_move(move_from, move_to)
            score = self._quiescence_search(new_board_obj_qs, alpha, beta, player_to_optimize_for,
                                           current_total_half_moves + 1, depth_remaining - 1,
                                           board_history_tuples_for_rep, action_history_for_referee,
                                           current_ply_from_root_qs + 1) # Sai: is_maximizing_turn_qs phải được truyền vào
            if is_maximizing_turn_qs: alpha = max(alpha, score)
            else: beta = min(beta, score)
            if alpha >= beta: break
        
        self.rules.board_instance = original_rules_board_qs
        self.evaluator.board_instance = original_eval_board_qs
        return alpha if is_maximizing_turn_qs else beta


    def _minimax_alpha_beta_recursive(self, current_board_obj, depth, alpha, beta, is_maximizing_player_turn, player_to_optimize_for, 
                                      board_history_tuples_for_repetition, action_history_for_referee, current_ply_from_root):
        # --- Phần đầu giữ nguyên (Timeout, TT lookup) ---
        self.actual_depth_reached_in_last_search = max(self.actual_depth_reached_in_last_search, self.initial_max_depth_for_this_call - depth)
        if time.time() - self.current_search_start_time > self.time_limit_for_move: raise TimeoutError("AI search time limit exceeded")
        board_tuple_for_tt = current_board_obj.to_tuple()
        tt_key = (board_tuple_for_tt, depth, is_maximizing_player_turn, player_to_optimize_for)
        if tt_key in self.transposition_table:
            tt_entry = self.transposition_table[tt_key]
            if tt_entry['depth'] >= depth:
                if tt_entry['type'] == 'exact': return tt_entry['score']
                if tt_entry['type'] == 'lower_bound': alpha = max(alpha, tt_entry['score'])
                elif tt_entry['type'] == 'upper_bound': beta = min(beta, tt_entry['score'])
                if alpha >= beta: return tt_entry['score']

        original_rules_board = self.rules.board_instance
        original_eval_board = self.evaluator.board_instance
        self.rules.board_instance = current_board_obj
        self.evaluator.board_instance = current_board_obj

        current_player_for_this_node = player_to_optimize_for if is_maximizing_player_turn else self.rules.get_opponent_color(player_to_optimize_for)
        is_checkmate_current, _ = self.rules.is_checkmate(current_player_for_this_node)
        is_stalemate_current = self.rules.is_stalemate(current_player_for_this_node)
        current_total_half_moves_at_node = self.move_count_for_eval + current_ply_from_root

        if depth == 0 or is_checkmate_current or is_stalemate_current:
            # Sửa cách gọi Quiescence Search
            eval_score = self._quiescence_search(current_board_obj, alpha, beta, 
                                                 player_to_optimize_for, # Người chơi mà chúng ta đang tối ưu cho
                                                 current_total_half_moves_at_node, 
                                                 QUIESCENCE_MAX_DEPTH, 
                                                 board_history_tuples_for_repetition, 
                                                 action_history_for_referee, 
                                                 0, # current_ply_from_root_qs
                                                 # is_maximizing_player_turn # Truyền is_maximizing_turn cho QS
                                                 ) # Cần sửa _quiescence_search để nhận is_maximizing_turn
            
            self.rules.board_instance = original_rules_board
            self.evaluator.board_instance = original_eval_board
            self.transposition_table[tt_key] = {'score': eval_score, 'type': 'exact', 'depth': depth}
            return eval_score

        # --- Phần còn lại của minimax (lặp lại 3 lần, sinh nước đi, lặp qua nước đi, đệ quy, TT store) giữ nguyên ---
        # ... (Logic kiểm tra lặp lại 3 lần)
        current_board_tuple_for_hist = current_board_obj.to_tuple() 
        history_to_check_3fold = board_history_tuples_for_repetition + [(current_board_tuple_for_hist, current_player_for_this_node)]
        if self.rules.check_threefold_repetition_from_history(current_board_tuple_for_hist, current_player_for_this_node, history_to_check_3fold):
            self.rules.board_instance = original_rules_board
            self.evaluator.board_instance = original_eval_board
            self.transposition_table[tt_key] = {'score': self.evaluator.STALEMATE_SCORE, 'type': 'exact', 'depth': depth}
            return self.evaluator.STALEMATE_SCORE

        possible_moves_tuples = self.rules.get_all_valid_moves(current_player_for_this_node)
        if not possible_moves_tuples: 
            eval_score = self.evaluator.evaluate_board(player_to_optimize_for, current_total_half_moves_at_node)
            self.rules.board_instance = original_rules_board
            self.evaluator.board_instance = original_eval_board
            self.transposition_table[tt_key] = {'score': eval_score, 'type': 'exact', 'depth': depth}
            return eval_score
        
        possible_moves_tuples.sort(key=lambda move_tuple: self._get_move_score_for_ordering(current_board_obj, move_tuple[0], move_tuple[1], move_tuple[2], depth, current_player_for_this_node), reverse=True)
        
        best_val = float('-inf') if is_maximizing_player_turn else float('inf')
        original_alpha_for_tt = alpha 
        best_move_found_in_node = None

        for i, (move_from, move_to, piece_char_moved) in enumerate(possible_moves_tuples):
            # ... (Logic kiểm tra referee - giữ nguyên)
            action_type, target_info, board_data_after_action = self.referee.get_action_details(current_board_obj, move_from, move_to, piece_char_moved)
            board_tuple_after_action = current_board_obj.to_tuple(board_data_after_action) 
            # ... (phần còn lại của referee check)

            new_board_hist_tuples_for_child = board_history_tuples_for_repetition + [(board_tuple_after_action, self.rules.get_opponent_color(current_player_for_this_node))]
            new_action_hist_for_child = action_history_for_referee + [{"player": current_player_for_this_node, "action_type": action_type, "target_key": "...", "board_tuple_after_action": board_tuple_after_action, "move_tuple": (move_from, move_to)}]
            new_board_obj_for_recursive_call = XiangqiBoard(board_data_after_action) 
            new_depth = depth - 1 # (Có thể thêm search extensions ở đây)

            evaluation = self._minimax_alpha_beta_recursive(new_board_obj_for_recursive_call, new_depth, alpha, beta, 
                                                            not is_maximizing_player_turn, 
                                                            player_to_optimize_for, 
                                                            new_board_hist_tuples_for_child, new_action_hist_for_child,
                                                            current_ply_from_root + 1) 
            if is_maximizing_player_turn:
                if evaluation > best_val: best_val = evaluation; best_move_found_in_node = (move_from, move_to, piece_char_moved)
                alpha = max(alpha, evaluation)
            else: 
                if evaluation < best_val: best_val = evaluation; best_move_found_in_node = (move_from, move_to, piece_char_moved)
                beta = min(beta, evaluation)
            
            if alpha >= beta: 
                if not current_board_obj.get_piece_at(move_to[0], move_to[1]): 
                    self._update_killer_move(depth, (move_from, move_to))
                    self._update_history_heuristic(piece_char_moved, move_to, depth * depth) 
                break 
        
        self.rules.board_instance = original_rules_board
        self.evaluator.board_instance = original_eval_board
        tt_store_type = 'exact'
        if best_val <= original_alpha_for_tt: tt_store_type = 'upper_bound'
        elif best_val >= beta: tt_store_type = 'lower_bound'
        self.transposition_table[tt_key] = {'score': best_val, 'type': tt_store_type, 'depth': depth, 'best_move': best_move_found_in_node if tt_store_type != 'upper_bound' else None}
        return best_val


    def _mcts_simulation_phase(self, node_to_simulate_from):
        # --- Giữ nguyên logic từ V15.0, đảm bảo evaluator dùng đúng board ---
        current_board_sim = XiangqiBoard()
        current_board_sim.board = [list(row) for row in node_to_simulate_from.board_state_tuple]
        current_player_sim = node_to_simulate_from.player_to_move
        
        original_rules_board_sim = self.rules.board_instance
        original_eval_board_sim = self.evaluator.board_instance
        self.rules.board_instance = current_board_sim
        self.evaluator.board_instance = current_board_sim # QUAN TRỌNG

        for i_rollout in range(MCTS_ROLLOUT_DEPTH_LIMIT):
            is_mate_sim, winner_sim = self.rules.is_checkmate(current_player_sim)
            if is_mate_sim:
                self.rules.board_instance = original_rules_board_sim
                self.evaluator.board_instance = original_eval_board_sim
                # Kết quả theo góc nhìn của node_to_simulate_from.player_to_move
                # Nếu current_player_sim (người bị chiếu bí) là node_to_simulate_from.player_to_move -> thua (-1.0)
                # Nếu current_player_sim là đối thủ -> thắng (1.0)
                return -1.0 if current_player_sim == node_to_simulate_from.player_to_move else 1.0

            if self.rules.is_stalemate(current_player_sim):
                self.rules.board_instance = original_rules_board_sim
                self.evaluator.board_instance = original_eval_board_sim
                return 0.0

            possible_moves_sim = self.rules.get_all_valid_moves(current_player_sim)
            if not possible_moves_sim: 
                self.rules.board_instance = original_rules_board_sim
                self.evaluator.board_instance = original_eval_board_sim
                # Nếu không có nước đi và không bị chiếu bí -> stalemate
                return 0.0 

            # Rollout Policy: Tạm thời random, có thể cải thiện bằng heuristic nhanh
            chosen_move_sim = random.choice(possible_moves_sim)
            current_board_sim.make_move(chosen_move_sim[0], chosen_move_sim[1])
            current_player_sim = self.rules.get_opponent_color(current_player_sim)
        
        # Hết độ sâu rollout, dùng hàm đánh giá
        # Đánh giá theo góc nhìn của player_to_move của node gốc của rollout (node_to_simulate_from)
        final_rollout_eval = self.evaluator.evaluate_board(node_to_simulate_from.player_to_move, 
                                                           self.move_count_for_eval + i_rollout + 1) # Ước lượng số nước
        self.rules.board_instance = original_rules_board_sim
        self.evaluator.board_instance = original_eval_board_sim
        
        if final_rollout_eval > 200: return 0.8 # Thắng nhẹ
        elif final_rollout_eval < -200: return -0.8 # Thua nhẹ
        return 0.0 # Hòa


    def _mcts_backpropagate(self, node, rollout_result):
        # rollout_result là theo góc nhìn của node.player_to_move
        # (tức là, 1.0 nếu node.player_to_move thắng từ rollout đó)
        temp_node = node
        while temp_node:
            temp_node.visits += 1
            # Nếu player của node cha là đối thủ của player của node hiện tại (luôn đúng),
            # thì kết quả thắng của con là thua của cha.
            # rollout_result là cho player của node (lá) mà rollout bắt đầu.
            # Khi backpropagate lên cha, nếu cha là đối thủ, thì win của cha là -rollout_result.
            if temp_node.player_to_move != self.rules.get_opponent_color(temp_node.parent.player_to_move if temp_node.parent else ""):
                 temp_node.wins += rollout_result # Đúng nếu result là cho player của node hiện tại
            else: # Lượt của đối thủ của người chơi ở node cha
                 temp_node.wins -= rollout_result # (rollout_result là cho player của node lá)
            
            # Đơn giản hóa: result truyền vào là cho player của node hiện tại (node)
            # Khi lên cha, thì kết quả đó phải đảo ngược cho cha.
            # rollout_result = -rollout_result # Đảo ngược cho tầng trên
            temp_node = temp_node.parent
            if temp_node: # Đảo ngược kết quả cho player của node cha
                rollout_result *= -1.0


    def _perform_mcts_search(self, root_board_obj, player_color_ai, time_limit_seconds):
        root_node = MCTSNode(root_board_obj.to_tuple(), player_color_ai, 
                             book_knowledge=self.book_knowledge, 
                             rules_instance=self.rules, 
                             eval_instance=self.evaluator)
        start_mcts_time = time.time()
        sims_count = 0
        # for _ in range(MCTS_SIMULATION_COUNT_PER_MOVE): # Hoặc dùng time_limit
        while time.time() - start_mcts_time < time_limit_seconds - 0.05 : # Để lại chút thời gian
            # if time.time() - start_mcts_time > time_limit_seconds - 0.02: break
            sims_count += 1
            node_to_explore = root_node
            # 1. Selection
            while not node_to_explore.is_terminal:
                if not node_to_explore.is_fully_expanded():
                    break # Sẽ expand node này
                selected_child = node_to_explore.best_child_uct()
                if selected_child is None: # Không có con nào để chọn (ví dụ, tất cả con là terminal)
                    break 
                node_to_explore = selected_child
            
            # 2. Expansion
            if not node_to_explore.is_terminal and not node_to_explore.is_fully_expanded():
                expanded_child = node_to_explore.expand()
                if expanded_child:
                    node_to_explore = expanded_child 
            
            # 3. Simulation
            rollout_val_for_player_at_node_to_explore = 0.0
            if node_to_explore.is_terminal:
                rollout_val_for_player_at_node_to_explore = node_to_explore.terminal_value
            else:
                rollout_val_for_player_at_node_to_explore = self._mcts_simulation_phase(node_to_explore)

            # 4. Backpropagation
            self._mcts_backpropagate(node_to_explore, rollout_val_for_player_at_node_to_explore)
        
        self.mcts_simulations_performed = sims_count # Lưu lại số sim
        print(f"MCTS: Hoàn thành {self.mcts_simulations_performed} simulations trong {time.time() - start_mcts_time:.2f}s")
        
        if not root_node.children:
            print(f"MCTS Warning: Root node cho {player_color_ai} không có con nào sau simulations.")
            return None 
        
        # Chọn nước đi dựa trên số lần visit cao nhất (robust)
        # Hoặc tỉ lệ thắng cao nhất nếu số visit đủ lớn
        best_child_for_move = None
        if any(c.visits > 0 for c in root_node.children):
            best_child_for_move = max(root_node.children, key=lambda node: node.visits)
        elif root_node.children: # Nếu tất cả visit = 0, chọn ngẫu nhiên hoặc con đầu tiên
            print(f"MCTS Warning: Tất cả các con của root cho {player_color_ai} có 0 visits. Chọn con đầu tiên.")
            best_child_for_move = root_node.children[0]
        
        if best_child_for_move and best_child_for_move.move_leading_to_this_node:
            # print(f"MCTS best move debug: {best_child_for_move.move_leading_to_this_node}")
            return best_child_for_move.move_leading_to_this_node
        else:
            print(f"MCTS Error: Không thể chọn best_child_for_move hoặc không có move_leading_to_this_node.")
            return None


    def find_best_move(self, initial_max_depth_suggestion_ignored, player_color_ai, 
                       current_board_history_tuples_param=None, 
                       current_action_history_param=None, 
                       current_move_count_from_game=0, 
                       game_kifu_uci_list_param=None,
                       time_limit_seconds=10): 
        
        self.current_search_start_time = time.time()
        self.time_limit_for_move = float(time_limit_seconds) 
        self._reset_search_helpers() 
        
        current_board_history_tuples = copy.deepcopy(current_board_history_tuples_param if current_board_history_tuples_param is not None else [])
        current_action_history = copy.deepcopy(current_action_history_param if current_action_history_param is not None else [])
        game_kifu_uci_list = copy.deepcopy(game_kifu_uci_list_param if game_kifu_uci_list_param is not None else [])
        
        self.move_count_for_eval = current_move_count_from_game 
        current_game_board_obj = self.rules.board_instance

        # Cập nhật board_instance cho evaluator (quan trọng!)
        self.evaluator.board_instance = current_game_board_obj
        # Và cho rules (mặc dù nó thường được set lại bên trong các hàm tìm kiếm)
        self.rules.board_instance = current_game_board_obj


        print(f"AI ({player_color_ai}) bắt đầu tìm nước. Tổng nước đi: {self.move_count_for_eval}. Giới hạn thời gian: {self.time_limit_for_move:.1f}s.")

        # 1. Sách Khai Cuộc
        if self.book_knowledge and self.move_count_for_eval < 12:
            book_move_uci_str = self.book_knowledge.get_book_move_for_position(current_game_board_obj, player_color_ai, game_kifu_uci_list)
            if book_move_uci_str:
                parsed_book_move = self._uci_to_coords_tuple(book_move_uci_str, player_color_ai, current_game_board_obj)
                if parsed_book_move:
                    # (Kiểm tra tính hợp lệ của nước đi từ sách - giữ nguyên)
                    print(f"AI ({player_color_ai}) chơi từ sách: {book_move_uci_str} -> {self._coords_to_uci_str(parsed_book_move[0], parsed_book_move[1])} ({parsed_book_move[2]})")
                    return parsed_book_move 
        
        # 2. Quyết định thuật toán và thực thi
        best_move_found = None
        game_progress = self.evaluator.get_game_progress_score(self.move_count_for_eval)
        
        # Ưu tiên MCTS nếu có đủ thời gian và không phải tàn cuộc quá sâu
        # (Có thể thêm điều kiện: nếu không có nước đi nào quá tốt từ Alpha-Beta ở độ sâu nông ban đầu)
        # Hoặc, nếu là lượt đầu của AI (ví dụ, Đen đi sau), MCTS có thể tốt hơn để tạo đa dạng
        should_try_mcts = (game_progress < 2.0 and self.time_limit_for_move > 2.5) # Ví dụ: không dùng MCTS nếu thời gian quá ít
        
        if should_try_mcts:
            print(f"AI ({player_color_ai}) thử MCTS. Game progress: {game_progress:.2f}")
            mcts_budget = self.time_limit_for_move * 0.6 # Dành phần lớn thời gian cho MCTS nếu thử
            if self.move_count_for_eval < 4: mcts_budget = self.time_limit_for_move * 0.8 # Nhiều hơn cho khai cuộc

            best_move_found = self._perform_mcts_search(current_game_board_obj, player_color_ai, mcts_budget)
            if best_move_found:
                time_taken = time.time() - self.current_search_start_time
                print(f"AI ({player_color_ai}) MCTS hoàn tất. Nước: {self._coords_to_uci_str(best_move_found[0], best_move_found[1])} ({best_move_found[2]}). Sims: {self.mcts_simulations_performed}. T.gian: {time_taken:.2f}s")
                # self.actual_depth_reached_in_last_search có thể set là self.mcts_simulations_performed
                return best_move_found
            else:
                print(f"AI ({player_color_ai}) MCTS không tìm thấy nước đi, chuyển sang Alpha-Beta.")
        
        # Nếu MCTS không được thử hoặc thất bại, dùng Alpha-Beta
        if not best_move_found:
            print(f"AI ({player_color_ai}) sử dụng Alpha-Beta. Game progress: {game_progress:.2f}")
            # Tính toán thời gian còn lại cho Alpha-Beta
            time_spent_on_mcts = time.time() - self.current_search_start_time if should_try_mcts else 0
            remaining_time_for_ab = self.time_limit_for_move - time_spent_on_mcts - 0.1 # Trừ hao 0.1s
            if remaining_time_for_ab < 0.5: # Nếu còn quá ít thời gian
                print(f"AI ({player_color_ai}) Alpha-Beta: Không đủ thời gian còn lại ({remaining_time_for_ab:.2f}s).")
                # Cố gắng tìm nước nhanh ở độ sâu 1 hoặc 2
                effective_upper_depth_limit = 1 if remaining_time_for_ab < 1.0 else 2
            else:
                # Điều chỉnh độ sâu tối đa dựa trên game_progress và thời gian còn lại
                absolute_max_depth_ab = 10 # Giảm giới hạn tuyệt đối cho AB nếu MCTS đã chạy
                if game_progress < 0.8: 
                    effective_upper_depth_limit = min(absolute_max_depth_ab, 3 if remaining_time_for_ab < 4 else 4) 
                elif game_progress < 1.8: 
                    effective_upper_depth_limit = min(absolute_max_depth_ab, 4 if remaining_time_for_ab < 6 else 5) 
                else: 
                    effective_upper_depth_limit = min(absolute_max_depth_ab, 5 if remaining_time_for_ab < 8 else 7)
            
            print(f"AI ({player_color_ai}) Alpha-Beta. Giới hạn độ sâu lặp: {effective_upper_depth_limit}. Thời gian còn lại: {remaining_time_for_ab:.2f}s")
            
            best_move_overall_ab = None
            best_eval_overall_ab = float('-inf')
            original_search_start_time_for_ab_iter = self.current_search_start_time # Lưu lại để tính timeout cho AB
            # Nếu MCTS đã chạy, current_search_start_time đã bị "tiêu hao"
            # Cần một mốc thời gian mới cho riêng Alpha-Beta
            ab_start_time_this_instance = time.time()


            for current_search_depth_iter in range(1, effective_upper_depth_limit + 1):
                # Cập nhật lại time_limit_for_move cho _minimax_alpha_beta_recursive dựa trên remaining_time_for_ab
                # Hoặc, _minimax_alpha_beta_recursive nên nhận một tham số time_budget riêng
                # Tạm thời, nó vẫn dùng self.time_limit_for_move, nhưng check timeout bên trong
                # Cần đảm bảo self.current_search_start_time là đúng cho check timeout của minimax
                # self.current_search_start_time = ab_start_time_this_instance # Reset cho mỗi lần gọi minimax? Không, cho cả find_best_move
                # Cách tốt hơn: minimax nhận time_budget
                
                # Nếu dùng self.time_limit_for_move, nó phải là thời điểm kết thúc tuyệt đối
                # self.current_search_start_time là thời điểm bắt đầu của find_best_move
                # Thời gian còn lại cho vòng lặp ID này:
                time_left_for_this_id_iteration = (self.current_search_start_time + self.time_limit_for_move) - time.time() - 0.05
                if time_left_for_this_id_iteration < 0.1 : # Nếu còn quá ít, không chạy sâu hơn
                    print(f"AI ({player_color_ai}) Alpha-Beta: Hết giờ trước khi bắt đầu depth {current_search_depth_iter}.")
                    break


                self.initial_max_depth_for_this_call = current_search_depth_iter 
                self.actual_depth_reached_in_last_search = 0 # Reset cho mỗi độ sâu ID
                
                # ... (phần còn lại của vòng lặp Iterative Deepening Alpha-Beta giữ nguyên) ...
                # Đảm bảo self.rules.board_instance và self.evaluator.board_instance được set đúng
                self.rules.board_instance = current_game_board_obj
                self.evaluator.board_instance = current_game_board_obj

                current_best_move_this_iter = None
                current_max_eval_this_iter = float('-inf')
                alpha, beta = float('-inf'), float('inf')
                possible_moves_ab = self.rules.get_all_valid_moves(player_color_ai)
                if not possible_moves_ab: break 

                possible_moves_ab.sort(key=lambda m: self._get_move_score_for_ordering(current_game_board_obj, m[0], m[1], m[2], current_search_depth_iter, player_color_ai), reverse=True)
                
                try:
                    for move_from, move_to, piece_char_moved in possible_moves_ab:
                        # ... (Referee check - giữ nguyên) ...
                        temp_board_obj_ab = XiangqiBoard(copy.deepcopy(current_game_board_obj.board)) # Tạo board mới cho mỗi nước thử
                        temp_board_obj_ab.make_move(move_from, move_to) # Thực hiện trên board mới

                        # Chuẩn bị history cho đệ quy
                        board_hist_child = current_board_history_tuples + [(temp_board_obj_ab.to_tuple(), self.rules.get_opponent_color(player_color_ai))]
                        action_hist_child = current_action_history # (Cần cập nhật action cho nước hiện tại nếu referee dùng)

                        evaluation = self._minimax_alpha_beta_recursive(
                            temp_board_obj_ab, current_search_depth_iter - 1, 
                            alpha, beta, False, player_color_ai, 
                            board_hist_child, action_hist_child, 1 
                        )
                        if evaluation > current_max_eval_this_iter:
                            current_max_eval_this_iter = evaluation
                            current_best_move_this_iter = (move_from, move_to, piece_char_moved)
                        alpha = max(alpha, evaluation)
                        if alpha >= beta: break # Cắt tỉa beta

                    if current_best_move_this_iter:
                        best_move_overall_ab = current_best_move_this_iter
                        best_eval_overall_ab = current_max_eval_this_iter
                        print(f"AI ({player_color_ai}) Alpha-Beta depth {current_search_depth_iter}. Nước: {self._coords_to_uci_str(best_move_overall_ab[0], best_move_overall_ab[1])} ({best_move_overall_ab[2]}), Đ.giá: {best_eval_overall_ab:.0f}, T.gian: {time.time() - self.current_search_start_time:.2f}s, Độ sâu TT: {self.actual_depth_reached_in_last_search}")
                
                except TimeoutError:
                    print(f"AI ({player_color_ai}) Alpha-Beta hết thời gian ở độ sâu lặp {current_search_depth_iter}.")
                    break 
                
                if time.time() - self.current_search_start_time >= self.time_limit_for_move - 0.05:
                    break
            
            best_move_found = best_move_overall_ab # Gán kết quả từ Alpha-Beta

        # Xử lý cuối cùng
        final_time_taken = time.time() - self.current_search_start_time
        if best_move_found:
            print(f"AI ({player_color_ai}) Tìm kiếm hoàn tất. Nước cuối: {self._coords_to_uci_str(best_move_found[0], best_move_found[1])} ({best_move_found[2]}). T.gian: {final_time_taken:.2f}s")
        else:
            print(f"AI ({player_color_ai}) Không tìm thấy nước đi nào sau toàn bộ quá trình. T.gian: {final_time_taken:.2f}s")
            all_valid_at_end = self.rules.get_all_valid_moves(player_color_ai)
            if all_valid_at_end:
                print(f"AI ({player_color_ai}) Chọn nước ngẫu nhiên từ {len(all_valid_at_end)} nước hợp lệ.")
                return random.choice(all_valid_at_end)
        
        return best_move_found # Có thể là None nếu không tìm thấy gì
