import math

from location import Location


def surrounding_lines_of(source, begin: Location) -> tuple[str, str, str]:
    idx = begin.index

    def find_line_bounds(index: int) -> tuple[int, int]:
        start = index
        while start > 0 and source[start - 1] != '\n':
            start -= 1
        end = index
        while end < len(source) and source[end] != '\n':
            end += 1
        return start, end

    # Current line
    curr_start, curr_end = find_line_bounds(idx)
    current_line = source[curr_start:curr_end]

    # Previous line
    prev_line = ""
    if curr_start > 0:
        prev_end = curr_start - 1  # skip the newline
        prev_start = prev_end
        while prev_start > 0 and source[prev_start - 1] != '\n':
            prev_start -= 1
        prev_line = source[prev_start:prev_end]

    # Next line
    next_line = ""
    if curr_end < len(source):
        next_start = curr_end + 1 if source[curr_end] == '\n' else curr_end
        next_end = next_start
        while next_end < len(source) and source[next_end] != '\n':
            next_end += 1
        next_line = source[next_start:next_end]

    return prev_line, current_line, next_line


def error(path, source, begin: Location, end: Location, message: str):
    header = f'{path}:{begin.row}:{begin.col}: [ERROR]: '
    before, current, after = surrounding_lines_of(source, begin)
    source  = f'  {begin.row-1:02} | ' + before + '\n'
    source += f'  {begin.row+0:02} | ' + current + '\n'
    source += f'  {" " * max(2, int(math.log10(begin.row)))} | ' + '-' * (begin.col - 1) + '^' * max(1, end.col - begin.col) + '\n'
    source += f'  {begin.row+1:02} | ' + after + '\n'
    return RuntimeError(header + message + source)