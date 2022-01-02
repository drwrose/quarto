from BGATable import BGATable
import random
from import_pyquarto import Piece, Quarto, Board, Player

class BGAQuarto(BGATable):
    select_state_id = 10
    animation_state_id = 11
    place_state_id = 12
    game_over_state_id = 99

    # Piece number assignment according to BGA.
    pieces = [
        (1, Piece('lqtf')),
        (2, Piece('lrsh')),
        (3, Piece('lrsf')),
        (4, Piece('lrth')),
        (5, Piece('lrtf')),
        (6, Piece('lqsh')),
        (7, Piece('lqsf')),
        (8, Piece('lqth')),
        (9, Piece('dqtf')),
        (10, Piece('drsh')),
        (11, Piece('drsf')),
        (12, Piece('drth')),
        (13, Piece('drtf')),
        (14, Piece('dqsh')),
        (15, Piece('dqsf')),
        (16, Piece('dqth')),
        ]

    piece_number_to_piece = {}
    piece_to_piece_number = {}
    for piece_number, piece in pieces:
        piece_number_to_piece[piece_number] = piece
        piece_to_piece_number[piece] = piece_number

    def __init__(self, bga, table_id):
        self.selected_piece_number = None

        self.quarto = Quarto()

        # Temporary Python structures to play randomly
        self.unused_pieces = list(range(1, 17))
        self.unused_squares = []
        for x in range(1, 5):
            for y in range(1, 5):
                self.unused_squares.append((x, y))

        super(BGAQuarto, self).__init__(bga, table_id)

    def table_notification(self, notification_type, data_dict, live):
        if notification_type == 'placePiece':
            args = data_dict['args']
            piece_number = int(args['number'])
            x = int(args['x'])
            y = int(args['y'])
            print("placePiece: %s, (%s, %s)" % (piece_number, x, y))
            self.someone_placed_piece(piece_number, x, y)
        elif notification_type == 'selectPiece':
            args = data_dict['args']
            piece_number = int(args['number'])
            print("selectPiece %s" % (piece_number))
            self.someone_selected_piece(piece_number)
        else:
            super(BGAQuarto, self).table_notification(notification_type, data_dict, live)

    def my_turn(self):
        if 'id' not in self.game_state:
            # Game hasn't started yet, really.
            super(BGAQuarto, self).my_turn()
            return

        state_id = int(self.game_state['id'])
        if state_id == self.select_state_id:
            print("my turn to select piece")
            self.me_select_piece()
        elif state_id == self.place_state_id:
            print("my turn to place piece")
            self.me_place_piece()
        elif state_id == self.animation_state_id:
            print("animation state")
        elif state_id == self.game_over_state_id:
            print("game over state")
        else:
            print("my turn to do something else? %s" % (self.game_state,))
            super(BGAQuarto, self).my_turn()

    def me_select_piece(self):
        assert(self.unused_pieces)

        me = self.quarto.get_current_give_player()

        piece = me.robot_choose_piece()
        piece_number = self.piece_to_piece_number[piece]

        select_url = 'https://boardgamearena.com/%s/%s/%s/selectPiece.html' % (self.gameserver, self.game_name, self.game_name)
        select_params = {
            'number' : piece_number,
            'table' : self.table_id,
            }

        r = self.bga.session.get(select_url, params = select_params)
        assert(r.status_code == 200)

    def me_place_piece(self):
        assert(self.unused_squares)

        me = self.quarto.get_current_place_player()
        piece = self.piece_number_to_piece[self.selected_piece_number]

        si = me.robot_choose_square(piece)
        ri = Board.get_ri(si)
        ci = Board.get_ri(si)

        select_url = 'https://boardgamearena.com/%s/%s/%s/placePiece.html' % (self.gameserver, self.game_name, self.game_name)
        select_params = {
            'x' : ci + 1,
            'y' : ri + 1,
            'table' : self.table_id,
            }

        r = self.bga.session.get(select_url, params = select_params)
        assert(r.status_code == 200)

    def someone_selected_piece(self, piece_number):
        self.selected_piece_number = piece_number
        assert(piece_number in self.unused_pieces)
        self.unused_pieces.remove(piece_number)

    def someone_placed_piece(self, piece_number, x, y):
        assert(piece_number == self.selected_piece_number)
        assert((x, y) in self.unused_squares)
        self.unused_squares.remove((x, y))

        si = Board.get_si(y - 1, x - 1)
        piece = self.piece_number_to_piece[piece_number]
        self.quarto.place_piece(si, piece)
