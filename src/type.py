from abc import ABC, abstractmethod
from typing import List, Optional, Set, Dict
from enum import Enum, auto

from ir import Op


# --- Qualifiers ---
class Qualifier(Enum):
    MUT   = auto()
    CONST = auto()


# --- Base Type Class ---
class Type(ABC):
    def __init__(self, name: str, size: int, qualifiers: Optional[Set[Qualifier]] = None):
        self.name = name
        self.size = size
        self.qualifiers = qualifiers or {Qualifier.CONST}

    @abstractmethod
    def __repr__(self):
        pass

    def __eq__(self, other):
        return self.is_equal(other)

    def operation(self, op: Op, other: 'Type') -> Optional['Type']:
        raise NotImplementedError()

    def is_equal(self, other: 'Type') -> bool:
        assert isinstance(other, Type), f'{other} is not a Type'
        return (
            self.name == other.name and
            self.size == other.size and
            self.qualifiers == other.qualifiers
        )

    def qualifier_str(self) -> str:
        return ' '.join(q.name.lower() for q in sorted(self.qualifiers, key=lambda x: x.name))

    def is_subtype_of(self, other: 'Type') -> bool:
        """
        Whether this type is equal to or a child of `other`
        """
        if isinstance(other, InferredType):
            return True
        return self.is_equal(other)


class InferredType(Type):
    def __init__(self):
        super().__init__('inferred', 0)

    def is_subtype_of(self, other: Type) -> bool:
        return True

    def __repr__(self):
        return f'<inferred>'


# --- Primitive Type ---
class PrimitiveType(Type):
    SAFE_COERCIONS: Dict[str, Set[str]] = {
        'bool':     { 'char',   'u8', 'u16', 'u32', 'u64', 'f32', 'f64', 'i8' 'i16', 'i32', 'i64', 'int' },
        'char':     {   'u8',  'u16', 'u32', 'u64', 'f32', 'f64', 'i8' 'i16', 'i32', 'i64', 'int' },
        'u8':       {  'u16',  'u32', 'u64', 'f32', 'f64', 'i16', 'i32', 'i64', 'int'},
        'i8':       {  'i16',  'i32', 'i64', 'int', 'f32', 'f64'},
        'u16':      {  'u32',  'u64', 'f32', 'f64', 'i32', 'i64', 'int'},
        'i16':      {  'i32',  'i64', 'int', 'f32', 'f64'},
        'u32':      {  'u64',  'f64', 'i64', 'int'},
        'i32':      {  'f64',  'i64', 'int'},
        'f32':      {  'f64'},
        'i64':      {  'int'},
        'int':      {  'i64'},
        'u64':      { },
        'f64':      { },
    }

    def __init__(self, name: str, size: int, qualifiers: Optional[Set[Qualifier]] = None):
        super().__init__(name, size, qualifiers)

    def peer_resolution(self, other: Type) -> Optional[Type]:
        if other.name in PrimitiveType.SAFE_COERCIONS.get(self.name, set()):
            return other
        elif self.name in PrimitiveType.SAFE_COERCIONS.get(other.name, set()):
            return self
        elif isinstance(other, LiteralType):
            if other.name.isnumeric() and self.name in ('int', 'i8', 'i16', 'i32', 'i64', 'u8', 'u16', 'u32', 'u64'):
                if self.size >= other.size:
                    return self
            elif self.name == 'bool' and other.name.lower() in ('0', '1', 'true', 'false'):
                return self
            assert False, "Not implemented"
        else:
            return self if self.is_equal(other) else None

    def operation(self, op: Op, other: Type) -> Optional[Type]:
        is_commutative = False
        match op:
            case Op.ADD|Op.SUB|Op.MUL:
                if t := self.peer_resolution(other):
                    return t
                is_commutative = True
            case Op.DIV|Op.MOD:
                if t := self.peer_resolution(other):
                    return t
            case Op.EQ|Op.NEQ:
                if t := self.peer_resolution(other):
                    return PrimitiveType(name='bool', size=1)
                is_commutative = True
            case Op.AND|Op.OR:
                if t := self.peer_resolution(other):
                    if t.name == 'bool':
                        return t
                is_commutative = True
            case Op.GT|Op.LT|Op.GTE|Op.LTE:
                if t := self.peer_resolution(other):
                    return t
            case _:
                raise RuntimeError(f'Unknown binary operator {op}')

        # if is_commutative:
        #     return other.operation(op, self)
        raise RuntimeError(f"invalid binary operator '{op}' for {self} and {other}")

    def is_subtype_of(self, other: 'Type') -> bool:
        if isinstance(other, PrimitiveType):
            if self.name == other.name:
                return True
            allowed = PrimitiveType.SAFE_COERCIONS.get(self.name, set())
            return other.name in allowed
        elif isinstance(other, LiteralType):
            if self.name in ('int', 'i8', 'i16', 'i32', 'i64', 'u8', 'u16', 'u32', 'u64'):
                if other.name.isnumeric() and self.size >= other.size:
                    return True
            return False
        return isinstance(other, InferredType)

    def __repr__(self):
        return f"{self.qualifier_str()} {self.name}".strip()


class LiteralType(Type):
    def __init__(self, value):
        assert type(value) == int or type(value) == bool, "Other's not implemented"
        super().__init__(str(value), value.bit_length()//8 + 1)

    def value(self) -> int:
        return int(self.name)

    def operation(self, op: Op, other: Type) -> Optional[Type]:
        if isinstance(other, LiteralType):
            match op:
                case Op.ADD:
                    return LiteralType(self.value() + other.value())
                case Op.SUB:
                    return LiteralType(self.value() - other.value())
                case Op.MUL:
                    return LiteralType(self.value() * other.value())
                case Op.DIV:
                    if other.value() == 0:
                        raise ZeroDivisionError("Division by zero")
                    return LiteralType(self.value() // other.value())
                case Op.MOD:
                    if other.value() == 0:
                        raise ZeroDivisionError("Division by zero")
                    return LiteralType(self.value() % other.value())
                case Op.EQ:
                    return LiteralType(self.value() == other.value())
                case Op.NEQ:
                    return LiteralType(self.value() != other.value())
                case Op.GT:
                    return LiteralType(self.value() > other.value())
                case Op.LT:
                    return LiteralType(self.value() < other.value())
                case Op.GTE:
                    return LiteralType(self.value() >= other.value())
                case Op.LTE:
                    return LiteralType(self.value() <= other.value())
                case _:
                    raise RuntimeError(f'Unknown binary operator {op} for {self} and {other}')
        return other.operation(op, self)

    def is_subtype_of(self, other: 'Type') -> bool:
        if isinstance(other, PrimitiveType):
            if self.name.isnumeric() and other.name in ('int', 'i8', 'i16', 'i32', 'i64', 'u8', 'u16', 'u32', 'u64'):
                if other.size >= self.size:
                    return True
        elif isinstance(other, InferredType):
            return True
        return self.is_equal(other)


    def __repr__(self):
        return f"{self.name}".strip()

# --- Pointer Type ---
class PointerType(Type):
    def __init__(self, pointee: Type, qualifiers: Optional[Set[Qualifier]] = None):
        super().__init__(name=f"{pointee.name}*", size=8, qualifiers=qualifiers)
        self.pointee = pointee

    def get_attribute(self, attribute):
        return self.pointee.get_attribute(attribute)

    def operation(self, op: Op, other: Type) -> Optional[Type]:
        match op:
            case Op.ADD|Op.SUB:
                if isinstance(other, PrimitiveType) or isinstance(other, LiteralType):
                    return self
            case Op.EQ|Op.NEQ:
                if isinstance(other, PrimitiveType) or isinstance(other, LiteralType):
                    return self
            case _:
                raise RuntimeError(f'Unknown binary operator {op}')
        raise RuntimeError(f'invalid binary operator {op} for {self}')

    def is_subtype_of(self, other: 'Type') -> bool:
        if not isinstance(other, PointerType):
            return True if isinstance(other, InferredType) else False

        # TODO: Hack for now.
        if self.name == 'void*' or other.name == 'void*':
            return True

        # 1. Same base types, allowing qualifier widening (e.g., to const)
        if self.pointee.is_equal(other.pointee):
            return Qualifier.MUT in self.qualifiers or Qualifier.MUT not in other.qualifiers

        # 2. Subtype relationship between pointed types
        if self.pointee.is_subtype_of(other.pointee):
            return Qualifier.MUT in self.qualifiers or Qualifier.MUT not in other.qualifiers

        return False

    def __repr__(self):
        return f"{self.qualifier_str()}* {str(self.pointee)}".strip()


# --- Array Type ---
class ArrayType(Type):
    def __init__(self, element_type: Type, length: int, qualifiers: Optional[Set[Qualifier]] = None):
        super().__init__(name=f"{element_type.name}[{length}]", size=element_type.size * length, qualifiers=qualifiers)
        self.element_type = element_type
        self.length = length

    def get_attribute(self, attribute):
        if attribute == 'len':
            return LiteralType(self.size)
        else:
            raise TypeError(f'No attribute {attribute} on {self}')

    def is_subtype_of(self, other: 'Type') -> bool:
        if isinstance(other, InferredType):
            return True
        elif isinstance(other, PointerType):
            return self.element_type.is_equal(other.pointee)
        return self.is_equal(other)

    def __repr__(self):
        return f"{self.qualifier_str()} [{self.length}]{str(self.element_type)}".strip()

# --- Function Type ---
class FunctionType(Type):
    def __init__(self, return_types: List[Type], param_types: List[Type]):
        super().__init__(name="func", size=8)
        self.return_types = return_types
        self.param_types = param_types

    def is_equal(self, other: 'Type') -> bool:
        return isinstance(other, FunctionType) and (
            self.param_types == other.param_types and
            self.return_types == other.return_types
        )

    def __repr__(self):
        params = ', '.join(str(p) for p in self.param_types)
        rets   = ', '.join(str(p) for p in self.return_types)
        return f"{self.name}({params}) -> ({rets})"

# --- Struct Type ---
class StructType(Type):
    def __init__(self, name: str, fields: dict[str, Type]):
        total_size = sum(ty.size for name, ty in fields.items())
        super().__init__(name=f"struct {name}", size=total_size)
        self.fields = fields
        self.methods: Dict[str, FunctionType] = {}

    def get_attribute(self, attribute):
        return self.fields[attribute]

    def add_method(self, name: str, fn_type: FunctionType):
        self.methods[name] = fn_type

    def has_method(self, name: str) -> bool:
        return name in self.methods

    def __repr__(self):
        field_list = ', '.join(str(f) for f in self.fields)
        return f"{self.name} {{ {field_list} }}"


# --- Nullable Type ---
class OptionalType(Type):
    def __init__(self, base_type: Type):
        super().__init__(name=f"{base_type.name}?", size=base_type.size + 1)
        self.base_type = base_type

    def is_subtype_of(self, other: 'Type') -> bool:
        return self.is_equal(other) or self.base_type.is_equal(other)

    def __repr__(self):
        return f"{str(self.base_type)}?"


# --- Generic Type ---
class GenericType(Type):
    def __init__(self, name: str, param_names: List[str]):
        super().__init__(name, size=-1)
        self.param_names = param_names

    def instantiate(self, param_types: List[Type]) -> 'InstantiatedGenericType':
        return InstantiatedGenericType(self, param_types)

    def __repr__(self):
        params = ', '.join(self.param_names)
        return f"{self.name}<{params}>"


class InstantiatedGenericType(Type):
    def __init__(self, generic: GenericType, param_types: List[Type]):
        name = f"{generic.name}<{', '.join(p.name for p in param_types)}>"
        super().__init__(name, size=0)
        self.generic = generic
        self.param_types = param_types

    def __repr__(self):
        return self.name


# --- Type Registry ---
class TypeRegistry:
    def __init__(self, data=None):
        self._registry = {}

    def intern(self, t: Type) -> Type:
        key = str(t)
        if key in self._registry:
            return self._registry[key]
        self._registry[key] = t
        return t

    def lookup(self, key: str) -> Optional[Type]:
        return self._registry.get(key)



def example_usage():
    # Primitive types
    int_type = PrimitiveType("int", 4)
    float_type = PrimitiveType("float", 4)
    mut_int = PrimitiveType("int", 4, {Qualifier.MUT})

    # Pointer and array types
    ptr_to_int = PointerType(int_type)
    array_of_ints = ArrayType(int_type, 5)

    # Struct
    struct_type = StructType("MyStruct", [mut_int, float_type])

    # Add method to struct
    method_type = FunctionType(return_types=[int_type], param_types=[int_type])
    struct_type.add_method("get_id", method_type)


    # Optional type
    optional_int = OptionalType(int_type)

    # Generic type
    vec_generic = GenericType("Vec", ["T"])
    vec_of_int = vec_generic.instantiate([int_type])

    # Intern types
    registry = TypeRegistry()
    t1 = registry.intern(vec_of_int)
    t2 = registry.intern(vec_of_int)
    assert t1 is t2

    # Print everything
    print(mut_int)
    print(ptr_to_int)
    print(array_of_ints)
    print(struct_type)
    print(optional_int)
    print(vec_generic)
    print(vec_of_int)
    print(method_type)


if __name__ == "__main__":
    example_usage()

