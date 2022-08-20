import gc
import random

import displayio
import time
import adafruit_imageload
import terminalio
from adafruit_display_text.bitmap_label import Label
from adafruit_progressbar.horizontalprogressbar import (
    HorizontalProgressBar,
    HorizontalFillDirection,
)
import vectorio

from displayio_listselect import ListSelect


class SpaceMinerGame(displayio.Group):
    ROUND_TIME = 20

    FRAME_DELAY = 0.001 / 2
    print(FRAME_DELAY)

    STATE_WAITING_TO_PLAY = 0
    STATE_PLAYING = 1
    STATE_GAME_OVER = 2
    STATE_SHOP = 3

    def __init__(self, display_size, display):
        super().__init__()
        self.display = display
        self.display_size = display_size
        self.CURRENT_STATE = SpaceMinerGame.STATE_WAITING_TO_PLAY
        self.round_start_time = -1.0
        self.round_score = 0
        self.total_score = 0
        self.ore_spawn_rate = -1.0
        self.ore_spawn_health = 1
        self.last_ore_spawn_time = -1.0
        self.ores_missed = 0
        self.round_collected_ore = 0
        self.total_collected_ore = 0

        self.health_progress_bar = None

        self.stats = {
            "laser_power": 1,
            "ship_health": 100
        }

        # round end GUI
        self.round_end_group = displayio.Group()
        self.round_end_lbl = Label(terminalio.FONT, text="",
                                   anchor_point=(0.5, 0.5),
                                   anchored_position=(display_size[0] // 2, display_size[1] // 2),
                                   color=0xFFFFFF, scale=2, background_color=0x00000)

        self.round_end_group.hidden = True
        self.round_end_group.append(self.round_end_lbl)
        self.append(self.round_end_group)

        # upgrade shop GUI
        self.shop_group = displayio.Group()
        bg_palette = displayio.Palette(1)
        bg_palette[0] = 0x333333
        self.shop_bg = vectorio.Rectangle(pixel_shader=bg_palette,
                                          width=display_size[0], height=display_size[1],
                                          x=0, y=0)
        self.shop_group.append(self.shop_bg)

        self.shop_items = ["Laser Power", "Ship Health"]
        self.shop_list_select = ListSelect(
            scale=2,
            items=self.shop_items
        )
        self.shop_group.append(self.shop_list_select)
        self.shop_group.hidden = True
        self.shop_list_select.anchor_point = (0.5, 0.5)
        self.shop_list_select.anchored_position = (self.display_size[0] // 2, self.display_size[1] // 2)

        self.shop_lbl = Label(terminalio.FONT, scale=2, text="", anchor_point=(0.5, 0.0),
                              anchored_position=(self.display_size[0] // 2, 10))
        self.shop_group.append(self.shop_lbl)
        self.append(self.shop_group)

        self.setup_health_progress_bar()

        self.ship = Ship(display_size)
        self.ship.y = display_size[1] - self.ship.height
        self.append(self.ship)

        self.lasers = []
        self.ores = []

        # Setup laser sprites
        #self.blue_laser = displayio.OnDiskBitmap("blue_laser.bmp")
        #self.lasers.append(displayio.TileGrid(self.blue_laser, pixel_shader=self.blue_laser.pixel_shader))
        #self.blue_laser.pixel_shader.make_transparent(0)
        # self.lasers.append(displayio.TileGrid(self.blue_laser, pixel_shader=self.blue_laser.pixel_shader))

        self.blue_laser, self.blue_laser_palette = adafruit_imageload.load("blue_laser.bmp")
        self.blue_laser_palette.make_transparent(0)
        self.lasers.append(displayio.TileGrid(self.blue_laser, pixel_shader=self.blue_laser_palette))

        self.lasers[0].hidden = True

        for laser in self.lasers:
            # self.append(laser)
            self.insert(0, laser)

        self.last_update_time = 0

        self.left_btn_is_down = False
        self.right_btn_is_down = False

    def setup_health_progress_bar(self):
        if self.health_progress_bar is not None:
            self.remove(self.health_progress_bar)
            self.health_progress_bar = None
            gc.collect()

        HEALTH_PROGRESS_WIDTH = 80
        HEALTH_PROGRESS_HEIGHT = 8
        self.health_progress_bar = HorizontalProgressBar(
            (self.display_size[0] - 80, 0), (HEALTH_PROGRESS_WIDTH, HEALTH_PROGRESS_HEIGHT),
            direction=HorizontalFillDirection.LEFT_TO_RIGHT,
            max_value=self.stats["ship_health"], value=self.stats["ship_health"],
            border_thickness=0
        )

        self.append(self.health_progress_bar)

    def left_arrow_btn_event(self):
        if self.CURRENT_STATE == SpaceMinerGame.STATE_PLAYING:
            self.ship.left_arrow_btn_event()
        if self.CURRENT_STATE == SpaceMinerGame.STATE_SHOP:
            self.shop_list_select.move_selection_up()

    def right_arrow_btn_event(self):
        if self.CURRENT_STATE == SpaceMinerGame.STATE_PLAYING:
            self.ship.right_arrow_btn_event()
        if self.CURRENT_STATE == SpaceMinerGame.STATE_SHOP:
            self.shop_list_select.move_selection_down()

    def b_btn_event(self):
        if self.CURRENT_STATE != SpaceMinerGame.STATE_PLAYING:
            self.round_end_group.hidden = True
            self.reset_round()
            self.CURRENT_STATE = SpaceMinerGame.STATE_PLAYING
            self.start_round(1.0, 1)

    def y_btn_event(self):
        if self.CURRENT_STATE != SpaceMinerGame.STATE_PLAYING:
            if not self.round_end_group.hidden:
                self.round_end_group.hidden = True
                self.show_shop()
            else:
                self.round_end_group.hidden = False
                self.shop_group.hidden = True
                self.CURRENT_STATE = SpaceMinerGame.STATE_WAITING_TO_PLAY

    def a_btn_event(self):
        if self.CURRENT_STATE == SpaceMinerGame.STATE_PLAYING:
            index = self.first_availabe_laser_index
            if index is not None:
                # fire a laser
                self.lasers[index].x = self.ship.x + self.ship.width // 2
                self.lasers[index].y = self.ship.y - 1
                self.lasers[index].hidden = False

        if self.CURRENT_STATE == SpaceMinerGame.STATE_SHOP:
            print("click buy ")
            if self.shop_list_select.selected_item == "Laser Power":
                if self.total_collected_ore >= 10:
                    self.total_collected_ore -= 10
                    self.stats["laser_power"] += 1
                    self.update_shop_label()
            elif self.shop_list_select.selected_item == "Ship Health":
                if self.total_collected_ore >= 5:
                    self.total_collected_ore -= 5
                    self.stats["ship_health"] += 1
                    self.update_shop_label()

    def update_shop_label(self):
        self.shop_lbl.text = f"ORE: {self.total_collected_ore}\nLP: {self.stats['laser_power']} | HP: {self.stats['ship_health']}"

    def show_shop(self):
        self.shop_group.hidden = False
        self.CURRENT_STATE = SpaceMinerGame.STATE_SHOP
        self.update_shop_label()

    @property
    def first_availabe_laser_index(self):
        for index, laser in enumerate(self.lasers):
            if laser.hidden == True:
                return index

        return None

    # def rect_collision(self, rect_1_x, rect_1_y, rect_1_width, rect_1_height, rect_2_x, rect_2_y, rect_2_width,
    #                    rect_2_height):
    #     if rect_1_x < rect_2_x + rect_1_width and \
    #             rect_1_x + rect_2_width > rect_2_x and \
    #             rect_1_y < rect_2_y + rect_1_height and \
    #             rect_1_height + rect_1_y > rect_2_y:
    #         return True
    #     return False

    def point_in_rect(self, point, rect):
        if rect[0] < point[0] < rect[0] + rect[2] and \
                rect[1] < point[1] < rect[1] + rect[3]:
            return True
        return False

    def laser_collision(self, ore, laser):
        laser_center = (laser.x + laser.tile_width // 2, laser.y + laser.tile_height // 2)
        # print(f"laser_center: {laser_center}")
        if self.point_in_rect(laser_center, (ore.x, ore.y, ore.width, ore.height)):
            return True

        return False

    def ship_collision(self, ore):
        ore_bottom_center = (ore.x + ore.width // 2, ore.y + ore.height)
        if self.point_in_rect(ore_bottom_center, (self.ship.x, self.ship.y, self.ship.width, self.ship.height)):
            return True

        return False

    def start_round(self, ore_spawn_rate, ore_health):
        self.round_start_time = time.monotonic()
        self.ore_spawn_rate = ore_spawn_rate
        self.ore_spawn_health = ore_health

    @property
    def first_available_ore(self):
        for ore in self.ores:
            if ore.hidden:
                return ore

        return None

    def spawn_ore(self, ore_health):

        print(f"len: {len(self.ores)}")
        self.last_ore_spawn_time = time.monotonic()

        _new_ore = self.first_available_ore

        if _new_ore is None:
            # setup ore sprites
            _new_ore = Ore(self.display_size, ore_health)
            self.ores.append(_new_ore)
            self.insert(0, _new_ore)
        else:
            _new_ore.health = ore_health
        _new_ore.y = 0
        _new_ore.x = random.randint(0, self.display_size[0] - _new_ore.width)
        _new_ore.hidden = False

    def update_round_end_info(self):
        self.round_score -= self.ores_missed
        self.total_score += self.round_score
        self.total_collected_ore += self.round_collected_ore
        self.round_end_lbl.text = f"ore: {self.round_collected_ore}\nores_missed: {self.ores_missed}\nround score: {self.round_score}\nTotal score: {self.total_score}"

    def reset_round(self):
        self.round_collected_ore = 0
        self.ores_missed = 0
        self.round_score = 0
        self.ship.health = self.stats["ship_health"]
        self.setup_health_progress_bar()

        for ore in self.ores:
            ore.hidden = True
            print("hiding ore")
        self.round_start_time = -1.0
        self.last_ore_spawn_time = -1.0
        self.round_end_lbl.text = ""

    def tick(self):

        now = time.monotonic()
        if self.CURRENT_STATE == SpaceMinerGame.STATE_PLAYING:

            if now <= self.round_start_time + SpaceMinerGame.ROUND_TIME:

                if now > self.last_update_time + self.FRAME_DELAY:

                    # print("Updating now")
                    self.last_update_time = now
                    if self.right_btn_is_down:
                        self.right_arrow_btn_event()

                    if self.left_btn_is_down:
                        self.left_arrow_btn_event()

                    # move all lasers
                    for laser in self.lasers:
                        if laser.hidden == False:
                            if laser.y > 0:
                                laser.y -= 1
                            else:
                                laser.hidden = True

                    # move ores

                    for ore in self.ores:
                        if ore.hidden == False:
                            ore.tick(now, self)

                            # check collision between laser and ore
                            for laser in self.lasers:
                                if laser.hidden == False:

                                    # if self.rect_collision(ore.x, ore.y, ore.width, ore.height, laser.x, laser.y,
                                    #                        laser.tile_width, laser.tile_height):
                                    # if ore.x < laser.x < ore.x + ore.width and laser.y < ore.y + ore.height:

                                    if self.laser_collision(ore, laser):
                                        self.round_score += 1

                                        ore.health -= self.stats["laser_power"]
                                        if ore.health <= 0:
                                            print(f'captured ore {ore.y} - {laser.y} ')
                                            self.round_score += 3

                                        laser.hidden = True
                                        ore.hidden = True
                                        ore.y = 0
                                        self.round_collected_ore += 1

                            # check collision between ore and ship
                            if self.ship_collision(ore):
                                self.ship.health -= 25
                                self.health_progress_bar.value = self.ship.health
                                self.round_score -= 3
                                self.ores_missed += 1
                                if self.ship.health <= 0:
                                    self.CURRENT_STATE = SpaceMinerGame.STATE_GAME_OVER
                                    self.update_round_end_info()
                                    self.round_end_group.hidden = False
                                    print("Game Over")

                                ore.hidden = True
                                ore.y = 0

                    if now > self.last_ore_spawn_time + (1.0 / self.ore_spawn_rate):
                        self.spawn_ore(self.ore_spawn_health)





            else:  # round end
                self.update_round_end_info()
                self.round_end_group.hidden = False
                print(self.round_end_lbl.text)

                self.CURRENT_STATE = SpaceMinerGame.STATE_WAITING_TO_PLAY


class Ore(displayio.Group):
    ORE_UPDATE_DELAY = 0.01 / 2

    def __init__(self, display_size, health):
        super().__init__()
        self.display_size = display_size
        self.moving_left = False
        self.last_update_time = 0
        self.health = health

        # Setup the file as the bitmap data source
        # self.ore_bitmap = displayio.OnDiskBitmap("grey_ore_0.bmp")
        # self.ore_bitmap.pixel_shader.make_transparent(0)
        # self.ore_tilegrid = displayio.TileGrid(self.ore_bitmap, pixel_shader=self.ore_bitmap.pixel_shader)

        self.ore_bitmap, self.ore_bitmap_palette = adafruit_imageload.load("grey_ore_0.bmp")
        self.ore_bitmap_palette.make_transparent(0)
        self.ore_tilegrid = displayio.TileGrid(self.ore_bitmap, pixel_shader=self.ore_bitmap_palette)

        self.hidden = True
        self.append(self.ore_tilegrid)

    @property
    def next_update_time(self):
        return self.last_update_time + self.ORE_UPDATE_DELAY

    def tick(self, now, game_obj):

        if now > self.next_update_time:
            self.last_update_time = now
            if self.moving_left:
                if self.x > 0:
                    self.x -= 1
                else:
                    self.moving_left = False

            else:  # right

                if self.x < self.display_size[0] - self.width:
                    self.x += 1
                else:
                    self.moving_left = True

            if self.y < self.display_size[1]:
                self.y += 1
            else:
                self.hidden = True
                game_obj.ores_missed += 1
                self.y = 0

    @property
    def width(self):
        return self.ore_bitmap.width

    @property
    def height(self):
        return self.ore_bitmap.height


class Ship(displayio.Group):
    STARTING_HEALTH = 100

    def __init__(self, display_size):
        super().__init__()

        self.health = Ship.STARTING_HEALTH

        self.display_size = display_size

        # Setup the file as the bitmap data source
        #self.ship_bitmap = displayio.OnDiskBitmap("ship.bmp")

        # Create a TileGrid to hold the bitmap
        # tile_grid = displayio.TileGrid(self.ship_bitmap, pixel_shader=self.ship_bitmap.pixel_shader)
        # self.ship_bitmap.pixel_shader.make_transparent(0)

        self.ship_bitmap, self.ship_palette = adafruit_imageload.load("ship.bmp")
        self.ship_palette.make_transparent(0)
        tile_grid = displayio.TileGrid(self.ship_bitmap, pixel_shader=self.ship_palette)
        self.append(tile_grid)

    def left_arrow_btn_event(self):
        if self.x > 0:
            self.x -= 1

    def right_arrow_btn_event(self):
        if self.x < self.display_size[0] - self.width:
            self.x += 1

    def a_btn_event(self):
        pass

    @property
    def height(self):
        return self.ship_bitmap.height

    @property
    def width(self):
        return self.ship_bitmap.width
