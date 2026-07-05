from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from typing import TypeAlias


ExecutionValue: TypeAlias = Decimal | str


@dataclass(frozen=True)
class ExecutedStep:
    operation: str
    operands: tuple[str, ...]
    result: ExecutionValue
    expression: str


@dataclass(frozen=True)
class ProgramExecution:
    result: ExecutionValue
    trace: str
    steps: tuple[ExecutedStep, ...]


@dataclass(frozen=True)
class ResolvedOperand:
    value: Decimal
    display: str


class ProgramExecutionError(ValueError):
    pass


SUPPORTED_PROGRAM_OPS = {
    "add",
    "subtract",
    "multiply",
    "divide",
    "exp",
    "greater",
    "table_sum",
    "table_average",
    "table_max",
    "table_min",
}


def execute_program(program: str) -> ProgramExecution:
    """Execute a FinQA arithmetic program.

    Supports both canonical multi-step programs such as
    `add(9.17, 3.55), divide(#0, const_2)` and nested fixture-style programs
    such as `divide(subtract(12.0, 10.0), 10.0)`.
    """

    expressions = [part for part in split_top_level(program or "") if part]
    if not expressions:
        raise ProgramExecutionError("program is empty")

    steps: list[ExecutedStep] = []
    for expression in expressions:
        evaluate_expression(expression, steps)

    if not steps:
        raise ProgramExecutionError("program produced no steps")
    return ProgramExecution(
        result=steps[-1].result,
        trace="; ".join(step.expression for step in steps),
        steps=tuple(steps),
    )


def final_answer_from_program(program: str) -> str:
    execution = execute_program(program)
    return format_execution_value(execution.result)


def evaluate_expression(expression: str, steps: list[ExecutedStep]) -> ResolvedOperand:
    operation, raw_args = parse_function_call(expression)
    if operation not in SUPPORTED_PROGRAM_OPS:
        raise ProgramExecutionError(f"unsupported operation: {operation}")

    operands = tuple(resolve_operand(arg, steps) for arg in raw_args)
    values = [operand.value for operand in operands]
    displays = tuple(operand.display for operand in operands)
    result = apply_operation(operation, values)
    result_display = format_execution_value(result)
    rendered = render_expression(operation, displays, result_display)
    steps.append(
        ExecutedStep(
            operation=operation,
            operands=displays,
            result=result,
            expression=rendered,
        )
    )
    if isinstance(result, str):
        # `greater` is normally a final yes/no FinQA answer. If a caller tries to use it as a
        # nested operand, the numeric placeholder will make that misuse visible in the trace.
        return ResolvedOperand(Decimal("1") if result == "yes" else Decimal("0"), result)
    return ResolvedOperand(result, result_display)


def parse_function_call(expression: str) -> tuple[str, list[str]]:
    text = expression.strip()
    if not text.endswith(")"):
        raise ProgramExecutionError(f"expected function call: {expression}")
    open_index = text.find("(")
    if open_index <= 0:
        raise ProgramExecutionError(f"expected function call: {expression}")
    operation = text[:open_index].strip().lower()
    args_text = text[open_index + 1 : -1]
    if not operation.replace("_", "").isalpha():
        raise ProgramExecutionError(f"invalid operation: {operation}")
    return operation, [part for part in split_top_level(args_text) if part]


def split_top_level(text: str) -> list[str]:
    parts: list[str] = []
    depth = 0
    start = 0
    for index, char in enumerate(text):
        if char == "(":
            depth += 1
        elif char == ")":
            depth -= 1
            if depth < 0:
                raise ProgramExecutionError(f"unbalanced parentheses: {text}")
        elif char == "," and depth == 0:
            parts.append(text[start:index].strip())
            start = index + 1
    if depth != 0:
        raise ProgramExecutionError(f"unbalanced parentheses: {text}")
    tail = text[start:].strip()
    if tail:
        parts.append(tail)
    return parts


def resolve_operand(raw_arg: str, steps: list[ExecutedStep]) -> ResolvedOperand:
    arg = raw_arg.strip()
    if not arg:
        raise ProgramExecutionError("empty operand")
    if looks_like_function_call(arg):
        return evaluate_expression(arg, steps)
    if arg.startswith("#"):
        return resolve_reference(arg, steps)
    if arg.startswith("const_"):
        value = parse_constant(arg)
        return ResolvedOperand(value, format_decimal(value, max_decimal_places=6))
    if arg.endswith("%"):
        value = parse_decimal(arg[:-1]) / Decimal("100")
        return ResolvedOperand(value, arg)
    value = parse_decimal(arg)
    return ResolvedOperand(value, arg)


def looks_like_function_call(text: str) -> bool:
    open_index = text.find("(")
    return open_index > 0 and text.endswith(")") and text[:open_index].strip().replace("_", "").isalpha()


def resolve_reference(arg: str, steps: list[ExecutedStep]) -> ResolvedOperand:
    try:
        index = int(arg[1:])
    except ValueError as exc:
        raise ProgramExecutionError(f"invalid reference: {arg}") from exc
    if index < 0 or index >= len(steps):
        raise ProgramExecutionError(f"reference out of range: {arg}")
    result = steps[index].result
    if isinstance(result, str):
        raise ProgramExecutionError(f"reference is non-numeric: {arg}")
    return ResolvedOperand(result, format_decimal(result, max_decimal_places=6))


def parse_constant(arg: str) -> Decimal:
    suffix = arg.removeprefix("const_")
    if suffix.startswith("m"):
        suffix = "-" + suffix[1:]
    return parse_decimal(suffix)


def parse_decimal(text: str) -> Decimal:
    cleaned = text.strip().replace(",", "").replace("$", "")
    if cleaned.startswith("(") and cleaned.endswith(")"):
        cleaned = "-" + cleaned[1:-1]
    if cleaned.endswith("%"):
        cleaned = cleaned[:-1]
    try:
        return Decimal(cleaned)
    except InvalidOperation as exc:
        raise ProgramExecutionError(f"invalid decimal operand: {text}") from exc


def apply_operation(operation: str, values: list[Decimal]) -> ExecutionValue:
    try:
        if operation == "add":
            return sum(values, Decimal("0"))
        if operation == "subtract":
            require_arity(operation, values, 2)
            return values[0] - values[1]
        if operation == "multiply":
            result = Decimal("1")
            for value in values:
                result *= value
            return result
        if operation == "divide":
            require_arity(operation, values, 2)
            return values[0] / values[1]
        if operation == "exp":
            require_arity(operation, values, 2)
            return decimal_power(values[0], values[1])
        if operation == "greater":
            require_arity(operation, values, 2)
            return "yes" if values[0] > values[1] else "no"
        if operation == "table_sum":
            return sum(values, Decimal("0"))
        if operation == "table_average":
            if not values:
                raise ProgramExecutionError("table_average requires at least one operand")
            return sum(values, Decimal("0")) / Decimal(len(values))
        if operation == "table_max":
            return max(values)
        if operation == "table_min":
            return min(values)
    except (InvalidOperation, ZeroDivisionError, ValueError) as exc:
        raise ProgramExecutionError(f"failed to execute {operation}") from exc
    raise ProgramExecutionError(f"unsupported operation: {operation}")


def require_arity(operation: str, values: list[Decimal], expected: int) -> None:
    if len(values) != expected:
        raise ProgramExecutionError(f"{operation} expected {expected} operands, got {len(values)}")


def decimal_power(base: Decimal, exponent: Decimal) -> Decimal:
    if exponent == exponent.to_integral_value():
        return base**int(exponent)
    return Decimal(str(float(base) ** float(exponent)))


def render_expression(operation: str, operands: tuple[str, ...], result_display: str) -> str:
    displayed = tuple(display_operand(operand) for operand in operands)
    if operation == "add":
        expression = " + ".join(displayed)
    elif operation == "subtract":
        expression = f"{displayed[0]} - {displayed[1]}"
    elif operation == "multiply":
        expression = " * ".join(displayed)
    elif operation == "divide":
        expression = f"{displayed[0]} / {displayed[1]}"
    elif operation == "exp":
        expression = f"{displayed[0]} ^ {displayed[1]}"
    elif operation == "greater":
        expression = f"{displayed[0]} > {displayed[1]}"
    elif operation == "table_sum":
        expression = f"sum({', '.join(displayed)})"
    elif operation == "table_average":
        expression = f"average({', '.join(displayed)})"
    elif operation == "table_max":
        expression = f"max({', '.join(displayed)})"
    elif operation == "table_min":
        expression = f"min({', '.join(displayed)})"
    else:
        expression = f"{operation}({', '.join(displayed)})"
    return f"{expression} = {result_display}"


def display_operand(display: str) -> str:
    stripped = display.strip()
    if stripped.startswith("-"):
        return f"({stripped})"
    return stripped


def format_execution_value(value: ExecutionValue) -> str:
    if isinstance(value, str):
        return value
    return format_decimal(value, max_decimal_places=6)


def format_decimal(value: Decimal, *, max_decimal_places: int) -> str:
    quantizer = Decimal("1") if max_decimal_places == 0 else Decimal("1").scaleb(-max_decimal_places)
    rounded = value.quantize(quantizer, rounding=ROUND_HALF_UP)
    if rounded == Decimal("-0"):
        rounded = Decimal("0")
    text = f"{rounded:.{max_decimal_places}f}"
    if "." in text:
        text = text.rstrip("0").rstrip(".")
    return text
