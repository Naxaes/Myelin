from parser import Module



def remove_unused_functions(module: Module):
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

    print(entry)
    for name, callers in graph.items():
        print(f'{name} -> {callers}')


    visited = set()
    queue = [entry.name]
    while queue:
        node = queue.pop(0)
        visited.add(node)
        for n in graph[node]:
            if n not in visited:
                queue.append(n)

    module.functions = {name: func for name, func in module.functions.items() if name in visited}
