from ir import Op, Block, Function
from type import *


class State(Enum):
    OWNING = auto()
    MOVED = auto()
    SHARED_BORROWING = auto()
    SHARED_BORROWED = auto()
    EXCLUSIVELY_BORROWING = auto()
    EXCLUSIVELY_BORROWED = auto()


class BorrowChecker:
    def __init__(self, functions, data, constants, user_types):
        self.functions = functions
        self.data = data
        self.constants = constants
        self.user_types = user_types
        self.state = {}
        self.successors = {}

    @staticmethod
    def check(module):
        functions = module.functions
        data = module.data
        constants = module.constants
        user_types = module.types
        self = BorrowChecker(functions, data, constants, user_types)
        return self.check_()

    def has_later_use(self, block, offset, var):
        for code in block.instructions[offset:]:
            if var in code.refs:
                return True
        return False

    def check_block(self, block, state):
        """Check a single block for borrow errors"""
        for i, code in enumerate(block.instructions):
            if code.op == Op.MOVE:
                dst = code.dest
                src = code.refs[0]

                # Check if the source is in a state that doesn't allow moving
                if state[src][0] == State.MOVED:
                    return f"'{dst}' cannot move '{src}'; '{src}' is already moved to '{state[src][1]}'"
                if state[src][0] == State.EXCLUSIVELY_BORROWED:
                    return f"'{dst}' cannot move '{src}'; '{src}' is exclusively borrowed by '{state[src][1]}'"
                if state[src][0] == State.SHARED_BORROWED:
                    return f"'{dst}' cannot move '{src}'; '{src}' is shared borrowed by '{state[src][1]}'"

                # Check if the source is borrowed by another variable
                # for name, (status, var) in state.items():
                #     if status == State.EXCLUSIVELY_BORROWED and var == src:
                #         return f"Cannot move '{src}' while it is exclusively borrowed by '{name}'"
                #     if status == State.SHARED_BORROWED and var == src:
                #         return f"Cannot move '{src}' while it is shared borrowed by '{name}'"

                state[dst] = (State.OWNING, src)
                state[src] = (State.MOVED, dst)
            elif code.op == Op.BRW:
                dst = code.dest
                src = code.refs[0]

                # Check if the source is in a state that doesn't allow shared borrowing
                if state[src][0] == State.MOVED:
                    return f"'{dst}' cannot share borrow '{src}'; '{src}' was moved to '{state[src][1]}'"
                if state[src][0] == State.EXCLUSIVELY_BORROWED:
                    return f"'{dst}' cannot share borrow '{src}'; '{src}' is exclusively borrowed from '{state[src][1]}'"

                state[dst] = (State.SHARED_BORROWING, src)
                state[src] = (State.SHARED_BORROWED,  dst)
            elif code.op == Op.REF:
                dst = code.dest
                src = code.refs[0]

                # Check if the source is in a state that doesn't allow immutable borrowing
                if state[src][0] == State.MOVED and self.has_later_use(block, i+1, state[src][1]):
                    return f"'{dst}' cannot mutably borrow moved value '{src}'; '{src}' was moved from '{state[src][1]}'"
                if state[src][0] == State.SHARED_BORROWED and self.has_later_use(block, i+1, state[src][1]):
                    return f"'{dst}' cannot mutably borrow '{src}'; '{src}' already shared borrowed by '{state[src][1]}'"
                if state[src][0] == State.EXCLUSIVELY_BORROWED and self.has_later_use(block, i+1, state[src][1]):
                    return f"'{dst}' cannot mutably borrow '{src}'; '{src}' already exclusively borrowed by '{state[src][1]}'"

                state[dst] = (State.EXCLUSIVELY_BORROWING, src)
                state[src] = (State.EXCLUSIVELY_BORROWED,  dst)
            else:
                for ref in code.refs:
                    if ref in state:
                        if state[ref][0] == State.MOVED:
                            return f"Cannot use moved value '{ref}', it was moved to '{state[ref][1]}'"
                state[code.dest] = (State.OWNING, None)

        return None

    def dfs(self, name: str, block: Block, state):
        error = self.check_block(block, state)
        if error:
            raise RuntimeError(f"Error in function '{name}' at block '{block.label}': {error}")

        for neighbour in self.successors[block.label]:
            new_state = state.copy()
            self.dfs(name, neighbour, new_state)

    def check_(self):
        """Borrow checking"""
        # Assuming DAG for now.
        for name, function in self.functions.items():
            if isinstance(function, Function):
                self.successors = function.successors
                entry = function.entry()
                state = {}
                try:
                    self.dfs(name, entry, state)
                except RuntimeError as e:
                    return str(e)
        return None



