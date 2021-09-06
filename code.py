
import board
import time
import displayio
from adafruit_magtag.magtag import MagTag
import adafruit_imageload


magtag = MagTag()

# connect to wifi to get that sweet, sweet time
try:
	magtag.network.connect()
	magtag.get_local_time()
	now = time.localtime()
	
except (ConnectionError, ValueError, RuntimeError) as e:
	magtag.exit_and_deep_sleep(600)


# 1. how often would you like to refresh, in hours?
refresh_every_hours = 12

# 2. what hour of the day would you like to refresh(es) to start? 
# starts at midnight by default. helpful if you want fewer per day, starting at specific times
refresh_start_hour = 0
refresh_start = time.mktime((now[0], now[1], now[2], 0, int(refresh_start_hour * 60), 0, now[6], now[7], now[8]))

# 3. how many hours ahead of the current phase should the magtag display?
# eg; if it refreshes once at midnight, what phase do you want it to display for the coming day (until the next midnight)?
display_phase_offset_hours = 12

# May 11, 2021 19:00 GMT is the reference for the start of the cycle (arbitrary, pick any new moon you'd like)
# https://tidesandcurrents.noaa.gov/moon_phases.shtml?year=2021&data_type=monMay
# (tm_year, tm_mon, tm_mday, tm_hour, tm_min, tm_sec, tm_wday, tm_yday, tm_isdst)
new_moon_reference = time.mktime((2021, 5, 11, 19, 0, 0, -1, -1, -1))


# lunar constants
lunar_cycle_days = 29.53058770576
lunar_cycle_secs = lunar_cycle_days * 24 * 60 * 60


# get the next refresh time
refresh_cycles = 24 // refresh_every_hours

for i in range(refresh_cycles):
	refresh_next = refresh_start + int(i  * refresh_every_hours * 60 * 60)
	if refresh_next > time.time():
		break

# turn all these seconds into 0–1 phase value
# 0 = new, 0.25 = first quarter, 0.5 = full, 0.75 = third quarter, 1 = new
next_phase = refresh_next + (display_phase_offset_hours * 60 * 60) - new_moon_reference
phase = (next_phase % lunar_cycle_secs) / lunar_cycle_secs
print("Displaying phase:", phase)


# ui
moon_group = displayio.Group()
date_group = displayio.Group()
display_group = displayio.Group()

date_sprite_tile_index = now[2] - 1
date_group.y = 79

num_tiles = 30
num_tiles_row = 15


# determine the tile indeces to display for each moon half
# ugly! full of magic pixel numbers! please forgive me! i guess?

# it is waxing my dude
if phase <= 0.5:
	# position the date to the left and moon to the right
	moon_group.x = -225 + int(phase * 2 * num_tiles_row) * 14	
	date_group.x = -148 // 2

	# new to first quarter
	if phase <= 0.25:
		moon_left_tile_index = 0
		moon_right_tile_index = int(phase * 4 * num_tiles_row)

	# first quarter to full
	else:
		tile_index = int((phase - 0.25) * 4 * num_tiles_row)

		if tile_index == 0:
			moon_left_tile_index = 0
		else:
			moon_left_tile_index = num_tiles - tile_index
		moon_right_tile_index = 15

# it is waning my dude
else:
	# position the date to the right and moon to the left
	moon_group.x = -196 + int((phase - 0.5) * 2 * num_tiles_row) * 14
	date_group.x = 296 - 148 // 2

	# half to third quarter
	if phase <= 0.75:
		moon_left_tile_index = num_tiles_row
		tile_index = num_tiles_row + int((phase - 0.5) * 4 * num_tiles_row)
		# wrap back to the first index, 0
		if tile_index > num_tiles:
			tile_index = 0
		moon_right_tile_index = tile_index

	# third quarter to new
	else:
		moon_left_tile_index = num_tiles_row - int((phase - 0.75) * 4 * num_tiles_row)
		moon_right_tile_index = 0


# ui images, palettes
phase_image, moon_palette = adafruit_imageload.load(
	"/img/moon-phases.bmp", 
	bitmap = displayio.Bitmap, 
	palette = displayio.Palette)
date_image, date_palette = adafruit_imageload.load(
	"/img/date-segments.bmp", 
	bitmap = displayio.Bitmap, 
	palette = displayio.Palette)

moon_palette = displayio.Palette(4)
moon_palette[0] = 0XFFFFFF
moon_palette[1] = 0XAAAAAA
moon_palette[2] = 0X555555
moon_palette[3] = 0X000000

date_palette.make_transparent(3)


# tiles
tile_wh = 1
phase_width = 246
phase_height = 128

moon_left = displayio.TileGrid(
	phase_image, 
	pixel_shader = moon_palette,
	width = tile_wh,
	height = tile_wh,
	tile_width = phase_width,
	tile_height = phase_height,
	default_tile = moon_left_tile_index)

moon_right = displayio.TileGrid(
	phase_image, 
	pixel_shader = moon_palette,
	width = tile_wh,
	height = tile_wh,
	tile_width = phase_width,
	tile_height = phase_height,
	default_tile = moon_right_tile_index)

date_sprite = displayio.TileGrid(
	date_image, 
	pixel_shader = date_palette,
	width = tile_wh,
	height = tile_wh,
	tile_width = 148,
	tile_height = 48,
	default_tile = date_sprite_tile_index)


# magic flip of the left side happens
moon_left.flip_x = True
moon_right.x = phase_width


# final grouping
moon_group.append(moon_left)
moon_group.append(moon_right)
date_group.append(date_sprite)
display_group.append(moon_group)
display_group.append(date_group)


# drawlring the whole thing to the display
display = board.DISPLAY
display.show(display_group)
time.sleep(2)
display.refresh()


# zzzzzzzzzzzz
secs_until_refresh = refresh_next - time.time()
print("Sleeping for about", secs_until_refresh // 60, "minutes")
magtag.exit_and_deep_sleep(secs_until_refresh)
