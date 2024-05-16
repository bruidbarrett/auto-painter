bl_info = {
    "name": "Auto Painter",
    "blender": (2, 90, 0),
    "category": "Object",
}

import bpy
import os
import subprocess
import cv2
import numpy as np
import random

random_seed = random.randint(0, 99999)


def log(message):
    log_file = "/Users/barrett/Tristan/Projects/Blender/Thesis/auto-painter/auto_painter.log"
    with open(log_file, "a") as f:
        f.write(message + "\n")

def bake_normal_map(obj, filepath):
    log(f"Baking normal map of {obj.name} to {filepath}")

    # Ensure the object has an active material
    if not obj.data.materials:
        mat = bpy.data.materials.new(name="Material")
        obj.data.materials.append(mat)
    else:
        mat = obj.active_material

    # Create a new image to bake to
    bake_image = bpy.data.images.new(name="Bake_Image", width=1024, height=1024, float_buffer=False)
    bake_image.filepath_raw = filepath
    bake_image.file_format = 'PNG'

    # Add an image texture node to the material
    if not mat.use_nodes:
        mat.use_nodes = True
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links

    tex_image_node = nodes.new(type='ShaderNodeTexImage')
    tex_image_node.image = bake_image
    tex_image_node.select = True
    mat.node_tree.nodes.active = tex_image_node

    # Set bake settings
    bpy.context.scene.cycles.bake_type = 'NORMAL'
    bpy.context.scene.render.bake.use_selected_to_active = False
    bpy.context.scene.render.bake.use_cage = False
    bpy.context.scene.render.bake.cage_extrusion = 0.0
    bpy.context.scene.render.bake.max_ray_distance = 0.0
    bpy.context.scene.render.bake.normal_space = 'OBJECT'
    bpy.context.scene.render.bake.use_clear = True

    # Bake to the image
    bpy.ops.object.bake(type='NORMAL')

    # Save the baked image
    bake_image.save_render(filepath)
    bpy.data.images.remove(bake_image)

    log(f"Normal map baked to {filepath}")

class OBJECT_OT_auto_painter(bpy.types.Operator):
    bl_idname = "object.auto_painter"
    bl_label = "Auto Paint and Apply Texture"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        log("Executing auto painter...")

        # Bake normal map as normals.png
        obj = bpy.context.active_object
        if obj and obj.type == 'MESH':
            normals_filepath = os.path.join(os.path.dirname(bpy.data.filepath), 'normals.png')
            bake_normal_map(obj, normals_filepath)
        else:
            log("No active mesh object selected.")
            self.report({'ERROR'}, "No active mesh object selected.")
            return {'CANCELLED'}

        result = self.auto_paint(context)
        if result == {'CANCELLED'}:
            log("Auto painter cancelled.")
        else:
            log("Auto painter finished successfully.")
            result = self.apply_texture_to_normal(context)
            if result == {'CANCELLED'}:
                log("Apply final texture cancelled.")
            else:
                log("Apply final texture finished successfully.")
        log("Done.")
        return result

    def auto_paint(self, context):
            log("Starting auto_paint...")

            # Generate a random seed
            log(f"SEED GENERATED IN ADDON IS {random_seed}")

            # Determine the directory of the currently opened Blender file
            current_blend_dir = os.path.dirname(bpy.data.filepath)
            log(f"Current blend directory: {current_blend_dir}")

            if not current_blend_dir:
                log("No .blend file is currently opened.")
                self.report({'ERROR'}, "No .blend file is currently opened.")
                return {'CANCELLED'}

            blender_executable = bpy.app.binary_path
            operation_script_path = os.path.join(current_blend_dir, 'auto_painter.py')

            blender_file_path = os.path.join(current_blend_dir, 'painter.blend')
            if not os.path.exists(blender_file_path):
                log(f"Blender file not found: {blender_file_path}")
                self.report({'ERROR'}, f"Blender file not found: {blender_file_path}")
                return {'CANCELLED'}

            if not os.path.exists(operation_script_path):
                log(f"Operation script not found: {operation_script_path}")
                self.report({'ERROR'}, f"Operation script not found: {operation_script_path}")
                return {'CANCELLED'}

            # Construct the command to run Blender in background mode with the seed argument
            command = [
                blender_executable,
                "-b", blender_file_path,
                "-P", operation_script_path,
                "--",  # This separates script arguments from blender's arguments
                str(random_seed)  # Passing seed as an argument
            ]

            log(f"Running command: {' '.join(command)}")

            # Run the command
            result = subprocess.run(command, capture_output=True, text=True)
            log("Subprocess result:")
            log(f"Return code: {result.returncode}")
            # log(f"stdout: {result.stdout}")
            # log(f"stderr: {result.stderr}")

            if result.returncode != 0:
                log(f"Blender background process failed: {result.stderr}")
                self.report({'ERROR'}, f"Blender background process failed: {result.stderr}")
                return {'CANCELLED'}

            log("Blender background process completed successfully.")

            return {'FINISHED'}

    def apply_texture_to_normal(self, context):
            log("Starting apply_texture_to_normal...")

            # Determine the directory of the currently opened Blender file
            current_blend_dir = os.path.dirname(bpy.data.filepath)
            
            final_image_filename = f'final_{random_seed}.png'  # Use the seed in the file name
            final_image_path = os.path.join(current_blend_dir, final_image_filename)

            log(f"Current blend directory: {current_blend_dir}")
            log(f"Final image path: {final_image_path}")

            if not os.path.exists(final_image_path):
                log(f"Final image not found: {final_image_path}")
                self.report({'ERROR'}, f"Final image not found: {final_image_path}")
                return {'CANCELLED'}

            # Load the final.png image
            try:
                final_image = bpy.data.images.load(final_image_path, check_existing=False)
                final_image.reload()
            except Exception as e:
                log(f"Failed to load {final_image_filename}: {e}")
                self.report({'ERROR'}, f"Failed to load {final_image_filename}: {e}")
                return {'CANCELLED'}

            # Get the active object
            obj = bpy.context.active_object

            if obj is None:
                log("No active object selected.")
                self.report({'ERROR'}, "No active object selected.")
                return {'CANCELLED'}

            if obj.type != 'MESH':
                log("Active object is not a mesh.")
                self.report({'ERROR'}, "Active object is not a mesh.")
                return {'CANCELLED'}

            # Get the active material
            mat = obj.active_material

            if mat is None:
                log("Active object has no material.")
                self.report({'ERROR'}, "Active object has no material.")
                return {'CANCELLED'}

            # Use nodes
            mat.use_nodes = True
            nodes = mat.node_tree.nodes
            links = mat.node_tree.links

            # Create an Image Texture node
            tex_image_node = nodes.new(type='ShaderNodeTexImage')
            tex_image_node.image = final_image
            tex_image_node.image.colorspace_settings.name = 'Non-Color'
            tex_image_node.location = (0, 0)

            # Find the Normal Map node or create one
            normal_map_node = None
            for node in nodes:
                if node.type == 'NORMAL_MAP':
                    normal_map_node = node
                    break

            if normal_map_node is None:
                normal_map_node = nodes.new(type='ShaderNodeNormalMap')
                normal_map_node.location = (300, 0)

            normal_map_node.space = 'OBJECT'

            # Link the Image Texture node to the Normal Map node
            links.new(tex_image_node.outputs['Color'], normal_map_node.inputs['Color'])

            # Find the Principled BSDF node
            principled_bsdf = None
            for node in nodes:
                if node.type == 'BSDF_PRINCIPLED':
                    principled_bsdf = node
                    break

            if principled_bsdf is None:
                log("No Principled BSDF node found in the material.")
                self.report({'ERROR'}, "No Principled BSDF node found in the material.")
                return {'CANCELLED'}

            # Link the Normal Map node to the Principled BSDF node
            links.new(normal_map_node.outputs['Normal'], principled_bsdf.inputs['Normal'])

            log("Final image texture applied to the normal input of the selected object's material.")
            self.report({'INFO'}, f"Final image texture applied to the normal input of the selected object's material.")
            return {'FINISHED'}

class OBJECT_PT_auto_painter_panel(bpy.types.Panel):
    bl_idname = "OBJECT_PT_auto_painter_panel"
    bl_label = "Auto Painter"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'Auto Painter'

    def draw(self, context):
        layout = self.layout
        obj = context.active_object

        layout.label(text="Auto Painter")

        if obj:
            layout.label(text=f"Selected: {obj.name}")
            layout.operator("object.auto_painter", text="Auto Paint")
        else:
            layout.label(text="No object selected")

def register():
    log("Registering add-on...")
    bpy.utils.register_class(OBJECT_OT_auto_painter)
    bpy.utils.register_class(OBJECT_PT_auto_painter_panel)
    log("Add-on registered successfully.")

def unregister():
    log("Unregistering add-on...")
    bpy.utils.unregister_class(OBJECT_OT_auto_painter)
    bpy.utils.unregister_class(OBJECT_PT_auto_painter_panel)
    log("Add-on unregistered successfully.")

if __name__ == "__main__":
    # clear log file 
    log_file = "/Users/barrett/Tristan/Projects/Blender/Thesis/auto-painter/auto_painter.log"
    open(log_file, 'w').close()
    register()
