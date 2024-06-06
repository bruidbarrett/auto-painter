import cv2
import os
import numpy as np
import matplotlib.pyplot as plt

def detect_strokes(image_path):
    """Detect and analyze strokes based on their direction and length."""
    image = cv2.imread(image_path)
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    edges = cv2.Canny(gray, 50, 150, apertureSize=3)
    
    # Adjusting parameters to detect longer lines and be more selective
    lines = cv2.HoughLinesP(edges, 1, np.pi / 180, threshold=30, minLineLength=10, maxLineGap=20)
    
    directions = []
    lengths = []
    
    if lines is not None:
        for line in lines:
            x1, y1, x2, y2 = line[0]
            length = np.sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2)
            angle = np.arctan2(y2 - y1, x2 - x1) * 180 / np.pi
            directions.append(angle)
            lengths.append(length)
            # Drawing lines on the image for visualization
            cv2.line(image, (x1, y1), (x2, y2), (0, 255, 0), 2)
    
    return directions, lengths, image

def analyze_folder(folder_path, display=False):
    """Process all images in a folder for stroke direction and length analysis."""
    files = [os.path.join(folder_path, f) for f in os.listdir(folder_path) if f.endswith('.png')]
    all_directions = []
    all_lengths = []
    
    for file in files:
        directions, lengths, annotated_image = detect_strokes(file)
        all_directions.extend(directions)
        all_lengths.extend(lengths)
        
        if display:
            plt.figure(figsize=(10, 5))
            plt.imshow(cv2.cvtColor(annotated_image, cv2.COLOR_BGR2RGB))
            plt.title(f'Strokes Detected in {os.path.basename(file)}')
            plt.show()
    
    return all_directions, all_lengths

def plot_comparative_results(real_directions, real_lengths, generated_directions, generated_lengths):
    """Plot comparative histograms of stroke directions and lengths for both datasets."""
    plt.figure(figsize=(12, 6))
    
    # Plotting stroke directions comparison
    plt.subplot(1, 2, 1)
    plt.hist(real_directions, bins=180, range=(-100, 100), color='blue', alpha=0.5, label='Real Paintings')
    plt.hist(generated_directions, bins=180, range=(-100, 100), color='red', alpha=0.5, label='Generated Paintings')
    plt.title('Comparison of Stroke Directions')
    plt.xlabel('Angle (degrees)')
    plt.ylabel('Frequency')
    plt.legend()
    plt.yscale('log')
    
    # Plotting stroke lengths comparison
    plt.subplot(1, 2, 2)
    plt.hist(real_lengths, bins=50, color='blue', alpha=0.5, label='Real Paintings')
    plt.hist(generated_lengths, bins=50, color='red', alpha=0.5, label='Generated Paintings')
    plt.title('Comparison of Stroke Lengths')
    plt.xlabel('Length (pixels)')
    plt.ylabel('Frequency')
    plt.legend()
    plt.yscale('log')
    
    plt.show()

def main():
    # path_to_real_images = input("Enter the path to the folder of real paintings: ")
    path_to_real_images = "/Users/barrett/Tristan/Projects/Blender/Thesis/Refrences"
    
    # path_to_generated_images = input("Enter the path to the folder of generated paintings: ")
    path_to_generated_images = "/Users/barrett/Tristan/Projects/Blender/Thesis/Generated"
    
    print("\nAnalyzing real paintings...")
    real_directions, real_lengths = analyze_folder(path_to_real_images, display=False)
    
    print("\nAnalyzing generated paintings...")
    generated_directions, generated_lengths = analyze_folder(path_to_generated_images, display=True)
    
    print("\nComparing results...")
    plot_comparative_results(real_directions, real_lengths, generated_directions, generated_lengths)

if __name__ == "__main__":
    main()
