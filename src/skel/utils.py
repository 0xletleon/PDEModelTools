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


def read_bone_transform(file):
    """读取骨骼变换数据"""
    try:
        # 头部坐标
        head = struct.unpack("<fff", file.read(12))
        # 尾部坐标
        tail = struct.unpack("<fff", file.read(12))
        # 结束标记？
        end_tag = struct.unpack("<f", file.read(4))[0]

        log.debug("Head: %s Tail: %s End tag: %s", head, tail, end_tag)

        return head, tail, end_tag
    except struct.error as e:
        log.debug("读取骨骼变换数据失败: %s", e)
        return None


def validate_file(file):
    """验证文件是否是skel文件"""
    try:
        header = file.read(12)
        return header == b"\xFF\xFF\xFF\xFF\x00\x00\x00\x00\x00\x00\x00\x00"
    except Exception as e:
        log.debug("文件验证失败: %s", e)
        return False


def convert_coordinates(coords):
    """转换坐标系"""
    x, y, z = coords

    return x, z, y


def calculate_bone_roll(bone):
    """计算骨骼的roll角度"""
    if "arm" in bone.name.lower():
        return math.radians(90)
    elif "leg" in bone.name.lower():
        return math.radians(-90)
    elif "hand" in bone.name.lower():
        return math.radians(180)
    return 0


def print_hierarchy(bones):
    """打印骨骼层级结构"""
    log.debug("骨骼层级结构:")
    for name, level in bones:
        # indent = "  " * (level - 1)
        log.debug("%s %s", name, level)


def create_bone_chain(edit_bones, bones, transforms):
    """创建骨骼链"""
    bone_dict = {}

    # 创建所有骨骼
    for i, (name, level) in enumerate(bones):
        if i < len(transforms):
            bone = edit_bones.new(name)
            head, tail, end_tag = transforms[i]

            # 转换坐标
            head = convert_coordinates(head)
            tail = convert_coordinates(tail)

            # 设置骨骼位置
            bone.head = Vector(head)
            bone.tail = Vector(tail)

            # 计算骨骼方向
            # bone.roll = calculate_bone_roll(bone)

            # 存储骨骼信息
            bone_dict[name] = {"bone": bone, "level": level}

    # 设置父子关系
    for name, data in bone_dict.items():
        bone = data["bone"]
        level = data["level"]

        if level > 1:
            # 查找最近的父骨骼
            parent_level = level - 1
            potential_parents = [
                (n, d) for n, d in bone_dict.items() if d["level"] == parent_level
            ]

            if potential_parents:
                # 选择最近的父骨骼
                closest_parent = min(
                    potential_parents,
                    key=lambda x: (x[1]["bone"].head - bone.head).length,
                )
                bone.parent = closest_parent[1]["bone"]
                # 设置父骨骼的尾为子骨骼的头
                closest_parent[1]["bone"].tail = bone.head


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
