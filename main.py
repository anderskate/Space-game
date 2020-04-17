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

from space_garbage import fly_garbage


TIC_TIMEOUT = 0.1

coroutines = []


async def sleep(tics=1):
    """Implement a wait before executing other coroutines."""
    for _ in range(tics):
        await asyncio.sleep(0)


async def animate_spaceship(canvas, row, column, frames):
    """Determine the position of the spaceship and display it.

    Params:
        * canvas: window object from curses
        * row: number of row
        * column: number of column
        * frames: tuple with images of a spaceship
    """

    # Define height and width of the canvas
    canvas_height, canvas_width = canvas.getmaxyx()

    while True:
        for frame in itertools.cycle(frames):
            # Define height and width of the frame
            frame_height, frame_width = get_frame_size(frame)
            rows_direction, columns_direction, _ = read_controls(canvas)

            # Subtract 1 so as not to erase the borders
            row_number = min(
                row + rows_direction,
                canvas_height - frame_height - 1,
            )
            column_number = min(
                column + columns_direction,
                canvas_width - frame_width - 1,
            )

            # Set 1 so as not to erase the borders
            if row + rows_direction > 0:
                row = row_number
            else:
                row = 1

            if column + columns_direction > 0:
                column = column_number
            else:
                column = 1

            draw_frame(canvas, row, column, frame)
            await sleep()
            draw_frame(canvas, row, column, frame, negative=True)


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
    while True:
        random_frame = random.choice(trash_frames)
        _, frame_width = get_frame_size(random_frame)

        # To prevent garbage from flying outside the borders,
        # subtract 1 for the border and frame width
        random_column = random.randint(1, canvas_width - frame_width - 1)

        coroutines.append(fly_garbage(canvas, random_column, random_frame))
        await sleep(10)


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
    canvas.border()
    canvas.nodelay(True)
    curses.curs_set(False)
    canvas_height, canvas_width = canvas.getmaxyx()
    window_center_coordinates = (canvas_height // 2, canvas_width // 2)

    global coroutines

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
    control_spaceship_coroutine = animate_spaceship(
        canvas,
        center_row_of_canvas,
        center_column_of_canvas,
        frames,
    )
    coroutines.append(control_spaceship_coroutine)

    fill_orbit_with_garbage_coroutine = fill_orbit_with_garbage(
        canvas,
        canvas_width,
        trash_frames,
    )
    coroutines.append(fill_orbit_with_garbage_coroutine)

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
