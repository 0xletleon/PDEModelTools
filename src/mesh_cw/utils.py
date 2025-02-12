# mesh_cw\utils.py
import struct
import traceback
from typing import List, Tuple, Dict, Optional, Any
from dataclasses import dataclass
from .. import tools
from ..log import log

# 常量
HEADER_SIZE = 0x1D
VERTEX_HEADER_OFFSET = 0x19
COLORMAP_PATTERN = b"ColorMap"
COLORMAP_PATH_OFFSET = 0x8
COLORMAP_DATA_OFFSET = 0xC


@dataclass
class ColorMapData:
    """贴图数据结构"""

    path: str = ""
    name: str = ""


def read_dynamic_head(self, data):
    """读取头部信息"""
    log.debug(">>> 开始读取头部信息")

    try:
        # 网格信息
        mesh_info = []
        # 文件读取位置
        data_index = 0
        # 读取包含的对象数量1
        include_obj_number1 = struct.unpack_from("<I", data, data_index)[0]
        # 修正数据读取位置
        data_index += 0x4

        # 读取包含的对象名称
        for _ in range(include_obj_number1):
            # 读取物体名称长度
            name_length = struct.unpack_from("<I", data, data_index)[0]
            # 修正数据读取位置
            data_index += 0x4
            # 读取物体名称
            obj_name = struct.unpack_from(f"<{name_length}s", data, data_index)[
                0
            ].decode("utf-8")
            log.debug("对象名称: %s", obj_name)
            # 保存名称
            mesh_info.append(obj_name)
            # 修正数据读取位置
            data_index += name_length

        # 读取包含的对象数量2
        include_obj_number2 = struct.unpack_from("<I", data, data_index)[0]
        # 修正数据读取位置
        data_index += 0x4

        # 检查头部数量是否一致
        if include_obj_number1 != include_obj_number2:
            log.debug("! 头部信息解析失败: 包含的对象数量不一致")
            self.report({"ERROR"}, "头部信息解析失败")
            traceback.print_exc()
            return {"CANCELLED"}

        # 跳过物体的 MinPos MaxPos
        skip_len = include_obj_number1 * 0x18
        log.debug("data_index: %s", hex(data_index))

        # 修正数据读取位置
        data_index += skip_len

        log.debug("data_index: %s skip_len: %s", hex(data_index), hex(skip_len))

        # 返回 物体开始位置，物体信息
        return data_index, mesh_info
    except Exception as e:
        log.debug("! 读取头部信息失败: %s", e)
        self.report({"ERROR"}, "读取头部信息失败")
        traceback.print_exc()
        return {"CANCELLED"}


# 定义读取头部信息函数
def read_head(data, start_index):
    """读取头部信息"""
    log.debug(">>> 开始读取头部信息: %s", hex(start_index))

    # 检查是否有足够的字节数进行解包
    if len(data) < start_index + 0x1D:
        log.debug("! 头部信息解析失败: 不足的字节数在偏移量 %s", start_index)
        traceback.print_exc()
        return None
        # self.report({"ERROR"}, "头部信息解析失败")
        # return {"CANCELLED"}

    log.debug("start_index: %s", hex(start_index))
    # 文物体包含网格物体数量
    mesh_obj_number = struct.unpack_from("<I", data, start_index)[0]
    # 本物体面数据组数量
    mesh_face_group_number = struct.unpack_from("<I", data, start_index + 0x4)[0]
    # 本网格变换矩阵数量
    mesh_matrices_number = struct.unpack_from("<I", data, start_index + 0x8)[0]
    # 本网格字节总数
    mesh_byte_size = struct.unpack_from("<I", data, start_index + 0x19)[0]

    # 打印头部信息
    log.debug(
        "<<< 网格物体数量: %s 本物体面数据组数量 %s 本网格变换矩阵数量: %s 本网格字节总数: %s",
        hex(mesh_obj_number),
        hex(mesh_face_group_number),
        hex(mesh_matrices_number),
        hex(mesh_byte_size),
    )

    # 返回文件中包含网格物体数量, 本物体面数据组数量, 本网格变换矩阵数量, 本网格字节总数
    return mesh_obj_number, mesh_face_group_number, mesh_matrices_number, mesh_byte_size


# 定义解析顶点数据函数
def read_vertices(self, vertices_data, mesh_matrices_number, mesh_byte_size):
    """解析顶点数据"""
    log.debug(">>> 开始解析顶点数据")
    # 顶点数据
    vertices = []
    # 法向数据
    normals = []
    # UV 坐标数据
    uvs = []

    # 数据块的大小 (0x34 是一个猜测的大小，可能需要根据实际情况动态计算)
    block_size = int(mesh_byte_size / mesh_matrices_number)
    if block_size <= 0:
        log.debug("! 数据块的大小计算失败: %s", block_size)
        self.report({"ERROR"}, "数据块的大小计算失败")
        traceback.print_exc()
        return {"CANCELLED"}

    log.debug("> 数据块的大小: %s", block_size)

    # 解析顶点数据
    try:
        for mni in range(mesh_matrices_number):
            # 计算当前块的起始位置
            mniv = block_size * mni
            # 确保有足够的字节进行解包
            if mniv + block_size <= mesh_byte_size:
                vx = struct.unpack_from("f", vertices_data, mniv)[0]
                vy = struct.unpack_from("f", vertices_data, mniv + 0x4)[0]
                vz = struct.unpack_from("f", vertices_data, mniv + 0x8)[0]
                # 将顶点添加到顶点列表
                vertices.append((vx, vy, vz))

                # 读取法向数据
                nx = tools.read_half_float(vertices_data, mniv + 0x0C)
                ny = tools.read_half_float(vertices_data, mniv + 0x0E)
                nz = tools.read_half_float(vertices_data, mniv + 0x10)
                normals.append((nx, ny, nz))
                # log.debug(">> 读取法向数据: %s , %s , %s", nx, ny, nz)

                # 读取UV坐标
                uv_start = mniv + block_size - 0x8
                # log.debug(">> uv_start: %s , mniv : %s ", uv_start, mniv)
                u = tools.read_half_float(vertices_data, uv_start)
                v = tools.read_half_float(vertices_data, uv_start + 0x2)
                uvs.append((u, 1 - v))
                # log.debug(">> 读取UV坐标: %s , %s ", u, 1 - v)

            else:
                log.debug("! 顶点数据解析失败: 不足的字节数在偏移量 %s", mniv)
                break
    except Exception as e:
        log.debug("! 顶点数据解析失败: %s", e)
        # self.report({"ERROR"}, f"顶点数据解析失败 : {e}")
        # traceback.print_exc()
        # return {"CANCELLED"}
        return None

    log.debug("<<< 顶点数据解析完成: %s 组", hex(len(vertices)))
    # 返回 顶点数据, 法向数据, UV坐标数据
    return vertices, normals, uvs, block_size


# 定义解析面数据函数
def read_faces(self, faces_data_block, index_length):
    """解析面数据"""
    log.debug(">>> 开始解析面数据 %s", hex(index_length))
    faces = []
    try:
        # 确保有足够的字节进行解包
        for i in range(0, index_length, 12):
            f0 = struct.unpack_from("H", faces_data_block, i)[0]
            f1 = struct.unpack_from("H", faces_data_block, i + 0x4)[0]
            f2 = struct.unpack_from("H", faces_data_block, i + 0x8)[0]
            faces.append((f0, f1, f2))
            # log.debug("> 解析面: %s -> %s %s %s",f0,f1,f2)
    except Exception as e:
        log.debug("! 面数据解析失败: %s", e)
        # self.report({"ERROR"}, f"面数据解析失败 : {e}")
        traceback.print_exc()
        # return {"CANCELLED"}
        return None

    log.debug("<<< 面数据读取完毕: %s 组", hex(len(faces)))

    return faces


# 定义分割网格数据函数
def split_mesh(self, data):
    """分割网格数据"""
    log.debug(">>> 开始分割网格数据")

    # 数据起始位置
    data_start = 0
    # 是否为首次读取
    # first_read = True
    # 网格对象
    mesh_obj = []

    # 读取动态头部
    data_index, mesh_info = read_dynamic_head(self, data)
    # 修正数据起始位置
    data_start = data_index
    log.debug("> fix数据起始位置: %s", hex(data_start))

    try:
        for mi_name in mesh_info:
            log.debug(">>> 读取网格信息名称: %s", mi_name)

            # 读取头部信息
            read_head_temp = read_head(data, data_start)

            if read_head_temp is None:
                log.debug("! 读取头部信息失败")
                # return mesh_obj
                break

            # 返回文件中包含网格物体数量, 本物体面数据组数量, 本网格变换矩阵数量, 本网格字节总数
            (
                mesh_obj_number,
                mesh_face_group_number,
                mesh_matrices_number,
                mesh_byte_size,
            ) = read_head_temp

            # 获取顶点数据长度
            vertices_data = data[data_start + 0x1D : data_start + 0x1D + mesh_byte_size]
            log.debug("> 获取顶点数据长度: %s", hex(len(vertices_data)))
            if len(vertices_data) <= 0:
                log.debug("! 获取顶点数据长度失败")
                break

            # 解析顶点数据块
            read_vertices_temp = read_vertices(
                self, vertices_data, mesh_matrices_number, mesh_byte_size
            )
            # 判断是否读取失败
            if read_vertices_temp is None:
                log.debug("! 解析顶点数据失败")
                # return mesh_obj
                break
            # 顶点数据, UV坐标数据, 切线数据
            vertices_array, normals, uvs, block_size = read_vertices_temp

            # 获取面数据块大小
            faces_data_size = struct.unpack(
                "<I",
                data[
                    data_start
                    + 0x1D
                    + mesh_byte_size : data_start
                    + 0x1D
                    + mesh_byte_size
                    + 0x4
                ],
            )[0]
            log.debug("> 获取面数据块大小: %s", hex(faces_data_size))
            # 获取面数据块
            faces_data_block = data[
                data_start
                + 0x1D
                + mesh_byte_size
                + 0x4 : data_start
                + 0x1D
                + mesh_byte_size
                + 0x4
                + faces_data_size
            ]
            log.debug("> 索引地址: %s", hex(data_start + 0x1D + mesh_byte_size + 0x4))
            log.debug("> 获取面数据块: %s", hex(len(faces_data_block)))
            # 解析面数据块
            faces_array = read_faces(self, faces_data_block, len(faces_data_block))
            # 判断是否读取失败
            if faces_array is None:
                log.debug("! 解析面数据失败")
                # return mesh_obj
                break

            # 结束位置,也是新的开始
            data_start = data_start + 0x1D + mesh_byte_size + 0x4 + faces_data_size
            log.debug("> data_start: %s", hex(data_start))

            # 查找ColorMap
            colors_data = data[data_start : len(data)]
            readed_colormap = read_colormap(self, colors_data)
            log.debug("> colormap: %s", readed_colormap)

            # 向mesh_obj中添加数据
            mesh_obj.append(
                {
                    "name": str(mi_name),
                    "vertices": {
                        "mesh_obj_number": mesh_obj_number,
                        "mesh_matrices_number": mesh_matrices_number,
                        "mesh_byte_size": mesh_byte_size,
                        "data": vertices_array,
                    },
                    "faces": {"size": faces_data_size, "data": faces_array},
                    "normals": normals,
                    "uvs": uvs,
                    "colormap": readed_colormap,
                }
            )

            # 检查是否到达文件末尾
            log.debug(
                "len(mesh_obj): %s ,mesh_obj_number: %s", len(mesh_obj), mesh_obj_number
            )
            # if len(mesh_obj) >= mesh_obj_number:
            #     log.debug("<<< 数据到达尾部")
            #     break

            # 查找下一个头部
            next_mesh_start = find_next_head(data, data_start, block_size)

            if next_mesh_start is None:
                log.debug("<<< 没有找到下一个头部")
                return mesh_obj
            log.debug("<<< 下一个头部: %s", hex(next_mesh_start))
            # 修正位置
            data_start = next_mesh_start

        return mesh_obj
    except Exception as e:
        log.debug("! 分割网格数据失败: %s", e)
        traceback.print_exc()
        return mesh_obj


def read_colormap(self, data: bytes) -> ColorMapData:
    """读取贴图信息"""
    colormap = ColorMapData()

    try:
        position = data.find(COLORMAP_PATTERN)
        if position != -1:
            # path_length = struct.unpack_from(
            #     "<I", data, position + COLORMAP_PATH_OFFSET
            # )[0]
            path_length = struct.unpack_from(
                "<B", data, position + COLORMAP_PATH_OFFSET
            )[0]
            path = data[
                position
                + COLORMAP_DATA_OFFSET : position
                + COLORMAP_DATA_OFFSET
                + path_length
            ].decode("utf-8", errors="replace")
            colormap.path = path
            colormap.name = extract_name_from_path(path)
            log.debug("> colormap path: %s, name: %s", colormap.path, colormap.name)

    except Exception as e:
        log.debug("! 解析颜色数据失败: %s", e)
        traceback.print_exc()

    return colormap


def extract_name_from_path(path: str) -> str:
    """从路径中提取文件名（不包含扩展名）"""
    try:
        file_name = path.split("/")[-1]
        return file_name.split(".")[0]
    except Exception:
        return ""


def find_next_head(data: bytes, data_start: int, block_size: int) -> Optional[int]:
    """查找下一个网格头部"""
    data_len = len(data)
    log.debug(
        ">> 查找下一个头部: start:%s block_size:%s data_size:%s",
        hex(data_start),
        hex(block_size),
        hex(data_len),
    )

    if data_start >= data_len:
        log.debug("! 起始位置超出数据范围")
        return None

    # 逐字节查找头部
    while data_start < data_len - HEADER_SIZE:
        try:
            # 读取关键数据
            vertex_groups = read_struct(data, "<I", data_start + 0x8)
            texture_index = read_struct(data, "<I", data_start + 0x14)
            vertex_bytes = read_struct(data, "<I", data_start + VERTEX_HEADER_OFFSET)

            # 验证数据有效性
            if (
                vertex_groups < vertex_bytes
                and vertex_groups > 0
                and vertex_bytes > 0
                and texture_index <= 0xFF
                and vertex_groups * block_size == vertex_bytes
            ):

                log.debug("找到下一个头部位置: %s", hex(data_start))
                return data_start

            data_start += 1
        except Exception as e:
            log.debug("! 查找下一个网格头部失败: %s", e)
            traceback.print_exc()

    log.debug("! 未找到下一个头部")
    return None


def read_struct(data: bytes, format_str: str, offset: int) -> Any:
    """安全读取结构数据"""
    try:
        return struct.unpack_from(format_str, data, offset)[0]
    except struct.error as e:
        log.error(f"结构读取失败: {e}")
        return None
