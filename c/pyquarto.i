// This file is an interface file for SWIG, to define the C++ classes
// and methods that are exposed to Python in the module pyquarto.pyd.

%module pyquarto
%include "std_string.i"
%include "std_shared_ptr.i"

%{
#include "Quarto.h"
#include "Board.h"
#include "Piece.h"
#include "Player.h"
%}

%shared_ptr(Board)

%include "Quarto.h"
%include "Board.h"
%include "Piece.h"
%include "Player.h"

// Rename Piece.hash to Piece.__hash__ for Python
%extend Piece {
  int __hash__() {
    return self->hash();
  }
}
