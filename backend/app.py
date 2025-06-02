# File: backend/app.py
# Version: V15.1 - Xử lý depth_reached cho MCTS

from flask import Flask, request, jsonify
from flask_cors import CORS
import json
import copy
import os 
import time 

from engine.board import XiangqiBoard
from engine.rules import GameRules
from engine.evaluation import Evaluation
from engine.ai import AIPlayer # AIPlayer giờ có mcts_simulations_performed
from engine.referee import Referee
from engine.book_knowledge import BookKnowledge

app = Flask(__name__)
CORS(app) 

book_knowledge_manager = BookKnowledge()

GAME_SESSIONS = {} 
DEFAULT_SESSION_ID = "default_game"

# --- get_game_state và reset_game_state_api giữ nguyên ---
def get_game_state(session_id=DEFAULT_SESSION_ID):
    if session_id not in GAME_SESSIONS:
        GAME_SESSIONS[session_id] = {
            "moves_since_capture_or_pawn_move": 0,
            "board_history_for_repetition": [], 
            "action_history_for_referee": [],   
            "current_game_kifu_uci": [] ,
            "last_referee_message": None
        }
    return GAME_SESSIONS[session_id]

@app.route('/reset_game_state_internal', methods=['POST'])
def reset_game_state_api():
    session_id = request.json.get("session_id", DEFAULT_SESSION_ID) if request.is_json else DEFAULT_SESSION_ID
    game_state = get_game_state(session_id) 
    game_state["moves_since_capture_or_pawn_move"] = 0
    game_state["board_history_for_repetition"] = []
    game_state["action_history_for_referee"] = []
    game_state["current_game_kifu_uci"] = [] 
    game_state["last_referee_message"] = None
    return jsonify({"message": f"Game state for session {session_id} reset."}), 200

# --- get_book_guidance_api và get_piece_counts_api giữ nguyên ---
@app.route('/get_book_guidance', methods=['POST'])
def get_book_guidance_api():
    data = request.json; fen_string = data.get('fen'); player_to_move = data.get('player_to_move')
    if not fen_string or not player_to_move: return jsonify({'error': 'Thiếu FEN hoặc player_to_move'}), 400
    board_array_from_fen, _, _, _ = XiangqiBoard.fen_to_board_array(fen_string)
    if not board_array_from_fen: return jsonify({'error': 'FEN không hợp lệ'}), 400
    # Cần tạo instance board từ board_array_from_fen
    temp_board_for_guidance = XiangqiBoard(board_array_from_fen)
    study_info_tuple = book_knowledge_manager.find_endgame_study_flexibly(temp_board_for_guidance, player_to_move)
    study_info = study_info_tuple[0] if study_info_tuple else None
    if study_info: 
        return jsonify({
            "study_id": study_info.get("study_id"), "name": study_info.get("name"),
            "description": study_info.get("description_general"), "guidance": study_info.get("guidance")
        })
    return jsonify({'message': 'Không tìm thấy thông tin sách cho thế cờ này.'}), 200

@app.route('/get_piece_counts', methods=['POST'])
def get_piece_counts_api():
    data = request.json
    board_state_frontend = data.get('board_state')
    if not board_state_frontend: return jsonify({'error': 'Thiếu board_state'}), 400
    current_board = XiangqiBoard(); current_board.set_board_state(board_state_frontend)
    counts = current_board.get_piece_counts()
    is_legal, message = current_board.check_piece_count_legality()
    return jsonify({'counts': counts, 'is_legal': is_legal, 'legality_message': message})

@app.route('/get_ai_move', methods=['POST'])
def get_ai_move_api():
    # ... (Phần đầu của hàm giữ nguyên: lấy data, session, board, rules, eval, referee) ...
    start_api_time = time.time()
    data = request.json
    session_id = data.get("session_id", DEFAULT_SESSION_ID)
    game_state_current_session = get_game_state(session_id)
    game_state_current_session["last_referee_message"] = None

    try:
        board_state_frontend = data.get('board_state') 
        player_to_move_ai = data.get('player_to_move')  
        move_count_half_moves_from_frontend = data.get('move_count', 0) 
        time_limit_for_ai_turn = float(data.get('time_limit_seconds', 10.0))

        if not board_state_frontend or not player_to_move_ai:
            return jsonify({'error': 'Thiếu board_state hoặc player_to_move'}), 400

        current_engine_board = XiangqiBoard() 
        current_engine_board.set_board_state(board_state_frontend)
        current_engine_board.current_half_move_count = move_count_half_moves_from_frontend

        rules_for_this_turn = GameRules(current_engine_board) 
        eval_for_this_turn = Evaluation(rules_for_this_turn, book_knowledge_manager) 
        referee_for_this_turn = Referee(rules_for_this_turn) 
        referee_for_this_turn.action_history = copy.deepcopy(game_state_current_session["action_history_for_referee"])
        
        # ... (Logic cập nhật action_history cho đối thủ, luật 60 nước, lặp 3 lần, chiếu bí/hết nước cho AI - giữ nguyên) ...
        # (Đảm bảo các return jsonify ở đây là hợp lệ)
        is_mate_for_ai, mate_winner_if_ai_loses = rules_for_this_turn.is_checkmate(player_to_move_ai)
        if is_mate_for_ai:
            # ... return jsonify ...
            game_state_current_session["last_referee_message"] = {"text": f"Máy ({player_to_move_ai}) bị chiếu bí!", "type": "error"}
            return jsonify({'error': game_state_current_session["last_referee_message"]["text"], 'game_over': True, 'winner': mate_winner_if_ai_loses, 'referee_message': game_state_current_session["last_referee_message"]}), 200
        if rules_for_this_turn.is_stalemate(player_to_move_ai):
            # ... return jsonify ...
            game_state_current_session["last_referee_message"] = {"text": f"Máy ({player_to_move_ai}) hết nước đi (hòa cờ)!", "type": "info"}
            return jsonify({'error': game_state_current_session["last_referee_message"]["text"], 'game_over': True, 'winner': 'draw_stalemate', 'referee_message': game_state_current_session["last_referee_message"]}), 200


        ai_player_instance = AIPlayer(rules_for_this_turn, eval_for_this_turn, 
                                      referee_for_this_turn, book_knowledge_manager)
        
        best_move_tuple_from_ai = ai_player_instance.find_best_move(
            0, player_to_move_ai, 
            game_state_current_session["board_history_for_repetition"],
            copy.deepcopy(referee_for_this_turn.action_history),
            move_count_half_moves_from_frontend,
            copy.deepcopy(game_state_current_session["current_game_kifu_uci"]),
            time_limit_for_ai_turn
        )
        
        # Lấy thông tin tìm kiếm từ AIPlayer instance
        search_info_display = ""
        if ai_player_instance.mcts_simulations_performed > 0:
            search_info_display = f"MCTS Sims: {ai_player_instance.mcts_simulations_performed}"
        elif ai_player_instance.actual_depth_reached_in_last_search > 0:
            search_info_display = f"AB Depth: {ai_player_instance.actual_depth_reached_in_last_search}"
        else:
            search_info_display = "N/A"


        if best_move_tuple_from_ai:
            (from_sq_ai, to_sq_ai, piece_moved_by_ai_char) = best_move_tuple_from_ai
            # ... (Cập nhật game_state_current_session - giữ nguyên) ...
            board_tuple_before_ai_move = current_engine_board.to_tuple() # Board TRƯỚC khi AI đi
            game_state_current_session["board_history_for_repetition"].append((board_tuple_before_ai_move, player_to_move_ai))
            # ... (cập nhật kifu, action_history, kiểm tra luật cấm lặp của AI, 50-move rule)

            return jsonify({
                'from_sq': from_sq_ai, 'to_sq': to_sq_ai, 
                'piece_moved': piece_moved_by_ai_char,
                'depth_reached': search_info_display, # Hiển thị thông tin tìm kiếm
                'referee_message': game_state_current_session["last_referee_message"]
            })
        else: 
            game_state_current_session["last_referee_message"] = {"text": f"Máy ({player_to_move_ai}) không tìm thấy nước đi hợp lệ (AI returned None).", "type": "warning"}
            return jsonify({
                'error': game_state_current_session["last_referee_message"]["text"], 
                'game_over': True, 
                'winner': 'draw_ai_no_valid_moves', 
                'referee_message': game_state_current_session["last_referee_message"],
                'depth_reached': search_info_display
            }), 200

    except Exception as e:
        import traceback
        tb_str = traceback.format_exc()
        print(f"Lỗi nghiêm trọng trong API get_ai_move: {e}\n{tb_str}")
        return jsonify({'error': f'Lỗi máy chủ nội bộ: {str(e)}', 'game_over': True, 'referee_message': {"text": f"Lỗi máy chủ nghiêm trọng: {str(e)}", "type": "error"}}), 500

if __name__ == '__main__':
    app.run(debug=True, port=5000)
