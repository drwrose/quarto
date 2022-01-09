#ifndef SEARCHRESULT_H
#define SEARCHRESULT_H

#include "SearchAccumulator.h"

class Board;

// Manages the accumulated search results, plus additional numbers to
// help choose the solution.
class SearchResult : public SearchAccumulator {
public:
  // How valuable is a "near win" in the next round compared to an
  // accidental win in some vague future round?
  static constexpr int near_win_value = 20;

  SearchResult();

  void compute_win_score();
  void compute_win_score(const Board &board);
  int near_win_count() const { return _near_win_count; }

  void output(std::ostream &out) const;

  // Returns a numeric value that corresponds to the preference of
  // choosing this result for a win, among other results that don't
  // include any forced loss possibilities.  Higher values correspond
  // to more desirable choices.
  int win_score() const {
    return _win_score;
  }

  // Returns a numeric value that corresponds to the preference of
  // this result, among other results that might include one or more
  // forced loss possibilities.
  double win_ratio() const {
    assert(lose_count() != 0);
    return (double)win_score() / (double)lose_count();
  }

private:
  int _near_win_count;
  int _win_score;
};

inline std::ostream &operator << (std::ostream &out, const SearchResult &sr) {
  sr.output(out);
  return out;
}

#endif  // SEARCHRESULT_H
