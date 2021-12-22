This is an experimental brute-force AI to play the game Quarto,
e.g. https://boardgamearena.com/gamepanel?game=quarto .

To build the C++ code, use CMake and point it at the c directory.  For
now, this builds a command-line program call mquarto that plays a game
with itself.  Parameters may be tweaked in the code to change the
board size and number of players, and/or allow one or more human
players into the game.
