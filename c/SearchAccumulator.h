#ifndef SEARCHACCUMULATOR_H
#define SEARCHACCUMULATOR_H

#include "Piece.h"

#include <iostream>
#include <assert.h>

// Keeps the numerical result of wins, losses, and ties detected by
// Board::search_wins().
class SearchAccumulator {
public:
  SearchAccumulator();

  void output(std::ostream &out) const;

  void operator += (const SearchAccumulator &other);

  // aux_si and aux_piece are arbitrary values piggybacking on the
  // result data.
  void set_aux_si(unsigned int si) { _aux_si = si; }
  unsigned int get_aux_si() const { return _aux_si; }

  void set_aux_piece(Piece piece) { _aux_piece = piece; }
  const Piece &get_aux_piece() const { return _aux_piece; }

  bool is_forced_win() const {
    return (_win_count != 0 && _lose_count == 0 && _tie_count == 0);
  }
  bool is_accidental_win() const {
    return (_accidental_win_count != 0 && _lose_count == 0 && _tie_count == 0);
  }

  bool is_forced_loss() const {
    return (_lose_count != 0 && _win_count == 0 && _tie_count == 0);
  }

  bool is_forced_tie() const {
    return (_tie_count !=0 && _win_count == 0 && _lose_count == 0);
  }

  bool is_not_loss() const {
    return (_lose_count == 0);
  }

  int win_count() const {
    return _win_count;
  }
  int accidental_win_count() const {
    return _accidental_win_count;
  }
  int win_score() const {
    return 2 * _win_count + _accidental_win_count;
  }
  int lose_count() const {
    return _lose_count;
  }
  double win_ratio() const {
    assert(_lose_count != 0);
    return (double)win_score() / (double)lose_count();
  }
  int tie_count() const {
    return _tie_count;
  }

  void inc_win() {
    _win_count++;
    _accidental_win_count++;
  }
  void inc_win(const SearchAccumulator &other) {
    _win_count += other._win_count;
    _accidental_win_count += other._accidental_win_count;
  }
  void inc_accidental_win() {
    _accidental_win_count++;
  }
  void inc_accidental_win(const SearchAccumulator &other) {
    _accidental_win_count += other._accidental_win_count;
  }
  void inc_lose() {
    _lose_count++;
  }
  void inc_lose(const SearchAccumulator &other) {
    _lose_count += other._lose_count;
  }
  void inc_tie() {
    _tie_count++;
  }
  void inc_tie(const SearchAccumulator &other) {
    _tie_count += other._tie_count;
  }

private:
  unsigned int _aux_si;
  Piece _aux_piece;
  int _win_count;
  int _accidental_win_count;
  int _lose_count;
  int _tie_count;
};

inline std::ostream &operator << (std::ostream &out, const SearchAccumulator &sr) {
  sr.output(out);
  return out;
}

#endif  // SEARCHACCUMULATOR_H
