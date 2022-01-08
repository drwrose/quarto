#include "SearchResult.h"

SearchResult::
SearchResult() :
  _near_win_count(0)
{
}

SearchResult::
SearchResult(const SearchAccumulator &accumulator) :
  SearchAccumulator(accumulator),
  _near_win_count(0)
{
}

void SearchResult::
output(std::ostream &out) const {
  SearchAccumulator::output(out);
  out << "," << _near_win_count;
}
