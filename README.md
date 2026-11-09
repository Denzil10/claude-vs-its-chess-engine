# Raw Claude vs the chess engine Claude wrote

Claude Opus 5.5 with no tools (`claude -p --tools ""`) plays White against [the engine Claude Code built](https://github.com/Denzil10/claude-chess-engine) (1 s/move). Game 1: Claude gets only the move list. Game 2: Claude also gets the board (FEN plus a text diagram). Three illegal tries on one move forfeit the game.

- Page with replays and every comment Claude made: https://denzil10.github.io/claude-vs-its-chess-engine/
- `match.py`: the referee (`python match.py <name> blind|board <engine dir> <out dir>`, needs `python-chess`, `node`, and the `claude` CLI)
- `games/`: PGN and the full prompt/reply log of each game

Results (2026-11-10): blind, checkmated on move 53 with 5 illegal tries; with the board, checkmated on move 33 with 1 illegal try. One game each.

Video: https://youtu.be/9tj0ONSNWME
