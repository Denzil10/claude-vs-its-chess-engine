"""Raw Claude (no tools, no code) plays White against the chess engine Claude wrote in ep05.

Usage: python match.py <game name> <mode> <engine dir> <out dir>
  mode "blind": Claude gets only the move list each turn (it must keep the board in its head).
  mode "board": Claude also gets the position as FEN and a text diagram each turn.
Rules: the engine gets 1 s a move (UCI movetime, same as the ep05 ladder). Claude gets 3 tries per
move; a reply that is not a legal move counts as a try. Three misses on one move = Claude forfeits.
Every call and reply is logged to <out dir>/<game>.jsonl; the PGN to <game>.pgn.
"""
import json, re, subprocess, sys, time, pathlib, datetime
import chess, chess.engine, chess.pgn

game, mode, eng_dir, out = sys.argv[1], sys.argv[2], pathlib.Path(sys.argv[3]).resolve(), pathlib.Path(sys.argv[4])
out.mkdir(parents=True, exist_ok=True)
LOG = open(out / f"{game}.jsonl", "a")
SYSTEM = ("You are playing a game of chess as White against a chess engine. You have no tools and no code. "
          "Reply in exactly two lines: line 1, a short comment on your move under 12 words; line 2, only your move in SAN.")
B, R, G, Y, D, X = "\033[1m", "\033[31m", "\033[32m", "\033[33m", "\033[2m", "\033[0m"


def log(**kw):
    kw["t"] = datetime.datetime.now().isoformat(timespec="seconds"); LOG.write(json.dumps(kw) + "\n"); LOG.flush()


def movelist(board):
    b = chess.Board(); parts = []
    for i, m in enumerate(board.move_stack):
        if i % 2 == 0: parts.append(f"{i // 2 + 1}.")
        parts.append(b.san(m)); b.push(m)
    return " ".join(parts) or "(none, game start)"


def ask(board, misses):
    p = f"Moves so far: {movelist(board)}\n"
    if mode == "board":
        p += f"Position (FEN): {board.fen()}\nBoard (White at the bottom, uppercase = White):\n{board}\n"
    for m in misses:
        p += f"You tried {m}, which is not a legal move in this position.\n"
    p += "Your move."
    t0 = time.time()
    r = subprocess.run(["claude", "-p", "--model", "opus", "--tools", "", "--no-session-persistence",
                        "--setting-sources", "", "--strict-mcp-config", "--output-format", "json",
                        "--system-prompt", SYSTEM, p], capture_output=True, text=True, timeout=600)
    try:
        j = json.loads(r.stdout); text = j.get("result", ""); model = ",".join(j.get("modelUsage", {}).keys())
    except json.JSONDecodeError:
        text, model = r.stdout + r.stderr, "?"
    lines = [l.strip() for l in text.strip().splitlines() if l.strip()]
    comment = lines[0] if len(lines) > 1 else ""
    raw = lines[-1] if lines else ""
    san = re.sub(r"^\d+\.(\.\.)?\s*", "", raw).strip(" .*`")
    log(ply=board.ply(), prompt=p, reply=text, model=model, secs=round(time.time() - t0, 1))
    return comment, san, round(time.time() - t0, 1)


def show(board, last=None):
    rows = str(board.unicode(invert_color=True, empty_square="·")).splitlines()
    print()
    for i, row in enumerate(rows):
        print(f"   {D}{8 - i}{X}  " + " ".join(row.split()))
    print(f"      {D}a b c d e f g h{X}\n")


eng = chess.engine.SimpleEngine.popen_uci(["node", "uci.js"], cwd=str(eng_dir))
board = chess.Board(); illegal_total = 0; result = None
print(f"{B}RAW CLAUDE (no tools) vs THE ENGINE CLAUDE WROTE{X}   mode: {mode}   engine: 1 s/move")
show(board)
while not board.is_game_over(claim_draw=True):
    n = board.fullmove_number
    if board.turn == chess.WHITE:
        misses = []
        while True:
            comment, san, secs = ask(board, misses)
            try:
                mv = board.parse_san(san)
                break
            except ValueError:
                illegal_total += 1; misses.append(san)
                print(f" {R}{B}ILLEGAL{X}  {n}. {san or '(no move)'}   {D}try {len(misses)}/3{X}")
                log(ply=board.ply(), illegal=san, tries=len(misses))
                if len(misses) == 3:
                    result = "0-1"; break
        if result: print(f"\n {R}{B}THREE ILLEGAL MOVES. CLAUDE FORFEITS.{X}"); break
        print(f" {G}{B}CLAUDE{X}  {n}. {board.san(mv)}   {D}{secs}s{X}   \"{comment}\"")
    else:
        mv = eng.play(board, chess.engine.Limit(time=1.0)).move
        print(f" {Y}{B}ENGINE{X}  {n}... {board.san(mv)}")
    board.push(mv); log(ply=board.ply(), move=mv.uci(), fen=board.fen())
    if board.ply() % 2 == 0 or board.is_game_over(): show(board)
eng.quit()
result = result or board.result(claim_draw=True)
outcome = board.outcome(claim_draw=True)
why = outcome.termination.name if outcome else "FORFEIT (3 illegal moves)"
print(f"\n {B}RESULT {result}{X}  {why}   moves: {board.fullmove_number}   illegal tries: {illegal_total}")
log(result=result, why=why, illegal_total=illegal_total, moves=board.fullmove_number)
pg = chess.pgn.Game.from_board(board)
pg.headers.update({"Event": f"Raw Claude vs its engine ({mode})", "White": "Claude Opus (no tools)",
                   "Black": "Claude's engine (1 s/move)", "Result": result})
(out / f"{game}.pgn").write_text(str(pg) + "\n")
