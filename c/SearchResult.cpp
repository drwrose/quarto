#include "SearchResult.h"
#include "Board.h"

SearchResult::
SearchResult() :
  _near_win_count(0),
  _win_score(0)
{
}

// Pre-computes the value returned by win_score().
void SearchResult::
compute_win_score() {
  _win_score = 2 * win_count() + accidental_win_count() + near_win_count() * near_win_value;
}

// Records the relevant factors in the board configuration that
// corresponds to this SearchResult that will contribute to
// win_score() and/or win_ratio().
void SearchResult::
compute_win_score(const Board &board) {
  _near_win_count = board.count_near_wins();
  compute_win_score();
}

void SearchResult::
output(std::ostream &out) const {
  SearchAccumulator::output(out);
  out << "," << _near_win_count;
}
