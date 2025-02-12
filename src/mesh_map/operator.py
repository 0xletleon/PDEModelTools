"""
mesh_map.operator
~~~~~~~~~~~~~~~~

用于导入和处理地图网格数据。

主要功能:
- 导入 .mesh 地图文件
- 创建 地图网格对象
- 设置材质贴图名称 
"""

import os
import math
import bpy
from typing import Set
from bpy_extras.io_utils import ImportHelper
from bpy.props import StringProperty
from bpy.types import Operator
from . import utils
from ..log import log

# 常量定义
ROTATION_X = math.radians(90)
DEFAULT_UV_LAYER = "UVMap"
COLORMAP_NODE_NAME = "Colormap"
BSDF_NODE_NAME = "Principled BSDF"


class MeshImporter:
    """网格导入器"""

    def __init__(self, context: bpy.types.Context):
        self.context = context
        self._processed_materials: Set[str] = set()

    def create_mesh_object(
        self, mesh_data: utils.MeshData, base_name: str, index: int
    ) -> bpy.types.Object:
        """创建网格对象"""
        # 创建网格
        name = f"{base_name}_{index}"
        mesh = bpy.data.meshes.new(name)
        obj = bpy.data.objects.new(name, mesh)

        # 链接到场景
        self.context.collection.objects.link(obj)

        # 构建几何体
        self._build_geometry(mesh, mesh_data)

        # 设置变换
        self._setup_transform(obj)

        # 设置材质
        if mesh_data.colormap.name:
            self._setup_material(obj, mesh_data.colormap.name)

        return obj

    def _build_geometry(self, mesh: bpy.types.Mesh, mesh_data: utils.MeshData) -> None:
        """构建网格几何体"""
        # 创建顶点和面
        mesh.from_pydata(mesh_data.vertices["data"], [], mesh_data.faces["data"])

        # 创建UV和法向
        self._create_uvs(mesh, mesh_data.uvs)
        self._create_normals(mesh, mesh_data.normals)

        # 更新网格
        mesh.update()

    def _create_uvs(self, mesh: bpy.types.Mesh, uvs: list) -> None:
        """创建 UV 映射"""
        uv_layer = mesh.uv_layers.new(name=DEFAULT_UV_LAYER)
        for poly in mesh.polygons:
            for loop_idx in poly.loop_indices:
                vert_idx = mesh.loops[loop_idx].vertex_index
                if vert_idx >= len(uvs):
                    # 处理缺少 UV 数据的情况
                    # log.error(f"顶点索引 {vert_idx} 超出 UV 列表长度 {len(uvs)}")
                    uv_coord = (0.0, 0.0)  # 默认 UV
                else:
                    uv_coord = uvs[vert_idx]
                uv_layer.data[loop_idx].uv = uv_coord

    def _create_normals(self, mesh: bpy.types.Mesh, normals: list) -> None:
        loop_normals = []
        for poly in mesh.polygons:
            for v in poly.vertices:
                if v >= len(normals):
                    loop_normals.append((0.0, 0.0, 1.0))  # Default normal
                else:
                    loop_normals.append(normals[v])

        mesh.normals_split_custom_set(loop_normals)

    def _setup_transform(self, obj: bpy.types.Object) -> None:
        """设置对象变换"""
        obj.rotation_mode = "XYZ"
        obj.rotation_euler = (ROTATION_X, 0, 0)

    def _setup_material(self, obj: bpy.types.Object, colormap_name: str) -> None:
        """设置材质"""
        # 检查材质是否已存在
        if colormap_name in self._processed_materials:
            mat = bpy.data.materials[colormap_name]
        else:
            mat = self._create_material(colormap_name)
            self._processed_materials.add(colormap_name)

        # 分配材质
        if obj.data.materials:
            obj.data.materials[0] = mat
        else:
            obj.data.materials.append(mat)

    def _create_material(self, colormap_name: str) -> bpy.types.Material:
        """创建材质"""
        mat = bpy.data.materials.new(name=colormap_name)
        mat.use_nodes = True
        nodes = mat.node_tree.nodes
        links = mat.node_tree.links

        # 清理默认节点
        nodes.clear()

        # 创建节点
        bsdf = nodes.new(type="ShaderNodeBsdfPrincipled")
        bsdf.name = BSDF_NODE_NAME
        bsdf.location = (0, 0)

        tex_node = nodes.new(type="ShaderNodeTexImage")
        tex_node.name = COLORMAP_NODE_NAME
        tex_node.location = (-300, 0)
        tex_node.image = self._get_texture(colormap_name)

        output = nodes.new(type="ShaderNodeOutputMaterial")
        output.location = (300, 0)

        # 连接节点
        links.new(bsdf.inputs["Base Color"], tex_node.outputs["Color"])
        links.new(output.inputs["Surface"], bsdf.outputs["BSDF"])

        return mat

    def _get_texture(self, name: str) -> bpy.types.Image:
        """获取或加载贴图"""
        return bpy.data.images.get(name)


class ImportMeshMapClass(Operator, ImportHelper):
    """导入 .mesh 地图模型"""

    bl_idname = "import.mesh_map"
    bl_label = "导入.mesh地图模型"
    bl_options = {"REGISTER", "UNDO"}

    filename_ext = ".mesh"
    filter_glob: StringProperty(default="*.mesh", options={"HIDDEN"})  # type: ignore

    def execute(self, context: bpy.types.Context) -> Set[str]:
        try:
            return self._execute_main(context)
        except Exception as e:
            log.error("操作失败: %s", e, exc_info=True)
            self.report({"ERROR"}, f"严重错误: {str(e)}")
            return {"CANCELLED"}

    def _execute_main(self, context: bpy.types.Context) -> Set[str]:
        """主要执行逻辑"""
        # 检查文件路径
        if not os.path.exists(self.filepath):
            self.report({"ERROR"}, "文件路径不存在")
            return {"CANCELLED"}

        # 读取网格数据
        mesh_file = utils.MeshFile(self.filepath)
        mesh_objects = mesh_file.read()

        if not mesh_objects:
            self.report({"ERROR"}, "未能读取到有效的网格数据")
            return {"CANCELLED"}

        # 创建导入器
        importer = MeshImporter(context)

        # 获取基础名称
        base_name = os.path.splitext(os.path.basename(self.filepath))[0]

        # 处理每个网格对象
        for idx, mesh_data in enumerate(mesh_objects, 1):
            if not mesh_data.normals or len(mesh_data.normals) != len(
                mesh_data.vertices.get("data", [])
            ):
                log.error(f"跳过网格 {idx}: 法向数据不匹配")
                continue
            importer.create_mesh_object(mesh_data, base_name, idx)

        self.report({"INFO"}, f"成功导入 {len(mesh_objects)} 个网格对象")
        return {"FINISHED"}
