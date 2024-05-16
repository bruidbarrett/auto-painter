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
from datetime import datetime


def log(message):
    log_file = "/Users/barrett/Tristan/Projects/Blender/Thesis/auto_painter_addon.log"
    with open(log_file, "a") as f:
        f.write(message + "\n")

def correct_colors(original_img, modified_img, hue_threshold, sat_threshold, value_threshold):
    log("Correcting colors IN THE ADDON ITSELF...")
    hsv_original = cv2.cvtColor(original_img, cv2.COLOR_BGR2HSV)
    hsv_modified = cv2.cvtColor(modified_img, cv2.COLOR_BGR2HSV)

    for channel in range(3):
        original_channel = hsv_original[:, :, channel]
        modified_channel = hsv_modified[:, :, channel]

        if channel == 0:
            channel_diff = modified_channel.astype(int) - original_channel.astype(int)
            channel_percentage_diff = channel_diff / 180.0
        else:
            channel_diff = modified_channel.astype(int) - original_channel.astype(int)
            channel_percentage_diff = channel_diff / 255.0 

        mask_over = channel_percentage_diff > min(hue_threshold, sat_threshold, value_threshold)
        mask_under = channel_percentage_diff < -max(hue_threshold, sat_threshold, value_threshold)

        if channel == 0:
            modified_channel[mask_over] = (original_channel[mask_over] + hue_threshold * 180).astype(original_channel.dtype) % 180
            modified_channel[mask_under] = (original_channel[mask_under] - hue_threshold * 180).astype(original_channel.dtype) % 180
        else:
            modified_channel[mask_over] = (original_channel[mask_over] + sat_threshold * 255).astype(original_channel.dtype)
            modified_channel[mask_under] = (original_channel[mask_under] - value_threshold * 255).astype(original_channel.dtype)
            modified_channel = np.clip(modified_channel, 0, 255)
        hsv_modified[:, :, channel] = modified_channel

    result_img = cv2.cvtColor(hsv_modified, cv2.COLOR_HSV2BGR)
    log("Color correction completed.")
    return result_img

def bake_normal_map(obj, filepath):
    log(f"Baking normal map of {obj.name} to {filepath}")

    # Ensure the object has an active material
    if not obj.data.materials:
        mat = bpy.data.materials.new(name="Material")
        obj.data.materials.append(mat)
    else:
        mat = obj.active_material

    # Create a new image to bake to
    bake_image = bpy.data.images.new(name="Bake_Image", width=2048, height=2048, float_buffer=False)
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

class AutoPainterProperties(bpy.types.PropertyGroup):
    hue_threshold: bpy.props.FloatProperty(
        name="Hue Threshold",
        description="Threshold for hue adjustment",
        default=100.0,
        min=0.0,
        max=100.0
    )
    sat_threshold: bpy.props.FloatProperty(
        name="Saturation Threshold",
        description="Threshold for saturation adjustment",
        default=100.0,
        min=0.0,
        max=100.0
    )
    value_threshold: bpy.props.FloatProperty(
        name="Value Threshold",
        description="Threshold for value adjustment",
        default=100.0,
        min=0.0,
        max=100.0
    )

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

        # Construct the command to run Blender in background mode
        command = [
            blender_executable,
            "-b", blender_file_path,
            "-P", operation_script_path,
        ]

        log(f"Running command: {' '.join(command)}")

        # Run the command
        result = subprocess.run(command, capture_output=True, text=True)
        log("Subprocess result:")
        log(f"Return code: {result.returncode}")
        log(f"stdout: {result.stdout}")
        log(f"stderr: {result.stderr}")

        if result.returncode != 0:
            log(f"Blender background process failed: {result.stderr}")
            self.report({'ERROR'}, f"Blender background process failed: {result.stderr}")
            return {'CANCELLED'}

        log("Blender background process completed successfully.")

        # Masking and final image processing
        try:
            log("Starting masking process...")

            # Read images
            original_image_path = os.path.join(current_blend_dir, 'normals.png')
            modified_image_path = os.path.join(current_blend_dir, 'painted.png')
            masked_image_path = os.path.join(current_blend_dir, 'masked.png')

            log(f"Original image path: {original_image_path}")
            log(f"Modified image path: {modified_image_path}")

            original_image = cv2.imread(original_image_path)
            modified_image = cv2.imread(modified_image_path)

            log(f"Original image read: {original_image is not None}")
            log(f"Modified image read: {modified_image is not None}")

            if original_image is None:
                log(f"Failed to read original image: {original_image_path}")
                return {'CANCELLED'}

            if modified_image is None:
                log(f"Failed to read modified image: {modified_image_path}")
                return {'CANCELLED'}

            log("Images read successfully.")

            # Create mask of original normal map
            mask = np.all(original_image == [0, 0, 0], axis=-1)

            # Apply mask to rendered image
            modified_image[mask] = [0, 0, 0]
            cv2.imwrite(masked_image_path, modified_image)
            log(f"Masked image saved to {masked_image_path}")

            # Apply color correction
            hue_threshold = context.scene.auto_painter_props.hue_threshold
            sat_threshold = context.scene.auto_painter_props.sat_threshold
            value_threshold = context.scene.auto_painter_props.value_threshold
            result_image = correct_colors(original_image, modified_image, hue_threshold, sat_threshold, value_threshold)

            # Generate the filename with the object name and timestamp
            obj_name = bpy.context.active_object.name
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            final_image_filename = f"final_{obj_name}_{timestamp}.png"
            final_image_path = os.path.join(current_blend_dir, final_image_filename)

            # Save and reload final image
            cv2.imwrite(final_image_path, result_image)
            log(f"Final image saved to {final_image_path}")

            # Reload the image in Blender
            final_image = bpy.data.images.load(final_image_path)
            final_image.reload()

            log("Masking and final image processing completed successfully.")
        except Exception as e:
            log(f"Exception during masking and final image processing: {e}")
            return {'CANCELLED'}

        return {'FINISHED'}

    def apply_texture_to_normal(self, context):
        log("Starting apply_texture_to_normal...")

        # Determine the directory of the currently opened Blender file
        current_blend_dir = os.path.dirname(bpy.data.filepath)
        obj_name = bpy.context.active_object.name
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        final_image_filename = f"final_{obj_name}_{timestamp}.png"
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
            layout.operator("object.auto_painter", text="Auto Paint and Apply Texture")
        else:
            layout.label(text="No object selected")

        layout.prop(context.scene.auto_painter_props, "hue_threshold")
        layout.prop(context.scene.auto_painter_props, "sat_threshold")
        layout.prop(context.scene.auto_painter_props, "value_threshold")

def register():
    log("Registering add-on...")
    bpy.utils.register_class(AutoPainterProperties)
    bpy.types.Scene.auto_painter_props = bpy.props.PointerProperty(type=AutoPainterProperties)
    bpy.utils.register_class(OBJECT_OT_auto_painter)
    bpy.utils.register_class(OBJECT_PT_auto_painter_panel)
    log("Add-on registered successfully.")

def unregister():
    log("Unregistering add-on...")
    bpy.utils.unregister_class(AutoPainterProperties)
    del bpy.types.Scene.auto_painter_props
    bpy.utils.unregister_class(OBJECT_OT_auto_painter)
    bpy.utils.unregister_class(OBJECT_PT_auto_painter_panel)
    log("Add-on unregistered successfully.")

if __name__ == "__main__":
    register()
