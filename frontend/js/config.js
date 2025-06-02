// File: frontend/js/config.js
// Định nghĩa các hằng số và cấu hình cơ bản của game.

const PIECE_CHAR_MAP = {
    'K': '帥', 'A': '仕', 'E': '相', 'H': '傌', 'R': '俥', 'C': '炮', 'P': '兵',
    'k': '將', 'a': '士', 'e': '象', 'h': '馬', 'r': '車', 'c': '砲', 'p': '卒'
};

const PIECE_VALUES_DETAILED = {
    'K': { type: 'General', color: 'red', char: '帥', value: 10000 },
    'A': { type: 'Advisor', color: 'red', char: '仕', values: { opening: 2, midgame: 2.5, endgame: 2.5 } },
    'E': { type: 'Elephant', color: 'red', char: '相', values: { opening: 2, midgame: 2.5, endgame: 2.5 } },
    'H': { type: 'Horse', color: 'red', char: '傌', values: { opening: 4, midgame: 4.5, endgame: 5 } },
    'R': { type: 'Chariot', color: 'red', char: '俥', values: { opening: 9, midgame: 9, endgame: 10 } },
    'C': { type: 'Cannon', color: 'red', char: '炮', values: { opening: 4.5, midgame: 4.5, endgame: 4 } },
    'P': { type: 'Pawn', color: 'red', char: '兵', values: { opening: 1, midgame_river_crossed: 2, midgame_not_crossed: 1, endgame_advanced: 3.5, endgame_river_crossed: 2.5, endgame_not_crossed: 1.5 } },

    'k': { type: 'General', color: 'black', char: '將', value: 10000 },
    'a': { type: 'Advisor', color: 'black', char: '士', values: { opening: 2, midgame: 2.5, endgame: 2.5 } },
    'e': { type: 'Elephant', color: 'black', char: '象', values: { opening: 2, midgame: 2.5, endgame: 2.5 } },
    'h': { type: 'Horse', color: 'black', char: '馬', values: { opening: 4, midgame: 4.5, endgame: 5 } },
    'r': { type: 'Chariot', color: 'black', char: '車', values: { opening: 9, midgame: 9, endgame: 10 } },
    'c': { type: 'Cannon', color: 'black', char: '砲', values: { opening: 4.5, midgame: 4.5, endgame: 4 } },
    'p': { type: 'Pawn', color: 'black', char: '卒', values: { opening: 1, midgame_river_crossed: 2, midgame_not_crossed: 1, endgame_advanced: 3.5, endgame_river_crossed: 2.5, endgame_not_crossed: 1.5 } }
};


const INITIAL_BOARD_SETUP = [
    ['r', 'h', 'e', 'a', 'k', 'a', 'e', 'h', 'r'],
    [null,null,null,null,null,null,null,null,null],
    [null,'c',null,null,null,null,null,'c',null],
    ['p',null,'p',null,'p',null,'p',null,'p'],
    [null,null,null,null,null,null,null,null,null], 
    [null,null,null,null,null,null,null,null,null], 
    ['P',null,'P',null,'P',null,'P',null,'P'],
    [null,'C',null,null,null,null,null,'C',null],
    [null,null,null,null,null,null,null,null,null],
    ['R', 'H', 'E', 'A', 'K', 'A', 'E', 'H', 'R']
];

// FEN chuẩn cho thế cờ ban đầu, Đỏ đi trước
const INITIAL_BOARD_SETUP_FEN = "rnbakabnr/9/1c5c1/p1p1p1p1p/9/9/P1P1P1P1P/1C5C1/9/RNBAKABNR w - - 0 1";


const API_BASE_URL = 'http://127.0.0.1:5000';

const TIME_CONTROL_SCHEMES = {
    "none": { 
        name: "Không giới hạn", 
        description: "Không giới hạn thời gian cho mỗi nước đi hoặc toàn ván.",
        periods: [] 
    },
    "scheme1_book": { 
        name: "PA1: 40n/30p, 20n/30p, 10n/15p (Lặp lại)",
        description: "GĐ1: 40 nước/30 phút. GĐ2 (sau 40 nước): 20 nước/30 phút. GĐ3 (sau 60 nước): 10 nước/15 phút (lặp lại).",
        periods: [
            { timeLimitSeconds: 30 * 60, movesRequired: 40, movesToEnterPeriod: 0, description: "GĐ1: 40 nước" },
            { timeLimitSeconds: 30 * 60, movesRequired: 20, movesToEnterPeriod: 40, description: "GĐ2: 20 nước" },
            { timeLimitSeconds: 15 * 60, movesRequired: 10, movesToEnterPeriod: 60, description: "GĐ lặp lại: 10 nước" } 
        ],
        repeatingLastPeriod: true 
    },
    "scheme3_book": { 
        name: "PA3: 30n/60p, 20n/30p, 10n/10p (Lặp lại)",
        description: "GĐ1: 30 nước/60 phút. GĐ2 (sau 30 nước): 20 nước/30 phút. GĐ3 (sau 50 nước): 10 nước/10 phút (lặp lại).",
        periods: [
            { timeLimitSeconds: 60 * 60, movesRequired: 30, movesToEnterPeriod: 0, description: "GĐ1: 30 nước" },   
            { timeLimitSeconds: 30 * 60, movesRequired: 20, movesToEnterPeriod: 30, description: "GĐ2: 20 nước" },  
            { timeLimitSeconds: 10 * 60, movesRequired: 10, movesToEnterPeriod: 50, description: "GĐ lặp lại: 10 nước" } 
        ],
        repeatingLastPeriod: true 
    },
    "blitz_5_0": {
        name: "Cờ chớp 5 phút",
        description: "Mỗi bên có tổng cộng 5 phút cho toàn ván.",
        periods: [
            { timeLimitSeconds: 5 * 60, movesRequired: 999, movesToEnterPeriod: 0, description: "Toàn ván" } 
        ],
        repeatingLastPeriod: false
    },
    "rapid_15_0": { 
        name: "Cờ nhanh 15 phút",
        description: "Mỗi bên có tổng cộng 15 phút cho toàn ván.",
         periods: [
            { timeLimitSeconds: 15 * 60, movesRequired: 999, movesToEnterPeriod: 0, description: "Toàn ván" }
        ],
        repeatingLastPeriod: false
    }
};
