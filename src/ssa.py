

def check_if_in_ssa_form(module):
    """
    Check if the module is in SSA form.
    """
    for function in module.functions.values():
        seen_vars = set()
        for block in function.blocks:
            for instruction in block.instructions:
                if instruction.dest is None:
                    continue
                if instruction.dest in seen_vars:
                    print(f"Error in function '{function.name}' at block '{block.label}':")
                    print(f"Variable '{instruction.dest}' is defined multiple times in the  same block.")
                    return False
                seen_vars.add(instruction.dest)
    return True
