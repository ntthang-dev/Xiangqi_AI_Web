# Xiangqi AI Web 🎮

Welcome to Xiangqi AI Web - A modern web-based Chinese Chess (Xiangqi) game with AI opponent! 🚀

## Installation & Setup 🔧
1. Clone the repository
```bash
git clone git@github.com:ntthang-dev/Xiangqi_AI_Web.git
cd Xiangqi_AI_Web
```

2. Install Python dependencies
```bash
pip install -r requirements.txt
```

3. Start the server
```bash
python backend/app.py 
```

4. Open your web browser and visit http://localhost:5000

## Directory Structure 📂
```
Xiangqi_AI_Web/
├── frontend/          # Web interface files
│   ├── static/       # CSS, JS, images
│   │   ├── css/     # Style files 🎨
│   │   ├── js/      # Game logic 🔄
│   │   └── img/     # Game pieces & board 🖼️
│   └── templates/    # HTML templates 📄
├── backend/          # Game logic
│   ├── engine/      # Core game rules ⚙️
│   │   ├── board.py # Board representation
│   │   └── rules.py # Move validation
│   └── utils/       # Helper functions 🛠️
├── ai/              # AI implementation 🤖
│   ├── ai.py       # Main AI logic
│   ├── mcts.py     # Monte Carlo Tree Search
│   └── evaluation.py # Position evaluation
└── docs/            # Documentation 📚
```

## AI Algorithm Details 🧠

### Core Concepts
The AI combines multiple advanced algorithms to create a strong and versatile opponent:

### Search Algorithms Explained
- 🌳 Alpha-Beta Pruning
    - Intelligent move pruning for efficient search
    - Formula: α = max(α, -NegaMax(position, depth-1, -β, -α))
    
- 🎲 Monte Carlo Tree Search (MCTS)
    - Balances exploration and exploitation
    - Four phases: Selection → Expansion → Simulation → Backpropagation
    - UCT formula: UCB = wins/visits + C * sqrt(ln(total_visits)/visits)
    - Implementation: [ai/mcts.py](ai/mcts.py)

- 🔄 Iterative Deepening
    - Progressive depth search
    - Time management integration
    - Code location: [ai/ai.py](ai/ai.py)

[Previous content remains the same...]

### Implementation Files 📁
- Main AI Logic: [ai/ai.py](ai/ai.py)
- MCTS Implementation: [ai/mcts.py](ai/mcts.py)
- Position Evaluation: [ai/evaluation.py](ai/evaluation.py)
- Game Rules: [backend/engine/rules.py](backend/engine/rules.py)
- Board State: [backend/engine/board.py](backend/engine/board.py)

[Rest of the content remains the same...]

## Game Features 🎮
[Previous content remains the same...]

## Contributing 🤝
Contributions welcome! Please read CONTRIBUTING.md for details.

## License 📄
MIT License - [see LICENSE file](LICENSE)



## Contact 📬
Issues and feature requests: [GitHub Issues](https://github.com/ntthang-dev/Xiangqi_AI_Web/issues)

Happy Gaming! 🎉

⭐️ From @ntthang-dev

HCMC - Vietnam