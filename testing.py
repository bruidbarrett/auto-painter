import cv2
import numpy as np
from blend_modes import soft_light

def apply_soft_light_blend(masked_path, colors_path, output_path):
    # Read the masked image and convert to grayscale
    masked_img = cv2.imread(masked_path, cv2.IMREAD_GRAYSCALE)
    if masked_img is None:
        raise ValueError(f"Could not open or find the image {masked_path}")

    # Convert grayscale image to 4 channels (RGBA) where R=G=B and A=255
    masked_img_rgba = cv2.cvtColor(masked_img, cv2.COLOR_GRAY2RGBA)

    masked_img_float = masked_img_rgba.astype(float)  # Convert to float for blending

    # Read the colors image
    colors_img = cv2.imread(colors_path, cv2.IMREAD_UNCHANGED)
    if colors_img is None:
        raise ValueError(f"Could not open or find the image {colors_path}")
    if colors_img.shape[2] < 4:
        colors_img = cv2.cvtColor(colors_img, cv2.COLOR_RGB2RGBA)

    # Convert RGB to HSV, maximize saturation, then convert back to RGBA
    colors_img_hsv = cv2.cvtColor(colors_img, cv2.COLOR_RGBA2RGB)
    colors_img_hsv = cv2.cvtColor(colors_img_hsv, cv2.COLOR_RGB2HSV)
    colors_img_hsv[:, :, 1] = 255  # Set saturation to maximum
    colors_img_rgb = cv2.cvtColor(colors_img_hsv, cv2.COLOR_HSV2RGB)
    colors_img_rgba = cv2.cvtColor(colors_img_rgb, cv2.COLOR_RGB2RGBA)

    colors_img_float = colors_img_rgba.astype(float)  # Convert to float for blending

    # Apply soft_light blend mode with 100% opacity
    blended_img_float = soft_light(colors_img_float, masked_img_float, opacity=0.6)

    # Convert the blended image back to uint8
    blended_img_uint8 = blended_img_float.astype(np.uint8)

    # Save the result
    cv2.imwrite(output_path, blended_img_uint8)
    print(f"Blended image saved to {output_path}")

# Usage
apply_soft_light_blend('masked.png', 'colors.png', 'output1.png')
