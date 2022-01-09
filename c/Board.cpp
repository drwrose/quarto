#include "Board.h"
#include "Player.h"
#include "Quarto.h"

#include <assert.h>
#include <iomanip>
#include <algorithm>
#include <vector>
#include <random>
#include <sstream>

Board::
Board() {
  _occupied = 0;
  _num_used_pieces = 0;
  _used_pieces = 0;
  _advanced = false;
  _win = 0;
}

// This constructor makes a copy of the Board, and then places the
// indicated piece at the indicated square.  Use place_piece() instead
// of calling this directly.
Board::
Board(const Board &copy, unsigned int si, Piece piece) :
  _occupied(copy._occupied),
  _num_used_pieces(copy._num_used_pieces),
  _used_pieces(copy._used_pieces),
  _advanced(copy._advanced)
{
  std::copy(std::begin(copy._board), std::end(copy._board), std::begin(_board));
  assert(si < num_squares);
  assert(is_empty(si));
  assert(is_unused(piece));
  _board[si] = piece.get_code();
  _num_used_pieces++;
  _occupied |= get_mask(si);
  _used_pieces |= piece.get_bit();
  calc_win();
}

Board::
~Board() {
}

// Sets the advanced flag, indicating the advanced-variant rules are
// in play.  When this is true, a 2x2 box of matching pieces is also
// counted a win, in addition to the normal 4-in-a-row win.
void Board::
set_advanced(bool advanced) {
  _advanced = advanced;
}

// Returns true if the indicated square is empty, false if it contains
// a piece.
bool Board::
is_empty(unsigned int si) const {
  return (_occupied & get_mask(si)) == 0;
}

// Returns the piece at the indicated square.  It is an error to call
// this if !is_empty(si).
Piece Board::
get_piece(unsigned int si) const {
  assert(si < num_squares);
  assert(!is_empty(si));
  return Piece(_board[si]);
}

// Returns a new Board with the the indicated piece placed at the
// indicated square.  It is an error to call this if the square is
// already occupied, or if the piece in question has already been
// placed elsewhere.
std::shared_ptr<Board> Board::
place_piece(unsigned int si, Piece piece) const {
  return std::make_shared<Board>(*this, si, piece);
}

bool Board::
is_unused(Piece piece) const {
  return (_used_pieces & piece.get_bit()) == 0;
}

// Returns the index of the player whose turn it is to give a piece.
// This is also the player who placed the last piece.
int Board::
get_current_give_player_index() const {
  // The give player is the one right before the place player.
  int pi = get_current_place_player_index();
  return (pi + Player::num_players - 1) % Player::num_players;
}

// Returns the index of the player whose turn it is to place the
// next piece.
int Board::
get_current_place_player_index() const {
  return get_num_used_pieces() % Player::num_players;
}

// If the game was won, returns the winning player index.  It is an
// error to call this unlesss is_win() is true.
int Board::
get_winning_player_index() const {
  assert(is_win());
  return get_current_give_player_index();
}

// Returns the number of rows (or squares) that are "near wins",
// e.g. three matching pieces in the same row, with an empty square.
int Board::
count_near_wins() const {
  int near_wins = 0;

  near_wins += count_row_near_wins(0, 1, 2, 3);
  near_wins += count_row_near_wins(4, 5, 6, 7);
  near_wins += count_row_near_wins(8, 9, 10, 11);
  near_wins += count_row_near_wins(12, 13, 14, 15);
  near_wins += count_row_near_wins(0, 4, 8, 12);
  near_wins += count_row_near_wins(1, 5, 9, 13);
  near_wins += count_row_near_wins(2, 6, 10, 14);
  near_wins += count_row_near_wins(3, 7, 11, 15);
  near_wins += count_row_near_wins(0, 5, 10, 15);
  near_wins += count_row_near_wins(3, 6, 9, 12);

  if (_advanced) {
    // If the advanced rules are in effect, check also for winning
    // 2x2 squares.
    near_wins += count_row_near_wins(0, 1, 4, 5);
    near_wins += count_row_near_wins(1, 2, 5, 6);
    near_wins += count_row_near_wins(2, 3, 6, 7);
    near_wins += count_row_near_wins(4, 5, 8, 9);
    near_wins += count_row_near_wins(5, 6, 9, 10);
    near_wins += count_row_near_wins(6, 7, 10, 11);
    near_wins += count_row_near_wins(8, 9, 12, 13);
    near_wins += count_row_near_wins(9, 10, 13, 14);
    near_wins += count_row_near_wins(10, 11, 14, 15);
  }

  return near_wins;
}

// Returns true if this board position marks the end of the game, or
// false if another play may be made.
bool Board::
is_game_over() const {
  return (_num_used_pieces >= num_squares || _num_used_pieces >= Piece::num_pieces || _win != 0);
}

// Chooses the appropriate give_piece to hand to the next player, as an
// AI player.  Returns Piece, and fills best_result.
Piece Board::
choose_piece(SearchResult &best_result, int me_player_index, bool show_log) const {
  assert(!is_game_over());
  assert(me_player_index == get_current_give_player_index());

  int max_me_levels, max_search_levels;
  get_max_search_levels(max_me_levels, max_search_levels, 1);
  if (show_log) std::cerr << "choose_piece(), max_search_levels = " << max_me_levels << ", " << max_search_levels << "\n";

  // Get a list of all of the possible pieces, and search below for
  // each one.
  std::vector<SearchResult> result_list;
  for (unsigned int pi = 0; pi < Piece::num_pieces; ++pi) {
    Piece give_piece(pi);
    if (!is_unused(give_piece)) {
      // This square is already used, not an option.
      continue;
    }

    SearchResult next_result;
    next_result.set_aux_piece(give_piece);
    search_wins(next_result, me_player_index, max_me_levels, max_search_levels, give_piece);
    next_result.compute_win_score();
    result_list.push_back(next_result);
  }

  // Shuffle the result_list, so we don't have any systemic
  // preferences.
  std::shuffle(result_list.begin(), result_list.end(), Quarto::random_generator);

  choose_from_result_list(best_result, result_list, show_log);
  return best_result.get_aux_piece();
}

// Chooses the appropriate square to place the indicated piece, as an
// AI player.  Fills chosen_si and chosen_piece.
void Board::
choose_square_and_piece(unsigned int &chosen_si, Piece &chosen_piece, int me_player_index, Piece give_piece) const {
  assert(!is_game_over());
  assert(me_player_index == get_current_place_player_index());

  int max_me_levels, max_search_levels;
  get_max_search_levels(max_me_levels, max_search_levels);
  std::cerr << "choose_square(), max_search_levels = " << max_me_levels << ", " << max_search_levels << "\n";

  // First, get a list of all of the possible squares.
  std::vector<int> si_list;
  for (unsigned int si = 0; si < num_squares; ++si) {
    if (!is_empty(si)) {
      // This square is already occupied, not an option.
      continue;
    }

    si_list.push_back(si);
  }
  assert(!si_list.empty());

  // And go through that list in random order so we don't have any
  // systemic preferences.
  std::shuffle(si_list.begin(), si_list.end(), Quarto::random_generator);

  // Now consider actually placing the piece in each of those squares.
  std::vector<std::shared_ptr<Board> > next_boards_by_si;
  next_boards_by_si.insert(next_boards_by_si.end(), num_squares, 0);

  for (unsigned int si : si_list) {
    std::shared_ptr<Board> next_board = place_piece(si, give_piece);
    if (next_board->is_win()) {
      // Here's an easy win.  No need to search further.
      std::cerr << "found easy win at " << si << "\n";
      chosen_si = si;
      return;
    }

    next_boards_by_si[si] = next_board;
  }

  // Now search below and choose the best option.
  std::vector<SearchResult> result_list;
  for (unsigned int si : si_list) {
    std::shared_ptr<Board> &next_board = next_boards_by_si[si];

    SearchResult next_result;
    next_result.set_aux_si(si);
    next_board->search_wins(next_result, me_player_index, max_me_levels - 1, max_search_levels - 1, true);
    next_result.compute_win_score(*next_board);
    result_list.push_back(next_result);
  }

  SearchResult best_result;
  choose_from_result_list(best_result, result_list, true);
  std::cerr << "choosing si " << best_result.get_aux_si() << " and piece " << best_result.get_aux_piece() << "\n";
  chosen_si = best_result.get_aux_si();
  chosen_piece = best_result.get_aux_piece();
}

// Writes a simple multi-line ASCII rendering of the board to the
// indicated stream.
void Board::
write(std::ostream &out) const {
  for (int ri = 0; ri < num_rows; ++ri) {
    for (int ci = 0; ci < num_cols; ++ci) {
      if ((_win & get_mask(ri, ci)) != 0) {
        out << "[";
      } else {
        out << " ";
      }
      if (is_empty(ri, ci)) {
        int si = get_si(ri, ci);
        out << std::setfill('-') << std::setw(Piece::num_attribs - 1) << (si + 1) << "-";
      } else {
        out << get_piece(ri, ci);
      }
      if ((_win & get_mask(ri, ci)) != 0) {
        out << "]";
      } else {
        out << " ";
      }
      out << " ";
    }
    out << "\n";
  }

  for (Piece::Code code = 0; code < Piece::num_pieces; ++code) {
    Piece piece(code);
    if (is_unused(piece)) {
      out << "  " << code + 1 << ". " << piece << "\n";
    }
  }
}

// Returns the multi-line ASCII rendering of the board as a string.
// This is the same output generated by write(), it is useful for
// Python output.
std::string Board::
get_formatted_output() const {
  std::ostringstream strm;
  write(strm);
  return strm.str();
}

// Fills _win with a bitmask of all of the squares that contribute to
// a win (four in a row).  Sets it to 0 if there is no win.
void Board::
calc_win() {
  _win = 0;

  // Check for a winning 4-in-a-row.
  calc_row_win(0, 1, 2, 3);
  calc_row_win(4, 5, 6, 7);
  calc_row_win(8, 9, 10, 11);
  calc_row_win(12, 13, 14, 15);
  calc_row_win(0, 4, 8, 12);
  calc_row_win(1, 5, 9, 13);
  calc_row_win(2, 6, 10, 14);
  calc_row_win(3, 7, 11, 15);
  calc_row_win(0, 5, 10, 15);
  calc_row_win(3, 6, 9, 12);

  if (_advanced) {
    // If the advanced rules are in effect, check also for winning
    // 2x2 squares.
    calc_row_win(0, 1, 4, 5);
    calc_row_win(1, 2, 5, 6);
    calc_row_win(2, 3, 6, 7);
    calc_row_win(4, 5, 8, 9);
    calc_row_win(5, 6, 9, 10);
    calc_row_win(6, 7, 10, 11);
    calc_row_win(8, 9, 12, 13);
    calc_row_win(9, 10, 13, 14);
    calc_row_win(10, 11, 14, 15);
  }
}

// Called for four squares in a row.  If the indicated squares
// indicate a win, adds the appropriate bitmask to _win.  Otherwise,
// does nothing.
void Board::
calc_row_win(int a, int b, int c, int d) {
  int empty_count = (int)is_empty(a) + (int)is_empty(b) + (int)is_empty(c) + (int)is_empty(d);
  if (empty_count != 0) {
    // The row is not yet filled, it's not a win.
    return;
  }

  // The row is filled, it's a win if one of the attribs all match.
  if ((_board[a] & _board[b] & _board[c] & _board[d]) != 0) {
    // One of the 1-bits matches.
    _win |= (get_mask(a) | get_mask(b) | get_mask(c) | get_mask(d));
  }

  if ((_board[a] | _board[b] | _board[c] | _board[d]) != Piece::all_attribs) {
    // One of the 0-bits matches.
    _win |= (get_mask(a) | get_mask(b) | get_mask(c) | get_mask(d));
  }

  // None of the attribs match.
}

// Returns 1 if this row is a near win, 0 if it is not.
int Board::
count_row_near_wins(int a, int b, int c, int d) const {
  int empty_count = (int)is_empty(a) + (int)is_empty(b) + (int)is_empty(c) + (int)is_empty(d);
  if (empty_count == 1) {
    if (is_empty(a)) {
      return count_row_near_win(b, c, d);
    } else if (is_empty(b)) {
      return count_row_near_win(a, c, d);
    } else if (is_empty(c)) {
      return count_row_near_win(a, b, d);
    } else {
      assert(is_empty(d));
      return count_row_near_win(a, b, c);
    }
  }

  // The row is filled.
  return 0;
}

// Called for three occupied squares in a row of four squares.  If the
// indicated squares indicate a potential near-win--that is, all three
// pieces match at least one attribute--returns 1.  Otherwise, returns
// 0.
int Board::
count_row_near_win(int a, int b, int c) const {
  if ((_board[a] & _board[b] & _board[c]) != 0) {
    // One of the 1-bits matches.
    return 1;
  }

  if ((_board[a] | _board[b] | _board[c]) != Piece::all_attribs) {
    // One of the 0-bits matches.
    return 1;
  }

  // None of the attribs match.
  return 0;
}

// FIlls max_me_levels with the maximum number of levels we continue
// to search our own possible moves, and max_search_levels with the
// the maximum number of search levels we continue to search anything
// at all, based on the current state of the game.

// We limit these only to save on time, so we don't spend years
// computing quadrillions of moves.  By having max_me_levels as a
// separate, shorter cutoff, we prioritize the deepest searching for
// our opponent's moves over our own.  This means we may overlook some
// forced-win opportunities, and we may see some options that
// incorrectly appear to be forced-losses even though they have
// escapes; but we won't accidentally overlook any forced-losses,
// which is the most important.
void Board::
get_max_search_levels(int &max_me_levels, int &max_search_levels, int bias) const {
  int empty_squares = (num_squares - _num_used_pieces) + bias;
  if (empty_squares < 8) {
    // Only a few squares remain.  Go all the way down.
    max_me_levels = 8;
    max_search_levels = 8;

  } else if (empty_squares < 10) {
    // Go deeper now.
    max_me_levels = 5;
    max_search_levels = 7;

  } else if (empty_squares < 11) {
    // Safer to look even deeper.
    max_me_levels = 4;
    max_search_levels = 6;

  } else if (empty_squares < 13) {
    // Need to start looking deeper now.
    max_me_levels = 3;
    max_search_levels = 4;

  } else if (empty_squares < 14) {
    // Look only a few moves ahead, but not so few that we overlook an
    // early win.
    max_me_levels = 3;
    max_search_levels = 3;

  } else if (empty_squares < 15) {
    // Just look ahead enough not to get screwed.
    max_me_levels = 2;
    max_search_levels = 3;

  } else {
    // It really doesn't matter.
    max_me_levels = 2;
    max_search_levels = 2;
  }
}

void Board::
choose_from_result_list(SearchResult &best_result, const std::vector<SearchResult> &result_list, bool show_log) const {
  // OK, we didn't find an immediate win, see what wins we
  // have in subsequent turns.

  size_t best_tie_ri = 0;
  int best_tie_wins = -1;

  size_t best_mixed_ri = 0;
  double best_mixed_ratio = -1.0;

  size_t best_loss_ri = 0;
  int best_loss_wins = -1;

  for (size_t ri = 0; ri < result_list.size(); ++ri) {
    const SearchResult &next_result = result_list[ri];
    if (show_log) std::cerr << "  considering " << ri << ": " << next_result << ", " << next_result.get_aux_si() << ", " << next_result.get_aux_piece() << "\n";
    if (next_result.is_forced_win()) {
      // This is a forced win!  Pick this option.
      best_result = next_result;
      if (show_log) std::cerr << "found forced win at " << ri << "\n";
      return;

    } else if (next_result.is_forced_loss()) {
      // This is a forced loss.  Definitely don't pick this option.
      // Unless of course we have to.
      if (next_result.win_score() > best_loss_wins) {
        best_loss_ri = ri;
        best_loss_wins = next_result.win_score();
      }

    } else if (next_result.is_not_loss()) {
      // This option might result in a tie, pick this if we have no
      // better choices.  Pick the one that has the greatest
      // win_score, which counts accidental and forced wins together.
      if (next_result.win_score() > best_tie_wins) {
        best_tie_ri = ri;
        best_tie_wins = next_result.win_score();
      }

    } else {
      // This has both wins and losses.  Try to find the option with
      // the greatest ratio of win_counts to lose_counts.
      double win_ratio = next_result.win_ratio();
      if (win_ratio > best_mixed_ratio) {
        best_mixed_ri = ri;
        best_mixed_ratio = win_ratio;
      }
    }
  }

  if (best_tie_wins >= 0) {
    if (show_log) std::cerr << "choosing best tie option " << best_tie_ri << ", win score is " << best_tie_wins << "\n";
    best_result = result_list[best_tie_ri];
    return;
  }
  if (best_mixed_ratio >= 0.0) {
    if (show_log) std::cerr << "choosing best mixed option " << best_mixed_ri << ", ratio is " << best_mixed_ratio << "\n";
    best_result = result_list[best_mixed_ri];
    return;
  }
  if (best_loss_wins >= 0) {
    if (show_log) std::cerr << "choosing best loss option " << best_loss_ri << ", win score is " << best_loss_wins << "\n";
    best_result = result_list[best_loss_ri];
    return;
  }

  // We're screwed.  All of our options result in a loss.  Pick any
  // one.
  if (show_log) std::cerr << "choosing random loss option 0\n";
  best_result = result_list[0];
  return;
}

// Recursively search following board patterns for forced win
// conditions, starting with choosing a give_piece.  Fills win_counts
// with the count of win conditions detected for each player.  If
// save_piece is true, then me_accumulator.get_aux_piece() is also filled
// with the chosen give_piece.
void Board::
search_wins(SearchAccumulator &me_accumulator, int me_player_index, int max_me_levels, int max_search_levels, bool save_piece, bool show_log) const {
  if (show_log) {
    std::cerr << this << "->search_wins for piece(..., " << me_player_index << ", " << max_search_levels << ")\n";
    write(std::cerr);
  }

  if (max_search_levels <= 0) {
    if (show_log) std::cerr << this << " trivial no-op\n";
    return;
  }
  assert(!is_win());
  if (is_game_over()) {
    // The game resulted in a tie.
    if (show_log) std::cerr << this << " trivial tie\n";
    me_accumulator.inc_tie();
    return;
  }

  bool my_turn = (me_player_index == get_current_give_player_index());
  if (save_piece) {
    assert(my_turn);
    // If it's my turn, instead of examining all of the pieces, we can
    // instead choose our favorite piece and examine that one only.
    SearchResult next_result0;
    Piece give_piece = choose_piece(next_result0, me_player_index);

    if (show_log) std::cerr << this << " considering only " << give_piece << "\n";

    SearchAccumulator next_accumulator;
    search_wins(next_accumulator, me_player_index, max_me_levels, max_search_levels, give_piece);

    if (show_log) std::cerr << this << " " << give_piece << " results in " << next_accumulator << "\n";
    me_accumulator += next_accumulator;
    me_accumulator.set_aux_piece(give_piece);
    if (show_log) std::cerr << this << " done, computed " << me_accumulator << "\n";
    return;
  }

  SearchAccumulator forced_accumulator;
  bool got_any = false;

  unsigned int specific_pi;
  if (my_turn && max_me_levels <= 0) {
    // If we're too far down the search tree to keep searching all of
    // my own possible moves, just pick one particular move at random.
    specific_pi = std::uniform_int_distribution<>(0, Piece::num_pieces - 1)(Quarto::random_generator);
  }

  for (unsigned int pi = 0; pi < Piece::num_pieces; ++pi) {
    if (my_turn && max_me_levels <= 0) {
      if (pi != specific_pi) {
        // Skip the ones we're not considering.
        continue;
      }
    }

    Piece give_piece(pi);
    if (!is_unused(give_piece)) {
      // This square is already used, not an option.
      continue;
    }

    if (show_log) std::cerr << this << " considering " << give_piece << "\n";

    SearchAccumulator next_accumulator;
    search_wins(next_accumulator, me_player_index, max_me_levels, max_search_levels, give_piece);

    if (show_log) std::cerr << this << " " << give_piece << " results in " << next_accumulator << "\n";

    if (my_turn) {
      // On my turn, we don't consider choosing pieces that would
      // result in a forced loss for us, unless we have to.
      if (next_accumulator.is_forced_loss()) {
        forced_accumulator += next_accumulator;
        if (show_log) std::cerr << this << " skipping my forced loss\n";
        continue;
      }

    } else {
      // On the opponent's turn, we don't consider choosing pieces
      // that would result in a forced win for us, unless we have to.
      // But we do count a potential win as an "accidental" win.
      if (next_accumulator.is_forced_win()) {
        me_accumulator.inc_accidental_win(next_accumulator);
        forced_accumulator += next_accumulator;
        if (show_log) std::cerr << this << " skipping their forced loss\n";
        continue;
      }
    }

    // If it's not one of the above, count it in.
    me_accumulator += next_accumulator;
    got_any = true;
  }

  // Every move was forced.
  if (!got_any) {
    me_accumulator += forced_accumulator;
  }

  if (show_log) std::cerr << this << " done, computed " << me_accumulator << "\n";
}

// Recursively search following board patterns for forced win
// conditions, starting with the indicated give_piece.  Fills
// win_counts with the count of win conditions detected for each
// player.
void Board::
search_wins(SearchAccumulator &me_accumulator, int me_player_index, int max_me_levels, int max_search_levels, Piece give_piece, bool show_log) const {
  if (show_log) {
    std::cerr << this << "->search_wins for square(..., " << me_player_index << ", " << max_search_levels << ", " << give_piece << ")\n";
    write(std::cerr);
  }
  if (max_search_levels <= 0) {
    if (show_log) std::cerr << this << " trivial no-op\n";
    return;
  }
  assert(!is_win());
  if (is_game_over()) {
    // The game resulted in a tie.
    if (show_log) std::cerr << this << " trivial tie\n";
    me_accumulator.inc_tie();
    return;
  }

  std::vector<std::shared_ptr<Board> > next_boards;

  bool my_turn = (me_player_index == get_current_place_player_index());

  unsigned int specific_si;
  if (my_turn && max_me_levels <= 0) {
    // If we're too far down the search tree to keep searching all of
    // my own possible moves, just pick one particular move at random.
    specific_si = std::uniform_int_distribution<>(0, num_squares - 1)(Quarto::random_generator);
  }

  for (unsigned int si = 0; si < num_squares; ++si) {
    if (my_turn && max_me_levels <= 0) {
      if (si != specific_si) {
        // Skip the ones we're not considering.
        continue;
      }
    }

    if (!is_empty(si)) {
      // This square is already occupied, not an option.
      continue;
    }

    std::shared_ptr<Board> next_board = place_piece(si, give_piece);
    if (next_board->is_win()) {
      // Someone can win with this piece!  Don't look any further.  Is
      // it a win for me or for someone else?
      assert(my_turn == (next_board->get_winning_player_index() == me_player_index));
      if (my_turn) {
        // It's a win for me!
        me_accumulator.inc_win();
        if (show_log) std::cerr << this << " instant win at " << si << "\n";
      } else {
        // It's a win for someone else.
        me_accumulator.inc_lose();
        if (show_log) std::cerr << this << " instant loss at " << si << "\n";
      }
      return;

    } else {
      // Look further for more win conditions.
      next_boards.push_back(next_board);
    }
  }

  // OK, we didn't find an immediate win, see what wins we
  // have in subsequent turns.
  SearchAccumulator forced_accumulator;
  bool got_any = false;

  SearchAccumulator sum_accumulator;

  for (auto next_board : next_boards) {
    SearchAccumulator next_accumulator;
    if (show_log) std::cerr << this << " recursing into " << next_board << " {\n";
    next_board->search_wins(next_accumulator, me_player_index, max_me_levels - 1, max_search_levels - 1, false);
    if (show_log) std::cerr << "} back in " << this << ", " << next_accumulator << "\n";

    if (my_turn) {
      // On my turn, we don't consider choosing squares that would
      // result in a forced loss for us, unless we have to.
      if (next_accumulator.is_forced_loss()) {
        forced_accumulator += next_accumulator;
        if (show_log) std::cerr << this << " skipping my forced loss\n";
        continue;
      }

    } else {
      // On the opponent's turn, we don't consider choosing squares
      // that would result in a forced win for us, unless we have to.
      // But we do count a potential win as an "accidental" win.
      if (next_accumulator.is_forced_win()) {
        sum_accumulator.inc_accidental_win(next_accumulator);
        forced_accumulator += next_accumulator;
        if (show_log) std::cerr << this << " skipping their forced loss\n";
        continue;
      }
    }

    // If it's not one of the above, count it in.
    sum_accumulator += next_accumulator;
    got_any = true;
  }

  // Every move was forced.
  if (!got_any) {
    sum_accumulator += forced_accumulator;
  }

  if (show_log) std::cerr << this << " done, computed " << sum_accumulator << "\n";

  if (sum_accumulator.is_forced_win()) {
    // We have a forced win!  All subsequent moves result in a win for us.
    if (show_log) std::cerr << this << " is a win\n";
    me_accumulator.inc_win(sum_accumulator);

  } else if (sum_accumulator.is_forced_loss()) {
    // We have a forced loss.  All subsequent moves result in a loss for us.
    if (show_log) std::cerr << this << " is a loss\n";
    me_accumulator.inc_lose(sum_accumulator);
    me_accumulator.inc_accidental_win(sum_accumulator);

  } else if (sum_accumulator.is_forced_tie()) {
    // Everything from here on is a tie.
    if (show_log) std::cerr << this << " is a tie\n";
    me_accumulator.inc_tie(sum_accumulator);
    me_accumulator.inc_accidental_win(sum_accumulator);

  } else if (sum_accumulator.is_accidental_win()) {
    // We'll win if the opponent slips up.
    if (show_log) std::cerr << this << " is an accidental win\n";
    me_accumulator.inc_accidental_win(sum_accumulator);

  } else {
    if (show_log) std::cerr << this << " is mixed\n";
    me_accumulator += sum_accumulator;
  }
}
