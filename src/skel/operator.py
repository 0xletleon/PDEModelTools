# skel\operator.py
import os
import struct

import bpy

from . import utils
from ..log import log


class ImportSkelClass(bpy.types.Operator):
    """导入自定义骨骼文件"""

    bl_idname = "import.skel"
    bl_label = "导入骨骼.skel"
    bl_options = {"REGISTER", "UNDO"}

    # 使用bpy.props顶义文件路径属性
    filepath: bpy.props.StringProperty(
        subtype="FILE_PATH",
        default="",
    )  # type: ignore
    # 文件扩展名过滤
    filename_ext = ".skel"
    filter_glob: bpy.props.StringProperty(default="*.skel", options={"HIDDEN"})  # type: ignore

    def invoke(self, context, event):
        # 设置文件过滤器为.skel后缀
        self.filter_glob = "*.skel;"
        context.window_manager.fileselect_add(self)
        return {"RUNNING_MODAL"}

    def execute(self, context):
        """导入骨骼"""
        try:
            # 文件路径
            file_path = self.filepath

            # 从文件路径中提取文件名
            file_name = os.path.splitext(os.path.basename(file_path))[0]

            # 骨骼名称和层级关系
            bones = []
            # 骨骼变换数据
            transforms = []

            # 读取骨骼信息
            with open(file_path, "rb") as file:
                # 验证文件是否是skel文件
                if not utils.validate_file(file):
                    log.debug("无效的文件格式")
                    return {"CANCELLED"}

                # 读取骨骼名称和层级关系
                log.debug("读取骨骼名称和层级关系")
                while True:
                    # 获取当前文件位置
                    current_position = file.tell()
                    # 读取骨骼信息
                    bone_info = utils.read_bone_info(file)

                    # 如果读取失败，跳出循环
                    if bone_info is None:
                        log.debug("读取骨骼信息失败")
                        break

                    # 将骨骼信息添加到列表中
                    name, level = bone_info
                    bones.append((name, level))

                    # 检查是否到达骨骼名称部分的结尾
                    # 获取当前文件位置
                    current_position = file.tell()
                    # 获取下一个骨骼名称长度
                    next_name_length = struct.unpack("<I", file.read(4))[0]
                    # 向尾部移动23字节(+前面的4字节)(一个数据块大小为28(0x1C)字节)
                    file.seek(23, 1)
                    # 读取结束标记
                    end_tag = file.read(1).hex()
                    # 将文件指针恢复到原来的位置
                    file.seek(current_position)

                    log.debug("下文件名长度: %s 结束标记: %s", next_name_length, end_tag)

                    # 检查是否到达骨骼名称部分的结尾
                    if next_name_length <= 0 and end_tag == "3f":
                        log.debug("读取骨骼信息结束: %s", len(bones))
                        break

                log.debug("读取骨骼变换数据")
                log.debug("当前文件地址: %s", current_position)
                # 读取骨骼变换数据
                bones_len = len(bones)
                # 根据bones_len长度循环获取变换数据
                for i in range(bones_len):
                    log.debug(
                        "%s 读取 %s 骨骼变换数据 Level: %s",
                        i + 1 ,bones[i][0],bones[i][1]
                    )

                    # 读取变换数据
                    transform = utils.read_bone_transform(file)
                    # 如果读取失败，跳出循环
                    if transform is None:
                        break
                    # 将变换数据添加到列表中
                    transforms.append(transform)

                log.debug("读取骨骼变换数据结束: %s", len(transforms))
                # 打印骨骼层级
                utils.print_hierarchy(bones)

            # 创建骨架
            log.debug("创建骨架")
            # 创建骨架对象
            armature = bpy.data.armatures.new(file_name)
            armature_obj = bpy.data.objects.new(file_name, armature)

            # 显示名称
            armature.show_names = True
            # 显示轴
            armature.show_axes = True
            # armature.display_type = 'STICK'

            # 设置对象变换
            # armature_obj.scale = (scale, scale, scale)

            # 链接骨架对象到场景中
            context.collection.objects.link(armature_obj)
            # 激活骨架对象
            context.view_layer.objects.active = armature_obj

            # 进入编辑模式
            bpy.ops.object.mode_set(mode="EDIT")

            # 创建骨骼
            utils.create_bone_chain(armature.edit_bones, bones, transforms)

            # 添加骨骼约束
            bpy.ops.object.mode_set(mode="POSE")
            log.debug("添加骨骼约束")
            utils.add_bone_constraints(armature_obj)

            # 调整视图
            bpy.ops.object.mode_set(mode="OBJECT")
            # 选择骨架对象
            bpy.ops.object.select_all(action="DESELECT")
            armature_obj.select_set(True)
            context.view_layer.objects.active = armature_obj

            log.debug("成功导入 %s 个骨骼", len(bones))
            return {"FINISHED"}

        except Exception as e:
            log.debug("导入过程中发生错误: %s", str(e))
            return {"CANCELLED"}
