from parser import Module



def remove_unused_functions(module: Module, logger=None):
    graph = {}
    entry = None

    for function in module.functions.values():
        if function.name == module.name:
            entry = function

        callers = set()
        for block in function.blocks:
            for instruction in block.instructions:
                if instruction.op == 'call':
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
