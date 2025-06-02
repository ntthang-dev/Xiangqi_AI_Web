// File: frontend/js/rules_ui.js
// Chứa các hàm liên quan đến luật chơi cờ tướng,
// chủ yếu dùng cho việc hiển thị gợi ý nước đi trên UI và kiểm tra cơ bản phía client.
// Logic kiểm tra chi tiết và tạo nước đi chính sẽ nằm ở backend.

function getPieceInfo(pieceKey) {
    return PIECE_VALUES_DETAILED[pieceKey] || null;
}

function getOpponentColor(color) {
    return color === 'red' ? 'black' : 'red';
}

const isInBoard = (r, c) => r >= 0 && r < 10 && c >= 0 && c < 9;

const isInPalace = (r, c, color) => {
    if (c < 3 || c > 5) return false;
    if (color === 'red') return r >= 7 && r <= 9;
    if (color === 'black') return r >= 0 && r <= 2;
    return false;
};

function findKing(color, currentBoard) {
    const kingKey = color === 'red' ? 'K' : 'k';
    for (let r_idx = 0; r_idx < 10; r_idx++) {
        for (let c_idx = 0; c_idx < 9; c_idx++) {
            if (currentBoard[r_idx][c_idx] === kingKey) return { r: r_idx, c: c_idx };
        }
    }
    return null;
}

function generalsFacingClient(currentBoard) {
    const redKingPos = findKing('red', currentBoard);
    const blackKingPos = findKing('black', currentBoard);
    if (!redKingPos || !blackKingPos) return false;
    if (redKingPos.c !== blackKingPos.c) return false;
    const startR = Math.min(redKingPos.r, blackKingPos.r) + 1;
    const endR = Math.max(redKingPos.r, blackKingPos.r);
    for (let i = startR; i < endR; i++) {
        if (currentBoard[i][redKingPos.c]) return false;
    }
    return true;
}

function getRawMovesForPieceClient(r, c, pieceKey, currentBoard) {
    const piece = getPieceInfo(pieceKey);
    if (!piece) return [];
    let moves = [];
    const color = piece.color;

    switch (piece.type) {
        case 'General':
            [[ -1, 0], [1, 0], [0, -1], [0, 1]].forEach(([dr, dc]) => {
                const nr = r + dr, nc = c + dc;
                if (isInPalace(nr, nc, color)) {
                    const targetPieceKey = currentBoard[nr][nc];
                    if (!targetPieceKey || getPieceInfo(targetPieceKey).color !== color) {
                        moves.push({ r: nr, c: nc });
                    }
                }
            });
            // Flying general (for check detection, actual move is complex)
            const oppKing = findKing(getOpponentColor(color), currentBoard);
            if (oppKing && oppKing.c === c) {
                let clearPath = true;
                for (let i = Math.min(r, oppKing.r) + 1; i < Math.max(r, oppKing.r); i++) {
                    if (currentBoard[i][c]) { clearPath = false; break; }
                }
                if (clearPath) moves.push({ r: oppKing.r, c: oppKing.c }); // Can "target" opponent king
            }
            break;
        case 'Advisor':
            [[-1,-1],[-1,1],[1,-1],[1,1]].forEach(([dr,dc])=>{
                const nr = r+dr, nc = c+dc;
                if(isInPalace(nr,nc,color)) {
                    const targetPieceKey = currentBoard[nr][nc];
                    if (!targetPieceKey || getPieceInfo(targetPieceKey).color !== color) {
                        moves.push({r:nr,c:nc});
                    }
                }
            });
            break;
        case 'Elephant':
            [[-2,-2],[-2,2],[2,-2],[2,2]].forEach(([dr,dc])=>{
                const nr=r+dr, nc=c+dc;
                const br=r+dr/2, bc=c+dc/2;
                const riverCross = (color === 'red' && nr < 5) || (color === 'black' && nr > 4);
                if(isInBoard(nr,nc) && !riverCross && !currentBoard[br][bc]) {
                    const targetPieceKey = currentBoard[nr][nc];
                    if (!targetPieceKey || getPieceInfo(targetPieceKey).color !== color) {
                        moves.push({r:nr,c:nc});
                    }
                }
            });
            break;
        case 'Horse':
            [[-2,-1],[-2,1],[-1,-2],[-1,2],[1,-2],[1,2],[2,-1],[2,1]].forEach(([dr,dc])=>{
                const nr=r+dr, nc=c+dc;
                let br, bc;
                if(Math.abs(dr)===2) {br=r+dr/2; bc=c;}
                else {br=r; bc=c+dc/2;}
                if(isInBoard(nr,nc) && !currentBoard[br][bc]) {
                    const targetPieceKey = currentBoard[nr][nc];
                    if (!targetPieceKey || getPieceInfo(targetPieceKey).color !== color) {
                        moves.push({r:nr,c:nc});
                    }
                }
            });
            break;
        case 'Chariot':
            [[-1,0],[1,0],[0,-1],[0,1]].forEach(([dr,dc])=>{
                for(let i=1;i<10;i++){
                    const nr=r+dr*i, nc=c+dc*i;
                    if(!isInBoard(nr,nc)) break;
                    const targetPieceKey = currentBoard[nr][nc];
                    if(targetPieceKey){
                        if(getPieceInfo(targetPieceKey).color !== color) moves.push({r:nr,c:nc});
                        break;
                    }
                    moves.push({r:nr,c:nc});
                }
            });
            break;
        case 'Cannon':
             [[-1,0],[1,0],[0,-1],[0,1]].forEach(([dr,dc])=>{
                let jumped = false;
                for(let i=1;i<10;i++){
                    const nr=r+dr*i, nc=c+dc*i;
                    if(!isInBoard(nr,nc)) break;
                    const targetPieceKey = currentBoard[nr][nc];
                    if(targetPieceKey){
                        if(!jumped) jumped=true;
                        else {
                            if(getPieceInfo(targetPieceKey).color !== color) moves.push({r:nr,c:nc});
                            break;
                        }
                    } else {
                        if(!jumped) moves.push({r:nr,c:nc});
                    }
                }
            });
            break;
        case 'Pawn':
            const forward = color === 'red' ? -1 : 1;
            if (isInBoard(r + forward, c)) {
                const targetPieceKey = currentBoard[r+forward][c];
                if (!targetPieceKey || getPieceInfo(targetPieceKey).color !== color) {
                    moves.push({ r: r + forward, c: c });
                }
            }
            const crossedRiver = (color === 'red' && r < 5) || (color === 'black' && r > 4);
            if (crossedRiver) {
                if (isInBoard(r, c - 1)) {
                    const targetPieceKey = currentBoard[r][c-1];
                     if (!targetPieceKey || getPieceInfo(targetPieceKey).color !== color) {
                        moves.push({ r: r, c: c - 1 });
                    }
                }
                if (isInBoard(r, c + 1)) {
                    const targetPieceKey = currentBoard[r][c+1];
                    if (!targetPieceKey || getPieceInfo(targetPieceKey).color !== color) {
                        moves.push({ r: r, c: c + 1 });
                    }
                }
            }
            break;
    }
    return moves;
}

function isSquareAttackedClient(r_target, c_target, attackerColor, currentBoard) {
    for (let r_attacker = 0; r_attacker < 10; r_attacker++) {
        for (let c_attacker = 0; c_attacker < 9; c_attacker++) {
            const pieceKey = currentBoard[r_attacker][c_attacker];
            if (pieceKey && getPieceInfo(pieceKey).color === attackerColor) {
                if (getPieceInfo(pieceKey).type === 'General') {
                     if (c_attacker === c_target) {
                        let clearPath = true;
                        for (let i = Math.min(r_attacker, r_target) + 1; i < Math.max(r_attacker, r_target); i++) {
                            if (currentBoard[i][c_target]) { clearPath = false; break; }
                        }
                        if (clearPath) return true;
                    }
                } else {
                   if (getRawMovesForPieceClient(r_attacker, c_attacker, pieceKey, currentBoard).some(m => m.r === r_target && m.c === c_target)) return true;
                }
            }
        }
    }
    return false;
}

function isKingInCheckClient(kingColor, currentBoard) {
    const kingPos = findKing(kingColor, currentBoard);
    if (!kingPos) return true;
    return isSquareAttackedClient(kingPos.r, kingPos.c, getOpponentColor(kingColor), currentBoard);
}

function getValidMovesForPieceClient(r, c, pieceKey, currentBoard) {
    const piece = getPieceInfo(pieceKey);
    if (!piece) return [];
    return getRawMovesForPieceClient(r, c, pieceKey, currentBoard).filter(move => {
        const tempBoard = currentBoard.map(row => [...row]); // Deep copy
        tempBoard[move.r][move.c] = pieceKey;
        tempBoard[r][c] = null;
        if (isKingInCheckClient(piece.color, tempBoard) || generalsFacingClient(tempBoard)) return false;
        return true;
    });
}
