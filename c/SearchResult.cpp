#include "SearchResult.h"

SearchResult::
SearchResult() :
  _aux_si(0),
  _win_count(0),
  _accidental_win_count(0),
  _near_win_count(0),
  _lose_count(0),
  _tie_count(0)
{
}

void SearchResult::
output(std::ostream &out) const {
  out << "(" << _win_count << "/" << _accidental_win_count << "/" << _near_win_count << ", " << _lose_count << ", " << _tie_count << ")";
}


void SearchResult::
operator += (const SearchResult &other) {
  _win_count += other._win_count;
  _accidental_win_count += other._accidental_win_count;
  _near_win_count += other._near_win_count;
  _lose_count += other._lose_count;
  _tie_count += other._tie_count;
}
