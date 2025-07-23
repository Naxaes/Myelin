from ir import Op, Module, Function, Builtin


def remove_unused_functions(module: Module, logger=None):
    graph = {}
    entry = None

    for function in module.functions.values():
        if function.name == module.name:
            entry = function

        callers = set()
        for block in function.blocks:
            for instruction in block.instructions:
                if instruction.op == Op.CALL:
                    callers.update(instruction.args)

        graph[function.name] = callers

    visited = set()
    queue = [entry.name]
    while queue:
        node = queue.pop(0)
        visited.add(node)
        for n in graph[node]:
            if n not in visited:
                queue.append(n)

    removed = [name for name in module.functions if name not in visited]
    if logger and removed:
        logger(f"Removed unused functions: {', '.join(removed)}")

    module.functions = {name: func for name, func in module.functions.items() if name in visited}


from graphviz import Digraph

def generate_graph_viz(module):
    dot = Digraph(comment='Control Flow Graph')

    for function_name, function in module.functions.items():
        already_generated = set()
        for block, instruction in function.code():
            if instruction.op == Op.CALL:
                source = f'{function_name}__{block.label}'
                func = module.functions[instruction.args[0]]
                if isinstance(func, Function) and not (target := f'{func.name}__{func.entry().label}') in already_generated:
                    dot.edge(source, target, style='dotted')
                    already_generated.add(target)
                elif isinstance(func, Builtin) and not (target := f'{func.name}') in already_generated:
                    target = f'{func.name}'
                    dot.edge(source, target, style='dotted')
                    already_generated.add(target)

        with dot.subgraph(name=f'cluster_{function_name}') as subgraph:
            subgraph.attr(label=function_name)

            for block in function.blocks:
                name = f'{function_name}__{block.label}'

                def escape(s):
                    return s.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')

                # Create HTML-like label with block label as header and instructions as rows
                label = f'''<
                    <TABLE BORDER="1" CELLBORDER="0" CELLSPACING="0">
                        <TR><TD BGCOLOR="lightgray"><B>{block.label}</B></TD></TR>
                        {''.join(f'<TR><TD ALIGN="LEFT">{i:02}│ {escape(instr.to_text())}</TD></TR>' for i, instr in enumerate(block.instructions))}
                        
                        <TR><TD BGCOLOR="black" HEIGHT="1"></TD></TR>
                        <TR><TD ALIGN="LEFT">{escape(block.terminator.to_text())}</TD></TR>
                    </TABLE>
                >'''

                subgraph.node(name, label=label, shape='plaintext')

                match block.terminator.op:
                    case Op.RET:
                        # subgraph.edge(name, function_name)
                        pass
                    case Op.BR:
                        left, right = block.terminator.args
                        subgraph.edge(name, f'{function_name}__{function.blocks[left].label}')
                        subgraph.edge(name, f'{function_name}__{function.blocks[right].label}')
                    case Op.JMP:
                        target, *_ = block.terminator.args
                        subgraph.edge(name, f'{function_name}__{function.blocks[target].label}')
                    case _:
                        raise ValueError(f'Invalid terminator {block.terminator} for function {function_name}')

    return dot.source
