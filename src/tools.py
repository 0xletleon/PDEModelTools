# tools.py
import struct


def read_half_float(data, offset):
    """读取半精度浮点数"""
    try:
        value = struct.unpack('H', data[offset:offset + 2])[0]
        sign = (value >> 15) & 0x1
        exponent = (value >> 10) & 0x1F
        mantissa = value & 0x3FF

        if exponent == 0:
            return ((-1) ** sign) * (2 ** -14) * (mantissa / 1024)
        elif exponent == 31:
            return 0.0  # 简化处理特殊值
        else:
            return ((-1) ** sign) * (2 ** (exponent - 15)) * (1 + mantissa / 1024)
    except:
        return 0.0
