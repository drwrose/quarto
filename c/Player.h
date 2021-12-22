#ifndef PLAYER_H
#define PLAYER_H

#include "Piece.h"
#include <string>

class Quarto;

class Player {
public:
  static constexpr int num_players = 2;

  typedef unsigned int PlayerMask;

  Player(Quarto *quarto, int player_index);

  int get_player_index() const { return _player_index; }

  PlayerMask get_bit() const {
    return get_bit(_player_index);
  }
  static PlayerMask get_bit(int player_index) {
    return ((PlayerMask)1 << player_index);
  }

  void set_name(const std::string &name) { _name = name; }
  const std::string &get_name() const { return _name; }

  void set_robot(bool robot) {
    _robot = robot;
  }
  bool get_robot() const { return _robot; }

  Piece robot_choose_piece();
  unsigned int robot_choose_square(Piece give_piece);

  void output(std::ostream &out) const {
    out << get_name();
  }

private:
  Quarto *_quarto;
  int _player_index;
  std::string _name;
  bool _robot;

  bool _have_chosen_piece;
  Piece _chosen_piece;
};

inline std::ostream &operator << (std::ostream &out, const Player &player) {
  player.output(out);
  return out;
}

#endif  // PLAYER_H
