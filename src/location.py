class Location:
    Self = 'Location'

    def __init__(self, index: int, row: int, col: int):
        self.index = index
        self.row = row
        self.col = col

    def next(self, char: str) -> Self:
        if char == '\n':
            return self.next_row()
        # elif char == '\t':
        #     return Location(self.index + 1, self.row, self.col + 4)
        else:
            return self.next_col()

    def next_row(self) -> Self:
        return Location(self.index + 1, self.row + 1, 1)

    def next_col(self, count=1) -> Self:
        return Location(self.index + count, self.row, self.col + count)

    def __repr__(self):
        return f'Location(index={self.index}, row={self.row}, col={self.col})'
