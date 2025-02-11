# mesh_map\utils.py
import struct
import traceback

from .. import tools
from ..log import log


def find_next_head(data, data_start, block_size):
    """查找下一个物体头部"""
    data_len = len(data)
    log.debug(
        ">> 进入find_next_head: st:%s bs:%s DATA大小: %s <<",
        hex(data_start),
        hex(block_size),
        hex(data_len),
    )

    # 检查是否超出数据范围
    if data_start >= data_len:
        log.debug(
            "<<<<<<<<<<<<<<<<<<<<<!!! 没有找到下一个物体头部,开始查找地址: %s",
            hex(data_start),
        )
        return None

    # 逐字节检查
    while data_start < data_len - 0x1D:  # 确保剩余数据足够检查头部
        # 疑似变换矩阵组数
        vg = struct.unpack_from("<I", data, data_start + 0x8)[0]
        # 疑似贴图索引
        di = struct.unpack_from("<I", data, data_start + 0x14)[0]
        # 疑似变换矩阵总字节
        vb = struct.unpack_from("<I", data, data_start + 0x19)[0]
        # log.debug("vg: %s vb: %s vg*bs: %s", hex(vg), hex(vb), hex(vg * block_size))

        if vg >= vb:
            data_start += 1
            # log.debug("*** vg >= vb,跳过1字节 data_start: %s", hex(data_start))
            continue
        # 非0判断
        if vg == 0x0:
            data_start += 1
            # log.debug("*** vg == 0x0,跳过1字节 data_start: %s", hex(data_start))
            continue
        if vb == 0x0:
            data_start += 1
            # log.debug("*** vb == 0x0,跳过1字节 data_start: %s", hex(data_start))
            continue
        # 贴图索引不可能太大
        if di > 0xFF:
            data_start += 1
            # log.debug(
            #     "***!!! di > 0xA,跳过1字节 data_start: %s ,di: %s",
            #     hex(data_start),
            #     hex(di),
            # )
            continue

        # 判断是否为物体头部
        if vg * block_size == vb:
            log.debug("!!!@@@ 找到下一个物体头部: %s", hex(data_start))
            return data_start

        data_start += 1

    log.debug(
        "!!!@@@!!! 没有找到下一个物体头部,开始查找地址: %s",
        hex(data_start),
    )
    return None


def read_map_first_head(self, data):
    """读取地图第一个头部信息"""
    log.debug(">>> 开始读取地图第一个头部信息")
    # 读取位置
    data_index = 0

    # 确保有足够的数据
    if len(data) < 24:
        log.debug("Error: Not enough data")
        return

    # 读取相机位置?
    x1, y1, z1, x2, y2, z2 = struct.unpack_from("<ffffff", data)
    log.debug("Camera 1 Position: x1= %s, y1=%s, z1=%s", x1, y1, z1)
    log.debug("Camera 2 Position: x2=%s, y2=%s, z2=%s", x2, y2, z2)

    # 更新读取位置
    data_index += 24

    return data_index


# 定义读取头部信息函数
def read_head(self, data, start_index):
    """读取头部信息"""
    log.debug("↓↓↓↓↓↓↓ >>> 开始读取头部信息 st: %s ↓↓↓↓↓↓", hex(start_index))

    # 检查是否有足够的字节数进行解包
    if len(data) < start_index + 29:
        log.debug("! 头部信息解析失败: 不足的字节数在偏移量 %s ", start_index)
        # self.report({"ERROR"}, "头部信息解析失败")
        traceback.print_exc()
        # return {"CANCELLED"}
        return None

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
        "<<< 网格物体数量: %s 本物体面数据组数量 %s 本网格变换矩阵数量: %s 本网格字节总数: %s",
        hex(mesh_obj_number),
        hex(mesh_face_group_number),
        hex(mesh_matrices_number),
        hex(mesh_byte_size),
    )

    # 返回文件中包含网格物体数量, 本网格变换矩阵数量, 本网格字节总数
    return mesh_obj_number, mesh_matrices_number, mesh_byte_size


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
    # if block_size != 52:
    #     log.debug("! 数据块的大小计算失败: %s", block_size)
    #     # self.report({"ERROR"}, "数据块的大小计算失败")
    #     traceback.print_exc()
    #     # return {"CANCELLED"}
    #     return None

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
                nx = tools.read_half_float(vertices_data, mniv + 0x0C)
                ny = tools.read_half_float(vertices_data, mniv + 0x0E)
                nz = tools.read_half_float(vertices_data, mniv + 0x10)
                normals.append((nx, ny, nz))
                # log.debug(">> 读取法线数据: %s , %s , %s", nx, ny, nz)

                # 读取UV坐标
                uv_start = mniv + block_size - 0x10
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
        traceback.print_exc()
        # return {"CANCELLED"}
        return None

    log.debug("<<< 顶点数据解析完成: %s 组", len(vertices))

    return vertices, normals, uvs, block_size


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
        # self.report({"ERROR"}, f"面数据解析失败 : {e}")
        traceback.print_exc()
        # return {"CANCELLED"}
        return None

    log.debug("<<< 面数据读取完毕: %s 组", len(faces))

    return faces


# 定义分割网格数据函数
def split_mesh(self, data):
    """分割网格数据"""
    log.debug(">>> 开始分割网格数据")
    # 数据起始位置
    data_start = 0
    # 网格对象
    mesh_obj = []

    # 读取动态头部
    data_index = read_map_first_head(self, data)
    # 修正数据起始位置
    data_start = data_index
    log.debug("> fix数据起始位置: %s", hex(data_start))

    # 总物体数
    total_mesh_obj_number = 0
    # 已读计数
    readed_index = 0

    try:

        while True:
            # 读取头部信息
            read_head_temp = read_head(self, data, data_start)
            # 判断是否读取失败
            if read_head_temp is None:
                log.debug("! 读取头部信息失败")
                # return mesh_obj
                break
            # 解析头部信息 -> 文件中包含网格物体数量, 本网格变换矩阵数量, 本网格字节总数
            mesh_obj_number, mesh_matrices_number, mesh_byte_size = read_head_temp

            # 更新总物体数
            if total_mesh_obj_number == 0:
                total_mesh_obj_number = mesh_obj_number

            # 获取顶点数据长度
            vertices_data = data[data_start + 0x1D : data_start + 0x1D + mesh_byte_size]
            log.debug("> 获取顶点数据长度: %s", hex(len(vertices_data)))
            if len(vertices_data) <= 0:
                log.debug("! 获取顶点数据长度失败")
                # self.report({"ERROR"}, "获取顶点数据长度失败")
                traceback.print_exc()
                # return {"CANCELLED"}
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
                    + 4
                ],
            )[0]
            log.debug("> 获取面数据块大小: %s", hex(faces_data_size))
            if data_start + 0x1D + mesh_byte_size + 0x4 + faces_data_size >= len(data):
                log.debug(
                    "! 获取面数据块失败,遇到还未识别的数据块！ 开始地址:%s 偏移地址: %s",
                    hex(data_start + 0x1D),
                    hex(data_start + 0x1D + mesh_byte_size),
                )

                # 读取剩余数据(着色器,贴图,动画等) -> 是否存在另一个物体, 另一个物体头部地址
                find_start = find_next_head(
                    data,
                    data_start + 0x1D + mesh_byte_size,
                    block_size,
                )
                if find_start is None:
                    log.debug(
                        "! 111未找到下一个物体头部地址, mesh_obj len: %s",
                        hex(len(mesh_obj)),
                    )
                    # 直接停止!
                    break
                data_start = find_start
                # 已读+1
                readed_index += 1
                continue
                # break
            # 获取面数据块
            faces_data_block = data[
                data_start
                + 0x1D
                + mesh_byte_size
                + 4 : data_start
                + 0x1D
                + mesh_byte_size
                + 4
                + faces_data_size
            ]
            log.debug("> 索引地址: %s", hex(data_start + 0x1D + mesh_byte_size + 4))
            log.debug("> 获取面数据块: %s", hex(len(faces_data_block)))
            # 解析面数据块
            faces_array = read_faces(self, faces_data_block, len(faces_data_block))
            # 判断是否读取失败
            if faces_array is None:
                log.debug("! 解析面数据失败")
                # return mesh_obj
                break

            # # 向mesh_obj中添加数据
            # mesh_obj.append(
            #     {
            #         "vertices": {
            #             "mesh_obj_number": mesh_obj_number,
            #             "mesh_matrices_number": mesh_matrices_number,
            #             "mesh_byte_size": mesh_byte_size,
            #             "data": vertices_array,
            #         },
            #         "faces": {"size": faces_data_size, "data": faces_array},
            #         "uvs": uvs,
            #         "normals": normals,
            #         "colormap": color_map_val
            #     }
            # )

            # 结束位置,也是新的开始
            data_start += 0x1D + mesh_byte_size + 4 + faces_data_size
            log.debug("> data_start: %s", hex(data_start))

            # 已读+1
            readed_index += 1
            log.debug(
                "total_mesh_obj_number: %s , readed_index: %s",
                total_mesh_obj_number,
                readed_index,
            )

            if readed_index >= total_mesh_obj_number:
                log.debug("<<< 数据到达尾部")
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
                        "colormap": {
                            "path": "",
                            "name": "",
                        },
                    }
                )
                break

            # 读取剩余数据(着色器,贴图,动画等) -> 是否存在另一个物体, 另一个物体头部地址
            find_start = find_next_head(data, data_start, block_size)
            if find_start is None:
                log.debug(
                    "! 未找到下一个物体头部地址, mesh_obj len: %s",
                    hex(len(mesh_obj)),
                )
                # 直接停止!
                break

            # 贴图等数据
            colors_data = data[data_start:find_start]
            # 查找使用的贴图名称
            find_colormap = red_colormap(self, colors_data)
            log.debug("> find_colormap: %s", find_colormap)

            # 修改data_start
            data_start = find_start

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
                    "colormap": find_colormap,
                }
            )

            log.debug("↑↑↑↑↑↑ 完成获取下一个物体头部地址！ ↑↑↑↑↑↑\n")

            # 检查是否到达文件末尾
            # if len(mesh_obj) >= mesh_obj[0]["vertices"]["mesh_obj_number"] - 1:
            #     log.debug("<<< 数据到达尾部")
            #     break

        log.debug(" 👇 返回 mesh_obj！！！ 👇 ")
        return mesh_obj
    except Exception as e:
        log.debug("! 分割网格数据失败: %s", e)
        # self.report({"ERROR"}, f"分割网格数据失败: {e}")
        traceback.print_exc()
        # return {"CANCELLED"}
        return mesh_obj


def red_colormap(self, colors_data):
    """读取使用的贴图名称"""
    colormap = {
        "path": "",
        "name": "",
    }
    try:
        # 将字符串转换为字节序列
        pattern = b"ColorMap"
        log.debug("查找: %s", pattern.decode())

        # 查找模式在数据中的位置
        position = colors_data.find(pattern)

        if position != -1:
            print(f"找到ColorMap '{pattern.decode()}'，偏移地址: {hex(position)}")
            colormap_path_len = struct.unpack_from("<I", colors_data, position + 0x8)[0]
            log.debug("> colormap_text_len: %s", colormap_path_len)

            colormap["path"] = colors_data[
                position + 0xC : position + 0xC + colormap_path_len
            ].decode("ascii")
            log.debug("> colormap_text: %s", colormap["path"])

            # 接下来看情况是否需要去除多余路径只保留贴图名称
            # 提取文件名
            colormap["name"] = extract_name_from_path(colormap["path"])
            log.debug("> extracted_name: %s", colormap["name"])

        else:
            print("未找到ColorMap")

        return colormap
    except Exception as e:
        log.debug("! 解析颜色数据失败: %s", e)
        traceback.print_exc()
        return colormap


def extract_name_from_path(path):
    """从路径中提取文件名（不包含扩展名）"""
    # 分割路径，提取最后一个部分（文件名）
    file_name_with_extension = path.split("/")[-1]
    # 移除文件扩展名
    file_name = file_name_with_extension.split(".")[0]
    return file_name
