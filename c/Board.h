#ifndef BOARD_H
#define BOARD_H

#include "Piece.h"
#include "SearchResult.h"
#include "SearchAccumulator.h"

#include <stdint.h>
#include <assert.h>
#include <iostream>
#include <vector>
#include <memory>

class Board {
public:
  static constexpr unsigned int num_rows = 4;
  static constexpr unsigned int num_cols = 4;
  static constexpr unsigned int num_squares = num_rows * num_cols;

  typedef unsigned int BoardMask;

  Board();
  Board(const Board &copy, unsigned int si, Piece piece);
  ~Board();

  void set_advanced(bool advanced);

  static unsigned int get_si(unsigned int ri, unsigned int ci) {
    assert(ri < num_rows && ci < num_cols);
    return ri * num_rows + ci;
  }
  static unsigned int get_ri(unsigned int si) {
    assert(si < num_squares);
    return si / num_rows;
  }
  static unsigned int get_ci(unsigned int si) {
    assert(si < num_squares);
    return si % num_rows;
  }

  static BoardMask get_mask(unsigned int ri, unsigned int ci) {
    return get_mask(get_si(ri, ci));
  }
  bool is_empty(unsigned int ri, unsigned int ci) const {
    return is_empty(get_si(ri, ci));
  }
  Piece get_piece(unsigned int ri, unsigned int ci) const {
    return get_piece(get_si(ri, ci));
  }
  std::shared_ptr<Board> place_piece(unsigned int ri, unsigned int ci, Piece piece) const {
    return place_piece(get_si(ri, ci), piece);
  }

  static BoardMask get_mask(unsigned int si) {
    assert(si < num_squares);
    return ((BoardMask)1 << si);
  }
  bool is_empty(unsigned int si) const;
  Piece get_piece(unsigned int si) const;
  std::shared_ptr<Board> place_piece(unsigned int si, Piece piece) const;

  bool is_unused(Piece piece) const;

  int get_current_give_player_index() const;
  int get_current_place_player_index() const;
  int get_winning_player_index() const;

  bool is_win() const { return _win != 0; }
  BoardMask get_win() const { return _win; }
  int count_near_wins() const;

  bool is_game_over() const;
  BoardMask get_occupied() const { return _occupied; }
  int get_num_used_pieces() const { return _num_used_pieces; }

  Piece choose_piece(SearchResult &best_result, int me_player_index, bool show_log = false) const;
  void choose_square_and_piece(unsigned int &chosen_si, Piece &chosen_piece, int me_player_index, Piece give_piece) const;

  void write(std::ostream &out) const;
  std::string get_formatted_output() const;

private:
  void calc_win();
  void calc_row_win(int a, int b, int c, int d);

  int count_row_near_wins(int a, int b, int c, int d) const;
  int count_row_near_win(int a, int b, int c) const;

  void get_max_search_levels(int &max_me_levels, int &max_search_levels, int bias = 0) const;

  void choose_from_result_list(SearchResult &best_result, const std::vector<SearchResult> &result_list, bool show_log = false) const;
  void search_wins(SearchAccumulator &me_result, int me_player_index, int max_me_levels, int max_search_levels, bool save_piece, bool show_log = false) const;
  void search_wins(SearchAccumulator &me_result, int me_player_index, int max_me_levels, int max_search_levels, Piece give_piece, bool show_log = false) const;

private:
  Piece::Code _board[num_squares];
  BoardMask _occupied;
  int _num_used_pieces;
  Piece::PieceMask _used_pieces;
  bool _advanced;
  BoardMask _win;
};

#endif  // Board
