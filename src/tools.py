# tools.py
import struct


def read_half_float(data: bytes, offset: int) -> float:
    """读取半精度浮点数 (IEEE 754-2008)"""
    try:
        (value,) = struct.unpack_from("H", data, offset)

        if value == 0:
            return 0.0  # 零值直接返回

        sign = -1 if (value & 0x8000) else 1
        exponent = (value >> 10) & 0x1F
        mantissa = value & 0x3FF

        if exponent == 0:
            # 非正规数或零
            return sign * (mantissa / (2**10)) * 2**-14
        elif exponent == 31:
            # 无穷大或 NaN
            return float("inf") if mantissa == 0 else float("nan")
        else:
            # 正规数
            return sign * (1 + mantissa / (2**10)) * 2 ** (exponent - 15)

    except struct.error as e:
        raise ValueError(f"无法解包半精度浮点数: {e}") from e
