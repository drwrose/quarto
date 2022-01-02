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
      strm << "l";
    } else {
      strm << "d";
    }
  }

  if (num_attribs >= 3) {
    if (code & 0x4) {
      strm << "r";
    } else {
      strm << "q";
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
    strm << "f";
  } else {
    strm << "h";
  }

  return strm.str();
}

Piece::Code Piece::
parse_desc(const std::string &desc) {
  if (desc.length() != num_attribs) {
    throw std::runtime_error("Invalid desc length");
  }

  Code code = 0;

  for (size_t p = 0; p < desc.length(); ++p) {
    switch (tolower(desc[p])) {
    case 'l':
      code |= 0x8;
      break;
    case 'd':
      break;

    case 'r':
      code |= 0x4;
      break;
    case 'q':
      break;

    case 's':
      code |= 0x2;
      break;
    case 't':
      break;

    case 'f':
      code |= 0x1;
      break;
    case 'h':
      break;

    default:
      throw std::runtime_error("Invalid desc");
    }
  }

  return code;
}
