import cv2
import os
import numpy as np
import matplotlib.pyplot as plt

def detect_edges(image):
    """Apply Canny Edge Detection to an image and calculate edge orientations."""
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    edges = cv2.Canny(gray, 100, 200)
    # Sobel operators to find x and y gradients
    sobelx = cv2.Sobel(gray, cv2.CV_64F, 1, 0, ksize=5)
    sobely = cv2.Sobel(gray, cv2.CV_64F, 0, 1, ksize=5)
    # Calculate the angle of the gradients
    edge_orientations = np.arctan2(sobely, sobelx) * (180 / np.pi)
    return edges, edge_orientations

def analyze_folder(folder_path, label, display=False):
    """Process all images in a folder for edge detection and optionally plot results."""
    files = [os.path.join(folder_path, f) for f in os.listdir(folder_path) if f.endswith('.png')]
    edge_images = []
    orientation_distributions = []
    for file in files:
        image = cv2.imread(file)
        if image is not None:
            edges, orientations = detect_edges(image)
            edge_images.append(edges)
            orientation_distributions.append(orientations)
            if display:
                plt.figure(figsize=(15, 5))
                plt.subplot(131), plt.imshow(cv2.cvtColor(image, cv2.COLOR_BGR2RGB)), plt.title(f'Original Image - {label}')
                plt.subplot(132), plt.imshow(edges, cmap='gray'), plt.title(f'Edges Detected - {label}')
                plt.subplot(133), plt.imshow(orientations, cmap='hsv'), plt.title(f'Edge Orientations - {label}')
                plt.show()
    return edge_images, orientation_distributions

def compare_edge_statistics(real_edges, generated_edges, real_orientations, generated_orientations):
    """Compare edge density and plot histograms for real and generated images."""
    real_densities = [np.sum(edges) / edges.size for edges in real_edges]
    generated_densities = [np.sum(edges) / edges.size for edges in generated_edges]
    
    plt.figure(figsize=(24, 6))

    plt.subplot(121)
    plt.hist(real_densities, bins=40, range=(0, 100), alpha=0.7, label='Real Paintings')
    plt.hist(generated_densities, bins=40, range=(0, 100), alpha=0.7, label='Generated Paintings', color='r')
    plt.title('Comparison of Edge Density')
    plt.xlabel('Edge Density')
    plt.ylabel('Frequency')
    plt.legend()

    # Flatten orientation arrays for histogram plotting
    real_orientations_flat = np.hstack([o.flatten() for o in real_orientations])
    generated_orientations_flat = np.hstack([o.flatten() for o in generated_orientations])

    plt.subplot(122)
    plt.hist(real_orientations_flat, bins=180, range=(-180, 180), alpha=0.7, label='Real Paintings')
    plt.hist(generated_orientations_flat, bins=180, range=(-180, 180), alpha=0.7, label='Generated Paintings', color='r')
    plt.title('Comparison of Edge Orientation Distributions')
    plt.xlabel('Edge Orientation (Degrees)')
    plt.ylabel('Frequency')
    plt.legend()
    plt.yscale('log')

    plt.show()

def main():
    path_to_real_images = "/Users/barrett/Tristan/Projects/Blender/Thesis/Refrences"
    path_to_generated_images = "/Users/barrett/Tristan/Projects/Blender/Thesis/Generated"

    real_edges, real_orientations = analyze_folder(path_to_real_images, 'Real', display=False)
    generated_edges, generated_orientations = analyze_folder(path_to_generated_images, 'Generated', display=False)

    compare_edge_statistics(real_edges, generated_edges, real_orientations, generated_orientations)

if __name__ == "__main__":
    main()
