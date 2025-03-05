"""
mesh_map.utils
~~~~~~~~~~~~~

提供网格文件解析和处理的核心功能。

主要功能:
- 网格文件读取和解析
- 顶点数据处理
- 面数据处理
- 材质和贴图信息提取

"""

import struct
import traceback
from typing import List, Tuple, Dict, Optional, Any
from dataclasses import dataclass
from .. import tools
from ..log import log

# 常量定义
HEADER_SIZE = 0x1D
VERTEX_HEADER_OFFSET = 0x19
FIRST_HEADER_SIZE = 0x18
UV_OFFSET = 0x10
COLORMAP_PATTERN = b"ColorMap"
COLORMAP_PATH_OFFSET = 0x8
COLORMAP_DATA_OFFSET = 0xC


@dataclass
class ColorMapData:
    """贴图数据结构"""

    path: str = ""
    name: str = ""


@dataclass
class VertexData:
    """顶点数据结构"""

    position: Tuple[float, float, float] = (0.0, 0.0, 0.0)
    normal: Tuple[float, float, float] = (0.0, 0.0, 0.0)
    uv: Tuple[float, float] = (0.0, 0.0)


@dataclass
class MeshData:
    """网格数据结构"""

    vertices: Dict[str, Any] = None
    faces: Dict[str, Any] = None
    uvs: List[Tuple[float, float]] = None
    normals: List[Tuple[float, float, float]] = None
    colormap: ColorMapData = None
    has_done: bool = False

    def __post_init__(self):
        if self.vertices is None:
            self.vertices = {}
        if self.faces is None:
            self.faces = {}
        if self.uvs is None:
            self.uvs = []
        if self.normals is None:
            self.normals = []
        if self.colormap is None:
            self.colormap = ColorMapData()
        if self.has_done:
            self.has_done = False


def safe_read(func):
    """安全读取装饰器"""

    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except (OSError, ValueError, RuntimeError) as e:
            log.debug(f"! {func.__name__} 失败: {e}")
            traceback.print_exc()
            return None

    return wrapper


def check_bounds(data: bytes, start: int, size: int) -> bool:
    """检查数据边界"""
    if start + size > len(data):
        log.error(f"数据越界: {start + size} > {len(data)}")
        return False
    return True


def read_struct(data: bytes, format_str: str, offset: int) -> Any:
    """安全读取结构数据"""
    try:
        return struct.unpack_from(format_str, data, offset)[0]
    except struct.error as e:
        log.error(f"结构读取失败: {e}")
        return None


def extract_name_from_path(path: str) -> str:
    """从路径中提取文件名（不包含扩展名）"""
    try:
        file_name = path.split("/")[-1]
        return file_name.split(".")[0]
    except Exception:
        return ""


class MeshReader:
    """网格数据读取器"""

    def __init__(self, data: bytes):
        self.data = data
        self.position = 0
        self.mesh_objects: List[MeshData] = []
        self.total_mesh_count = 0
        self.read_count = 0

    @safe_read
    def read_first_header(self) -> Optional[int]:
        """读取首个头部信息"""
        log.debug(">>> 开始读取地图第一个头部信息")

        if len(self.data) < FIRST_HEADER_SIZE:
            log.debug("Error: 数据不足")
            return None

        # 读取MinPos MaxPos
        min_x, min_y, min_z, max_x, max_y, max_z = struct.unpack_from(
            "<ffffff", self.data
        )
        log.debug("MinPos: x: %s y: %s z: %s", min_x, min_y, min_z)
        log.debug("MaxPos: x: %s y: %s z: %s", max_x, max_y, max_z)

        self.position = FIRST_HEADER_SIZE
        return self.position

    @safe_read
    def read_mesh_header(self) -> Optional[Dict[str, int]]:
        """读取网格头部信息"""
        log.debug("↓↓↓↓↓↓↓ >>> 开始读取头部信息 st: %s ↓↓↓↓↓↓", hex(self.position))

        if not check_bounds(self.data, self.position, HEADER_SIZE):
            return None

        header = {
            "total_count": read_struct(self.data, "<I", self.position),
            "face_groups": read_struct(self.data, "<I", self.position + 0x4),
            "vertex_count": read_struct(self.data, "<I", self.position + 0x8),
            "byte_size": read_struct(
                self.data, "<I", self.position + VERTEX_HEADER_OFFSET
            ),
        }

        log.debug(
            "<<< 网格物体数量: %s 面数据组数量: %s 顶点数量: %s 字节总数: %s",
            hex(header["total_count"]),
            hex(header["face_groups"]),
            hex(header["vertex_count"]),
            hex(header["byte_size"]),
        )

        return header

    @safe_read
    def read_vertices(
        self, vertex_count: int, byte_size: int
    ) -> Optional[Dict[str, Any]]:
        """读取顶点数据"""
        log.debug(">>> 开始解析顶点数据")

        vertices_start = self.position + HEADER_SIZE
        vertices_data = self.data[vertices_start : vertices_start + byte_size]

        if len(vertices_data) <= 0:
            log.debug("! 获取顶点数据长度失败")
            return None

        block_size = byte_size // vertex_count
        log.debug("> 数据块的大小: %s", hex(block_size))

        result = {"vertices": [], "normals": [], "uvs": [], "block_size": block_size}

        try:
            for i in range(vertex_count):
                offset = block_size * i
                if offset + block_size > byte_size:
                    break

                # 读取顶点位置
                vx = struct.unpack_from("f", vertices_data, offset)[0]
                vy = struct.unpack_from("f", vertices_data, offset + 0x4)[0]
                vz = struct.unpack_from("f", vertices_data, offset + 0x8)[0]
                result["vertices"].append((vx, vy, vz))

                # 读取法线
                nx = tools.read_half_float(vertices_data, offset + 0x0C)
                ny = tools.read_half_float(vertices_data, offset + 0x0E)
                nz = tools.read_half_float(vertices_data, offset + 0x10)
                result["normals"].append((nx, ny, nz))

                # 读取UV
                uv_offset = offset + block_size - UV_OFFSET
                u = tools.read_half_float(vertices_data, uv_offset)
                v = tools.read_half_float(vertices_data, uv_offset + 0x2)
                result["uvs"].append((u, 1 - v))

            # return result

        except (OSError, ValueError, RuntimeError) as e:
            log.debug(f"解析顶点 {i} 的 UV 数据失败: {e}")
            result["uvs"].append((0.0, 0.0))  # 默认 UV
            traceback.print_exc()
            return None

        # 确保 UV 数量与顶点数量一致
        if len(result["vertices"]) != len(result["uvs"]):
            log.warning(
                f"UV 数量不匹配: {len(result['uvs'])} vs {len(result['vertices'])}"
            )
            # 如果需要，填充默认 UV
            result["uvs"] = [(0.0, 0.0)] * len(result["vertices"])
        return result

    @safe_read
    def read_faces(
        self, faces_start: int, faces_size: int
    ) -> Optional[List[Tuple[int, int, int]]]:
        """读取面数据"""
        log.debug(">>> 开始解析面数据 size: %s", faces_size)

        faces_data = self.data[faces_start : faces_start + faces_size]
        faces = []

        try:
            for i in range(0, faces_size, 12):
                f0 = struct.unpack_from("H", faces_data, i)[0]
                f1 = struct.unpack_from("H", faces_data, i + 0x4)[0]
                f2 = struct.unpack_from("H", faces_data, i + 0x8)[0]
                faces.append((f0, f1, f2))

            log.debug("<<< 面数据读取完毕: %s 组", len(faces))
            return faces

        except (OSError, ValueError, RuntimeError) as e:
            log.debug("! 面数据解析失败: %s", e)
            traceback.print_exc()
            return None

    @safe_read
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

        except (OSError, ValueError, RuntimeError) as e:
            log.debug("! 解析颜色数据失败: %s", e)
            traceback.print_exc()

        return colormap


class MeshProcessor:
    """网格数据处理器"""

    def __init__(self, reader: MeshReader):
        self.reader = reader

    def process_all(self) -> List[MeshData]:
        """处理所有网格数据"""
        log.debug(">>> 开始分割网格数据")

        # 读取首个头部
        if self.reader.read_first_header() is None:
            return []

        try:
            while True:
                # 读取并处理单个网格
                mesh_data = self.process_single_mesh()

                if mesh_data is None:
                    break

                self.reader.mesh_objects.append(mesh_data)
                self.reader.read_count += 1

                # 检查是否处理完所有网格
                if self.reader.read_count >= self.reader.total_mesh_count:
                    log.debug("<<< 数据处理完成")
                    break

                if mesh_data.has_done is True:
                    break

            log.debug("👇 共处理 %d 个网格对象", len(self.reader.mesh_objects))
            return self.reader.mesh_objects

        except (OSError, ValueError, RuntimeError) as e:
            log.debug("! 网格数据处理失败: %s", e)
            traceback.print_exc()
            return self.reader.mesh_objects

    def process_single_mesh(self) -> Optional[MeshData]:
        """处理单个网格数据"""
        # 1. 读取头部信息
        header = self.reader.read_mesh_header()
        if header is None:
            return None

        # 更新总网格数
        if self.reader.total_mesh_count == 0:
            self.reader.total_mesh_count = header["total_count"]

        # 2. 读取顶点数据
        vertices_info = self.reader.read_vertices(
            header["vertex_count"], header["byte_size"]
        )
        if vertices_info is None:
            return None

        # 3. 读取面数据
        faces_start = self.reader.position + HEADER_SIZE + header["byte_size"]
        try:
            faces_size = struct.unpack(
                "<I", self.reader.data[faces_start : faces_start + 0x4]
            )[0]
        except struct.error:
            log.debug("! 读取面数据大小失败")
            return None

        log.debug("> 获取面数据块大小: %s", hex(faces_size))

        # 检查面数据边界
        if faces_start + 0x4 + faces_size >= len(self.reader.data):
            log.debug("! 面数据超出边界")
            next_start = find_next_head(
                self.reader.data, faces_start, vertices_info["block_size"]
            )
            if next_start is not None:
                self.reader.position = next_start
            return None

        faces_array = self.reader.read_faces(faces_start + 0x4, faces_size)
        if faces_array is None:
            return None

        # 4. 查找下一个网格位置和处理贴图数据
        next_data_start = faces_start + 0x4 + faces_size
        next_mesh_start = find_next_head(
            self.reader.data, next_data_start, vertices_info["block_size"]
        )

        colormap = ColorMapData()
        has_done = False
        if next_mesh_start is not None:
            colors_data = self.reader.data[next_data_start:next_mesh_start]
            colormap = self.reader.read_colormap(colors_data)
            self.reader.position = next_mesh_start
        else:
            log.debug("! 未找到下一个网格头部,尝试获取colormap！")
            colors_data = self.reader.data[next_data_start : len(self.reader.data)]
            colormap = self.reader.read_colormap(colors_data)
            has_done = True

        # 5. 构建网格数据
        return MeshData(
            vertices={
                "mesh_obj_number": header["total_count"],
                "mesh_vertices_number": header["vertex_count"],
                "mesh_byte_size": header["byte_size"],
                "data": vertices_info["vertices"],
            },
            faces={"size": faces_size, "data": faces_array},
            uvs=vertices_info["uvs"],
            normals=vertices_info["normals"],
            colormap=colormap,
            has_done=has_done,
        )


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
        except (OSError, ValueError, RuntimeError) as e:
            log.debug("! 查找下一个网格头部失败: %s", e)
            traceback.print_exc()

    log.debug("! 未找到下一个头部")
    return None


class MeshFile:
    """网格文件处理类"""

    def __init__(self, filepath: str):
        self.filepath = filepath

    def read(self) -> List[MeshData]:
        """读取并处理网格文件"""
        try:
            with open(self.filepath, "rb") as f:
                data = f.read()

            reader = MeshReader(data)
            processor = MeshProcessor(reader)
            return processor.process_all()

        except (OSError, ValueError, RuntimeError) as e:
            log.debug("! 文件读取失败: %s", e)
            traceback.print_exc()
            return []
