import bpy
import os
import cv2
import numpy as np

def log(message):
    log_file = "/Users/barrett/Tristan/Projects/Blender/Thesis/auto-painter/auto_painter.log"
    with open(log_file, "a") as f:
        f.write(message + "\n")

def correct_colors(original_img, modified_img, hue_threshold, sat_threshold, value_threshold):
    log("Correcting colors IN AUTO PAINTER...")
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

def main():
    log("Starting main function...")
    current_blend_dir = os.path.dirname(bpy.data.filepath)
    blender_file_path = os.path.join(current_blend_dir, 'painter.blend')
    image_path = os.path.join(current_blend_dir, 'normals.png')
    output_path = os.path.join(current_blend_dir, 'painted.png')
    mask_path = os.path.join(current_blend_dir, 'masked.png')
    final_path = os.path.join(current_blend_dir, 'final.png')

    # Open the Blender file
    bpy.ops.wm.open_mainfile(filepath=blender_file_path)

    # Replace the packed image data with the new image
    packed_image_name = 'normals.png'
    image_found = False
    for image in bpy.data.images:
        if image.name == packed_image_name:
            log(f"Found packed image: {image.name}")
            image.filepath = image_path
            log(f"Setting image filepath to: {image.filepath}")
            image.source = 'FILE'
            image.reload()
            image.pack()
            image_found = True
            log("Image replaced and repacked successfully.")
            break

    if not image_found:
        log(f"Image named '{packed_image_name}' not found in the blend file.")
        return

    # Set resolution
    bpy.context.scene.render.resolution_x = 2048
    bpy.context.scene.render.resolution_y = 2048
    bpy.context.scene.render.resolution_percentage = 100

    # Set output path
    bpy.context.scene.render.filepath = output_path
    bpy.context.scene.render.image_settings.file_format = 'PNG'

    # Render painted normals
    log("Rendering painted normals...")
    bpy.ops.render.render(write_still=True)
    log("Painted normal map generated!")

    # Create mask of original normal map
    original_image = cv2.imread(image_path)
    mask = np.all(original_image == [0, 0, 0], axis=-1)
    log("Mask created.")

    # Apply mask to rendered image
    modified_image = cv2.imread(output_path)
    modified_image[mask] = [0, 0, 0]
    cv2.imwrite(mask_path, modified_image)
    log("Clipping mask applied successfully.")

    # Apply color correction
    hue_threshold = 100
    sat_threshold = 100
    value_threshold = 100
    result_image = correct_colors(original_image, modified_image, hue_threshold, sat_threshold, value_threshold)
    cv2.imwrite(final_path, result_image)
    log("Color correction applied!")

if __name__ == "__main__":
    log("Running as main script.")
    main()