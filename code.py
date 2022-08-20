import board
import displayio
import keypad

from space_miner_helpers import Ship, SpaceMinerGame

keys = keypad.Keys((board.SW_LEFT, board.SW_RIGHT, board.SW_A, board.SW_B, board.SW_Y), value_when_pressed=False, pull=True)

display = board.DISPLAY
display.brightness = 0.1


main_group = displayio.Group()

game = SpaceMinerGame((display.width, display.height), display)

# Add the TileGrid to the Group
main_group.append(game)

# Add the Group to the Display
display.show(main_group)

left_btn_is_down = False
right_btn_is_down = False

# Loop forever so you can enjoy your image
while True:
    event = keys.events.get()
    # event will be None if nothing has happened.
    if event:
        if event.pressed:
            print("pressed", event)
            if event.key_number == 1:
                game.right_btn_is_down = True
            elif event.key_number == 0:
                game.left_btn_is_down = True

        else:
            print("released", event)
            if event.key_number == 1:
                game.right_btn_is_down = False
                game.right_arrow_btn_event()
            elif event.key_number == 0:
                game.left_btn_is_down = False
                game.left_arrow_btn_event()

            elif event.key_number == 2:  # A button
                game.a_btn_event()
            elif event.key_number == 3:  # B button
                game.b_btn_event()
            elif event.key_number == 4:  # B button
                game.y_btn_event()


    game.tick()
