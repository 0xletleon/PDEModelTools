import math
import os

import bpy

from . import utils


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
            idx = 0
            # 读取数据块
            for this_obj in mesh_obj:
                # 读取顶点数据
                vertices = this_obj["vertices"]["data"]
                # 读取面数据
                faces = this_obj["faces"]["data"]

                # 读取UV坐标
                # uv_coords = this_obj["vertices"]["uv_coords"]
                # 读取切线
                # tangents = this_obj["vertices"]["tangents"]

                # 创建新网格
                new_mesh = bpy.data.meshes.new(f"{mesh_name}_{idx}")
                new_obj = bpy.data.objects.new(f"{mesh_name}_{idx}", new_mesh)

                # 将对象添加到场景中
                context.collection.objects.link(new_obj)

                # 创建顶点 点, 线, 面
                new_mesh.from_pydata(vertices, [], faces)

                # 设置UV坐标 !实验
                # if uv_coords:
                #     uv_layer = new_mesh.uv_layers.new(name="UVMap")
                #     for loop_idx, face in enumerate(new_mesh.loops):
                #         vert_idx = face.vertex_index
                #         u, v = uv_coords[vert_idx]
                #         uv_layer.data[loop_idx].uv = (u, v)

                # 设置切线 !实验
                # if tangents:
                #     # 创建切线层
                #     tangent_layer = new_mesh.attributes.new(name="Tangent", type='FLOAT_VECTOR', domain='CORNER')
                #     for loop_idx, face in enumerate(new_mesh.loops):
                #         tan = tangents[face.vertex_index]
                #         tangent_layer.data[loop_idx].vector = (tan[0], tan[1], tan[2])

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
            self.report({"ERROR"}, f"地图模型加载失败: {e}")
            utils.traceback.print_exc()
            return {"CANCELLED"}

    # 定义invoke方法来显示文件选择对话框
    def invoke(self, context, event):
        # 调用文件选择对话框
        context.window_manager.fileselect_add(self)
        return {"RUNNING_MODAL"}
