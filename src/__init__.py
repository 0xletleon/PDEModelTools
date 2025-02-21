# __init__.py
import bpy

from . import ui
from .anim.operator import ImportAnimClass
from .mesh_map.operator import ImportMeshMapClass
from .mesh_prop.operator import ImportMeshPropClass
from .mesh_cw.operator import ImportMeshCWClass
from .skel.operator import ImportSkelClass


class PMTPreferences(bpy.types.AddonPreferences):
    """插件偏好设置"""

    bl_idname = __name__  # 使用插件模块名作为标识

    pmt_bone_dir: bpy.props.StringProperty(
        name="骨骼文件夹路径",
        description="存放骨骼的文件夹",
        subtype="DIR_PATH",
        default="D:\\Games\\FC\\finalcombat\\skeleton\\",
    )  # type: ignore

    def draw(self, context):
        self.layout.prop(self, "pmt_bone_dir")


# 类表
classes = (
    PMTPreferences,
    ui.ImportPanel,
    ImportMeshPropClass,
    ImportMeshMapClass,
    ImportMeshCWClass,
    ImportAnimClass,
    ImportSkelClass,
)


# 注册和注销函数
def register():
    """注册类"""
    for cls in classes:
        bpy.utils.register_class(cls)


def unregister():
    """注销类"""
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
