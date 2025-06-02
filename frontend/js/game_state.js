// File: frontend/js/game_state.js
// Quản lý trạng thái game phía client, bao gồm cả time control và xem lại ván đấu.

const gameState = {
    boardState: [],
    currentPlayer: 'red',
    selectedPiece: null,
    validMoves: [],
    gameMode: 'pvaRed', // pvaRed, pvaBlack, ava
    playerColor: 'red', // Màu của người chơi (nếu có)
    // aiDifficulty: 2, // Đã loại bỏ, AI tự điều chỉnh
    moveHistory: [], // [{ player, notation, fromR, fromC, toR, toC, pieceKey, capturedPieceKey }]
    boardHistory: [], // [{ board: JSON_stringified_board_state, player_moved_to_this_state: 'red'/'black'/null, move_notation: "P2=5" }]
    
    checkHistory: [], // Dùng cho luật cấm chiếu lặp lại phía client (nếu có)
    chaseHistory: [], // Dùng cho luật cấm đuổi lặp lại phía client (nếu có)
    
    lastMove: null, // { from: {r,c}, to: {r,c}, piece: 'P', captured: 'p' }
    gamePaused: false,
    isGameOver: false, // Thêm cờ để biết game đã kết thúc thực sự chưa
    
    mainGameTimerInterval: null,
    mainSecondsElapsed: 0,
    redTimeSpent: 0, 
    blackTimeSpent: 0,
    turnStartTime: 0,
    timeSpentCurrentTurnBeforePause: 0,
    moveCount: 0, // Tổng số nửa nước đi

    // Time Control
    selectedTimeControlSchemeKey: "none", 
    playerTimeControlState: {
        red: { currentPeriodIndex: 0, movesMadeInCurrentPeriod: 0, timeRemainingInCurrentPeriodSeconds: Infinity, totalMovesInScheme: 0 },
        black: { currentPeriodIndex: 0, movesMadeInCurrentPeriod: 0, timeRemainingInCurrentPeriodSeconds: Infinity, totalMovesInScheme: 0 }
    },
    timeControlIntervalId: null,

    // Game Review
    isReviewMode: false,
    currentReviewIndex: 0, // Index trong moveHistory (hoặc boardHistory)

    initialize: function() {
        this.boardState = INITIAL_BOARD_SETUP.map(row => [...row]);
        this.currentPlayer = 'red';
        this.selectedPiece = null;
        this.validMoves = [];
        this.moveHistory = [];
        // boardHistory[0] là trạng thái ban đầu, trước nước đi đầu tiên
        this.boardHistory = [{ 
            board: JSON.stringify(this.boardState), 
            player_moved_to_this_state: null, // Không có ai đi để đến trạng thái ban đầu
            move_notation: "Bắt đầu" 
        }]; 
        
        this.checkHistory = [];
        this.chaseHistory = [];
        this.lastMove = null;
        this.moveCount = 0;
        this.gamePaused = false;
        this.isGameOver = false; // Reset cờ kết thúc game
        
        this.mainSecondsElapsed = 0;
        this.redTimeSpent = 0;
        this.blackTimeSpent = 0;
        this.turnStartTime = 0;
        this.timeSpentCurrentTurnBeforePause = 0;

        if (this.mainGameTimerInterval) clearInterval(this.mainGameTimerInterval);
        this.mainGameTimerInterval = null;
        if (this.timeControlIntervalId) clearInterval(this.timeControlIntervalId);
        this.timeControlIntervalId = null;

        this.isReviewMode = false;
        this.currentReviewIndex = 0;
    },

    initializeTimeControl: function() {
        // ... (Giữ nguyên như trước)
        const scheme = TIME_CONTROL_SCHEMES[this.selectedTimeControlSchemeKey];
        if (!scheme || scheme.periods.length === 0) {
            this.playerTimeControlState.red = { currentPeriodIndex: -1, movesMadeInCurrentPeriod: 0, timeRemainingInCurrentPeriodSeconds: Infinity, totalMovesInScheme: 0 };
            this.playerTimeControlState.black = { currentPeriodIndex: -1, movesMadeInCurrentPeriod: 0, timeRemainingInCurrentPeriodSeconds: Infinity, totalMovesInScheme: 0 };
        } else {
            const firstPeriod = scheme.periods[0];
            this.playerTimeControlState.red = { 
                currentPeriodIndex: 0, 
                movesMadeInCurrentPeriod: 0, 
                timeRemainingInCurrentPeriodSeconds: firstPeriod.timeLimitSeconds,
                totalMovesInScheme: 0 
            };
            this.playerTimeControlState.black = { 
                currentPeriodIndex: 0, 
                movesMadeInCurrentPeriod: 0, 
                timeRemainingInCurrentPeriodSeconds: firstPeriod.timeLimitSeconds,
                totalMovesInScheme: 0
            };
        }
    },

    setGameMode: function(mode) {
        this.gameMode = mode;
        if (mode === 'pvaRed') this.playerColor = 'red';
        else if (mode === 'pvaBlack') this.playerColor = 'black';
        else this.playerColor = null; 
    },
    // setAiDifficulty đã bị loại bỏ
    selectPiece: function(r, c, pieceKey, moves) {
        this.selectedPiece = { r, c, pieceKey };
        this.validMoves = moves;
    },
    clearSelection: function() {
        this.selectedPiece = null;
        this.validMoves = [];
    },
    addMoveToHistory: function(fromR, fromC, toR, toC, pieceKey, boardBeforeMove, capturedPieceKey) {
        const notation = formatMoveNotation(fromR, fromC, toR, toC, pieceKey, boardBeforeMove); 
        this.moveHistory.push({ 
            player: getPieceInfo(pieceKey).color, 
            notation: notation,
            fromR: fromR, fromC: fromC, toR: toR, toC: toC,
            pieceKey: pieceKey,
            capturedPieceKey: capturedPieceKey // Lưu quân bị ăn
        });
    },
    recordBoardHistory: function(playerWhoMadeMove, moveNotation) {
        // playerWhoMadeMove là người vừa thực hiện nước đi DẪN ĐẾN trạng thái boardState hiện tại
        this.boardHistory.push({
            board: JSON.stringify(this.boardState), // Trạng thái SAU KHI nước đi được thực hiện
            player_moved_to_this_state: playerWhoMadeMove,
            move_notation: moveNotation // Kỳ phổ của nước đi đó
        });
    },
    recordCheckEvent: function(checkingPlayer, pieceKey, r, c, checkedKingPos) {
        // ... (Giữ nguyên)
        this.checkHistory.push({
            boardStateStr: JSON.stringify(this.boardState),
            checkingPlayer: checkingPlayer,
            checkingPieceInfo: { key: pieceKey, r: r, c: c },
            checkedKingPosStr: JSON.stringify(checkedKingPos)
        });
        if (this.checkHistory.length > 12) this.checkHistory.shift();
    },
    recordChaseEvent: function(chasingPlayer, chaserKey, targetKey) {
        // ... (Giữ nguyên)
         this.chaseHistory.push({
            chasingPlayer: chasingPlayer,
            chaserKey: chaserKey, 
            targetKey: targetKey, 
            boardStateStr: JSON.stringify(this.boardState)
        });
        if (this.chaseHistory.length > 12) this.chaseHistory.shift();
    },
    startMainTimer: function() {
        // ... (Giữ nguyên)
        if (this.mainGameTimerInterval) clearInterval(this.mainGameTimerInterval);
        updateMainGameTimerUI(this.mainSecondsElapsed); 
        this.mainGameTimerInterval = setInterval(() => {
            if (!this.gamePaused && !this.isGameOver) { // Chỉ chạy timer nếu game chưa kết thúc
                this.mainSecondsElapsed++;
                updateMainGameTimerUI(this.mainSecondsElapsed);
            }
        }, 1000);
    },
    stopPlayerTimer: function() { 
        // ... (Giữ nguyên)
        if (this.turnStartTime && !this.gamePaused && !this.isGameOver) {
            const timeTaken = (performance.now() - this.turnStartTime) / 1000;
            if (this.currentPlayer === 'red') this.redTimeSpent += timeTaken;
            else this.blackTimeSpent += timeTaken;
        }
    }, 
    startPlayerTimer: function() { 
        // ... (Giữ nguyên)
        if (!this.gamePaused && !this.isGameOver) {
            this.turnStartTime = performance.now();
            this.timeSpentCurrentTurnBeforePause = 0; 
        }
    },
    togglePause: function() {
        // ... (Giữ nguyên, nhưng có thể thêm kiểm tra isGameOver)
        if (this.isGameOver) return; // Không cho phép pause/resume nếu game đã kết thúc

        this.gamePaused = !this.gamePaused;
        const pauseButton = document.getElementById('pauseResumeBtn');
        const statusDisplay = document.getElementById('status');

        if (this.gamePaused) {
            if(this.turnStartTime) this.timeSpentCurrentTurnBeforePause = (performance.now() - this.turnStartTime) / 1000;
            if (pauseButton) {
                pauseButton.textContent = "Tiếp Tục";
                pauseButton.classList.replace('bg-orange-500', 'bg-teal-500');
                pauseButton.classList.replace('hover:bg-orange-600', 'hover:bg-teal-600');
            }
            if (statusDisplay) statusDisplay.textContent = "Đã tạm dừng";
        } else {
            if(this.turnStartTime) this.turnStartTime = performance.now() - (this.timeSpentCurrentTurnBeforePause * 1000);
            if (pauseButton) {
                pauseButton.textContent = "Tạm Dừng";
                pauseButton.classList.replace('bg-teal-500', 'bg-orange-500');
                pauseButton.classList.replace('hover:bg-teal-600', 'hover:bg-orange-600');
            }
            if (statusDisplay) statusDisplay.textContent = `Đến lượt ${this.currentPlayer === 'red' ? 'Đỏ' : 'Đen'}`;
        }
    },
    getGamePhase: function() { 
        // ... (Giữ nguyên)
        const totalPieces = this.boardState.flat().filter(p => p !== null).length;
        if (this.moveCount < 20 && totalPieces > 22) return 'opening';
        if (totalPieces <= 16 || this.moveCount > 60) return 'endgame'; 
        return 'midgame';
    },

    startPeriodCountdownTimer: function() {
        // ... (Giữ nguyên, nhưng thêm kiểm tra isGameOver)
        if (this.timeControlIntervalId) clearInterval(this.timeControlIntervalId);
        if (this.selectedTimeControlSchemeKey === "none" || this.isGameOver) {
            updateTimeControlDisplay('red', this.playerTimeControlState.red, null); 
            updateTimeControlDisplay('black', this.playerTimeControlState.black, null);
            return;
        }
        // ... (phần còn lại của hàm giữ nguyên)
        this.timeControlIntervalId = setInterval(() => {
            if (this.gamePaused || this.isGameOver) { // Thêm isGameOver
                return;
            }

            const playerState = this.playerTimeControlState[this.currentPlayer];
            const scheme = TIME_CONTROL_SCHEMES[this.selectedTimeControlSchemeKey];

            if (playerState.currentPeriodIndex === -1 || !scheme || scheme.periods.length === 0) return;

            if (playerState.timeRemainingInCurrentPeriodSeconds > 0) {
                 playerState.timeRemainingInCurrentPeriodSeconds--;
            }
           
            updateTimeControlDisplay(this.currentPlayer, playerState, scheme);

            if (playerState.timeRemainingInCurrentPeriodSeconds <= 0) {
                const currentPeriodConfig = scheme.periods[playerState.currentPeriodIndex];
                if (playerState.movesMadeInCurrentPeriod < currentPeriodConfig.movesRequired) {
                    clearInterval(this.timeControlIntervalId);
                    const winner = this.currentPlayer === 'red' ? 'Đen' : 'Đỏ';
                    const loser = this.currentPlayer === 'red' ? 'Đỏ' : 'Đen';
                    console.log(`${loser} thua do hết giờ trong giai đoạn!`);
                    handleGameOverUI({ message: `${winner} thắng!`, reason: `${loser} thua do hết giờ.` });
                } else {
                    this.advanceOrResetTimePeriod(this.currentPlayer);
                }
            }
        }, 1000);
    },

    advanceOrResetTimePeriod: function(player) {
        // ... (Giữ nguyên)
        const scheme = TIME_CONTROL_SCHEMES[this.selectedTimeControlSchemeKey];
        if (!scheme || scheme.periods.length === 0) return;

        let playerState = this.playerTimeControlState[player];
        if (playerState.currentPeriodIndex === -1) return; 

        playerState.totalMovesInScheme = Math.floor(this.moveCount / 2); 
        playerState.movesMadeInCurrentPeriod = 0; 

        let determinedNextPeriodIndex = 0;
        for (let i = scheme.periods.length - 1; i >= 0; i--) {
            if (playerState.totalMovesInScheme >= scheme.periods[i].movesToEnterPeriod) {
                determinedNextPeriodIndex = i;
                break;
            }
        }
        
        if (scheme.repeatingLastPeriod && determinedNextPeriodIndex === scheme.periods.length - 1 && playerState.currentPeriodIndex === determinedNextPeriodIndex) {
            // Nếu đang ở giai đoạn cuối lặp lại và vẫn ở đó, chỉ reset thời gian
             playerState.currentPeriodIndex = determinedNextPeriodIndex;
        } else if (determinedNextPeriodIndex < scheme.periods.length) {
            playerState.currentPeriodIndex = determinedNextPeriodIndex;
        } else {
            playerState.currentPeriodIndex = -1; 
            playerState.timeRemainingInCurrentPeriodSeconds = Infinity;
            updateTimeControlDisplay(player, playerState, scheme);
            return;
        }
       
        const newPeriodConfig = scheme.periods[playerState.currentPeriodIndex];
        playerState.timeRemainingInCurrentPeriodSeconds = newPeriodConfig.timeLimitSeconds;
        updateTimeControlDisplay(player, playerState, scheme);
    },

    updatePlayerTimeStateAfterMove: function(player) {
        // ... (Giữ nguyên)
        if (this.selectedTimeControlSchemeKey === "none") return;

        let playerState = this.playerTimeControlState[player];
        const scheme = TIME_CONTROL_SCHEMES[this.selectedTimeControlSchemeKey];
        if (!scheme || playerState.currentPeriodIndex === -1 || scheme.periods.length === 0) return;

        playerState.movesMadeInCurrentPeriod++;
        const currentPeriodConfig = scheme.periods[playerState.currentPeriodIndex];

        if (playerState.movesMadeInCurrentPeriod >= currentPeriodConfig.movesRequired && currentPeriodConfig.movesRequired < 999) {
            this.advanceOrResetTimePeriod(player);
        } else {
            updateTimeControlDisplay(player, playerState, scheme);
        }
    }
};

// Các hàm isGameOverClient, getAllValidMovesClient, checkThreefoldRepetitionClient, checkPerpetualActionClient
// nên được chuyển sang main.js hoặc một file tiện ích client-side riêng,
// vì chúng phụ thuộc vào gameState và các hàm UI khác.
// Tạm thời để đây để dễ tham chiếu, nhưng sẽ di chuyển sau.

function isGameOverClientSide() { // Đổi tên để tránh trùng với biến gameState.isGameOver
    if (gameState.isReviewMode) return false; // Không kiểm tra game over khi đang xem lại

    if (!findKing('red', gameState.boardState)) {
        return { winner: 'black', reason: 'checkmate_red_king_missing', message: 'Đen thắng! (Tướng Đỏ bị bắt)' };
    }
    if (!findKing('black', gameState.boardState)) {
        return { winner: 'red', reason: 'checkmate_black_king_missing', message: 'Đỏ thắng! (Tướng Đen bị bắt)' };
    }

    // playerWhoJustMoved là người vừa đi nước TRƯỚC KHI đến lượt gameState.currentPlayer
    const playerWhoMightBeCheckmated = gameState.currentPlayer;
    const playerWhoMightWin = getOpponentColor(playerWhoMightBeCheckmated);

    if (isKingInCheckClient(playerWhoMightBeCheckmated, gameState.boardState)) {
        const allPlayerMoves = getAllValidMovesClient(playerWhoMightBeCheckmated, gameState.boardState);
        if (allPlayerMoves.length === 0) {
            return { winner: playerWhoMightWin, reason: 'checkmate', message: `${playerWhoMightWin === 'red' ? 'Đỏ' : 'Đen'} thắng do chiếu bí!` };
        }
    } else { // Không bị chiếu
        const allPlayerMoves = getAllValidMovesClient(playerWhoMightBeCheckmated, gameState.boardState);
        if (allPlayerMoves.length === 0) {
            return { winner: 'draw', reason: 'stalemate', message: 'Hòa cờ do hết nước đi!' };
        }
    }
    
    // Kiểm tra lặp lại 3 lần (client-side)
    if (checkThreefoldRepetitionClient()) {
        return { winner: 'draw', reason: 'draw_repetition', message: 'Hòa cờ do lặp lại 3 lần!' };
    }

    // TODO: Kiểm tra các luật cấm lặp của trọng tài phía client (nếu cần thiết và có đủ history)
    // Ví dụ: checkPerpetualActionClient(gameState.checkHistory, 'check', playerWhoJustMoved)
    // Điều này phức tạp hơn vì cần xác định đúng `playerWhoJustMoved` và loại hành động.
    // Tạm thời dựa vào backend cho các luật phức tạp này.

    return false; // Game chưa kết thúc
}

function getAllValidMovesClient(color, currentBoard) { 
    // ... (Giữ nguyên)
    let allMoves = [];
    for (let r = 0; r < 10; r++) {
        for (let c = 0; c < 9; c++) {
            const pieceKey = currentBoard[r][c];
            if (pieceKey && getPieceInfo(pieceKey) && getPieceInfo(pieceKey).color === color) {
                getValidMovesForPieceClient(r, c, pieceKey, currentBoard)
                    .forEach(move => allMoves.push({ fromR: r, fromC: c, toR: move.r, toC: move.c, pieceKey }));
            }
        }
    }
    return allMoves;
}
function checkThreefoldRepetitionClient() { 
    // ... (Giữ nguyên)
    if (gameState.boardHistory.length < 6) return false; 
    const currentStateBoardStr = gameState.boardHistory[gameState.boardHistory.length - 1].board;
    const playerToMoveNow = gameState.currentPlayer;
    let count = 0;
    for (let i = 0; i < gameState.boardHistory.length; i++) {
        const pastStateEntry = gameState.boardHistory[i];
        // player_moved_to_this_state là người đã đi để tạo ra thế cờ đó.
        // Vậy, người sẽ đi TIẾP THEO từ thế cờ đó là đối thủ của player_moved_to_this_state
        let playerToMoveInPastState;
        if (pastStateEntry.player_moved_to_this_state === null) { // Trạng thái ban đầu
            playerToMoveInPastState = 'red';
        } else {
            playerToMoveInPastState = getOpponentColor(pastStateEntry.player_moved_to_this_state);
        }

        if (pastStateEntry.board === currentStateBoardStr && playerToMoveInPastState === playerToMoveNow) {
            count++;
        }
    }
    return count >= 3;
}
// function checkPerpetualActionClient(history, actionType, playerWhoJustMoved) { 
//     // ... (Logic này có thể cần xem xét lại cách dùng hoặc dựa vào backend)
// }


// function checkPerpetualActionClient(history, actionType, playerWhoJustMoved) { 
//     if (history.length < 3) return false;
//     const relevantActionsByPlayer = history.filter(act =>
//         (actionType === 'check' && act.checkingPlayer === playerWhoJustMoved) ||
//         (actionType === 'chase' && act.chasingPlayer === playerWhoJustMoved)
//     );
//     if (relevantActionsByPlayer.length < 3) return false;
//     const lastAction = relevantActionsByPlayer[relevantActionsByPlayer.length - 1];
//     let occurrences = 0;
//     for (const pastAction of relevantActionsByPlayer) {
//         if (actionType === 'check' && pastAction.boardStateStr === lastAction.boardStateStr && pastAction.checkedKingPosStr === lastAction.checkedKingPosStr) {
//             occurrences++;
//         } else if (actionType === 'chase' && pastAction.boardStateStr === lastAction.boardStateStr && pastAction.chaserKey === lastAction.chaserKey && pastAction.targetKey === lastAction.targetKey) {
//             occurrences++;
//         }
//     }
//     return occurrences >= 3;
// }
