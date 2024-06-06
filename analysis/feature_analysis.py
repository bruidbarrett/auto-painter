import cv2
import os
import numpy as np
from sklearn.decomposition import PCA
import matplotlib.pyplot as plt
from scipy.spatial import ConvexHull

def extract_features(image_path, display=False):
    """Extract features using color histograms for hue, saturation, and value channels."""
    image = cv2.imread(image_path)
    hsv_image = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
    # Calculate the histogram for all three channels: hue, saturation, and value
    hist_hue = cv2.calcHist([hsv_image], [0], None, [180], [0, 180])
    hist_saturation = cv2.calcHist([hsv_image], [1], None, [256], [0, 256])
    hist_value = cv2.calcHist([hsv_image], [2], None, [256], [0, 256])
    # Normalize and flatten the histograms to create a feature vector
    hist_hue = cv2.normalize(hist_hue, hist_hue).flatten()
    hist_saturation = cv2.normalize(hist_saturation, hist_saturation).flatten()
    hist_value = cv2.normalize(hist_value, hist_value).flatten()
    
    if display:
        plt.figure(figsize=(18, 4))
        plt.subplot(141), plt.imshow(cv2.cvtColor(image, cv2.COLOR_BGR2RGB))
        plt.title('Original Image')
        plt.axis('off')  # Turn off axis numbers and ticks

        plt.subplot(142)
        plt.plot(hist_hue, color='r')
        plt.fill_between(range(len(hist_hue)), hist_hue, color='red', alpha=0.3)
        plt.title('Hue Histogram')

        plt.subplot(143)
        plt.plot(hist_saturation, color='g')
        plt.fill_between(range(len(hist_saturation)), hist_saturation, color='green', alpha=0.3)
        plt.title('Saturation Histogram')

        plt.subplot(144)
        plt.plot(hist_value, color='b')
        plt.fill_between(range(len(hist_value)), hist_value, color='blue', alpha=0.3)
        plt.title('Value Histogram')

        plt.show()

    return np.hstack((hist_hue, hist_saturation, hist_value))

def process_folder(folder_path, display=False):
    """Process all images in the folder and extract their features."""
    features = []
    files = [f for f in os.listdir(folder_path) if f.endswith('.png')]
    for file in files:
        file_path = os.path.join(folder_path, file)
        features.append(extract_features(file_path, display))
    return features

def plot_cluster_results(features_real, features_generated):
    """PCA Cluster Visualization of HSV Features"""
    all_features = np.vstack((features_real, features_generated))
    pca = PCA(n_components=2)
    reduced_features = pca.fit_transform(all_features)
    real_features_2D = reduced_features[:len(features_real)]
    generated_features_2D = reduced_features[len(features_real):]

    plt.figure(figsize=(10, 7))
    colors = ['blue', 'red']

    def plot_convex_hull(points, color):
        if len(points) >= 3:
            hull = ConvexHull(points)
            for simplex in hull.simplices:
                plt.plot(points[simplex, 0], points[simplex, 1], color=color, alpha=0.5)
            plt.fill(points[hull.vertices,0], points[hull.vertices,1], c=color, alpha=0.2)

    plot_convex_hull(real_features_2D, colors[0])
    plot_convex_hull(generated_features_2D, colors[1])

    plt.scatter(real_features_2D[:, 0], real_features_2D[:, 1], c='blue', label='Real Paintings')
    plt.scatter(generated_features_2D[:, 0], generated_features_2D[:, 1], c='red', label='Generated Paintings')
    plt.title('PCA-Reduced HSV Feature Distribution')
    plt.xlabel('Principal Component 1 (PC1)')
    plt.ylabel('Principal Component 2 (PC2)')
    plt.legend()
    plt.show()

def main():
    path_to_real_images = "/Users/barrett/Tristan/Projects/Blender/Thesis/Refrences"
    path_to_generated_images = "/Users/barrett/Tristan/Projects/Blender/Thesis/Generated"

    features_real = process_folder(path_to_real_images, display=True)
    features_generated = process_folder(path_to_generated_images, display=True)

    plot_cluster_results(features_real, features_generated)

if __name__ == "__main__":
    main()
