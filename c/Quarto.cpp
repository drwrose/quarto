#include "Quarto.h"

Quarto::
Quarto() {
  new_game();
}

Quarto::
~Quarto() {
  // Ensure all of the boards get fully deleted before we finish
  // destructing the Quarto instance.
  _board = 0;
  _search_boards.clear();
}

void Quarto::
new_game() {
  _board = 0;
  assert(_search_boards.empty());
  _board = std::make_shared<Board>();

  for (int pi = 0; pi < Player::num_players; ++pi) {
    _players.emplace_back(Player(this, pi));
  }

  // Temp hack?
  _players[0].set_robot(true);
  _players[1].set_robot(true);
  //_players[2].set_robot(true);

  /*
  _board = _board->place_piece(0, Piece("rhsd"));
  _board = _board->place_piece(1, Piece("qftl"));
  _board = _board->place_piece(2, Piece("qfsd"));
  _board = _board->place_piece(3, Piece("rftl"));

  _board = _board->place_piece(4, Piece("qhsl"));
  //_board = _board->place_piece(5, Piece("qftd"));
  _board = _board->place_piece(6, Piece("qhtd"));
  _board = _board->place_piece(7, Piece("rhtd"));

  _board = _board->place_piece(8, Piece("rftd"));
  _board = _board->place_piece(9, Piece("rhsl"));
  //  _board = _board->place_piece(10, Piece("rfsd"));
  _board = _board->place_piece(11, Piece("qhtl"));

  _board = _board->place_piece(12, Piece("qfsl"));
  _board = _board->place_piece(13, Piece("qhsd"));
  _board = _board->place_piece(14, Piece("rhtl"));
  _board = _board->place_piece(15, Piece("rfsl"));
  */
}

Player &Quarto::
get_player(int pi) {
  assert(pi >= 0 && pi < Player::num_players);
  return _players[pi];
}

const Player &Quarto::
get_player(int pi) const {
  assert(pi >= 0 && pi < Player::num_players);
  return _players[pi];
}

// The current place player places the indicated piece.  This updates
// the board and advances the turn.
void Quarto::
place_piece(unsigned int si, const Piece &piece) {
  _board = _board->place_piece(si, piece);
}

// Returns true if the game is over.
bool Quarto::
is_game_over() const {
  return _board->is_game_over();
}

// Returns true if the game was won.
bool Quarto::
is_win() const {
  return _board->is_win();
}

std::shared_ptr<Board> Quarto::
add_or_get_search_board(const std::shared_ptr<Board> &board) {
  // Adds the board to the search_boards set and returns that pointer,
  // if there isn't one like it already there.  If there was already
  // one like it, returns that one instead.
  SearchBoards::iterator sbi = _search_boards.insert(board).first;
  return (*sbi);
}
