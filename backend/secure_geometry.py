from fractions import Fraction
from typing import Any


class SecureGeometryError(ValueError):
    """安全几何实验室的可预期输入错误。"""


RELATION_STEPS = {
    "point_line": [
        "Alice 把点坐标扩展成四维向量 [x, y, z, 1]。",
        "Bob 把直线的两个平面方程分别看成四维系数向量。",
        "双方执行两次保密内积模拟，两个内积都为 0 时点在直线上。",
    ],
    "point_plane": [
        "Alice 把点坐标扩展成四维向量 [x, y, z, 1]。",
        "Bob 把平面 Ax + By + Cz + D = 0 写成 [A, B, C, D]。",
        "双方执行一次保密内积模拟，内积为 0 时点在平面上。",
    ],
    "line_line": [
        "Alice 从自己的直线上取两个确定点。",
        "用这两个点分别和 Bob 的两条平面方程做保密内积模拟。",
        "若两个点都在 Bob 的直线上则重合，否则继续比较方向向量，区分平行、相交和异面。",
    ],
    "line_plane": [
        "Alice 从自己的直线上取两个确定点。",
        "两个点都满足 Bob 的平面方程时，直线在平面内。",
        "否则比较直线方向向量和平面法向量，内积为 0 时平行，否则相交。",
    ],
    "plane_plane": [
        "Alice 从自己的平面上取三个不共线点。",
        "三个点都满足 Bob 的平面方程时，两个平面重合。",
        "否则比较两个平面的法向量，法向量平行则平行，不平行则相交。",
    ],
}


RELATION_NAMES = {
    "point_line": "点与直线",
    "point_plane": "点与平面",
    "line_line": "直线与直线",
    "line_plane": "直线与平面",
    "plane_plane": "平面与平面",
}


def to_fraction(value: Any, label: str) -> Fraction:
    if isinstance(value, bool):
        raise SecureGeometryError(f"{label} 不能是布尔值")
    try:
        return Fraction(str(value).strip())
    except (ValueError, ZeroDivisionError, AttributeError) as exc:
        raise SecureGeometryError(f"{label} 必须是数字或分数字符串") from exc


def parse_vector(value: Any, length: int, label: str) -> list[Fraction]:
    if not isinstance(value, list) or len(value) != length:
        raise SecureGeometryError(f"{label} 必须是长度为 {length} 的数组")
    return [to_fraction(item, f"{label}[{index}]") for index, item in enumerate(value)]


def parse_point(value: Any, label: str = "point") -> list[Fraction]:
    return parse_vector(value, 3, label)


def parse_plane(value: Any, label: str = "plane") -> list[Fraction]:
    plane = parse_vector(value, 4, label)
    if plane[0] == 0 and plane[1] == 0 and plane[2] == 0:
        raise SecureGeometryError(f"{label} 不是合法平面，A、B、C 不能全为 0")
    return plane


def parse_line(value: Any, label: str = "line") -> list[list[Fraction]]:
    if not isinstance(value, list) or len(value) != 2:
        raise SecureGeometryError(f"{label} 必须由两个平面方程组成")
    line = [parse_plane(value[0], f"{label}[0]"), parse_plane(value[1], f"{label}[1]")]
    direction = line_direction(line)
    if is_zero_vector(direction):
        raise SecureGeometryError(f"{label} 的两个平面法向量平行，不能确定唯一直线")
    if get_one_point_from_line(line) is None:
        raise SecureGeometryError(f"{label} 的两个平面没有公共交线")
    return line


def get_required(data: dict[str, Any], key: str, owner: str) -> Any:
    if key not in data:
        raise SecureGeometryError(f"{owner} 缺少字段 {key}")
    return data[key]


def dot_product(left: list[Fraction], right: list[Fraction]) -> Fraction:
    if len(left) != len(right):
        raise SecureGeometryError("内积向量长度必须一致")
    return sum(left[index] * right[index] for index in range(len(left)))


def vector_add(left: list[Fraction], right: list[Fraction]) -> list[Fraction]:
    if len(left) != len(right):
        raise SecureGeometryError("向量相加长度必须一致")
    return [left[index] + right[index] for index in range(len(left))]


def vector_sub(left: list[Fraction], right: list[Fraction]) -> list[Fraction]:
    if len(left) != len(right):
        raise SecureGeometryError("向量相减长度必须一致")
    return [left[index] - right[index] for index in range(len(left))]


def matrix_vector_multiply(matrix: list[list[Fraction]], vector: list[Fraction]) -> list[Fraction]:
    return [dot_product(row, vector) for row in matrix]


def transpose(matrix: list[list[Fraction]]) -> list[list[Fraction]]:
    return [list(row) for row in zip(*matrix)]


def mask_matrix(row_count: int) -> list[list[Fraction]]:
    column_count = max(1, row_count // 2)
    return [
        [Fraction((row_index + 1) * (column_index + 2) + (row_index % 2)) for column_index in range(column_count)]
        for row_index in range(row_count)
    ]


def secure_dot_product(alice_vector: list[Fraction], bob_vector: list[Fraction]) -> Fraction:
    matrix = mask_matrix(len(alice_vector))
    random_vector = [Fraction(index + 1) for index in range(len(matrix[0]))]
    disturbance = matrix_vector_multiply(matrix, random_vector)
    masked_alice = vector_add(alice_vector, disturbance)
    fake_inner_product = dot_product(masked_alice, bob_vector)
    bob_projection = matrix_vector_multiply(transpose(matrix), bob_vector)
    disturbance_inner_product = dot_product(random_vector, bob_projection)
    return fake_inner_product - disturbance_inner_product


def cross_product(left: list[Fraction], right: list[Fraction]) -> list[Fraction]:
    return [
        left[1] * right[2] - left[2] * right[1],
        left[2] * right[0] - left[0] * right[2],
        left[0] * right[1] - left[1] * right[0],
    ]


def is_zero_vector(vector: list[Fraction]) -> bool:
    return all(value == 0 for value in vector)


def solve_2x2(a1: Fraction, b1: Fraction, c1: Fraction, a2: Fraction, b2: Fraction, c2: Fraction):
    determinant = a1 * b2 - a2 * b1
    if determinant == 0:
        return None
    first = Fraction(c1 * b2 - c2 * b1, determinant)
    second = Fraction(a1 * c2 - a2 * c1, determinant)
    return first, second


def get_one_point_from_line(line: list[list[Fraction]]):
    first, second = line
    candidates = [
        (first[0], first[1], -first[3], second[0], second[1], -second[3], "z"),
        (first[0], first[2], -first[3], second[0], second[2], -second[3], "y"),
        (first[1], first[2], -first[3], second[1], second[2], -second[3], "x"),
    ]
    for a1, b1, c1, a2, b2, c2, fixed_axis in candidates:
        result = solve_2x2(a1, b1, c1, a2, b2, c2)
        if result is None:
            continue
        first_value, second_value = result
        if fixed_axis == "z":
            return [first_value, second_value, Fraction(0)]
        if fixed_axis == "y":
            return [first_value, Fraction(0), second_value]
        return [Fraction(0), first_value, second_value]
    return None


def line_direction(line: list[list[Fraction]]) -> list[Fraction]:
    first_normal = line[0][:3]
    second_normal = line[1][:3]
    return cross_product(first_normal, second_normal)


def get_two_points_from_line(line: list[list[Fraction]]) -> tuple[list[Fraction], list[Fraction]]:
    first_point = get_one_point_from_line(line)
    if first_point is None:
        raise SecureGeometryError("找不到直线上的点")
    direction = line_direction(line)
    second_point = vector_add(first_point, direction)
    return first_point, second_point


def get_three_points_from_plane(plane: list[Fraction]) -> tuple[list[Fraction], list[Fraction], list[Fraction]]:
    a, b, c, d = plane
    if a != 0:
        return (
            [Fraction(-d, a), Fraction(0), Fraction(0)],
            [Fraction(-d - b, a), Fraction(1), Fraction(0)],
            [Fraction(-d - c, a), Fraction(0), Fraction(1)],
        )
    if b != 0:
        return (
            [Fraction(0), Fraction(-d, b), Fraction(0)],
            [Fraction(1), Fraction(-d - a, b), Fraction(0)],
            [Fraction(0), Fraction(-d - c, b), Fraction(1)],
        )
    return (
        [Fraction(0), Fraction(0), Fraction(-d, c)],
        [Fraction(1), Fraction(0), Fraction(-d - a, c)],
        [Fraction(0), Fraction(1), Fraction(-d - b, c)],
    )


def point_plane_value(point: list[Fraction], plane: list[Fraction]) -> Fraction:
    return secure_dot_product([point[0], point[1], point[2], Fraction(1)], plane)


def point_on_plane(point: list[Fraction], plane: list[Fraction]) -> bool:
    return point_plane_value(point, plane) == 0


def point_on_line(point: list[Fraction], line: list[list[Fraction]]) -> bool:
    return point_on_plane(point, line[0]) and point_on_plane(point, line[1])


def calculate_point_line(alice: dict[str, Any], bob: dict[str, Any]) -> str:
    point = parse_point(get_required(alice, "point", "Alice"), "Alice.point")
    line = parse_line(get_required(bob, "line", "Bob"), "Bob.line")
    return "点在直线上" if point_on_line(point, line) else "点不在直线上"


def calculate_point_plane(alice: dict[str, Any], bob: dict[str, Any]) -> str:
    point = parse_point(get_required(alice, "point", "Alice"), "Alice.point")
    plane = parse_plane(get_required(bob, "plane", "Bob"), "Bob.plane")
    return "点在平面上" if point_on_plane(point, plane) else "点不在平面上"


def calculate_line_line(alice: dict[str, Any], bob: dict[str, Any]) -> str:
    first_line = parse_line(get_required(alice, "line", "Alice"), "Alice.line")
    second_line = parse_line(get_required(bob, "line", "Bob"), "Bob.line")
    first_point, second_point = get_two_points_from_line(first_line)
    if point_on_line(first_point, second_line) and point_on_line(second_point, second_line):
        return "重合"
    first_direction = line_direction(first_line)
    second_direction = line_direction(second_line)
    direction_cross = cross_product(first_direction, second_direction)
    if is_zero_vector(direction_cross):
        return "平行"
    second_line_point, _ = get_two_points_from_line(second_line)
    coplanar_value = dot_product(vector_sub(second_line_point, first_point), direction_cross)
    return "相交" if coplanar_value == 0 else "异面"


def calculate_line_plane(alice: dict[str, Any], bob: dict[str, Any]) -> str:
    line = parse_line(get_required(alice, "line", "Alice"), "Alice.line")
    plane = parse_plane(get_required(bob, "plane", "Bob"), "Bob.plane")
    first_point, second_point = get_two_points_from_line(line)
    if point_on_plane(first_point, plane) and point_on_plane(second_point, plane):
        return "重合"
    direction = line_direction(line)
    normal = plane[:3]
    return "平行" if dot_product(direction, normal) == 0 else "相交"


def calculate_plane_plane(alice: dict[str, Any], bob: dict[str, Any]) -> str:
    first_plane = parse_plane(get_required(alice, "plane", "Alice"), "Alice.plane")
    second_plane = parse_plane(get_required(bob, "plane", "Bob"), "Bob.plane")
    points = get_three_points_from_plane(first_plane)
    if all(point_on_plane(point, second_plane) for point in points):
        return "重合"
    normal_cross = cross_product(first_plane[:3], second_plane[:3])
    return "平行" if is_zero_vector(normal_cross) else "相交"


CALCULATORS = {
    "point_line": calculate_point_line,
    "point_plane": calculate_point_plane,
    "line_line": calculate_line_line,
    "line_plane": calculate_line_plane,
    "plane_plane": calculate_plane_plane,
}


def calculate_secure_geometry(relation: str, alice: dict[str, Any], bob: dict[str, Any]) -> dict[str, Any]:
    if relation not in CALCULATORS:
        raise SecureGeometryError("relation 只能是 point_line、point_plane、line_line、line_plane、plane_plane")
    if not isinstance(alice, dict) or not isinstance(bob, dict):
        raise SecureGeometryError("alice 和 bob 必须是对象")
    result = CALCULATORS[relation](alice, bob)
    return {
        "relation": relation,
        "relation_name": RELATION_NAMES[relation],
        "result": result,
        "steps": RELATION_STEPS[relation],
        "note": "当前为教学模拟版本，不保存用户输入；页面展示的是协议思想，不是生产级密码系统。",
    }
