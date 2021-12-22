#include "Piece.h"

#include <ctype.h>
#include <sstream>

std::string Piece::
format_desc(Code code) {
  // r(round) vs q(square)
  // f(flat) vs h(hollow)
  // s(short) vs t(tall)
  // l(light) vs d(dark)

  std::ostringstream strm;
  if (num_attribs >= 4) {
    if (code & 0x8) {
      strm << "r";
    } else {
      strm << "q";
    }
  }

  if (num_attribs >= 3) {
    if (code & 0x4) {
      strm << "f";
    } else {
      strm << "h";
    }
  }

  if (num_attribs >= 2) {
    if (code & 0x2) {
      strm << "s";
    } else {
      strm << "t";
    }
  }

  if (code & 0x1) {
    strm << "l";
  } else {
    strm << "d";
  }

  return strm.str();
}

Piece::Code Piece::
parse_desc(const std::string &desc) {
  if (desc.length() != num_attribs) {
    throw std::runtime_error("Invalid desc length");
  }

  Code code = 0;

  size_t p = 0;

  if (num_attribs >= 4) {
    switch (tolower(desc[p])) {
    case 'r':
      code |= 0x8;
      break;
    case 'q':
      break;
    default:
      throw std::runtime_error("Invalid desc");
    }
    ++p;
  }

  if (num_attribs >= 3) {
    switch (tolower(desc[p])) {
    case 'f':
      code |= 0x4;
      break;
    case 'h':
      break;
    default:
      throw std::runtime_error("Invalid desc");
    }
    ++p;
  }

  if (num_attribs >= 2) {
    switch (tolower(desc[p])) {
    case 's':
      code |= 0x2;
      break;
    case 't':
      break;
    default:
      throw std::runtime_error("Invalid desc");
    }
    ++p;
  }

  switch (tolower(desc[p])) {
  case 'l':
    code |= 0x1;
    break;
  case 'd':
    break;
  default:
    throw std::runtime_error("Invalid desc");
  }

  return code;
}
