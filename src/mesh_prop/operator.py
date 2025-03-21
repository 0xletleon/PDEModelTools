# mesh_prop\operator.py
import math
import os
import traceback
from typing import Set

import bpy
from bpy_extras.io_utils import ImportHelper
from bpy.props import StringProperty

from . import utils
from ..log import log

# 常量定义
ROTATION_X = math.radians(90)
DEFAULT_UV_LAYER = "UVMap"
COLORMAP_NODE_NAME = "Colormap"
BSDF_NODE_NAME = "Principled BSDF"


# 定义操作类
class ImportMeshPropClass(bpy.types.Operator, ImportHelper):
    """Import a .mesh file"""

    bl_idname = "import.mesh_prop"
    bl_label = "导入道具.mesh"
    bl_options = {"REGISTER", "UNDO"}
    
    filename_ext = ".mesh"
    filter_glob: StringProperty(default="*.mesh", options={"HIDDEN"})  # type: ignore

    _processed_materials: Set[str] = set()

    def execute(self, context):
        try:
            # 检查文件路径
            if not os.path.exists(self.filepath):
                self.report({"ERROR"}, "文件不存在，请检查路径是否正确")
                return {"CANCELLED"}

            # 读取二进制文件
            with open(self.filepath, "rb") as file:
                data = file.read()

            # 获取基础名称
            mesh_name = os.path.splitext(os.path.basename(self.filepath))[0]

            # 分割网格数据
            mesh_obj = utils.split_mesh(self, data)

            # 循环索引
            idx = 0
            # 读取数据块
            for this_obj in mesh_obj:
                # 读取顶点数据
                vertices = this_obj["vertices"]["data"]
                # 读取面数据
                faces = this_obj["faces"]["data"]
                # 读取法相
                normals = this_obj["normals"]
                # 读取UV坐标
                uvs = this_obj["uvs"]
                # 读取ColorMap
                colormap = this_obj["colormap"]
                log.debug("colormap x :%s", colormap.name)

                # 创建新网格
                new_mesh = bpy.data.meshes.new(f"{mesh_name}_{idx}")
                new_obj = bpy.data.objects.new(f"{mesh_name}_{idx}", new_mesh)

                # 将对象添加到场景中
                context.collection.objects.link(new_obj)

                # 创建顶点 点, 线, 面
                new_mesh.from_pydata(vertices, [], faces)

                # 创建UV图层
                uv_layer = new_mesh.uv_layers.new(name="UVMap")

                # 为每个循环（loop）设置UV坐标
                for face in new_mesh.polygons:
                    for loop_idx in face.loop_indices:
                        # 获取顶点索引
                        vertex_idx = new_mesh.loops[loop_idx].vertex_index
                        # 设置UV坐标
                        uv_layer.data[loop_idx].uv = uvs[vertex_idx]

                # 启用平滑着色
                new_mesh.shade_smooth()

                # 准备法向数据
                loop_normals = []
                for poly in new_mesh.polygons:
                    for vertex_idx in poly.vertices:
                        loop_normals.append(normals[vertex_idx])

                # 设置自定义法向
                new_mesh.normals_split_custom_set(loop_normals)

                # 设置材质
                if colormap.name:
                    self._setup_material(new_obj, colormap.name)

                # 更新网格
                new_mesh.update()

                # 设置物体的位置
                new_obj.location = (0, 0, 0)
                # 首先，设置旋转模式为欧拉角
                new_obj.rotation_mode = "XYZ"
                # 设置X轴的旋转值为90度（转换为弧度）
                new_obj.rotation_euler = (math.radians(90), 0, 0)

                # 循环索引+1
                idx += 1

            self.report({"INFO"}, "模型加载成功")
            return {"FINISHED"}
        except Exception as e:
            self.report({"ERROR"}, f"模型加载失败: {e}")
            traceback.print_exc()
            return {"CANCELLED"}

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
