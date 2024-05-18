import colorsys
import bpy
import os
import cv2
import numpy as np
import sys

def log(message):
    log_file = "/Users/barrett/Tristan/Projects/Blender/Thesis/auto-painter/auto_painter.log"
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
    hue_threshold = 0.02  # 1%
    sat_threshold = 0.07  # 5%
    val_threshold = 0.07  # 5%

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

def main():
    log("Starting main function...")
    current_blend_dir = os.path.dirname(bpy.data.filepath)
    blender_file_path = os.path.join(current_blend_dir, 'painter.blend')
    image_path = os.path.join(current_blend_dir, 'normals.png')
    output_path = os.path.join(current_blend_dir, 'painted.png')
    mask_path = os.path.join(current_blend_dir, 'masked.png')

    # Parse command-line arguments for seed and desired percentage
    seed_index = sys.argv.index("--") + 1 if "--" in sys.argv else -1
    seed = sys.argv[seed_index] if seed_index != -1 and seed_index < len(sys.argv) else 'default_seed'

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

    # Set resolution
    bpy.context.scene.render.resolution_x = 1024
    bpy.context.scene.render.resolution_y = 1024
    bpy.context.scene.render.resolution_percentage = 100
    # sample count 
    bpy.context.scene.cycles.samples = 20

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

    # Apply color correction with desired percentage
    result_image = correct_colors_advanced(original_image, modified_image)
    cv2.imwrite(final_path, result_image)
    log("Color correction applied!")

if __name__ == "__main__":
    log(f"Command-line arguments received: {sys.argv}")
    log("Running as main script.")
    main()
