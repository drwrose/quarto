from BGATable import BGATable
import random

class BGAQuarto(BGATable):
    select_state_id = 10
    animation_state_id = 11
    place_state_id = 12
    game_over_state_id = 99

    # Piece number assignment according to BGA.
    pieces = [
        (1, 'lqtf'),
        (2, 'lrsh'),
        (3, 'lrsf'),
        (4, 'lrth'),
        (5, 'lrtf'),
        (6, 'lqsh'),
        (7, 'lqsf'),
        (8, 'lqth'),
        (9, 'dqtf'),
        (10, 'drsh'),
        (11, 'drsf'),
        (12, 'drth'),
        (13, 'drtf'),
        (14, 'dqsh'),
        (15, 'dqsf'),
        (16, 'dqth'),
        ]

    def __init__(self, bga, table_id):
        self.selected_piece_number = None

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
        piece_number = random.choice(self.unused_pieces)

        #https://boardgamearena.com/4/quarto/quarto/selectPiece.html?number=1&table=226600309&dojo.preventCache=1640462571803

        select_url = 'https://boardgamearena.com/%s/%s/%s/selectPiece.html' % (self.gameserver, self.game_name, self.game_name)
        select_params = {
            'number' : piece_number,
            'table' : self.table_id,
            }

        r = self.bga.session.get(select_url, params = select_params)
        assert(r.status_code == 200)

    def me_place_piece(self):
        assert(self.unused_squares)
        x, y = random.choice(self.unused_squares)

        #https://boardgamearena.com/4/quarto/quarto/placePiece.html?x=1&y=4&table=226600309&dojo.preventCache=1640462661462

        select_url = 'https://boardgamearena.com/%s/%s/%s/placePiece.html' % (self.gameserver, self.game_name, self.game_name)
        select_params = {
            'x' : x,
            'y' : y,
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
