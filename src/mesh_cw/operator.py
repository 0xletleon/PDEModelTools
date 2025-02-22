# mesh_cw\operator.py
import math
import os
import traceback
from typing import Set
from bpy_extras.io_utils import ImportHelper
import bpy

from . import utils
from ..log import log

# 常量定义
ROTATION_X = math.radians(90)
DEFAULT_UV_LAYER = "UVMap"
COLORMAP_NODE_NAME = "Colormap"
BSDF_NODE_NAME = "Principled BSDF"


# 定义操作类
class ImportMeshCWClass(bpy.types.Operator, ImportHelper):
    """Import .mesh files"""

    bl_idname = "import.cm_mesh"
    bl_label = "导入武器和人物.mesh"
    bl_options = {"REGISTER", "UNDO"}

    # 文件扩展名过滤
    filename_ext = ".mesh"
    filter_glob: bpy.props.StringProperty(default="*.mesh", options={"HIDDEN"})  # type: ignore
    # 使用bpy.props定义文件路径属性
    # filepath: bpy.props.StringProperty(subtype="FILE_PATH", default="")  # type: ignore
    files: bpy.props.CollectionProperty(
        type=bpy.types.OperatorFileListElement, options={"HIDDEN", "SKIP_SAVE"}
    )  # type: ignore
    directory: bpy.props.StringProperty(subtype="FILE_PATH")  # type: ignore

    # def __init__(self):
    #     self.context = bpy.types.Context
    #     self._processed_materials: Set[str] = set()

    # 定义invoke方法来显示文件选择对话框
    def invoke(self, context, event):
        # 调用文件选择对话框
        context.window_manager.fileselect_add(self)
        return {"RUNNING_MODAL"}

    def execute(self, context):
        for file in self.files:
            file_path = os.path.join(self.directory, file.name)
            try:
                # 定义数据文件的路径
                # file_path = self.filepath
                # 检查文件是否存在
                if not os.path.exists(file_path):
                    self.report({"ERROR"}, "文件不存在，请检查路径是否正确")
                    return {"CANCELLED"}

                # 读取二进制文件
                # data = None
                with open(file_path, "rb") as file:
                    data = file.read()

                # 获得文件名(不带后缀)
                mesh_name = os.path.splitext(os.path.basename(file_path))[0]
                log.debug("<<< 读取到的模型名称: %s", mesh_name)

                # 分割网格数据
                mesh_obj = utils.split_mesh(self, data)
                log.debug("<<< mesh_obj长度: %s", len(mesh_obj))
                if not mesh_obj:
                    self.report({"ERROR"}, "文件解析错误!")
                    return {"CANCELLED"}

                # 读取数据块
                for mesh_item in mesh_obj:
                    log.debug("<<< 正在创建物体名称: %s", mesh_name)
                    # 读取顶点数据
                    vertices = mesh_item["vertices"]["data"]
                    # 读取面数据
                    faces = mesh_item["faces"]["data"]
                    # 获取法向数据
                    normals = mesh_item["normals"]
                    # 读取UV坐标
                    uvs = mesh_item["uvs"]
                    # 读取ColorMap
                    colormap = mesh_item["colormap"]
                    log.debug("colormap x :%s", colormap.name)

                    # 创建新网格
                    new_mesh = bpy.data.meshes.new(mesh_name)
                    new_obj = bpy.data.objects.new(mesh_name, new_mesh)

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
                    # 设置旋转模式为欧拉角
                    new_obj.rotation_mode = "XYZ"
                    # 设置X轴的旋转值为90度（转换为弧度）
                    new_obj.rotation_euler = (math.radians(90), 0, 0)

                self.report({"INFO"}, "模型加载成功")
            except Exception as e:
                self.report({"ERROR"}, f"模型加载失败: {e}")
                traceback.print_exc()
                return {"CANCELLED"}
        return {"FINISHED"}

    def _setup_material(self, obj: bpy.types.Object, colormap_name: str) -> None:
        """设置材质"""
        # 检查材质是否已存在
        mat = bpy.data.materials.get(colormap_name)
        if not mat:
            mat = self._create_material(colormap_name)

        # 分配材质
        if obj.data.materials:
            obj.data.materials[0] = mat
        else:
            obj.data.materials.append(mat)

    def _create_material(self, colormap_name: str) -> bpy.types.Material:
        """创建材质"""
        # 再次检查避免竞态条件
        mat = bpy.data.materials.get(colormap_name)
        if mat:
            return mat

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
