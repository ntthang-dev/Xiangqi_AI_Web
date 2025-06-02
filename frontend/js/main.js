// File: frontend/js/main.js
// Logic chính của game phía client, bao gồm xử lý sự kiện, gọi API, cập nhật UI.

let youtubePlayer;
let musicPlaying = false;
// ImlggmPoTRo jfKfPfyJRdk
let currentYoutubeVideoId = 'ImlggmPoTRo'; // ID video mặc định, có thể thay đổi
let youtubeApiReady = false;
let initialVolume = 20; // Âm lượng khởi tạo

// Hàm này được gọi tự động bởi YouTube API khi sẵn sàng
function onYouTubeIframeAPIReady() {
    console.log("YouTube IFrame API is ready.");
    youtubeApiReady = true;
    try {
        youtubePlayer = new YT.Player('youtubePlayer', { // Target div ẩn
            height: '1', // Kích thước siêu nhỏ
            width: '1',  // Kích thước siêu nhỏ
            videoId: currentYoutubeVideoId,
            playerVars: {
                'autoplay': 1,
                'controls': 0, // Ẩn control mặc định của YouTube
                'loop': 1,
                'playlist': currentYoutubeVideoId, // Cần thiết cho loop
                'mute': 0, // Bắt đầu không tắt tiếng, nhưng âm lượng nhỏ
                'origin': window.location.origin // Thêm origin để tránh một số lỗi
            },
            events: {
                'onReady': onPlayerReady,
                'onStateChange': onPlayerStateChange
            }
        });
    } catch (e) {
        console.error("Error creating YouTube player:", e);
        const toggleMusicBtnPanel = document.getElementById('toggleMusicPanelBtn');
        if (toggleMusicBtnPanel) {
            toggleMusicBtnPanel.innerHTML = '<i class="fas fa-exclamation-triangle"></i> Lỗi Nhạc';
            toggleMusicBtnPanel.disabled = true;
        }
    }
}

function onPlayerReady(event) {
    console.log("YouTube Player is ready.");
    event.target.setVolume(initialVolume); // Đặt âm lượng ban đầu
    event.target.playVideo(); // Thử phát ngay khi sẵn sàng
    // musicPlaying sẽ được set trong onPlayerStateChange

    const toggleMusicBtnPanel = document.getElementById('toggleMusicPanelBtn');
    if (toggleMusicBtnPanel) {
        // Sẽ cập nhật dựa trên PlayerState
        toggleMusicBtnPanel.disabled = false;
    }
    const volumeSliderPanel = document.getElementById('volumeSliderPanel');
    if (volumeSliderPanel) {
        volumeSliderPanel.value = initialVolume;
    }
}

function onPlayerStateChange(event) {
    const toggleMusicBtnPanel = document.getElementById('toggleMusicPanelBtn');
    if (event.data === YT.PlayerState.PLAYING) {
        musicPlaying = true;
        if (toggleMusicBtnPanel) toggleMusicBtnPanel.innerHTML = '<i class="fas fa-volume-mute"></i> Tắt Nhạc';
    } else if (event.data === YT.PlayerState.PAUSED || event.data === YT.PlayerState.ENDED || event.data === YT.PlayerState.CUED) {
        musicPlaying = false;
        if (toggleMusicBtnPanel) toggleMusicBtnPanel.innerHTML = '<i class="fas fa-music"></i> Bật Nhạc';
        if (event.data === YT.PlayerState.ENDED && youtubePlayer.isLooping()) { // Tự động phát lại nếu loop
             youtubePlayer.playVideo();
        }
    }
}

function toggleMusicPanel() {
    const toggleMusicBtnPanel = document.getElementById('toggleMusicPanelBtn');
    if (!youtubePlayer || typeof youtubePlayer.getPlayerState !== 'function') {
        updateRefereeMessage("Trình phát nhạc chưa sẵn sàng hoặc có lỗi.", "warning");
        if (toggleMusicBtnPanel) {
            toggleMusicBtnPanel.innerHTML = '<i class="fas fa-exclamation-triangle"></i> Lỗi';
            toggleMusicBtnPanel.disabled = true;
        }
        if (!youtubeApiReady) { // Thử load lại API nếu chưa sẵn sàng
            console.log("Attempting to re-init YouTube API for music.");
            var tag = document.createElement('script');
            tag.src = "https://www.youtube.com/iframe_api";
            var firstScriptTag = document.getElementsByTagName('script')[0];
            if (firstScriptTag && firstScriptTag.parentNode) {
                firstScriptTag.parentNode.insertBefore(tag, firstScriptTag);
            } else {
                document.head.appendChild(tag);
            }
        }
        return;
    }

    if (musicPlaying) {
        youtubePlayer.pauseVideo();
    } else {
        youtubePlayer.playVideo();
    }
    // musicPlaying và text của nút sẽ được cập nhật bởi onPlayerStateChange
}

function changeMusicFromPanel() {
    const youtubeIdInputPanel = document.getElementById('youtubeIdInputPanel');
    if (!youtubePlayer || typeof youtubePlayer.loadVideoById !== 'function' || !youtubeIdInputPanel) {
        updateRefereeMessage("Trình phát nhạc chưa sẵn sàng để đổi bài.", "warning");
        return;
    }
    const newVideoId = youtubeIdInputPanel.value.trim();
    if (newVideoId) {
        currentYoutubeVideoId = newVideoId; // Cập nhật ID hiện tại
        youtubePlayer.loadVideoById({
            'videoId': newVideoId,
            // 'playerVars': {'playlist': newVideoId } // Cập nhật playlist cho loop
        });
        // Nếu muốn tự động phát sau khi đổi:
        // youtubePlayer.playVideo(); // Hoặc chờ onPlayerStateChange xử lý
        updateRefereeMessage(`Đã đổi nhạc sang video ID: ${newVideoId}`, "info");
    } else {
        updateRefereeMessage("Vui lòng nhập YouTube Video ID hợp lệ.", "warning");
    }
}

function setVolumeFromPanel(volumeValue) {
    if (youtubePlayer && typeof youtubePlayer.setVolume === 'function') {
        youtubePlayer.setVolume(volumeValue);
        initialVolume = volumeValue; // Lưu lại lựa chọn âm lượng
    }
}


document.addEventListener('DOMContentLoaded', () => {
    // ... (giữ nguyên các khai báo nút và logic game khác) ...
    const newGameButton = document.getElementById('newGameBtn');
    const pauseResumeButton = document.getElementById('pauseResumeBtn');
    const gameModeSelector = document.getElementById('gameModeSelect');
    const timeControlSelector = document.getElementById('timeControlSelect');
    const saveGameButton = document.getElementById('saveGameBtn');
    const clearHistoryButton = document.getElementById('clearHistoryBtn');
    const pieceCountDisplay = document.getElementById('pieceCountDisplay'); 
    
    // Music Panel Controls
    const toggleMusicBtnPanel = document.getElementById('toggleMusicPanelBtn');
    const volumeSliderPanel = document.getElementById('volumeSliderPanel');
    const youtubeIdInputPanel = document.getElementById('youtubeIdInputPanel');
    const changeMusicPanelBtn = document.getElementById('changeMusicPanelBtn');

    const goToStartBtn = document.getElementById('goToStartBtn');
    const prevMoveBtn = document.getElementById('prevMoveBtn');
    const nextMoveBtn = document.getElementById('nextMoveBtn');
    const goToEndBtn = document.getElementById('goToEndBtn');

    const reviewGameModalButton = document.getElementById('reviewGameButton');
    const newGameModalButton = document.getElementById('newGameModalButton');
    
    const API_BASE_URL_MAIN = API_BASE_URL; 

    function initializeNewGame() {
        gameState.initialize(); 
        
        if (gameModeSelector) gameState.setGameMode(gameModeSelector.value);
        if (timeControlSelector) gameState.selectedTimeControlSchemeKey = timeControlSelector.value;
        
        gameState.initializeTimeControl(); 

        updateStatusMessage(`Đến lượt ${gameState.currentPlayer === 'red' ? 'Đỏ' : 'Đen'}`);
        updateGamePhaseDisplayUI(gameState.getGamePhase());
        updatePlayerScoresUI(gameState.boardState, gameState.moveCount);
        fetchAndDisplayPieceCounts(); 
        
        gameState.startMainTimer();
        gameState.startPlayerTimer(); 
        updatePlayerTimersDisplayUI(gameState.redTimeSpent, gameState.blackTimeSpent, gameState.currentPlayer, gameState.gamePaused, gameState.isGameOver);
        
        const initialScheme = TIME_CONTROL_SCHEMES[gameState.selectedTimeControlSchemeKey];
        updateTimeControlDisplay('red', gameState.playerTimeControlState.red, initialScheme);
        updateTimeControlDisplay('black', gameState.playerTimeControlState.black, initialScheme);
        const ruleDisplayEl = document.getElementById('selectedTimeControlRule');
        if (ruleDisplayEl && initialScheme) {
            ruleDisplayEl.textContent = initialScheme.description || "";
        } else if (ruleDisplayEl) {
            ruleDisplayEl.textContent = "";
        }

        gameState.startPeriodCountdownTimer(); 

        if (pauseResumeButton) {
            pauseResumeButton.textContent = "Tạm Dừng";
            pauseResumeButton.classList.remove('bg-teal-500', 'hover:bg-teal-600');
            pauseResumeButton.classList.add('bg-orange-500', 'hover:bg-orange-600');
            pauseResumeButton.disabled = false;
        }
        updateMoveHistoryDisplay([]); 
        updateAiTimeMessage("Thời gian AI tính toán: -");
        updateAiDepthLog("Độ sâu AI đạt được: -");
        updateRefereeMessage("Ván cờ bắt đầu!", "info"); 
        
        hideGameOverModal();
        createBoardUI(gameState.boardState, handleSquareClick); 
        updateReviewControlsUI(); 
        loadPlayedGamesList(); 
        
        fetch(`${API_BASE_URL_MAIN}/reset_game_state_internal`, { 
            method: 'POST',
            headers: { 'Content-Type': 'application/json' }, 
            body: JSON.stringify({}) 
         })
            .then(response => response.json())
            .then(data => console.log("Backend game state reset:", data.message))
            .catch(error => console.error('Error resetting backend game state:', error));

        if (!gameState.isGameOver && 
            ((gameState.gameMode === 'pvaBlack' && gameState.currentPlayer === 'red') || 
             (gameState.gameMode === 'ava' && gameState.currentPlayer === 'red'))) {
            setTimeout(triggerAiMove, 100); 
        }
    }

    async function fetchAndDisplayPieceCounts() {
        if (!pieceCountDisplay) return;
        try {
            const response = await fetch(`${API_BASE_URL_MAIN}/get_piece_counts`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ board_state: gameState.boardState })
            });
            if (!response.ok) {
                const errorText = await response.text();
                throw new Error(`HTTP error! status: ${response.status}, ${errorText}`);
            }
            const data = await response.json();
            if (data.counts) {
                let displayText = "Số quân: ";
                const order = ['Chariot', 'Horse', 'Cannon', 'Advisor', 'Elephant', 'Pawn', 'General'];
                displayText += "Đỏ (";
                displayText += order.map(p => `${PIECE_CHAR_MAP[p.charAt(0).toUpperCase()]||p.charAt(0)}:${data.counts.red[p] || 0}`).join(',');
                displayText += ") ";
                displayText += "Đen (";
                displayText += order.map(p => `${PIECE_CHAR_MAP[p.charAt(0).toLowerCase()]||p.charAt(0)}:${data.counts.black[p] || 0}`).join(',');
                displayText += ")";
                pieceCountDisplay.textContent = displayText;

                if (!data.is_legal && data.legality_message) { 
                    updateRefereeMessage(data.legality_message, "error");
                }
            } else {
                pieceCountDisplay.textContent = "Số lượng quân: Lỗi";
            }
        } catch (error) {
            console.error("Lỗi khi lấy số lượng quân:", error);
            pieceCountDisplay.textContent = "Số lượng quân: Không tải được";
        }
    }

    function handleSquareClick(r, c) {
        if (gameState.gamePaused || gameState.isGameOver || gameState.isReviewMode) return;
        if (gameState.gameMode.startsWith('pva') && gameState.currentPlayer !== gameState.playerColor) return; 
        if (gameState.gameMode === 'ava') return; 

        const pieceKey = gameState.boardState[r][c];
        if (gameState.selectedPiece) { 
            const isValidTarget = gameState.validMoves.some(move => move.r === r && move.c === c);
            if (isValidTarget) { 
                const playerMakingMove = gameState.currentPlayer;
                const boardBeforeMove = gameState.boardState.map(row => [...row]); 
                const movingPieceKey = gameState.selectedPiece.pieceKey;
                const capturedPieceKeyOnTarget = gameState.boardState[r][c]; 

                gameState.boardState[r][c] = movingPieceKey;
                gameState.boardState[gameState.selectedPiece.r][gameState.selectedPiece.c] = null;
                
                const moveDetails = { 
                    from: { r: gameState.selectedPiece.r, c: gameState.selectedPiece.c }, 
                    to: { r: r, c: c }, 
                    piece: movingPieceKey, 
                    captured: capturedPieceKeyOnTarget 
                };
                gameState.lastMove = moveDetails;
                gameState.moveCount++;

                const moveNotation = formatMoveNotation(moveDetails.from.r, moveDetails.from.c, moveDetails.to.r, moveDetails.to.c, movingPieceKey, boardBeforeMove);
                gameState.addMoveToHistory(moveDetails.from.r, moveDetails.from.c, moveDetails.to.r, moveDetails.to.c, movingPieceKey, boardBeforeMove, capturedPieceKeyOnTarget);
                gameState.recordBoardHistory(playerMakingMove, moveNotation); 
                
                updateMoveHistoryDisplay(gameState.moveHistory); 
                gameState.updatePlayerTimeStateAfterMove(playerMakingMove);

                gameState.stopPlayerTimer();
                gameState.currentPlayer = getOpponentColor(gameState.currentPlayer);
                gameState.startPlayerTimer();
                gameState.clearSelection();
                
                createBoardUI(gameState.boardState, handleSquareClick);
                highlightLastMoveUI(gameState.lastMove);
                updateStatusMessage(`Đến lượt ${gameState.currentPlayer === 'red' ? 'Đỏ' : 'Đen'}`);
                updatePlayerScoresUI(gameState.boardState, gameState.moveCount);
                fetchAndDisplayPieceCounts(); 
                updatePlayerTimersDisplayUI(gameState.redTimeSpent, gameState.blackTimeSpent, gameState.currentPlayer, gameState.gamePaused, gameState.isGameOver);
                updateGamePhaseDisplayUI(gameState.getGamePhase());
                highlightCheckUI(gameState.currentPlayer, gameState.boardState);
                
                const schemeForNextPlayer = TIME_CONTROL_SCHEMES[gameState.selectedTimeControlSchemeKey];
                updateTimeControlDisplay(gameState.currentPlayer, gameState.playerTimeControlState[gameState.currentPlayer], schemeForNextPlayer);

                const gameOverStatusClient = isGameOverClientSide(); 
                if (gameOverStatusClient) {
                    handleGameOverUI(gameOverStatusClient);
                } else if (gameState.gameMode.startsWith('pva') && gameState.currentPlayer !== gameState.playerColor && !gameState.isGameOver) {
                    setTimeout(triggerAiMove, 100);
                }

            } else if (pieceKey && getPieceInfo(pieceKey) && getPieceInfo(pieceKey).color === gameState.currentPlayer) {
                const moves = getValidMovesForPieceClient(r, c, pieceKey, gameState.boardState);
                gameState.selectPiece(r, c, pieceKey, moves);
                clearHighlightsUI();
                highlightSelectedPieceUI(r, c);
                highlightValidMovesUI(moves);
            } else { 
                gameState.clearSelection();
                clearHighlightsUI();
            }
        } else { 
            if (pieceKey && getPieceInfo(pieceKey) && getPieceInfo(pieceKey).color === gameState.currentPlayer) {
                const moves = getValidMovesForPieceClient(r, c, pieceKey, gameState.boardState);
                gameState.selectPiece(r, c, pieceKey, moves);
                highlightSelectedPieceUI(r, c);
                highlightValidMovesUI(moves);
            }
        }
    }

    async function triggerAiMove() {
        if (gameState.gamePaused || gameState.isGameOver || gameState.isReviewMode) return;
        
        updateStatusMessage(`Máy (${gameState.currentPlayer === 'red' ? 'Đỏ' : 'Đen'}) đang suy nghĩ...`);
        const startTime = performance.now();
        const playerAiIsMovingFor = gameState.currentPlayer;

        let timeLimitForThisTurn = 10.0; 
        const tcState = gameState.playerTimeControlState[playerAiIsMovingFor];
        const scheme = TIME_CONTROL_SCHEMES[gameState.selectedTimeControlSchemeKey];
        if (tcState && tcState.currentPeriodIndex !== -1 && scheme && scheme.periods.length > 0) {
            timeLimitForThisTurn = Math.max(5, Math.min(30, Math.floor(tcState.timeRemainingInCurrentPeriodSeconds / 10))); 
            if (tcState.timeRemainingInCurrentPeriodSeconds < 15 && tcState.timeRemainingInCurrentPeriodSeconds > 2) {
                 timeLimitForThisTurn = Math.max(2, tcState.timeRemainingInCurrentPeriodSeconds - 2);
            } else if (tcState.timeRemainingInCurrentPeriodSeconds <= 2) {
                timeLimitForThisTurn = 1; 
            }
        }

        const aiMoveData = await fetchAIMove( 
            gameState.boardState, playerAiIsMovingFor, 0, 
            gameState.boardHistory, gameState.moveCount, gameState.lastMove, 
            gameState.moveHistory.map(m => m.notation), 
            timeLimitForThisTurn
        );
        
        const endTime = performance.now();
        const duration = ((endTime - startTime) / 1000).toFixed(2);
        updateAiTimeMessage(`Thời gian AI tính toán: ${duration} giây`);
        if(aiMoveData && aiMoveData.depth_reached !== undefined) { 
            updateAiDepthLog(`Độ sâu AI đạt được: ${aiMoveData.depth_reached}`);
        }

        if (aiMoveData && aiMoveData.referee_message) {
            updateRefereeMessage(aiMoveData.referee_message.text, aiMoveData.referee_message.type);
        }

        if (aiMoveData && aiMoveData.error) { 
            console.error("Backend AI trả về lỗi:", aiMoveData.error);
            updateStatusMessage(`Lỗi AI: ${aiMoveData.error}`, true);
            if (aiMoveData.game_over) {
                handleGameOverUI({ 
                    message: aiMoveData.winner === 'draw' ? 'Hòa cờ!' : `${aiMoveData.winner === 'red' ? 'Đỏ' : 'Đen'} thắng!`, 
                    reason: aiMoveData.error 
                });
            }
            return; 
        }
        
        if (aiMoveData && aiMoveData.last_move_ai_was_illegal) {
            console.warn("Nước đi của AI được backend xác định là phạm luật.");
            if (aiMoveData.game_over) {
                 handleGameOverUI({ 
                    message: `${aiMoveData.winner === 'red' ? 'Đỏ' : 'Đen'} thắng!`, 
                    reason: aiMoveData.referee_message ? aiMoveData.referee_message.text : "Máy phạm luật."
                });
            }
            return; 
        }

        if (aiMoveData && aiMoveData.fromR !== undefined && !gameState.isGameOver) { 
            const boardBeforeAIMove = gameState.boardState.map(row => [...row]);
            const capturedPieceKeyOnTarget = gameState.boardState[aiMoveData.toR][aiMoveData.toC];

            gameState.boardState[aiMoveData.toR][aiMoveData.toC] = aiMoveData.pieceKey;
            gameState.boardState[aiMoveData.fromR][aiMoveData.fromC] = null;
            
            const moveDetails = { 
                from: { r: aiMoveData.fromR, c: aiMoveData.fromC }, 
                to: { r: aiMoveData.toR, c: aiMoveData.toC }, 
                piece: aiMoveData.pieceKey,
                captured: capturedPieceKeyOnTarget
            };
            gameState.lastMove = moveDetails;
            gameState.moveCount++;

            const moveNotation = formatMoveNotation(moveDetails.from.r, moveDetails.from.c, moveDetails.to.r, moveDetails.to.c, aiMoveData.pieceKey, boardBeforeAIMove);
            gameState.addMoveToHistory(moveDetails.from.r, moveDetails.from.c, moveDetails.to.r, moveDetails.to.c, aiMoveData.pieceKey, boardBeforeAIMove, capturedPieceKeyOnTarget);
            gameState.recordBoardHistory(playerAiIsMovingFor, moveNotation);

            updateMoveHistoryDisplay(gameState.moveHistory);
            gameState.updatePlayerTimeStateAfterMove(playerAiIsMovingFor);

            gameState.stopPlayerTimer();
            gameState.currentPlayer = getOpponentColor(gameState.currentPlayer);
            gameState.startPlayerTimer();
            
            createBoardUI(gameState.boardState, handleSquareClick);
            highlightLastMoveUI(gameState.lastMove);
            updateStatusMessage(`Đến lượt ${gameState.currentPlayer === 'red' ? 'Đỏ' : 'Đen'}`);
            updatePlayerScoresUI(gameState.boardState, gameState.moveCount);
            fetchAndDisplayPieceCounts(); 
            updatePlayerTimersDisplayUI(gameState.redTimeSpent, gameState.blackTimeSpent, gameState.currentPlayer, gameState.gamePaused, gameState.isGameOver);
            updateGamePhaseDisplayUI(gameState.getGamePhase());
            highlightCheckUI(gameState.currentPlayer, gameState.boardState);

            const schemeForNextPlayer = TIME_CONTROL_SCHEMES[gameState.selectedTimeControlSchemeKey];
            updateTimeControlDisplay(gameState.currentPlayer, gameState.playerTimeControlState[gameState.currentPlayer], schemeForNextPlayer);

            const gameOverStatusClient = isGameOverClientSide();
            if (gameOverStatusClient) {
                handleGameOverUI(gameOverStatusClient);
            } else if (gameState.gameMode === 'ava' && !gameState.gamePaused && !gameState.isGameOver) {
                setTimeout(triggerAiMove, 300); 
            }
        } else if (!aiMoveData && !gameState.isGameOver) { 
            console.error("AI không tìm thấy nước đi hợp lệ hoặc có lỗi API không rõ ràng.");
            updateStatusMessage("Lỗi AI hoặc không có nước đi.", true);
            const winner = getOpponentColor(playerAiIsMovingFor);
            handleGameOverUI({ 
                message: `${winner === 'red' ? 'Đỏ' : 'Đen'} thắng!`, 
                reason: `Máy (${playerAiIsMovingFor === 'red' ? 'Đỏ' : 'Đen'}) không tìm được nước đi.` 
            });
        }
    }
    
    function handleGameOverUI(result) { 
        if (gameState.isGameOver) return; 
        gameState.isGameOver = true;
        gameState.gamePaused = true; 
        if (pauseResumeButton) pauseResumeButton.disabled = true;

        let message = result.message || "Ván đấu kết thúc!";
        let reason = result.reason || "";

        console.log("Game Over:", message, reason);
        showGameOverModal(message, reason);
        updateStatusMessage(message, true); 
        updatePlayerTimersDisplayUI(gameState.redTimeSpent, gameState.blackTimeSpent, gameState.currentPlayer, gameState.gamePaused, gameState.isGameOver);
        updateRefereeMessage(reason || message, result.winner === 'draw' ? "info" : "error"); 
        saveCurrentGameToLocalStorage(); 
    }

    function startReviewMode() {
        gameState.isReviewMode = true;
        gameState.gamePaused = true; 
        gameState.currentReviewIndex = gameState.boardHistory.length - 1; 
        displayBoardForReview();
        updateStatusMessage("Chế độ xem lại ván đấu.", false);
        updateReviewControlsUI();
        if (pauseResumeButton) pauseResumeButton.disabled = true;
    }

    function displayBoardForReview() {
        if (!gameState.isReviewMode || gameState.currentReviewIndex < 0 || gameState.currentReviewIndex >= gameState.boardHistory.length) return;

        const historyEntry = gameState.boardHistory[gameState.currentReviewIndex];
        const boardStateToDisplay = JSON.parse(historyEntry.board);
        createBoardUI(boardStateToDisplay, () => {}); 

        clearHighlightsUI(); 
        if (gameState.currentReviewIndex > 0 && gameState.currentReviewIndex <= gameState.moveHistory.length) {
            const moveToHighlight = gameState.moveHistory[gameState.currentReviewIndex -1];
            if (moveToHighlight) {
                 highlightLastMoveUI({ 
                    from: { r: moveToHighlight.fromR, c: moveToHighlight.fromC }, 
                    to: { r: moveToHighlight.toR, c: moveToHighlight.toC }
                });
                const playerMoved = moveToHighlight.player === 'red' ? 'Đỏ' : 'Đen';
                updateStatusMessage(`Xem lại: ${Math.ceil(gameState.currentReviewIndex /2)}. ${playerMoved}: ${moveToHighlight.notation}`, false);
            }
        } else if (gameState.currentReviewIndex === 0) {
             updateStatusMessage("Xem lại: Bắt đầu ván đấu.", false);
        }
        updateReviewControlsUI();
        fetchAndDisplayPieceCounts(); 
    }

    if(goToStartBtn) goToStartBtn.addEventListener('click', () => {
        if (!gameState.isReviewMode && gameState.moveHistory.length === 0 && gameState.boardHistory.length <=1) return; 
        if (!gameState.isReviewMode) startReviewMode();
        gameState.currentReviewIndex = 0;
        displayBoardForReview();
    });
    if(prevMoveBtn) prevMoveBtn.addEventListener('click', () => {
        if (!gameState.isReviewMode && gameState.moveHistory.length === 0 && gameState.boardHistory.length <=1) return;
        if (!gameState.isReviewMode) startReviewMode();
        if (gameState.currentReviewIndex > 0) {
            gameState.currentReviewIndex--;
            displayBoardForReview();
        }
    });
    if(nextMoveBtn) nextMoveBtn.addEventListener('click', () => {
        if (!gameState.isReviewMode && gameState.moveHistory.length === 0 && gameState.boardHistory.length <=1) return;
        if (!gameState.isReviewMode) startReviewMode();
        if (gameState.currentReviewIndex < gameState.boardHistory.length - 1) {
            gameState.currentReviewIndex++;
            displayBoardForReview();
        }
    });
    if(goToEndBtn) goToEndBtn.addEventListener('click', () => {
        if (!gameState.isReviewMode && gameState.moveHistory.length === 0 && gameState.boardHistory.length <=1) return;
        if (!gameState.isReviewMode) startReviewMode();
        gameState.currentReviewIndex = gameState.boardHistory.length - 1;
        displayBoardForReview();
    });

    function generateKifu() {
        let kifu = `[Event "Ván Cờ Tướng AI"]\n`;
        kifu += `[Site "Local Game"]\n`;
        kifu += `[Date "${new Date().toISOString().slice(0,10)}"]\n`;
        kifu += `[Round "-"]\n`;
        kifu += `[Red "${gameState.gameMode === 'pvaRed' || gameState.gameMode === 'ava' ? (gameState.gameMode === 'pvaRed' ? 'Người' : 'Máy 1') : 'Máy'}"]\n`;
        kifu += `[Black "${gameState.gameMode === 'pvaBlack' || gameState.gameMode === 'ava' ? (gameState.gameMode === 'pvaBlack' ? 'Người' : 'Máy 2') : 'Máy'}"]\n`;
        let resultStr = "*"; 
        if(gameState.isGameOver) {
            const gameOverInfo = isGameOverClientSide(); 
            if(gameOverInfo && gameOverInfo.winner) {
                if(gameOverInfo.winner === 'red') resultStr = "1-0";
                else if(gameOverInfo.winner === 'black') resultStr = "0-1";
                else if(gameOverInfo.winner === 'draw') resultStr = "1/2-1/2";
            }
        }
        kifu += `[Result "${resultStr}"]\n`;
        kifu += `[FEN "${INITIAL_BOARD_SETUP_FEN}"]\n\n`; 

        let moveText = "";
        for (let i = 0; i < gameState.moveHistory.length; i++) {
            if (i % 2 === 0) { 
                moveText += `${Math.floor(i / 2) + 1}. ${gameState.moveHistory[i].notation} `;
            } else { 
                moveText += `${gameState.moveHistory[i].notation}\n`;
            }
        }
        if (gameState.moveHistory.length % 2 !== 0) moveText += "\n"; 
        kifu += moveText.trim();
        if(gameState.isGameOver && resultStr !== "*") kifu += ` ${resultStr}`; 
        return kifu;
    }

    if(saveGameButton) saveGameButton.addEventListener('click', () => {
        if (gameState.moveHistory.length === 0 && gameState.boardHistory.length <=1) { 
            updateRefereeMessage("Chưa có nước đi nào để lưu!", "warning");
            return;
        }
        const kifuData = generateKifu();
        const blob = new Blob([kifuData], { type: 'text/plain;charset=utf-8' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `Xiangqi_Game_${new Date().getTime()}.txt`; 
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
        updateRefereeMessage("Đã lưu ván cờ!", "info");
        saveCurrentGameToLocalStorage(); 
    });

    function saveCurrentGameToLocalStorage() {
        if (gameState.moveHistory.length === 0 && gameState.boardHistory.length <=1 ) return; 
        const kifu = generateKifu(); 
        const gameSummary = {
            id: new Date().getTime(),
            date: new Date().toLocaleDateString(),
            firstMoves: gameState.moveHistory.slice(0, 5).map(m => m.notation).join('; ') || "Ván cờ mới",
            kifu: kifu,
            boardHistory: JSON.stringify(gameState.boardHistory), 
            moveHistoryForReview: JSON.stringify(gameState.moveHistory) 
        };

        let playedGames = JSON.parse(localStorage.getItem('playedXiangqiGames')) || [];
        playedGames.unshift(gameSummary); 
        if (playedGames.length > 10) playedGames.pop(); 
        localStorage.setItem('playedXiangqiGames', JSON.stringify(playedGames));
        loadPlayedGamesList();
    }

    function loadPlayedGamesList() {
        const listEl = document.getElementById('playedGamesList');
        if (!listEl) return;
        listEl.innerHTML = "";
        const playedGames = JSON.parse(localStorage.getItem('playedXiangqiGames')) || [];
        if (playedGames.length === 0) {
            listEl.textContent = "Chưa có ván nào được lưu.";
            return;
        }
        playedGames.forEach(game => {
            const itemEl = document.createElement('div');
            itemEl.classList.add('game-history-item', 'p-2', 'border-b', 'cursor-pointer', 'hover:bg-gray-100');
            itemEl.textContent = `${game.date} - ${game.firstMoves || 'Ván cờ'}`;
            itemEl.title = "Nhấn để xem lại";
            itemEl.addEventListener('click', () => {
                gameState.initialize(); 
                try { 
                    gameState.boardHistory = JSON.parse(game.boardHistory);
                    gameState.moveHistory = JSON.parse(game.moveHistoryForReview);
                } catch (e) {
                    console.error("Lỗi khi parse lịch sử game đã lưu:", e);
                    updateRefereeMessage("Lỗi khi tải lại ván cờ đã lưu.", "error");
                    return;
                }
                updateMoveHistoryDisplay(gameState.moveHistory);
                startReviewMode(); 
                gameState.currentReviewIndex = 0; 
                displayBoardForReview(); 
                updateStatusMessage(`Đang xem lại ván cờ ngày ${game.date}`, false);
            });
            listEl.appendChild(itemEl);
        });
    }
    
    if(clearHistoryButton) clearHistoryButton.addEventListener('click', () => {
        if (confirm("Bạn có chắc muốn xóa toàn bộ lịch sử các ván đã đấu?")) {
            localStorage.removeItem('playedXiangqiGames');
            loadPlayedGamesList();
            updateRefereeMessage("Đã xóa lịch sử ván đấu.", "info");
        }
    });

    // Event Listeners
    if (newGameButton) newGameButton.addEventListener('click', initializeNewGame);
    if (pauseResumeButton) {
        pauseResumeButton.addEventListener('click', () => {
            if (gameState.isGameOver && !gameState.isReviewMode) return; 
            gameState.togglePause(); 
            updatePlayerTimersDisplayUI(gameState.redTimeSpent, gameState.blackTimeSpent, gameState.currentPlayer, gameState.gamePaused, gameState.isGameOver);
            if (!gameState.gamePaused && !gameState.isGameOver &&
                ((gameState.gameMode.startsWith('pva') && gameState.currentPlayer !== gameState.playerColor) || gameState.gameMode === 'ava') 
                ) {
                setTimeout(triggerAiMove,100);
            }
        });
    }
    if (gameModeSelector) gameModeSelector.addEventListener('change', initializeNewGame); 
    if (timeControlSelector) {
        timeControlSelector.addEventListener('change', () => {
            initializeNewGame(); 
        });
    }

    // Music Panel Event Listeners
    if (toggleMusicBtnPanel) { 
        toggleMusicBtnPanel.disabled = !youtubeApiReady; // Chỉ bật khi API sẵn sàng
        toggleMusicBtnPanel.addEventListener('click', toggleMusicPanel);
    }
    if (volumeSliderPanel) {
        volumeSliderPanel.addEventListener('input', (e) => {
            setVolumeFromPanel(parseInt(e.target.value, 10));
        });
    }
    if (changeMusicPanelBtn && youtubeIdInputPanel) {
        changeMusicPanelBtn.addEventListener('click', changeMusicFromPanel);
    }
    
    if (reviewGameModalButton) {
        reviewGameModalButton.addEventListener('click', () => {
            hideGameOverModal();
            startReviewMode();
        });
    }
    if (newGameModalButton) {
        newGameModalButton.addEventListener('click', () => {
            hideGameOverModal();
            initializeNewGame(); 
        });
    }

    populateTimeControlSelect(); 
    initializeNewGame(); 
});
