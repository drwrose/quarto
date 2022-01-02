%module pyquarto
%include "std_string.i"

%{
#include "Quarto.h"
#include "Board.h"
#include "Piece.h"
%}

%include "Quarto.h"
%include "Board.h"
%include "Piece.h"
