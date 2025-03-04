# anim\operator.py
import os
import re
import struct

import bmesh
import bpy
from mathutils import Quaternion

from ..log import log


# 顶义操作类
class ImportAnimClass(bpy.types.Operator):
    """Import an game .anim file"""

    bl_idname = "import.anim"
    bl_label = "导入动画.anim"
    bl_options = {"REGISTER", "UNDO"}

    # 使用bpy.props顶义文件路径属性
    filepath: bpy.props.StringProperty(
        subtype="FILE_PATH",
        default="",
    )  # type: ignore
    # 文件扩展名过滤
    filename_ext = ".anim"
    filter_glob: bpy.props.StringProperty(default="*.anim", options={"HIDDEN"})  # type: ignore

    # 顶义invoke方法来显示文件选择对话框
    def invoke(self, context, event):
        # 设置文件过滤器为.anim后缀
        self.filter_glob = "*.anim;"
        context.window_manager.fileselect_add(self)
        return {"RUNNING_MODAL"}

    # run code
    def execute(self, context):
        # 文件的路径
        file_path = self.filepath

        # 检查文件是否存在
        if not os.path.exists(file_path):
            self.report({"ERROR"}, "文件不存在，请检查路径是否正确")
            return {"CANCELLED"}

        # 从文件路径中提取文件名（不包括扩展名）
        file_name = os.path.splitext(os.path.basename(file_path))[0]

        # 解析并获得帧数据
        frames_groups = self.get_file_frames(file_path, file_name)

        # 获取总帧数
        total_frames = max(len(group_data) for group_data in frames_groups.values())
        log.debug("!!!!!!!!!!! 总帧数: %s", total_frames)

        # 设置Blender场景的帧数
        bpy.context.scene.frame_start = 0
        bpy.context.scene.frame_end = total_frames

        # 创建动画
        for group_name, group_data in frames_groups.items():
            # 创建一个新的立方体网格
            mesh = bpy.data.meshes.new(name=group_name)
            # 创建一个新的立方体物体
            obj = bpy.data.objects.new(name=group_name, object_data=mesh)
            # 将物体添加到场景中
            context.collection.objects.link(obj)

            # 设置为活动物体
            bpy.context.view_layer.objects.active = obj
            # 保存当前模式
            current_mode = bpy.context.object.mode
            # 确保处于物体模式
            bpy.ops.object.mode_set(mode="OBJECT")

            # 添加立方体数据到网格
            bm = bmesh.new()
            # 设置尺寸
            bmesh.ops.create_cube(bm, size=0.2)
            bm.to_mesh(mesh)
            bm.free()

            # 恢复之前的模式
            bpy.ops.object.mode_set(mode=current_mode)
            # 更新网格数据
            mesh.update()

            # 设置关键帧 location rotation
            for frame, transform in enumerate(group_data):
                # 设置位置关键帧时直接使用调整后的坐标
                obj.location = transform["location"]

                # 设置位置关键帧
                obj.location = transform["location"]
                obj.keyframe_insert(data_path="location", frame=frame)

        self.report({"INFO"}, f"{file_name} 动画文件加载成功")
        return {"FINISHED"}

    # 解析并获得帧数据
    def get_file_frames(self, file_path, file_name):
        log.debug("开始处理 %s", file_name)

        # 读取文件
        with open(file_path, "rb") as file:
            # 所有帧数据
            all_frames = {}

            # 获取文件总大小
            file.seek(0, 2)
            file_size = file.tell()
            file.seek(0)

            # 查找帧数据
            log.debug("开始帧数据")
            while True:
                try:
                    # 获取骨骼名称长度
                    bone_name_length = struct.unpack("<I", file.read(4))[0]
                    log.debug("骨骼名称长度: %s", bone_name_length)

                    # 获取骨骼名称
                    bone_name = file.read(bone_name_length).decode("utf-8")
                    log.debug("骨骼名称:%s", bone_name)

                    # 获取骨骼帧数量
                    frames_number = struct.unpack("<I", file.read(4))[0]
                    log.debug("骨骼帧数量: %s", frames_number)

                    # 获取疑似FPS
                    unknown_fps = file.read(4)
                    log.debug("unknown_fps: %s", unknown_fps.hex())

                    # 获取帧数据占用的字节数据
                    frames_bytes = file.read(frames_number * 0x1C)
                    postions = []
                    for i in range(0, len(frames_bytes), 0x1C):
                        frame_data = frames_bytes[i : i + 0x1C]
                        # 方向
                        location = struct.unpack("3f", frame_data[0:0xC])
                        # 旋转
                        rotation = struct.unpack("3f", frame_data[0xC:0x18])
                        # postions.append({"location": location, "rotation": rotation})

                        # 坐标轴映射
                        adjusted_location = (
                            location[0],  # X 保持
                            -location[2],  # 原Z轴 → Blender的Y轴（反向）
                            location[1],  # 原Y轴 → Blender的Z轴（向上）
                        )

                        adjusted_quat = (
                            rotation[0],  # x
                            -rotation[2],  # z → -y（反向原Z轴）
                            rotation[1],  # y → z
                        )

                        postions.append(
                            {"location": adjusted_location, "rotation": adjusted_quat}
                        )

                    log.debug("postions lenght: %s", len(postions))

                    # 写入all_frames
                    log.debug("!写入all_frames")
                    # 添加到顶点组帧数据
                    all_frames[bone_name] = postions

                    # 正常退出
                    if file.tell() >= file_size:
                        log.debug("!正常退出 查找到尾部")
                        break
                except Exception as e:
                    log.debug("!查找帧数据出错! %s", str(e))
                    break

            log.debug("完成 查找到: %s 组帧数据", len(all_frames))
            return all_frames
