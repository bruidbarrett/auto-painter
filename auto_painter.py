import colorsys
import bpy
import os
import cv2
import numpy as np
import sys
import random

def log(message):
    log_file = "/Users/barrett/Tristan/Projects/Blender/Thesis/auto-painter/addon.log"
    with open(log_file, "a") as f:
        f.write(message + "\n")

def correct_colors_advanced(original_img, modified_img):
    # Convert images to HSV and ensure floating point precision
    hsv_original = cv2.cvtColor(original_img, cv2.COLOR_BGR2HSV).astype(np.float32)
    hsv_modified = cv2.cvtColor(modified_img, cv2.COLOR_BGR2HSV).astype(np.float32)

    # Normalizing HSV values to range [0, 1] for calculations
    hsv_original /= [180, 255, 255]
    hsv_modified /= [180, 255, 255]

    # Define the thresholds for hue, saturation, and value differences
    hue_threshold = 0.04 # 0.4%
    sat_threshold = 0.12 # 1.2%
    val_threshold = 0.12 # 1.2%

    # Correction logic
    for i in range(hsv_original.shape[0]):
        for j in range(hsv_original.shape[1]):
            # Calculate the hue difference correctly, considering circular nature
            h_diff = (hsv_modified[i, j, 0] - hsv_original[i, j, 0]) % 1
            if h_diff > 0.5:
                h_diff -= 1  # Correct for circular hue values
            h_diff = abs(h_diff)  # Get absolute difference

            # Differences for saturation and value
            s_diff = abs(hsv_modified[i, j, 1] - hsv_original[i, j, 1])
            v_diff = abs(hsv_modified[i, j, 2] - hsv_original[i, j, 2])

            # Apply correction if differences exceed the thresholds
            corrected_hsv = hsv_modified[i, j].copy()  # Start with the current modified values
            if h_diff > hue_threshold:
                corrected_hsv[0] = (hsv_original[i, j, 0] + np.sign(hsv_modified[i, j, 0] - hsv_original[i, j, 0]) * hue_threshold) % 1
            if s_diff > sat_threshold:
                corrected_hsv[1] = hsv_original[i, j, 1] + np.sign(hsv_modified[i, j, 1] - hsv_original[i, j, 1]) * sat_threshold
            if v_diff > val_threshold:
                corrected_hsv[2] = hsv_original[i, j, 2] + np.sign(hsv_modified[i, j, 2] - hsv_original[i, j, 2]) * val_threshold
                # Clip the value to the range [0, 1]
                corrected_hsv[2] = np.clip(corrected_hsv[2], 0, 1)

            # Assign corrected values (convert back to original scale if necessary)
            hsv_modified[i, j] = corrected_hsv * [180, 255, 255]

    # Convert corrected HSV back to BGR and to uint8
    corrected_img_bgr = cv2.cvtColor(hsv_modified.astype(np.uint8), cv2.COLOR_HSV2BGR)
    return corrected_img_bgr

def paint_normal_map(resolution_arg, samples_arg, seed):
    log("Starting NORMAL MAP painting...")
    current_blend_dir = os.path.dirname(bpy.data.filepath)
    blender_file_path = os.path.join(current_blend_dir, 'painter.blend')
    image_path = os.path.join(current_blend_dir, 'normals.png')
    output_path = os.path.join(current_blend_dir, 'painted.png')
    mask_path = os.path.join(current_blend_dir, 'masked.png')

    # Use the seed in your file paths
    final_path = os.path.join(current_blend_dir, f'final_{seed}.png')

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

    # set resolution and sample count
    bpy.context.scene.render.resolution_x = resolution_arg
    bpy.context.scene.render.resolution_y = resolution_arg
    bpy.context.scene.render.resolution_percentage = 100
    bpy.context.scene.cycles.samples = samples_arg

    # set output path
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

    # Apply color correction with desired percentage
    result_image = correct_colors_advanced(original_image, modified_image)
    cv2.imwrite(final_path, result_image)
    log("Color correction applied!")

def paint_color_map(resolution_arg, samples_arg, seed):
    log("Starting COLOR MAP painting...")
    current_blend_dir = os.path.dirname(bpy.data.filepath)
    blender_file_path = os.path.join(current_blend_dir, 'color_painter.blend')
    image_path = os.path.join(current_blend_dir, 'colors.png')
    pre_path = os.path.join(current_blend_dir, f'pre_colors_{seed}.png')


    # Convert black pixels to transparent
    image = cv2.imread(image_path, cv2.IMREAD_UNCHANGED)

    # Check if image has an alpha channel, if not, add one
    if image.shape[2] == 3:
        image = cv2.cvtColor(image, cv2.COLOR_RGB2RGBA)

    # Set black pixels to transparent
    image[np.all(image[:, :, :3] == [0, 0, 0], axis=-1)] = [0, 0, 0, 0]
    cv2.imwrite(image_path, image)

    # Open the Blender file
    bpy.ops.wm.open_mainfile(filepath=blender_file_path)
    
    # Replace the packed image data with the new image
    packed_image_name = 'colors.png'
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

    # set resolution and sample count
    bpy.context.scene.render.resolution_x = resolution_arg
    bpy.context.scene.render.resolution_y = resolution_arg
    bpy.context.scene.render.resolution_percentage = 100
    bpy.context.scene.cycles.samples = samples_arg

    # set output path
    bpy.context.scene.render.filepath = pre_path
    bpy.context.scene.render.image_settings.file_format = 'PNG'

    # Render painted colors
    log("Rendering painted color map...")
    bpy.ops.render.render(write_still=True)
    log("Painted color map generated!")

    # Load the final rendered image
    final_image = cv2.imread(pre_path, cv2.IMREAD_UNCHANGED)
    
    # Check if the image has an alpha channel
    if final_image.shape[2] == 4:
        # Split alpha channel if present
        color_channels, alpha_channel = final_image[..., :3], final_image[..., 3]
    else:
        color_channels = final_image

    # color correct hue
    hsv_image = cv2.cvtColor(color_channels, cv2.COLOR_RGB2HSV)
    hsv_image[:, :, 0] = (hsv_image[:, :, 0].astype(int) - 2) % 180  # Adjust hue by -0.5
    # hsv_image[:, :, 1] = np.maximum(hsv_image[:, :, 1] - 10, 0)   # Lower saturation by 4% of 255
    hsv_image[:, :, 2] = np.clip(hsv_image[:, :, 2] * 1.05, 0, 255) # Increase value by 5%
    adjusted_rgb = cv2.cvtColor(hsv_image, cv2.COLOR_HSV2RGB)

    # Combine with alpha channel if it was present
    if final_image.shape[2] == 4:
        adjusted_rgb = np.dstack((adjusted_rgb, alpha_channel))

    # Save the adjusted image
    adjusted_image_path = os.path.join(current_blend_dir, f'final_colors_{seed}.png')
    cv2.imwrite(adjusted_image_path, adjusted_rgb)

    log("Hue adjusted and final image saved!")



def main():
    log("Starting main function...")

    # parse cli arguments (resolution, samples, and seed)
    log(f"Command-line arguments received: {sys.argv}")
    args = sys.argv[sys.argv.index("--") + 1:]  # Get all args after "--"
    resolution_arg = int(args[args.index('render_resolution') + 1])
    samples_arg = int(args[args.index('samples') + 1])
    seed = args[args.index('seed') + 1]
    log(f"SEED IN AUTO_PAINTER.py: {seed}")

    # auto paint normal map
    paint_normal_map(resolution_arg, samples_arg, seed)

    # auto paint color map
    paint_color_map(resolution_arg, samples_arg, seed)

if __name__ == "__main__":
    main()
