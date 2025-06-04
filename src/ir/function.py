from typing import Callable, List, Any

from ir import Code, TERMINATORS, Op, ARITHMETICS, Block, Entry


def lt(a, b): return (a[0], min(a[1], b[1] - 1)), (max(a[0] + 1, b[0]), b[1])
def le(a, b): return (a[0], min(a[1], b[1])), (max(a[0], b[0]), b[1])
def ge(a, b): return (max(a[0], b[0]), a[1]), (b[0], min(a[1], b[1]))


class Builtin:
    def __init__(self, name, returns, params):
        self.name = name
        self.returns = returns
        self.params = params
        self.blocks = []

    def code(self):
        return []

    def __repr__(self):
        parameters = ', '.join(f'{x}: {t[0]}' for x, t in self.params.items())
        rets = ', '.join(ty for name, ty in self.returns)
        return f'{self.name}: @builtin({parameters}) -> {rets or "void"}'


class Function:
    def __init__(self,
                 name: str,
                 parameters: list[dict[str, str]] = None,
                 return_values: list[str] = None,
                 blocks: list[Block] = None,
                 predecessors: dict[str, list[Block]] = None,
                 successors: dict[str, list[Block]] = None,
                 is_module=False,
                 is_main=False
    ):
        self.name = name
        self.params = parameters or {}
        self.returns = return_values or []
        self.blocks = blocks or []
        self.is_module = is_module
        self.is_main = is_main

        self._predecessors = predecessors
        self._successors = successors
        self._live_in = None
        self._live_out = None

    def add(self, block: Block):
        id = len(self.blocks)
        self.blocks.append(block)
        return id

    def create_cfg(self) -> tuple[dict[str, list[Block]], dict[str, list[Block]]]:
        predecessors: dict[str, list[Block]] = {b.label: [] for b in self.blocks}
        successors: dict[str, list[Block]] = {b.label: [] for b in self.blocks}

        for i, block in enumerate(self.blocks):
            last = block.terminator
            assert last.op in TERMINATORS, f'Block {block.label} has unknown terminator {last.op}'
            match last.op:
                case Op.BR:
                    left, right = last.args
                    lhs, rhs = self.blocks[left], self.blocks[right]

                    successors[block.label] = [lhs, rhs]
                    predecessors[lhs.label].append(block)
                    predecessors[rhs.label].append(block)
                case Op.JMP:
                    id, *_ = last.args
                    target = self.blocks[id]
                    successors[block.label] = [target]
                    predecessors[target.label].append(block)
                case Op.RET:
                    successors[block.label] = []
                case _:
                    assert False, f'Unknown terminator {last.op} in block {block.label}'

        return predecessors, successors

    def code(self):
        for block in self.blocks:
            for code in block.instructions:
                yield block, code
            yield block, block.terminator

    def live_in(self):
        if self._live_in is None:
            self._live_in, self._live_out = self.live_variables()
        return self._live_in

    def live_out(self):
        if self._live_out is None:
            self._live_in, self._live_out = self.live_variables()
        return self._live_out

    @property
    def predecessors(self):
        if self._predecessors is None:
            self._predecessors, self._successors = self.create_cfg()
        return self._predecessors

    @property
    def successors(self):
        if self._successors is None:
            self._predecessors, self._successors = self.create_cfg()
        return self._successors

    def block_at(self, label):
        for block in self.blocks:
            if block.label == label:
                return block
        return None

    def every_predecessor_of_until(self, block, label):
        predecessors = set()
        current = set(self.predecessors[block.label])
        while predecessors != current and label not in (x.label for x in current):
            predecessors = current
            current = current.union(set(p for b in predecessors for p in self.predecessors[b.label]))
        return current

    def canonicalize(self) -> None:
        """
        1. Cannonicalize all instructions
        2. Cannonicalize all basic blocks
        3. Deterministically move all blocks, respecting order of execution/side-effects
        """
        for block in self.blocks:
            block.canonicalize()

    def lvn(self) -> None:
        table: dict[int, Entry] = {}
        environment: dict[str, int] = {}
        for param in self.params:
            environment[param['name']] = len(table)
            table[len(table)] = (Entry(None, param['name']))

        def merge(_: Block, s: list[Any]):
            t0: dict[str, Any] = {}
            e0: dict[str, Any] = {}
            for x in s:
                t1, e1 = x
                t0.update(t1)
                e0.update(e0)
            return t0, e0

        def trans(b: Block, s: set[Any]):
            t, e = s
            return b.lvn(t, e)

        first = table, environment
        in_, out = self.analyze(first, rest=first, merge=merge, transfer=trans, forward=True)

        # TODO: This must be done with a CFG flow algorithm
        # for block in self.blocks:
        #     table, environment = block.lvn(table, environment)

    def remove_unreachable_blocks(self):
        successors = self.successors
        queue = [self.blocks[0]]
        visited = set()

        while len(queue) > 0:
            block = queue.pop(-1)
            if block.label not in visited:
                visited.add(block.label)
                for b in successors[block.label]:
                    queue.append(b)

        if len(visited) < len(self.blocks):
            for b in self.blocks:
                if b.label not in visited:
                    b.instructions = []
            self.blocks = [b for b in self.blocks if b.label in visited]

    def analyze(self, init: Any, rest: Any, merge: Callable[[Block, List[Any]], Any],
                transfer: Callable[[Block, Any], Any], forward: bool) -> tuple[dict[str, Any], dict[str, Any]]:
        """
        :param init: Initial value of all in-data and out-data
        :param merge: Combines in-data from other nodes out-data
        :param transfer: Transfers in-data to out-data
        :param forward:
        :return:
        """
        predecessors, successors = self.predecessors, self.successors
        if forward:
            queue = self.blocks.copy()
            first_block = self.blocks[0]
            in_edges = predecessors
            out_edges = successors
        else:
            queue = list(reversed(self.blocks.copy()))
            first_block = self.blocks[-1]
            in_edges = successors
            out_edges = predecessors

        in_data = {first_block.label: init}
        out_data = {b.label: rest for b in self.blocks}

        block = queue.pop(0)
        in_data[block.label] = merge(block, [init])
        out_result = transfer(block, in_data[block.label])
        if out_data[block.label] != out_result:
            out_data[block.label] = out_result
            queue.extend(out_edges[block.label])

        while len(queue) > 0:
            block = queue.pop(0)

            # All out variables of the predecessors are in variables for this block.
            in_data[block.label] = merge(block, [out_data[b.label] for b in in_edges[block.label]])

            # All in variables will also be out variables.
            out_result = transfer(block, in_data[block.label])

            # If the out variables have been updated, then we need to process successors.
            if out_data[block.label] != out_result:
                out_data[block.label] = out_result
                queue.extend(out_edges[block.label])

        if forward:
            return in_data, out_data
        else:
            return out_data, in_data

    def reaching_definitions(self) -> tuple[dict[str, set[tuple[str, int]]], dict[str, set[tuple[str, int]]]]:
        """
        :return:
        """
        Var = tuple[str, str]

        def gen(b: Block) -> set[Var]:
            return set((name, b.label) for name in b.gen())

        def kill(b: Block, in_: set[Var]) -> set[Var]:
            defined = b.gen()
            return set((name, label) for name, label in in_ if name in defined)

        def merge(_: Block, s: list[set[Var]]):
            return set().union(*s)

        def trans(b: Block, in_: set[Var]):
            return gen(b).union(in_ - kill(b, in_))

        all_variables = set().union(*[b.gen() for b in self.blocks])

        parameters = set((v['name'], '__init__') for v in self.params)
        initial_state = set((v, None) for v in all_variables).union(parameters)
        return self.analyze(initial_state, initial_state, merge=merge, transfer=trans, forward=True)

    def very_busy_expressions(self) -> tuple[
        dict[str, set[tuple[str, Any, Any]]], dict[str, set[tuple[str, Any, Any]]]]:
        """
        :return:
        """
        Val = tuple[str, Any, Any]

        def merge(_: Block, s: list[set[Val]]):
            return set.intersection(*s)

        def trans(b: Block, in_: set[Val]):
            result = in_.copy()
            for i in reversed(b.instructions):
                if i.op in ARITHMETICS:
                    assert len(i.refs) == 2, 'Not implemented'
                    result = set(x for x in result if not any(y == i.dest for y in x))
                    result.add((i.op, i.refs[0], i.refs[1]))
                elif i.op == Op.LIT:
                    ty, idx, val = i.args
                    result = set(x for x in result if not any(y == i.dest for y in x))
                    result.add((i.op, val, None))
                    pass
            return result

        all_expressions = set()
        for b in self.blocks:
            for i in b.instructions:
                if i.op in ARITHMETICS:
                    refs = i.refs
                    assert len(refs) == 2, 'Not implemented'
                    value = (i.op, refs[0], refs[1])
                    all_expressions.add(value)
                elif i.op == Op.LIT:
                    ty, idx, val = i.args
                    value = (i.op, val, None)
                    all_expressions.add(value)

        initial_state = all_expressions
        return self.analyze(set(), initial_state, merge=merge, transfer=trans, forward=False)

    def live_variables(self) -> tuple[dict[str, set[str]], dict[str, set[str]]]:
        """
        :return:
        """

        def merge(_: Block, s: list[set[str]]):
            return set.union(*s)

        def trans(b: Block, in_: set[str]):
            result = in_.copy()
            for i in reversed(b.instructions):
                if i.dest and i.dest in result:
                    result.remove(i.dest)
                for a in i.refs:
                    if type(a) == str:
                        result.add(a)
            return result

        return self.analyze(set(), set(), merge=merge, transfer=trans, forward=False)

    def interval_analysis(self) -> tuple[dict[str, dict[str, tuple[int, int]]], dict[str, dict[str, tuple[int, int]]]]:
        """
        :return:
        """
        Interval = tuple[int, int]
        default = (-2 ** 31, 2 ** 31)
        init = {v['name']: default for v in self.params}
        predecessors, successors = self.predecessors, self.successors

        def merge(block: Block, preds: list[Block]):
            result = {}
            for pred in preds:
                for key, value in out_data[pred.label].items():
                    if key in result:
                        result[key] = min(result[key][0], value[0]), max(result[key][1], value[1])
                    else:
                        result[key] = value

                last = pred.terminator
                if last.op == Op.BR:
                    cond, *_ = last.refs
                    left, right = last.args
                    if self.blocks[left].label == block.label:
                        # True branch
                        inst = next(x for x in pred.instructions if x.dest == cond)
                        if inst.op == Op.LT:
                            lhs, rhs = inst.refs
                            l = out_data[pred.label][lhs]
                            r = out_data[pred.label][rhs]
                            a, b = lt(l, r)
                            if a[0] > a[1] or b[0] > b[1]:
                                result[cond] = (False, False)
                            else:
                                result[lhs] = a
                                result[rhs] = b
                                result[cond] = (True, True)
                        else:
                            assert False, f'Not implemented {inst.op}'
                    elif self.blocks[right].label == block.label:
                        # False branch
                        inst = next(x for x in pred.instructions if x.dest == cond)
                        if inst.op == Op.LT:
                            lhs, rhs = inst.refs
                            l = out_data[pred.label][lhs]
                            r = out_data[pred.label][rhs]
                            a, b = ge(l, r)
                            if a[0] > a[1] or b[0] > b[1]:
                                result[cond] = (True, True)
                            else:
                                result[lhs] = a
                                result[rhs] = b
                                result[cond] = (False, False)
                        else:
                            assert False, f'Not implemented {inst.op}'

            return result

        def trans(block: Block, in_: dict[str, Interval]):
            result = in_.copy()
            for i in filter(lambda x: x.dest, block.instructions):
                name = i.dest
                if i.op == Op.LIT:
                    ty, idx, val = i.args
                    result[name] = int(val), int(val)
                elif i.refs:
                    lhs = result[i.refs[0]]
                    rhs = result[i.refs[1]]
                    if i.op == Op.ADD:
                        result[name] = lhs[0] + rhs[0], lhs[1] + rhs[1]
                    elif i.op == Op.SUB:
                        result[name] = lhs[0] - rhs[0], lhs[1] - rhs[1]
                    elif i.op == Op.MUL:
                        a, b, c, d = lhs[0] * rhs[0], lhs[0] * rhs[1], lhs[1] * rhs[0], lhs[1] * rhs[1]
                        result[name] = min(a, b, c, d), max(a, b, c, d)
                    elif i.op == Op.LT:
                        result[name] = lhs[1] < rhs[0], lhs[0] < rhs[1]
            return result

        queue = self.blocks.copy()
        first_block = self.blocks[0]

        in_data = {first_block.label: init}
        out_data = {b.label: dict() for b in self.blocks}

        block = queue.pop(0)
        out_result = trans(block, in_data[block.label])
        if out_data[block.label] != out_result:
            out_data[block.label] = out_result
            queue.extend(successors[block.label])

        k = 0
        while len(queue) > 0:
            block = queue.pop(0)

            # All out variables of the predecessors are in variables for this block.
            in_data[block.label] = merge(block, predecessors[block.label])

            # All in variables will also be out variables.
            out_result = trans(block, in_data[block.label])

            # If the out variables have been updated, then we need to process successors.
            if out_data[block.label] != out_result:
                if k > 256:
                    break
                k += 1
                out_data[block.label] = out_result
                queue.extend(successors[block.label])

        return in_data, out_data

    def dominators(self) -> dict[str, set[str]]:
        """
        A block is dominating blocks if it has to be executed before the others.
        Domination is reflexive, meaning any block dominates itself, and antisymmetric.
        :return: A mapping from a block to a set of blocks it dominates.
        """
        predecessors, successors = self.predecessors, self.successors
        first = self.blocks[0].label
        universe = set(b.label for b in self.blocks)

        dom = {b.label: universe for b in self.blocks}
        dom[first] = set()

        queue = [first]
        while len(queue) > 0:
            node = queue.pop(0)

            predecessor_dominators = [dom[n.label] for n in predecessors[node]]
            node_dominators = set.intersection(*predecessor_dominators) if predecessor_dominators else set()
            new = node_dominators.union({node})

            if new != dom[node]:
                dom[node] = new
                for successor in successors[node]:
                    queue.append(successor.label)

        return dom

    def constant_propagation(self):
        in_, out = self.analyze(init=dict(), rest=dict(), merge=cprop_merge, transfer=cprop_transfer, forward=True)
        for b in self.blocks:
            for instr in b.instructions:
                if instr.dest and instr.dest in out[b.label] and out[b.label][instr.dest] != '?':
                    instr.op = Op.LIT
                    instr.args = (out[b.label][instr.dest],)

    def borrow_check(self, live_variables: dict[str, set[str]]) -> tuple[dict[str, Any], dict[str, Any]]:
        def merge(_: Block, s: list[dict[str, set[str]]]):
            result = dict()
            for x in s:
                result.update(x)
            return result

        def trans(b: Block, s: dict[str, set[str]]):
            return b.borrow_check(s, live_variables[b.label])

        first: dict[str, str] = dict()
        in_, out = self.analyze(first, first, merge=merge, transfer=trans, forward=True)
        return in_, out

    def automatically_drop(self) -> None:
        # * Can't free if a predecessor has freed
        # * Can't free unless all predecessor has the allocation live

        # 1. Find nodes that has an allocation
        # 2. For each such node, find the subgraph to the exit node by adding each successor to a visited set.
        # 3. Iterate backwards from the last node through all predecessors until we find one that has all predecessors in the visited set.

        blocks_with_allocations = {
            (block, instruction.dest, i)
            for i, block in enumerate(self.blocks) for instruction in block.instructions if instruction.op == Op.ALLOC
        }

        for start, name, i in blocks_with_allocations:
            visited = {}
            queue = [start]
            while queue:
                current = queue.pop(0)
                visited[current.label] = current
                successors = self.successors[current.label]
                for successor in successors:
                    if successor.label not in visited:
                        queue.append(successor)

            # TODO: This is not correct
            node = [b for b in self.blocks if b.label in visited][-1]
            queue = [node]
            v2 = set()
            while queue:
                current = queue.pop(0)
                predecessors = self.every_predecessor_of_until(current, start.label)
                labels = {p.label for p in predecessors}
                if labels.issubset(visited):
                    if current.instructions[-1].op in (Op.RET, Op.JMP, Op.BR):
                        current.instructions.insert(-1, Code(op=Op.FREE, args=(name,)))
                    else:
                        current.instructions.append(Code(op=Op.FREE, args=(name,)))
                    break
                queue.extend(p for p in predecessors if p.label in visited and p.label not in v2)
                v2.update(labels)
            else:
                raise RuntimeError(f"Couldn't free {name}. No shared nodes in subgraph found")

    def static_slice(self, variable: str):
        effected = {variable}
        program = {}
        for block in reversed(self.blocks):
            instructions = []
            for instruction in reversed(block.instructions):
                if instruction.op in (Op.BR, Op.JMP, Op.RET):
                    if instruction.refs:
                        effected.update({arg for arg in instruction.refs})
                    instructions.append(instruction)
                    continue

                added = False
                if instruction.dest:
                    if instruction.dest in effected:
                        instructions.append(instruction)
                        effected.update({arg for arg in instruction.refs if type(arg) == str})
                        added = True
                    if any(arg in effected for arg in instruction.refs) and not added:
                        instructions.append(instruction)
                        effected.update({arg for arg in instruction.refs if type(arg) == str})
                        added = True
                if instruction.refs and not added:
                    if any(arg in effected for arg in instruction.refs):
                        instructions.append(instruction)
            instructions.reverse()
            program[block.label] = instructions
        return program

    def __repr__(self):
        if self.is_module:
            return f'{self.name}: @module'
        else:
            parameters = ', '.join(f'{x}: {t[0]}' for x, t in self.params.items())
            rets = ', '.join(ty for name, ty in self.returns)
            return f'{self.name}: ({parameters}) -> {rets or "void"}'


def cprop_transfer(block, in_vals):
    def args_is_known(arg):
        return arg in out_vals and out_vals[arg] != '?'

    out_vals = dict(in_vals)
    for instr in block.instructions:
        if instr.dest:
            if instr.op == Op.LIT:
                out_vals[instr.dest] = instr.args[0]
            elif len(instr.args) >= 2 and args_is_known(instr.args[0]) and args_is_known(instr.args[1]):
                a, b = instr.args
                if instr.op == Op.ADD:
                    out_vals[instr.dest] = out_vals[a] + out_vals[b]
                elif instr.op == Op.SUB:
                    out_vals[instr.dest] = out_vals[a] - out_vals[b]
                elif instr.op == Op.MUL:
                    out_vals[instr.dest] = out_vals[a] * out_vals[b]
                elif instr.op == '>':
                    out_vals[instr.dest] = out_vals[a] > out_vals[b]
            else:
                out_vals[instr.dest] = '?'
    return out_vals


def cprop_merge(_, vals_list):
    out_vals = {}
    for vals in vals_list:
        for name, val in vals.items():
            if val == '?':
                out_vals[name] = '?'
            elif name in out_vals and out_vals[name] != val:
                out_vals[name] = '?'
            else:
                out_vals[name] = val
    return out_vals


def check_all_variables_are_initialized_before_use(function: Function):
    def merge_check(block: Block, set_list: list[set]) -> set[str]:
        for arguments in set_list:
            if len(block.arguments - arguments) > 0:
                raise Exception(f'Oh no! {block.label}: {block.arguments} - {arguments}')

        return set().union(*set_list)

    function.analyze(
        set(),
        set(),
        merge=merge_check,
        transfer=lambda b, in_: b.gen().union(in_),
        forward=True
    )
















