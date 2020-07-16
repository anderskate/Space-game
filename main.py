import time
import asyncio
import curses
import random
import itertools

from curses_tools import (
    draw_frame,
    read_controls,
    get_frame_size,
)

from physics import update_speed

from obstacles import show_obstacles, Obstacle

from explosion import explode

from game_scenario import get_garbage_delay_tics, PHRASES


TIC_TIMEOUT = 0.1

YEAR_CREATION_LASER_GUN = 2020

DEBUG_MODE = False

coroutines = []

obstacles = []

obstacles_in_last_collisions = []

spaceship_frame = ''

row_speed, column_speed = (0, 0)

year = 1957


async def count_years():
    """Count years passed."""
    global year
    while True:
        year += 1
        await sleep(2)


async def display_info_about_the_current_year(canvas):
    """Display current year information."""
    global year

    while True:
        try:
            draw_frame(canvas, 0, 0, f'Year - {year}: {PHRASES[year]}')
        except KeyError:
            try:
                draw_frame(
                    canvas,
                    0,
                    0,
                    f'Year - {year - 1}: {PHRASES[year - 1]}',
                    negative=True
                )
            except KeyError:
                pass
            draw_frame(canvas, 0, 0, f'Year - {year}')
        await asyncio.sleep(0)


async def show_gameover(canvas):
    """Display the end of the game."""
    gameover_frame = get_frame('gameover.txt')
    canvas_height, canvas_width = canvas.getmaxyx()
    center_row, center_column = (canvas_height // 4, canvas_width // 4)
    while True:
        draw_frame(canvas, center_row, center_column, gameover_frame)
        await asyncio.sleep(0)


async def sleep(tics=1):
    """Implement a wait before executing other coroutines."""
    for _ in range(tics):
        await asyncio.sleep(0)


async def animate_spaceship(frames):
    """Define the current frame for a spaceship.

    Params:
        * frames: tuple with images of a spaceship
    """
    global spaceship_frame
    while True:
        for frame in itertools.cycle(frames):
            spaceship_frame = frame
            await sleep()


async def run_spaceship(canvas, row, column):
    """Determine the position of the spaceship and display it.

    Params:
        * canvas: window object from curses
        * row: number of row
        * column: number of column
    """

    # Define height and width of the canvas
    canvas_height, canvas_width = canvas.getmaxyx()

    global spaceship_frame, row_speed, column_speed, year

    while True:
        # Define height and width of the frame
        frame_height, frame_width = get_frame_size(spaceship_frame)
        rows_direction, columns_direction, space_pressed = read_controls(
            canvas
        )

        row_speed, column_speed = update_speed(
            row_speed,
            column_speed,
            rows_direction,
            columns_direction,
        )

        # Subtract 1 so as not to erase the borders
        row_number = min(
            row + row_speed,
            canvas_height - frame_height - 1,
        )
        column_number = min(
            column + column_speed,
            canvas_width - frame_width - 1,
        )

        # Set 1 so as not to erase the borders
        if row + row_speed > 0:
            row = row_number
        else:
            row = 1

        if column + column_speed > 0:
            column = column_number
        else:
            column = 1

        # Make a gun shot if the user presses a space
        # and a year 2020 or more
        if space_pressed and year >= YEAR_CREATION_LASER_GUN:
            fire_coroutine = fire(canvas, row, column, rows_speed=-2)
            coroutines.append(fire_coroutine)

        draw_frame(canvas, row, column, spaceship_frame)
        # Stores the last frame of the animation that was drawn,
        # and which you want to erase later
        last_frame = spaceship_frame
        await sleep()
        draw_frame(canvas, row, column, last_frame, negative=True)

        for obstacle in obstacles:
            if obstacle.has_collision(row, column):
                gameover_coroutine = show_gameover(canvas)
                coroutines.append(gameover_coroutine)
                return


async def fire(canvas, start_row, start_column, rows_speed=-0.3,
               columns_speed=0):
    """Display animation of gun shot. Direction and speed can be specified."""

    row, column = start_row, start_column

    canvas.addstr(round(row), round(column), '*')
    await asyncio.sleep(0)

    canvas.addstr(round(row), round(column), 'O')
    await asyncio.sleep(0)
    canvas.addstr(round(row), round(column), ' ')

    row += rows_speed
    column += columns_speed

    symbol = '-' if columns_speed else '|'

    rows, columns = canvas.getmaxyx()
    max_row, max_column = rows - 1, columns - 1

    curses.beep()

    while 0 < row < max_row and 0 < column < max_column:
        canvas.addstr(round(row), round(column), symbol)
        await asyncio.sleep(0)

        # Check for a collision of fire with an obstacle
        for obstacle in obstacles:
            if obstacle.has_collision(row, column):
                obstacles_in_last_collisions.append(obstacle)
                return

        canvas.addstr(round(row), round(column), ' ')
        row += rows_speed
        column += columns_speed


async def blink(canvas, row, column, symbol='*', offset_tics=0):
    """Display animation of blink star.

    Params:
        * canvas: window object from curses
        * row: number of row
        * column: number of column
        * symbol: determines the type of star
        * offset_tics: delay before starting animation. So that the stars
        do not flicker at the same time
    """
    await sleep(offset_tics)

    while True:
        canvas.addstr(row, column, symbol, curses.A_DIM)
        await sleep(20)

        canvas.addstr(row, column, symbol)
        await sleep(3)

        canvas.addstr(row, column, symbol, curses.A_BOLD)
        await sleep(5)

        canvas.addstr(row, column, symbol)
        await sleep(3)


async def fill_orbit_with_garbage(canvas, canvas_width, trash_frames):
    """Add random garbage to canvas"""
    global year
    while True:
        garbage_frequency = get_garbage_delay_tics(year)
        if garbage_frequency:
            random_frame = random.choice(trash_frames)
            _, frame_width = get_frame_size(random_frame)

            # To prevent garbage from flying outside the borders,
            # subtract 1 for the border and frame width
            random_column = random.randint(1, canvas_width - frame_width - 1)

            coroutines.append(fly_garbage(canvas, random_column, random_frame))
            await sleep(garbage_frequency)
        else:
            await asyncio.sleep(0)


async def fly_garbage(canvas, column, garbage_frame, speed=0.5):
    """Animate garbage, flying from top to bottom.

    Сolumn position will stay same, as specified on start.
    """
    global obstacles

    rows_number, columns_number = canvas.getmaxyx()

    column = max(column, 0)
    column = min(column, columns_number - 1)

    row = 0

    frame_height, frame_width = get_frame_size(garbage_frame)
    obstacle = Obstacle(row, column, frame_height, frame_width)
    obstacles.append(obstacle)

    await sleep(1)
    while row < rows_number:
        draw_frame(canvas, row, column, garbage_frame)
        await asyncio.sleep(0)
        draw_frame(canvas, row, column, garbage_frame, negative=True)
        row += speed
        obstacle.row += speed

        # Remove garbage that has encountered fire
        if obstacle in obstacles_in_last_collisions:
            obstacles_in_last_collisions.remove(obstacle)
            obstacles.remove(obstacle)
            await explode(canvas, row, column)
            return

    # Remove an obstacle flying over the edge
    obstacles.remove(obstacle)


def create_stars(canvas, canvas_height, canvas_width, count=50):
    """Create a stars with random coordinates."""
    symbols = '+*.:'
    stars = []

    for _ in range(count):
        random_symbol = random.choice(symbols)
        random_x = random.randint(1, canvas_height - 1)
        random_y = random.randint(1, canvas_width - 1)
        time_offset = random.randint(0, 30)

        new_star = blink(
            canvas,
            random_x,
            random_y,
            random_symbol,
            time_offset,
        )
        stars.append(new_star)

    return stars


def get_frame(file):
    """Load animation frame from the file."""
    with open(file, 'r') as file:
        frame = file.read()
    return frame


def draw(canvas):
    """The main function of displaying all elements on the canvas."""
    global coroutines, obstacles

    canvas.border()
    canvas.nodelay(True)
    curses.curs_set(False)
    canvas_height, canvas_width = canvas.getmaxyx()
    window_center_coordinates = (canvas_height // 2, canvas_width // 2)

    canvas_for_phrase = canvas.derwin(canvas_height - 2, canvas_width // 2)

    coroutine_fire = fire(canvas, *window_center_coordinates)
    coroutines.append(coroutine_fire)

    coroutines += create_stars(canvas, canvas_height, canvas_width, 100)

    frames = (
        get_frame('rocket_frame_1.txt'),
        get_frame('rocket_frame_2.txt'),
    )
    trash_frames = (
        get_frame('duck.txt'),
        get_frame('hubble.txt'),
        get_frame('lamp.txt'),
        get_frame('trash_large.txt'),
        get_frame('trash_small.txt'),
        get_frame('trash_xl.txt'),
    )

    center_row_of_canvas = canvas_height // 2
    center_column_of_canvas = canvas_width // 2

    animate_spaceship_coroutine = animate_spaceship(frames)
    coroutines.append(animate_spaceship_coroutine)

    control_spaceship_coroutine = run_spaceship(
        canvas,
        center_row_of_canvas,
        center_column_of_canvas,
    )
    coroutines.append(control_spaceship_coroutine)

    fill_orbit_with_garbage_coroutine = fill_orbit_with_garbage(
        canvas,
        canvas_width,
        trash_frames,
    )
    coroutines.append(fill_orbit_with_garbage_coroutine)

    if DEBUG_MODE:
        obstacles_coroutine = show_obstacles(canvas, obstacles)
        coroutines.append(obstacles_coroutine)

    count_years_coroutine = count_years()
    coroutines.append(count_years_coroutine)

    year_info_coroutine = display_info_about_the_current_year(
        canvas_for_phrase
    )
    coroutines.append(year_info_coroutine)

    while True:
        for coroutine in coroutines.copy():
            try:
                coroutine.send(None)
            except StopIteration:
                coroutines.remove(coroutine)

        canvas.refresh()
        time.sleep(TIC_TIMEOUT)


def main():
    curses.update_lines_cols()
    curses.wrapper(draw)


if __name__ == '__main__':
    main()
