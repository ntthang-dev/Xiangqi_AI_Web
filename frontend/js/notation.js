// File: frontend/js/notation.js
// Xử lý việc tạo và hiển thị kỳ phổ.

function getXiangqiColumnNotation(col, pieceColor) {
    if (pieceColor === 'red') {
        return 9 - col;
    } else {
        return col + 1;
    }
}

function getPieceNotationName(pieceKey, fromR, fromC, currentBoard) {
    const pieceInfo = getPieceInfo(pieceKey); // from rules_ui.js or config.js
    if (!pieceInfo) return '?';
    let name = pieceInfo.char;

    if (['R', 'H', 'C', 'P', 'r', 'h', 'c', 'p'].includes(pieceKey.toUpperCase())) {
        let sameColPiecesRows = [];
        for (let r_idx = 0; r_idx < 10; r_idx++) {
            if (currentBoard[r_idx][fromC] === pieceKey) {
                sameColPiecesRows.push(r_idx);
            }
        }

        if (sameColPiecesRows.length > 1) {
            if (pieceInfo.color === 'red') {
                sameColPiecesRows.sort((a, b) => a - b); // Red: smaller index is "trước"
                const pieceIndexInColumn = sameColPiecesRows.indexOf(fromR);
                if (pieceIndexInColumn === 0) name = `${pieceInfo.char}trước`;
                else if (pieceIndexInColumn === sameColPiecesRows.length - 1) name = `${pieceInfo.char}sau`;
                // Add logic for middle pieces if more than 2, e.g., "giữa"
            } else { // Black
                sameColPiecesRows.sort((a, b) => b - a); // Black: larger index is "trước" (closer to Red)
                const pieceIndexInColumn = sameColPiecesRows.indexOf(fromR);
                if (pieceIndexInColumn === 0) name = `${pieceInfo.char}trước`;
                else if (pieceIndexInColumn === sameColPiecesRows.length - 1) name = `${pieceInfo.char}sau`;
            }
        }
    }
    return name;
}


function formatMoveNotation(fromR, fromC, toR, toC, pieceKey, currentBoardState) {
    const pieceInfo = getPieceInfo(pieceKey);
    if (!pieceInfo) return "Lỗi nước đi";

    const pieceName = getPieceNotationName(pieceKey, fromR, fromC, currentBoardState);
    const startColDisplay = getXiangqiColumnNotation(fromC, pieceInfo.color);

    let moveDirection;
    let moveValue;

    if (fromR === toR) {
        moveDirection = "bình";
        moveValue = getXiangqiColumnNotation(toC, pieceInfo.color);
    } else {
        const rowDiff = pieceInfo.color === 'red' ? (fromR - toR) : (toR - fromR);
        moveDirection = rowDiff > 0 ? "tiến" : "thoái";
        if (['Advisor', 'Elephant', 'Horse'].includes(pieceInfo.type) ||
            (pieceInfo.type === 'General' && Math.abs(fromC - toC) > 0)) {
            moveValue = getXiangqiColumnNotation(toC, pieceInfo.color);
        } else {
            moveValue = Math.abs(rowDiff);
        }
    }
    const firstPart = (pieceName.includes("trước") || pieceName.includes("sau")) ? pieceName : `${pieceInfo.char}${startColDisplay}`;
    return `${firstPart} ${moveDirection} ${moveValue}`;
}


function updateMoveHistoryDisplay(currentMoveHistory) {
    const moveHistoryContainer = document.getElementById('moveHistory');
    if (!moveHistoryContainer) return;

    let displayHistory = "";
    for (let i = 0; i < currentMoveHistory.length; i += 2) {
        const turnNumber = Math.floor(i / 2) + 1;
        const redMove = currentMoveHistory[i] ? currentMoveHistory[i].notation : "";
        const blackMove = currentMoveHistory[i + 1] ? currentMoveHistory[i + 1].notation : "";
        displayHistory += `<div class="mb-1"><span class="font-semibold">Hiệp ${turnNumber}:</span> Đỏ: ${redMove}${blackMove ? `, Đen: ${blackMove}` : ''}</div>`;
    }
    moveHistoryContainer.innerHTML = displayHistory || "Lịch sử nước đi...";
    moveHistoryContainer.scrollTop = moveHistoryContainer.scrollHeight;
}
