# ui.py
from .log import log
import bpy


class ImportPanel(bpy.types.Panel):
    """导入面板"""

    bl_label = "PDE Model Tools"
    bl_idname = "PDEIMPORT_PT_import_panel"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "PMT"

    def draw(self, context):
        """绘制面板"""
        layout = self.layout
        # 定义按钮配置 (标签, 操作符, 图标)
        button_configs = [
            ("导入模型", "", "FILE_3D"),
            ("", "import.mesh_prop", "道具 / Prop"),
            ("", "import.mesh_map", "地图 / Map"),
            ("", "import.cm_mesh", "人物&武器 / Character&Weapon"),
            ("导入骨骼", "", "GROUP_BONE"),
            ("", "import.skel", "骨骼 / Skel"),
            ("导入动画", "", "POSE_HLT"),
            ("", "import.anim", "动画 / Anim"),
            ("骨骼目录", "", "GROUP_BONE"),
        ]

        for label, operator, text in button_configs:
            if label:  # 分类标签
                layout.label(text=label, icon=text)
            else:  # 操作按钮
                layout.operator(operator, text=text)

        # 骨骼目录
        addon = context.preferences.addons.get(__package__)
        if addon and (addon_prefs := addon.preferences):
            bone_dir = addon_prefs.pmt_bone_dir
            log.debug("当前骨骼路径:%s", bone_dir)
            if bone_dir:
                layout.label(text=f"{bone_dir}")
            else:
                # 路径设置按钮
                layout.operator("preferences.addon_show", text="前往设置").module = (
                    __package__
                )
        else:
            layout.label(text="偏好设置未初始化", icon="ERROR")
