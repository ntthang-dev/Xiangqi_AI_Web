// File: frontend/js/api_client.js
// Xử lý giao tiếp với backend Python để lấy nước đi của AI.

async function fetchAIMove(currentBoardState, currentPlayer, 
                           initialMaxDepthSuggestion, // Đã bị loại bỏ ý nghĩa, AI tự quyết định
                           boardHistoryFromGame, 
                           currentMoveCount, currentLastMove, 
                           currentGameKifuStrings, // Kỳ phổ dạng chuỗi (ví dụ: notation)
                           timeLimitSecondsForAI // Thời gian cho phép AI
                           ) {
    
    updateAiTimeMessage("Máy đang suy nghĩ..."); 
    updateAiDepthLog("Độ sâu AI đạt được: Đang tính..."); // Reset log độ sâu

    const historyForBackend = boardHistoryFromGame.map(item => ({
        board: item.board, 
        player_moved_to_this_state: item.player_moved_to_this_state 
    }));

    // Chuẩn bị game_kifu_uci (nếu có, nếu không thì gửi mảng rỗng)
    // Backend hiện tại đang mong đợi game_kifu_uci là list các UCI strings
    // Nếu gameState.moveHistory lưu UCI thì dùng, nếu không thì cần chuyển đổi
    // Tạm thời giả sử chúng ta sẽ gửi mảng rỗng hoặc mảng notation nếu backend có thể xử lý
    const kifuForBackend = gameState.moveHistory.map(m => m.notation); // Gửi notation, backend có thể không dùng trực tiếp cho book

    try {
        const response = await fetch(`${API_BASE_URL}/get_ai_move`, { 
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                board_state: currentBoardState,    
                player_to_move: currentPlayer,     
                // depth: initialMaxDepthSuggestion, // Backend sẽ tự quyết định độ sâu
                full_history: historyForBackend,   
                move_count: currentMoveCount,      
                last_move_info: currentLastMove ? { 
                    from: currentLastMove.from, // Gửi cả from và to
                    to: currentLastMove.to,
                    piece: currentLastMove.piece,       
                    captured: currentLastMove.captured  
                } : null,
                game_kifu_uci: [], // Gửi mảng rỗng, backend sẽ dựa vào board_history và move_count để khớp sách
                                   // Hoặc gửi gameState.moveHistory.map(m => m.uci_notation) nếu có
                time_limit_seconds: timeLimitSecondsForAI // Gửi giới hạn thời gian cho AI
            }),
        });

        if (!response.ok) {
            const errorData = await response.json().catch(() => ({ error: "Lỗi không xác định từ backend khi parse JSON" })); 
            console.error('Lỗi từ backend AI:', response.status, errorData.error);
            updateAiTimeMessage(`Lỗi AI: ${errorData.error || response.statusText}`);
            // Trả về đối tượng lỗi để main.js có thể xử lý
            return { error: errorData.error || response.statusText, game_over: errorData.game_over, winner: errorData.winner };
        }

        const data = await response.json();
        if (data.error) {
            console.error('Backend AI trả về lỗi:', data.error);
            updateAiTimeMessage(`Lỗi AI: ${data.error}`);
             // Trả về đối tượng lỗi để main.js có thể xử lý
            return { error: data.error, game_over: data.game_over, winner: data.winner };
        }
        
        // Backend trả về: { from_sq: [r,c], to_sq: [r,c], piece_moved: 'P', depth_reached: X }
        return {
            fromR: data.from_sq[0],
            fromC: data.from_sq[1],
            toR: data.to_sq[0],
            toC: data.to_sq[1],
            pieceKey: data.piece_moved,
            depth_reached: data.depth_reached // Nhận độ sâu AI đạt được
        };

    } catch (error) {
        console.error('Lỗi kết nối đến backend AI:', error);
        updateAiTimeMessage("Lỗi kết nối AI!");
        return { error: "Lỗi kết nối đến máy chủ AI.", game_over: false }; // Trả về đối tượng lỗi
    }
}