#ifndef QUARTO_H
#define QUARTO_H

#include "Player.h"
#include "Board.h"
#include "Piece.h"

#include <set>
#include <vector>
#include <random>

class Quarto {
public:
  Quarto();
  ~Quarto();

  void new_game();

  const Board &get_board() const { return *_board; }

  Player &get_player(int pi);
  const Player &get_player(int pi) const;

  Player &get_current_give_player() { return get_player(_board->get_current_give_player_index()); }
  Player &get_current_place_player() { return get_player(_board->get_current_place_player_index()); }

  void place_piece(unsigned int si, const Piece &piece);
  bool is_game_over() const;
  bool is_win() const;
  Player &get_winning_player() { return get_player(_board->get_winning_player_index()); }

  std::shared_ptr<Board> add_or_get_search_board(const std::shared_ptr<Board> &board);

public:
  static std::minstd_rand random_generator;

private:
  int r_choose_square(const Board &board, Piece give_piece);

private:
  std::vector<Player> _players;
  std::shared_ptr<Board> _board;

  typedef std::set<std::shared_ptr<Board> > SearchBoards;
  SearchBoards _search_boards;
};

#endif  // QUARTO_H
