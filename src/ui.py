import bpy


class MeshPanel(bpy.types.Panel):
    """MESH面板"""

    bl_label = "MESH面板"


class ImportPanel(bpy.types.Panel):
    """导入面板"""

    bl_label = "PDE Model Tools"
    bl_idname = "PDEIMPORT_PT_import_panel"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "PMT"

    def draw(self, context):
        layout = self.layout
        layout.label(text="导入MESH")
        layout.operator("import.mesh_prop", text="道具模型")
        layout.operator("import.mesh_map", text="地图模型")
        layout.operator("import.wcm_mesh", text="武器和人物模型")
        layout.label(text="导入ANIM")
        layout.operator("import.anim", text="导入动画", icon="IMPORT")
        layout.label(text="导入SKEL")
        layout.operator("import.skel", text="导入骨骼", icon="IMPORT")
