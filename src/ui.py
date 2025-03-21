# ui.py
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
            ("导入动画", "", "POSE_HLT"),
            ("", "import.anim", "动画 / Anim"),
            ("导入骨骼", "", "GROUP_BONE"),
            ("", "import.skel", "骨骼 / Skel"),
        ]

        for label, operator, text in button_configs:
            if label:  # 分类标签
                layout.label(text=label, icon=text)
            else:  # 操作按钮
                layout.operator(operator, text=text)
