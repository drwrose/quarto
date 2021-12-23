#include "Quarto.h"

#include <assert.h>
#include <stdlib.h>
#include <stdio.h>  // for EOF
#include <string.h>
#include <ctype.h>
#include <iostream>
#include <fstream>
#include <sstream>
#include <string>
#include <vector>
#include <cstdlib>
#include <ctime>

extern "C" {
#include "pgetopt.h"
}

void
usage() {
  std::cerr
    << "\n"
    "Usage: mquarto [opts]\n"
    "\n";
}

void
help() {
  std::cerr
    << "\n"
    "A program to test the Quarto simulation.  TODO: write more here.\n"
    "\n"
    "mquarto [opts]\n"
    "\n"
    "Options:\n"
    "\n"
    "   -h\n"
    "       This page.\n"
    "\n";
}

void run_game() {
  Quarto quarto;

  while (!quarto.is_game_over()) {
    std::cout << "\n";
    quarto.get_board().write(std::cout);

    Piece give_piece;
    if (quarto.get_current_give_player().get_robot()) {
      // Ask the robot to choose a piece.
      std::cout << "\n" << quarto.get_current_give_player() << " is selecting a piece to give to " << quarto.get_current_place_player() << "...\n" << std::flush;
      give_piece = quarto.get_current_give_player().robot_choose_piece();
      std::cout << quarto.get_current_give_player() << " selected piece " << give_piece << "\n";

    } else {
      // Ask the human to choose a piece.
      std::cout << "\n" << quarto.get_current_give_player() << " select a piece to give to " << quarto.get_current_place_player() << ":\n";

      while (true) {
        int piece_number;
        std::cin >> piece_number;
        if (piece_number < 1 || piece_number > Piece::num_pieces) {
          std::cout << "Invalid piece number: " << piece_number << "\n";
        } else {
          give_piece = Piece(piece_number - 1);
          if (!quarto.get_board().is_unused(give_piece)) {
            std::cout << "Piece " << give_piece << " has been already used\n";
          } else {
            break;
          }
        }
      }
    }

    std::cout << "\n";
    quarto.get_board().write(std::cout);

    unsigned int si = 0;

    if (quarto.get_current_place_player().get_robot()) {
      // Ask the robot to choose a square.
      std::cout << "\n" << quarto.get_current_place_player() << " is selecting a square to place " << give_piece << "...\n" << std::flush;
      si = quarto.get_current_place_player().robot_choose_square(give_piece);
      std::cout << quarto.get_current_place_player() << " selected square " << si + 1 << "\n";

    } else {
      // Ask the human to choose a square.
      std::cout << "\n" << quarto.get_current_place_player() << " select a square to place " << give_piece << ":\n";

      while (true) {
        int square_number;
        std::cin >> square_number;
        if (square_number < 1 || square_number > Board::num_squares) {
          std::cout << "Invalid square number: " << square_number << "\n";
        } else {
          si = square_number - 1;
          if (!quarto.get_board().is_empty(si)) {
            std::cout << "Square " << square_number << " is already occupied.\n";
          } else {
            break;
          }
        }
      }
    }

    quarto.place_piece(si, give_piece);
  }

  quarto.get_board().write(std::cout);
  if (quarto.is_win()) {
    std::cout << "Congratulations, " << quarto.get_winning_player() << "!\n";
  } else {
    std::cout << "Game is a draw, thanks for playing.\n";
  }
}

int
main(int argc, char *argv[]) {
  extern char *poptarg;
  extern int poptind;
  static const char *optflags = "h";

  int flag = pgetopt(argc, argv, (char *)optflags);
  while (flag != EOF) {
    switch (flag) {

    case 'h':
      help();
      return 1;

    case '?':
      usage();
      return 1;

    default:
      std::cerr << "Unhandled switch: " << flag << "\n";
      break;
    }
    flag = pgetopt(argc, argv, (char *)optflags);
  }

  //Quarto::random_generator.seed((unsigned int)std::time(nullptr));
  run_game();

  return 0;
}
