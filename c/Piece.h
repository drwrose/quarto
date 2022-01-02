#ifndef PIECE_H
#define PIECE_H

#include <stdint.h>
#include <iostream>
#include <string>

class Piece {
public:
  static constexpr unsigned int num_attribs = 4;
  static constexpr unsigned int num_pieces = (1 << num_attribs);

  typedef unsigned int Code;  // e.g. bitmask of attribs
  typedef unsigned int PieceMask;

  static constexpr Code all_attribs = ((Code)1 << num_attribs) - 1;

  Piece(Code code = 0) {
    _code = code;
  }
  Piece(const std::string &desc) {
    _code = parse_desc(desc);
  }

  bool operator == (const Piece &other) const { return _code == other._code; }

  PieceMask get_bit() const {
    return ((PieceMask)1 << _code);
  }

  Code get_code() const { return _code; }
  std::string get_desc() const { return format_desc(get_code()); }

  static std::string format_desc(Code code);
  static Code parse_desc(const std::string &desc);

  void output(std::ostream &out) const {
    out << format_desc(_code);
  }

private:
  Code _code;
};

inline std::ostream &operator << (std::ostream &out, const Piece &piece) {
  piece.output(out);
  return out;
}

#endif  // Piece
