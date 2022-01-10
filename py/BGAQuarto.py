from BGATable import BGATable
import random
import json
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

        super(BGAQuarto, self).__init__(bga, table_id)

    def update_table_infos(self):
        """ Called whenever self.table_infos has been updated. """

        # Check whether we have the Standard or Advanced Quarto variant.
        variant = self.table_infos['options']['100']['value']
        advanced = (int(variant) == 2)
        print("Advanced = %s" % (advanced))
        self.quarto.set_advanced(advanced)

        super(BGAQuarto, self).update_table_infos()

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
        assert(self.is_table_thread())

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
        me = self.quarto.get_current_give_player()

        piece = me.robot_choose_piece()
        piece_number = self.piece_to_piece_number[piece]

        print("Robot %s chose piece %s, %s" % (me.get_name(), piece.get_desc(), piece_number))

        select_url = 'https://boardgamearena.com/%s/%s/%s/selectPiece.html' % (self.gameserver, self.game_name, self.game_name)
        select_params = {
            'number' : piece_number,
            'table' : self.table_id,
            }

        try:
            r = self.bga.session.get(select_url, params = select_params)
        except ConnectionError:
            message = "Connection error on %s" % (select_url)
            raise RuntimeError(message)

        assert(r.status_code == 200)
        #print(r.url)
        dict = json.loads(r.text)
        try:
            dict = json.loads(r.text)
        except json.decoder.JSONDecodeError:
            print(r.url)
            print("Server response wasn't JSON: %s" % (r.text))
            return

        if not dict['status']:
            print(r.url)
            print("Game server didn't allow move: %s" % (dict,))
            self.abandon_game()

    def me_place_piece(self):
        me = self.quarto.get_current_place_player()
        piece = self.piece_number_to_piece[self.selected_piece_number]

        if not self.quarto.get_board().is_unused(piece):
            # This can happen when the game is shutting down.
            print("Robot %s was handed an invalid piece %s" % (me.get_name(), piece.get_desc()))
            self.abandon_game()
            return

        print("Robot %s choosing place for piece %s, %s" % (me.get_name(), piece.get_desc(), self.selected_piece_number))
        assert(self.quarto.get_board().is_unused(piece))

        si = me.robot_choose_square(piece)
        ri = Board.get_ri(si)
        ci = Board.get_ci(si)

        print("Robot %s chose square %s: %s, %s" % (me.get_name(), si, ci + 1, ri + 1))

        select_url = 'https://boardgamearena.com/%s/%s/%s/placePiece.html' % (self.gameserver, self.game_name, self.game_name)
        select_params = {
            'x' : ci + 1,
            'y' : ri + 1,
            'table' : self.table_id,
            }

        try:
            r = self.bga.session.get(select_url, params = select_params)
        except ConnectionError:
            message = "Connection error on %s" % (select_url)
            raise RuntimeError(message)

        assert(r.status_code == 200)
        #print(r.url)
        try:
            dict = json.loads(r.text)
        except json.decoder.JSONDecodeError:
            print(r.url)
            print("Server response wasn't JSON: %s" % (r.text))
            return

        if not dict['status']:
            print(r.url)
            print("Game server didn't allow move: %s" % (dict,))
            self.abandon_game()

    def someone_selected_piece(self, piece_number):
        self.selected_piece_number = piece_number

        piece = self.piece_number_to_piece[self.selected_piece_number]
        if not self.quarto.get_board().is_unused(piece):
            # This can happen when the game is shutting down.
            print("Someone selected an invalid piece %s" % (piece.get_desc()))
            self.abandon_game()
            return

    def someone_placed_piece(self, piece_number, x, y):
        piece = self.piece_number_to_piece[piece_number]

        if not self.quarto.get_board().is_unused(piece):
            # This can happen when the game is shutting down.
            print("Someone placed an invalid piece %s" % (piece.get_desc()))
            self.abandon_game()
            return

        if piece_number != self.selected_piece_number:
            # This is weird, but not technically an error.
            print("Someone placed an unexpected piece %s" % (piece.get_desc()))

        si = Board.get_si(y - 1, x - 1)
        if not self.quarto.get_board().is_empty(si):
            # This can happen when the game is shutting down.
            print("Someone placed a piece on an invalid square %s, %s" % (x, y))
            self.abandon_game()
            return

        self.quarto.place_piece(si, piece)
        print(self.quarto.get_board().get_formatted_output())
