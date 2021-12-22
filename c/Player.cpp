#include "Player.h"
#include "Quarto.h"
#include "Board.h"

#include <sstream>

Player::
Player(Quarto *quarto, int player_index) :
  _quarto(quarto),
  _player_index(player_index),
  _have_chosen_piece(false)
{
  // Create a default name.
  std::ostringstream strm;
  strm << "Player " << _player_index + 1;
  _name = strm.str();

  _robot = false;
}

// The AI chooses a piece to give to the next player.  Returns piece.
Piece Player::
robot_choose_piece() {
  if (_have_chosen_piece) {
    // We already chose one previously, return that.
    _have_chosen_piece = false;
    return _chosen_piece;
  }

  // We have to choose one now.
  SearchResult best_result;
  return _quarto->get_board().choose_piece(best_result, _player_index);
}

// The AI chooses a square to place the indicated piece.  Returns si.
unsigned int Player::
robot_choose_square(Piece give_piece) {
  unsigned int chosen_si = 0;
  _quarto->get_board().choose_square_and_piece(chosen_si, _chosen_piece, _player_index, give_piece);
  _have_chosen_piece = true;
  return chosen_si;
}
