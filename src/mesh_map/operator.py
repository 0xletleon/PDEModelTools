# mesh_map\operator.py
import math
import os

import bpy

from . import utils
from ..log import log


# 定义操作类
class ImportMeshMapClass(bpy.types.Operator):
    """Import a .mesh file"""

    bl_idname = "import.mesh_map"
    bl_label = "导入.mesh地图模型"
    bl_options = {"REGISTER", "UNDO"}
    # 使用bpy.props定义文件路径属性
    filepath: bpy.props.StringProperty(subtype="FILE_PATH", default="")  # type: ignore
    # 文件扩展名过滤
    filename_ext = ".mesh"
    filter_glob: bpy.props.StringProperty(default="*.mesh", options={"HIDDEN"})  # type: ignore

    def execute(self, context):
        # 清除当前场景中的所有物体
        # bpy.ops.object.select_all(action="SELECT")
        # bpy.ops.object.delete()

        try:
            # 定义数据文件的路径
            file_path = self.filepath
            # 检查文件是否存在
            if not os.path.exists(file_path):
                self.report({"ERROR"}, "文件不存在，请检查路径是否正确")
                return {"CANCELLED"}

            # 读取二进制文件
            data = None
            with open(file_path, "rb") as file:
                data = file.read()

            # 获得文件名(不带后缀)
            mesh_name = os.path.splitext(os.path.basename(file_path))[0]

            # 分割网格数据
            mesh_obj = utils.split_mesh(self, data)

            # 循环索引
            idx = 1
            # 读取数据块
            for this_obj in mesh_obj:
                # 读取顶点数据
                vertices = this_obj["vertices"]["data"]
                # 读取面数据
                faces = this_obj["faces"]["data"]
                # 读取法线
                normals = this_obj["normals"]
                # 读取UV坐标
                uvs = this_obj["uvs"]
                # 贴图名称 ColorMap
                colormap = this_obj["colormap"]

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

                # 准备法线数据
                loop_normals = []
                for poly in new_mesh.polygons:
                    for vertex_idx in poly.vertices:
                        loop_normals.append(normals[vertex_idx])

                # 设置自定义法线
                new_mesh.normals_split_custom_set(loop_normals)

                # 更新网格
                new_mesh.update()

                # 设置物体的位置
                new_obj.location = (0, 0, 0)
                # 首先，设置旋转模式为欧拉角
                new_obj.rotation_mode = "XYZ"
                # 设置X轴的旋转值为90度（转换为弧度）
                new_obj.rotation_euler = (math.radians(90), 0, 0)

                # 检查是否有有效的贴图名称
                if colormap["name"]:
                    # 创建材质并设置贴图名称
                    material = bpy.data.materials.new(name=colormap["name"])
                    material.use_nodes = True
                    nodes = material.node_tree.nodes

                    # 清除默认的节点
                    for node in nodes:
                        nodes.remove(node)

                    # 创建一个 Principled BSDF 节点
                    bsdf = nodes.new(type="ShaderNodeBsdfPrincipled")
                    bsdf.location = (0, 0)

                    # 创建一个 Material Output 节点
                    output_node = nodes.new(type="ShaderNodeOutputMaterial")
                    output_node.location = (300, 0)

                    # 连接节点
                    material.node_tree.links.new(
                        output_node.inputs["Surface"], bsdf.outputs["BSDF"]
                    )

                    # 将材质分配给对象
                    if new_obj.data.materials:
                        new_obj.data.materials[0] = material
                    else:
                        new_obj.data.materials.append(material)
                else:
                    log.debug("没有找到有效的贴图名称，跳过材质创建")

                # 循环索引+1
                idx += 1

            self.report({"INFO"}, "模型加载成功")
            return {"FINISHED"}
        except Exception as e:
            self.report({"ERROR"}, f"地图模型加载失败: {e}")
            utils.traceback.print_exc()
            return {"CANCELLED"}

    # 定义invoke方法来显示文件选择对话框
    def invoke(self, context, event):
        # 调用文件选择对话框
        context.window_manager.fileselect_add(self)
        return {"RUNNING_MODAL"}
