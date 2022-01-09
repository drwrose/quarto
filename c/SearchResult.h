#ifndef SEARCHRESULT_H
#define SEARCHRESULT_H

#include "SearchAccumulator.h"

// Manages the accumulated search results, plus additional numbers to
// help choose the solution.
class SearchResult : public SearchAccumulator {
public:
  // How valuable is a "near win" in the next round compared to an
  // accidental win in some vague future round?
  static constexpr int near_win_value = 20;

  SearchResult();
  SearchResult(const SearchAccumulator &accumulator);

  void set_near_win_count(int near_win_count) { _near_win_count = near_win_count; }
  int get_near_win_count() const { return _near_win_count; }

  void output(std::ostream &out) const;

  int win_score() const {
    return SearchAccumulator::win_score() + _near_win_count * near_win_value;
  }
  double win_ratio() const {
    assert(lose_count() != 0);
    return (double)win_score() / (double)lose_count();
  }

private:
  int _near_win_count;
};

inline std::ostream &operator << (std::ostream &out, const SearchResult &sr) {
  sr.output(out);
  return out;
}

#endif  // SEARCHRESULT_H
