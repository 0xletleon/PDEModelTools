# skel\utils.py
import math
import struct

from mathutils import Vector

from ..log import log


def read_bone_info(file):
    """读取骨骼名称和层级"""
    try:
        # 骨骼名称长度
        name_length = struct.unpack("<I", file.read(4))[0]
        log.debug("骨骼名称长度: %s", name_length)
        # 骨骼名称
        name = file.read(name_length).decode("ascii")
        log.debug("骨骼名称: %s", name)
        # 骨骼层级
        level = struct.unpack("<I", file.read(4))[0]

        log.debug("骨骼信息: %s %s", name, level)

        # 返回骨骼名称和层级
        return name, level
    except struct.error as e:
        log.debug("读取骨骼信息失败: %s", e)
        return None


# 坐标系转换
def convert_to_blender(coords):
    x, y, z = coords
    # return (x, -z, y)  # Y轴取反并交换Y/Z
    return (x, z, -y)  # Y轴取反并交换Y/Z


def read_bone_transform(file):
    """读取骨骼变换数据"""
    try:
        data = file.read(28)
        # 头部坐标
        head = struct.unpack("<3f", data[0:12])
        # 尾部坐标
        tail = struct.unpack("<3f", data[12:24])
        # 缩放?
        scale = struct.unpack("<f", data[24:28])[0]
        return convert_to_blender(head), convert_to_blender(tail), scale
    except struct.error as e:
        log.debug("读取骨骼变换数据失败: %s", e)
        return None


def validate_file(file):
    """验证文件是否是skel文件"""
    try:
        header = file.read(12)
        return header == b"\xFF\xFF\xFF\xFF\x00\x00\x00\x00\x00\x00\x00\x00"
    except (OSError, ValueError, RuntimeError) as e:
        log.debug("文件验证失败: %s", e)
        return False


def create_bone_chain(edit_bones, bones, transforms):
    """创建骨骼链（修正层级关系版）"""
    bone_dict = {}
    scale_factor = 0.1  # 骨骼默认尾部延伸长度（当tail全零时使用）

    # 第一遍：创建所有骨骼
    for idx, (bone_info, transform) in enumerate(zip(bones, transforms)):
        name, parent_idx = bone_info  # 现在level字段实际是父骨骼索引
        head, tail, _ = transform

        # 创建新骨骼
        bone = edit_bones.new(name)

        # 设置头部坐标
        bone.head = Vector(head)

        # 处理尾部坐标（当tail全零时自动生成）
        if all(abs(v) < 1e-6 for v in tail):
            # 沿局部Y轴延伸（Blender骨骼默认方向）
            bone.tail = bone.head + Vector((0, scale_factor, 0))
        else:
            bone.tail = Vector(tail)

        # 存储骨骼信息（包含父索引）
        bone_dict[name] = {"bone": bone, "parent_idx": parent_idx, "index": idx}

    # 第二遍：建立父子关系
    for name, data in bone_dict.items():
        bone = data["bone"]
        parent_idx = data["parent_idx"]
        # 验证父骨骼索引
        if parent_idx != -1 and parent_idx < len(bones):
            bone.parent = bone_dict[bones[parent_idx][0]]["bone"]
        # # 根骨骼处理（parent_idx = -1）
        # if parent_idx == -1:
        #     continue

        # # 验证父骨骼是否存在
        # if parent_idx >= len(bones):
        #     log.warning(f"骨骼 {name} 的父索引 {parent_idx} 超出范围")
        #     continue

        parent_name = bones[parent_idx][0]
        if parent_name not in bone_dict:
            log.warning(f"找不到父骨骼 {parent_name}（{parent_idx}）")
            continue

        # 建立父子关系
        parent_bone = bone_dict[parent_name]["bone"]
        bone.parent = parent_bone

        # 自动连接骨骼端点（可选）
        if bone.head != parent_bone.tail:
            parent_bone.tail = bone.head  # 将父骨骼尾部连接到当前骨骼头部

    # 特殊处理：根骨骼默认方向
    if "root" in bone_dict:
        root_bone = bone_dict["root"]["bone"]
        if (root_bone.tail - root_bone.head).length < 1e-6:
            root_bone.tail.y += scale_factor  # 沿Y轴延伸


# def create_bone_chain(edit_bones, bones, transforms):
#     """创建骨骼链"""
#     bone_dict = {}

#     # 创建所有骨骼
#     for i, (name, level) in enumerate(bones):
#         if i < len(transforms):
#             bone = edit_bones.new(name)
#             head, tail, end_tag = transforms[i]

#             # 设置骨骼位置
#             bone.head = Vector(head)
#             bone.tail = Vector(tail)

#             # 存储骨骼信息
#             bone_dict[name] = {"bone": bone, "level": level}

#     # 设置父子关系
#     for name, data in bone_dict.items():
#         bone = data["bone"]
#         level = data["level"]

#         if level > 1:
#             # 查找最近的父骨骼
#             parent_level = level - 1
#             potential_parents = [
#                 (n, d) for n, d in bone_dict.items() if d["level"] == parent_level
#             ]

#             if potential_parents:
#                 # 选择最近的父骨骼
#                 closest_parent = min(
#                     potential_parents,
#                     key=lambda x: (x[1]["bone"].head - bone.head).length,
#                 )
#                 bone.parent = closest_parent[1]["bone"]
#                 # 设置父骨骼的尾为子骨骼的头
#                 closest_parent[1]["bone"].tail = bone.head


def add_bone_constraints(armature_obj):
    """添加骨骼约束"""
    pose = armature_obj.pose

    # 添加IK约束
    for bone_name in pose.bones:
        if "IK" in bone_name:
            target_name = bone_name.replace("IK", "")
            if target_name in pose.bones:
                constraint = pose.bones[target_name].constraints.new("IK")
                constraint.target = armature_obj
                constraint.subtarget = bone_name


def print_hierarchy(bones):
    """打印骨骼层级结构"""
    log.debug("骨骼层级结构:")
    for name, level in bones:
        # indent = "  " * (level - 1)
        log.debug("%s %s", name, level)
