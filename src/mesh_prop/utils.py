# mesh_prop\utils.py
import struct
import traceback

from .. import tools
from ..log import log


# 定义读取头部信息函数
def read_head(self, data, start_index):
    """读取头部信息"""
    log.debug(">>> 开始读取头部信息: %s", hex(start_index))

    # 检查是否有足够的字节数进行解包
    if len(data) < start_index + 0x1D:
        log.debug("! 头部信息解析失败: 不足的字节数在偏移量 %s", hex(start_index))
        self.report({"ERROR"}, "头部信息解析失败")
        traceback.print_exc()
        return {"CANCELLED"}

    log.debug("start_index: %s", hex(start_index))
    # 文件中包含网格物体数量(仅头一个文件有用)
    mesh_obj_number = struct.unpack_from("<I", data, start_index)[0]
    # 本物体面数据组数量
    mesh_face_group_number = struct.unpack_from("<I", data, start_index + 4)[0]
    # 本网格变换矩阵数量
    mesh_matrices_number = struct.unpack_from("<I", data, start_index + 8)[0]
    # 4个字节00标志（注释掉）
    # zeros_tag = struct.unpack_from("<I", data, 36)[0]
    # 1个字节01标志（注释掉）
    # zeroone_tag = struct.unpack_from("<B", data, 48)[0]
    # 本网格字节总数
    mesh_byte_size = struct.unpack_from("<I", data, start_index + 25)[0]

    # 打印头部信息
    log.debug(
        "<<< 网格物体数量: %s 本物体面数据组数量: %s 本网格变换矩阵数量: %s 本网格字节总数: %s",
        hex(mesh_obj_number), hex(mesh_face_group_number), hex(mesh_matrices_number), hex(mesh_byte_size)
    )

    # 返回文件中包含网格物体数量, 本网格变换矩阵数量, 本网格字节总数
    return mesh_obj_number, mesh_face_group_number, mesh_matrices_number, mesh_byte_size


# 定义解析顶点数据函数
def read_vertices(self, vertices_data, mesh_matrices_number, mesh_byte_size):
    """解析顶点数据"""
    log.debug(">>> 开始解析顶点数据")
    # 顶点数据
    vertices = []
    # 法线数据
    normals = []
    # UV 坐标数据
    uvs = []

    # 数据块的大小 (0x34)
    block_size = int(mesh_byte_size / mesh_matrices_number)
    if block_size <= 0:
        log.debug("! 数据块的大小计算失败: %s", hex(block_size))
        self.report({"ERROR"}, "数据块的大小计算失败")
        traceback.print_exc()
        return {"CANCELLED"}

    log.debug("> 数据块的大小: %s", hex(block_size))

    # 解析顶点数据
    try:
        for mni in range(mesh_matrices_number):
            # 计算当前块的起始位置
            mniv = block_size * mni
            # 确保有足够的字节进行解包
            if mniv + block_size <= mesh_byte_size:
                vx = struct.unpack_from("f", vertices_data, mniv)[0]
                vy = struct.unpack_from("f", vertices_data, mniv + 4)[0]
                vz = struct.unpack_from("f", vertices_data, mniv + 8)[0]
                # 将顶点添加到顶点列表
                vertices.append((vx, vy, vz))

                # 读取法线数据
                nx = tools.read_half_float(vertices_data, mniv + 0x0c)
                ny = tools.read_half_float(vertices_data, mniv + 0x0e)
                nz = tools.read_half_float(vertices_data, mniv + 0x10)
                normals.append((nx, ny, nz))
                # log.debug(">> 读取法线数据: %s , %s , %s", nx, ny, nz)

                # 读取UV坐标
                # 金币的UV有问题！！！或者说方法有问题！！！
                uv_start = mniv + block_size - 0xc
                # log.debug(">> uv_start: %s , mniv : %s ", uv_start, mniv)
                u = tools.read_half_float(vertices_data, uv_start)
                v = tools.read_half_float(vertices_data, uv_start + 0x2)
                uvs.append((u, 1 - v))
                log.debug(">> 读取UV坐标: %s , %s ", u, 1 - v)
            else:
                log.debug("! 顶点数据解析失败: 不足的字节数在偏移量 %s", mniv)
                break
    except Exception as e:
        log.debug("! 顶点数据解析失败: %s", e)
        self.report({"ERROR"}, f"顶点数据解析失败 : {e}")
        traceback.print_exc()
        return {"CANCELLED"}

    log.debug("<<< 顶点数据解析完成: %s 组", len(vertices))

    return vertices, normals, uvs


# 定义解析面数据函数
def read_faces(self, faces_data_block, index_length):
    """解析面数据"""
    log.debug(">>> 开始解析面数据 %s", index_length)
    faces = []
    try:
        # 确保有足够的字节进行解包
        for i in range(0, index_length, 12):
            f0 = struct.unpack_from("H", faces_data_block, i)[0]
            f1 = struct.unpack_from("H", faces_data_block, i + 4)[0]
            f2 = struct.unpack_from("H", faces_data_block, i + 8)[0]
            faces.append((f0, f1, f2))
            # log.debug("> 解析面: %s -> %s %s %s",i, f0, f1, f2)
    except Exception as e:
        log.debug("! 面数据解析失败: %s", e)
        self.report({"ERROR"}, f"面数据解析失败 : {e}")
        traceback.print_exc()
        return {"CANCELLED"}

    log.debug("<<< 面数据读取完毕: %s 组", hex(len(faces)))

    return faces


# 定义分割网格数据函数
def split_mesh(self, data):
    """分割网格数据"""
    log.debug(">>> 开始分割网格数据")

    # 数据起始位置
    data_start = 0
    # 是否为首次读取
    first_read = True
    # 网格对象
    mesh_obj = []

    try:
        while True:
            if first_read:
                data_start += 24
                first_read = False

            # 读取头部信息 -> 文件中包含网格物体数量, 本物体面数据组数量, 本网格变换矩阵数量, 本网格字节总数
            (
                mesh_obj_number,
                mesh_face_group_number,
                mesh_matrices_number,
                mesh_byte_size,
            ) = read_head(self, data, data_start)

            # 获取顶点数据长度
            vertices_data = data[data_start + 0x1D: data_start + 0x1D + mesh_byte_size]
            log.debug("> 获取顶点数据长度: %s", hex(len(vertices_data)))
            if len(vertices_data) <= 0:
                log.debug("! 获取顶点数据长度失败")
                self.report({"ERROR"}, "获取顶点数据长度失败")
                traceback.print_exc()
                return {"CANCELLED"}

            # 解析顶点数据块
            vertices_array, normals, uvs = read_vertices(
                self, vertices_data, mesh_matrices_number, mesh_byte_size
            )

            # 获取面数据块大小
            faces_data_size = struct.unpack(
                "<I",
                data[
                data_start
                + 0x1D
                + mesh_byte_size: data_start
                                  + 0x1D
                                  + mesh_byte_size
                                  + 4
                ],
            )[0]
            log.debug("> 获取面数据块大小: %s", hex(faces_data_size))
            # 获取面数据块
            faces_data_block = data[
                               data_start
                               + 0x1D
                               + mesh_byte_size
                               + 4: data_start
                                    + 0x1D
                                    + mesh_byte_size
                                    + 4
                                    + faces_data_size
                               ]
            log.debug("> 索引地址: %s", hex(data_start + 0x1d + mesh_byte_size + 4))
            log.debug("> 获取面数据块: %s", hex(len(faces_data_block)))
            # 解析面数据块
            faces_array = read_faces(self, faces_data_block, len(faces_data_block))

            # 向mesh_obj中添加数据
            mesh_obj.append(
                {
                    "vertices": {
                        "mesh_obj_number": mesh_obj_number,
                        "mesh_matrices_number": mesh_matrices_number,
                        "mesh_byte_size": mesh_byte_size,
                        "data": vertices_array,
                    },
                    "faces": {"size": faces_data_size, "data": faces_array},
                    "uvs": uvs,
                    "normals": normals,
                }
            )

            # 结束位置,也是新的开始
            data_start += 0x1D + mesh_byte_size + 4 + faces_data_size
            log.debug("> data_start: %s", hex(data_start))

            # 检查是否到达文件末尾
            if len(mesh_obj) >= mesh_obj[0]["vertices"]["mesh_obj_number"] - 1:
                log.debug("<<< 数据到达尾部")
                break

        return mesh_obj
    except Exception as e:
        log.debug("! 分割网格数据失败: %s", e)
        self.report({"ERROR"}, f"分割网格数据失败: {e}")
        traceback.print_exc()
        return {"CANCELLED"}
