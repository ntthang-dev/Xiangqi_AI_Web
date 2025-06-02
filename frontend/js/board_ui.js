// File: frontend/js/board_ui.js
// Xử lý cập nhật giao diện bàn cờ, quân cờ, thông tin game.

function createBoardUI(currentBoardState, squareClickHandler) {
    const boardElement = document.getElementById('board');
    if (!boardElement) return;

    boardElement.innerHTML = `
        <div class="river"><span>楚 河     漢 界</span></div>
        <div class="palace-line red-diag1"></div><div class="palace-line red-diag2"></div>
        <div class="palace-line black-diag1"></div><div class="palace-line black-diag2"></div>
    `; // Reset board giữ lại sông và cung

    for (let r = 0; r < 10; r++) {
        for (let c = 0; c < 9; c++) {
            const square = document.createElement('div');
            square.classList.add('square', 'relative'); // Thêm relative để marker định vị
            square.dataset.r = r;
            square.dataset.c = c;
            square.addEventListener('click', () => squareClickHandler(r, c));

            const pieceKey = currentBoardState[r][c];
            if (pieceKey) {
                const pieceInfo = getPieceInfo(pieceKey); 
                if(pieceInfo){
                    const pieceElement = document.createElement('span');
                    pieceElement.classList.add('piece', pieceInfo.color);
                    pieceElement.textContent = pieceInfo.char;
                    square.appendChild(pieceElement);
                }
            }
            boardElement.appendChild(square);
            addTraditionalMarkersUI(square, r, c); // Vẽ marker cho ô
        }
    }
}

function addTraditionalMarkersUI(squareElement, r, c) {
    // ... (Giữ nguyên logic vẽ marker như trước)
    const isCannonPos = ((r === 2 || r === 7) && (c === 1 || c === 7));
    const isPawnPos = ((r === 3 || r === 6) && (c === 0 || c === 2 || c === 4 || c === 6 || c === 8));

    if (isCannonPos || isPawnPos) {
        const L_marker_positions = [
            { r_offset: -0.4, c_offset: -0.4, horz: true, len: 0.3 }, { r_offset: -0.4, c_offset: -0.4, vert: true, len: 0.3 },
            { r_offset: -0.4, c_offset: 0.4, horz: true, len: -0.3 }, { r_offset: -0.4, c_offset: 0.4, vert: true, len: 0.3 },
            { r_offset: 0.4, c_offset: -0.4, horz: true, len: 0.3 }, { r_offset: 0.4, c_offset: -0.4, vert: true, len: -0.3 },
            { r_offset: 0.4, c_offset: 0.4, horz: true, len: -0.3 }, { r_offset: 0.4, c_offset: 0.4, vert: true, len: -0.3 },
        ];

        L_marker_positions.forEach(data => {
            if (isPawnPos) {
                if (c === 0 && data.c_offset < 0) return; 
                if (c === 8 && data.c_offset > 0) return; 
            }

            const marker = document.createElement('div');
            marker.style.position = 'absolute';
            marker.style.backgroundColor = '#8c5a32'; 
            marker.classList.add('marker-dynamic');


            const squareWidth = squareElement.offsetWidth || (document.getElementById('board').offsetWidth / 9); 
            const squareHeight = squareElement.offsetHeight || (document.getElementById('board').offsetHeight / 10);
            const markerThickness = 2; 
            const markerLength = squareWidth * 0.20; // Giảm kích thước marker một chút

            if (data.horz) { 
                marker.style.height = `${markerThickness}px`;
                marker.style.width = `${markerLength}px`;
                marker.style.top = `calc(50% + ${squareHeight * data.r_offset}px - ${markerThickness/2}px)`;
                if (data.len > 0) { 
                    marker.style.left = `calc(50% + ${squareWidth * data.c_offset}px)`;
                } else { 
                    marker.style.left = `calc(50% + ${squareWidth * data.c_offset}px - ${markerLength}px)`;
                }
            } else { 
                marker.style.width = `${markerThickness}px`;
                marker.style.height = `${markerLength}px`;
                marker.style.left = `calc(50% + ${squareWidth * data.c_offset}px - ${markerThickness/2}px)`;
                if (data.len > 0) { 
                    marker.style.top = `calc(50% + ${squareHeight * data.r_offset}px)`;
                } else { 
                    marker.style.top = `calc(50% + ${squareHeight * data.r_offset}px - ${markerLength}px)`;
                }
            }
            squareElement.appendChild(marker);
        });
    }
}


function highlightLastMoveUI(currentLastMove) {
    // ... (Giữ nguyên)
    const boardElement = document.getElementById('board');
    if (!boardElement) return;
    boardElement.querySelectorAll('.last-move-highlight').forEach(el => el.classList.remove('last-move-highlight'));
    if (currentLastMove && currentLastMove.from && currentLastMove.to) {
        const fromSquare = boardElement.querySelector(`.square[data-r="${currentLastMove.from.r}"][data-c="${currentLastMove.from.c}"]`);
        const toSquare = boardElement.querySelector(`.square[data-r="${currentLastMove.to.r}"][data-c="${currentLastMove.to.c}"]`);
        if (fromSquare) fromSquare.classList.add('last-move-highlight');
        if (toSquare) toSquare.classList.add('last-move-highlight');
    }
}

function highlightCheckUI(playerInCheck, currentBoardState) {
    // ... (Giữ nguyên)
    const boardElement = document.getElementById('board');
    if (!boardElement) return;
    boardElement.querySelectorAll('.check-highlight').forEach(el => el.classList.remove('check-highlight'));
    const kingPos = findKing(playerInCheck, currentBoardState); 
    if (kingPos && isKingInCheckClient(playerInCheck, currentBoardState)) { 
        const kingSquare = boardElement.querySelector(`.square[data-r="${kingPos.r}"][data-c="${kingPos.c}"]`);
        if (kingSquare) kingSquare.classList.add('check-highlight');
    }
}

function formatTime(totalSeconds) {
    // ... (Giữ nguyên)
    const minutes = Math.floor(totalSeconds / 60).toString().padStart(2, '0');
    const seconds = Math.floor(totalSeconds % 60).toString().padStart(2, '0'); // Ensure seconds is integer
    return `${minutes}:${seconds}`;
}

function updateMainGameTimerUI(currentMainSecondsElapsed) {
    // ... (Giữ nguyên)
    const gameTimerElement = document.getElementById('gameTimer');
    if (gameTimerElement) {
      gameTimerElement.textContent = `Tổng thời gian: ${formatTime(currentMainSecondsElapsed)}`;
    }
}

function updatePlayerTimersDisplayUI(currentRedTime, currentBlackTime, currentPlayerForHighlight, isGamePaused, isGameReallyOver) {
    // ... (Giữ nguyên)
    const redPlayerTimerElement = document.getElementById('redPlayerTimer');
    const blackPlayerTimerElement = document.getElementById('blackPlayerTimer');
    const redPlayerInfoElement = document.getElementById('redPlayerInfo');
    const blackPlayerInfoElement = document.getElementById('blackPlayerInfo');

    if (redPlayerTimerElement) redPlayerTimerElement.textContent = formatTime(currentRedTime);
    if (blackPlayerTimerElement) blackPlayerTimerElement.textContent = formatTime(currentBlackTime);

    if (redPlayerInfoElement) redPlayerInfoElement.classList.remove('active-player-timer');
    if (blackPlayerInfoElement) blackPlayerInfoElement.classList.remove('active-player-timer');

    if (!isGamePaused && !isGameReallyOver) {
        if (currentPlayerForHighlight === 'red' && redPlayerInfoElement) {
            redPlayerInfoElement.classList.add('active-player-timer');
        } else if (currentPlayerForHighlight === 'black' && blackPlayerInfoElement) {
            blackPlayerInfoElement.classList.add('active-player-timer');
        }
    }
}

function updatePlayerScoresUI(currentBoardState, currentMoveCount) {
    // ... (Giữ nguyên, hoặc cải thiện sau nếu cần)
    const redPlayerScoreElement = document.getElementById('redPlayerScore');
    const blackPlayerScoreElement = document.getElementById('blackPlayerScore');
    const currentRedScore = 0; 
    const currentBlackScore = 0;
    if (redPlayerScoreElement) redPlayerScoreElement.textContent = currentRedScore.toFixed(1);
    if (blackPlayerScoreElement) blackPlayerScoreElement.textContent = currentBlackScore.toFixed(1);
}


function updateGamePhaseDisplayUI(phase) {
    // ... (Giữ nguyên)
    const gamePhaseElement = document.getElementById('gamePhase');
    if (!gamePhaseElement) return;
    let phaseText = "Không xác định";
    if (phase === 'opening') phaseText = "Khai cuộc";
    else if (phase === 'midgame') phaseText = "Trung cuộc";
    else if (phase === 'endgame') phaseText = "Tàn cuộc";
    gamePhaseElement.textContent = `Giai đoạn: ${phaseText}`;
}

function clearHighlightsUI() {
    // ... (Giữ nguyên)
    const boardElement = document.getElementById('board');
    if (!boardElement) return;
    boardElement.querySelectorAll('.square').forEach(sq => {
        sq.classList.remove('selected', 'valid-move');
    });
}

function highlightSelectedPieceUI(r, c) {
    // ... (Giữ nguyên)
    const boardElement = document.getElementById('board');
    if (!boardElement) return;
    const selectedSquare = boardElement.querySelector(`.square[data-r="${r}"][data-c="${c}"]`);
    if (selectedSquare) selectedSquare.classList.add('selected');
}

function highlightValidMovesUI(currentValidMoves) {
    // ... (Giữ nguyên)
    const boardElement = document.getElementById('board');
    if (!boardElement) return;
    currentValidMoves.forEach(move => {
        const moveSquare = boardElement.querySelector(`.square[data-r="${move.r}"][data-c="${move.c}"]`);
        if (moveSquare) moveSquare.classList.add('valid-move');
    });
}

function showGameOverModal(message, reason) {
    // ... (Giữ nguyên)
    const modal = document.getElementById('gameOverModal');
    const msgElement = document.getElementById('gameOverMessage');
    const reasonElement = document.getElementById('gameOverReason');
    if (modal && msgElement && reasonElement) {
        msgElement.textContent = message;
        reasonElement.textContent = reason;
        modal.classList.remove('hidden');
    }
}

function hideGameOverModal() {
    // ... (Giữ nguyên)
    const modal = document.getElementById('gameOverModal');
    if (modal) modal.classList.add('hidden');
}

function updateStatusMessage(message, isError = false) {
    const statusEl = document.getElementById('status');
    if (statusEl) {
        statusEl.textContent = message;
        if (isError) {
            statusEl.classList.add('text-red-500', 'font-bold');
        } else {
            statusEl.classList.remove('text-red-500', 'font-bold');
        }
    }
}

function updateAiTimeMessage(message) {
    // ... (Giữ nguyên)
    const aiTimeEl = document.getElementById('aiTime');
    if (aiTimeEl) aiTimeEl.textContent = message;
}

function updateAiDepthLog(message) {
    const aiDepthLogEl = document.getElementById('aiDepthLog');
    if (aiDepthLogEl) aiDepthLogEl.textContent = message;
}

function updateRefereeMessage(message, type = 'info') { // type: 'info', 'warning', 'error'
    const refereeMessageEl = document.getElementById('refereeMessage');
    if (refereeMessageEl) {
        refereeMessageEl.textContent = message || "Thông báo từ trọng tài...";
        refereeMessageEl.classList.remove('text-yellow-700', 'bg-yellow-100', 'border-yellow-300'); // warning
        refereeMessageEl.classList.remove('text-red-700', 'bg-red-100', 'border-red-300');       // error
        refereeMessageEl.classList.remove('text-blue-700', 'bg-blue-100', 'border-blue-300');   // info
        
        if (type === 'warning') {
            refereeMessageEl.classList.add('text-yellow-700', 'bg-yellow-100', 'border-yellow-300');
        } else if (type === 'error') {
            refereeMessageEl.classList.add('text-red-700', 'bg-red-100', 'border-red-300');
        } else { // info
             refereeMessageEl.classList.add('text-blue-700', 'bg-blue-100', 'border-blue-300');
        }
        if (!message) { // Nếu không có message, trả về style mặc định
             refereeMessageEl.classList.remove('text-yellow-700', 'bg-yellow-100', 'border-yellow-300', 'text-red-700', 'bg-red-100', 'border-red-300', 'text-blue-700', 'bg-blue-100', 'border-blue-300');
             refereeMessageEl.classList.add('text-gray-600'); // Màu mặc định
        }
    }
}


function updateTimeControlDisplay(player, playerTCState, scheme) {
    // ... (Giữ nguyên)
    const redInfoEl = document.getElementById('redTimeControlInfo');
    const blackInfoEl = document.getElementById('blackTimeControlInfo');
    let infoEl = null;

    if (player === 'red') infoEl = redInfoEl;
    else if (player === 'black') infoEl = blackInfoEl;

    if (!infoEl) return;

    if (gameState.selectedTimeControlSchemeKey === "none" || !playerTCState || playerTCState.currentPeriodIndex === -1 || !scheme || scheme.periods.length === 0) {
        infoEl.innerHTML = ""; 
        return;
    }
    
    const periodConf = scheme.periods[playerTCState.currentPeriodIndex];
    if (!periodConf) { 
        infoEl.innerHTML = "Lỗi TC";
        return;
    }
    const movesLeft = periodConf.movesRequired - playerTCState.movesMadeInCurrentPeriod;
    const timeFormatted = formatTime(playerTCState.timeRemainingInCurrentPeriodSeconds);

    let displayText = "";
    if (periodConf.movesRequired >= 999) { 
         displayText = `TG còn lại: ${timeFormatted}`;
    } else {
        displayText = `${periodConf.description || `GĐ ${playerTCState.currentPeriodIndex + 1}`}:<br>Còn ${movesLeft} nước / ${timeFormatted}`;
    }
    infoEl.innerHTML = displayText;
}

function populateTimeControlSelect() {
    // ... (Giữ nguyên)
    const selectEl = document.getElementById('timeControlSelect');
    const ruleDisplayEl = document.getElementById('selectedTimeControlRule'); 
    if (!selectEl) return;
    selectEl.innerHTML = ''; 

    for (const key in TIME_CONTROL_SCHEMES) {
        const option = document.createElement('option');
        option.value = key;
        option.textContent = TIME_CONTROL_SCHEMES[key].name;
        selectEl.appendChild(option);
    }
    
    function displayRule() {
        if (ruleDisplayEl && TIME_CONTROL_SCHEMES[selectEl.value]) {
            ruleDisplayEl.textContent = TIME_CONTROL_SCHEMES[selectEl.value].description || "";
        } else if (ruleDisplayEl) {
            ruleDisplayEl.textContent = "";
        }
    }

    if (gameState && gameState.selectedTimeControlSchemeKey) {
        selectEl.value = gameState.selectedTimeControlSchemeKey;
    } else {
        selectEl.value = "none"; 
    }
    displayRule(); 

    selectEl.addEventListener('change', displayRule); 
}

function updateReviewControlsUI() {
    const goToStartBtn = document.getElementById('goToStartBtn');
    const prevMoveBtn = document.getElementById('prevMoveBtn');
    const nextMoveBtn = document.getElementById('nextMoveBtn');
    const goToEndBtn = document.getElementById('goToEndBtn');

    if (gameState.isReviewMode) {
        goToStartBtn.disabled = gameState.currentReviewIndex <= 0;
        prevMoveBtn.disabled = gameState.currentReviewIndex <= 0;
        nextMoveBtn.disabled = gameState.currentReviewIndex >= gameState.boardHistory.length - 1;
        goToEndBtn.disabled = gameState.currentReviewIndex >= gameState.boardHistory.length - 1;
    } else {
        goToStartBtn.disabled = true;
        prevMoveBtn.disabled = true;
        nextMoveBtn.disabled = true;
        goToEndBtn.disabled = true;
    }
}
