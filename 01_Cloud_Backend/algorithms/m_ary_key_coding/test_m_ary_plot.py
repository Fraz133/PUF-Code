"""
Test Script: Visualize M-ary Key Encoding at All 4 Time Nodes
==============================================================
Generates one plot per time node (0.1, 1, 2, 3) showing the 30×30
encoded matrix with the professor's categorical colormap and colorbar.
"""

import matplotlib
matplotlib.use('Agg')

import matplotlib.pyplot as plt
from matplotlib.colors import ListedColormap
import numpy as np
import sys
import os

from m_ary_extractor import generate_mary_key_timenode


def plot_m_ary_keys(image_path):
    """Generate and save M-ary key plots for all 4 time nodes."""
    print(f"Generating M-ary keys for: {image_path}")
    
    # Professor's 4 time nodes
    time_nodes = [0.1, 1, 2, 3]
    
    # 20 distinct categorical colors (similar to MATLAB's lines colormap)
    base_cmap_colors = plt.cm.tab20.colors
    
    output_dir = os.path.join(os.path.dirname(__file__), '..', '..', '..', 'artifacts')
    os.makedirs(output_dir, exist_ok=True)
    
    for t in time_nodes:
        result = generate_mary_key_timenode(image_path, t, grid_size=30)
        data = result['mary_key']
        M = result['mary_base']
        name = result['encoding']
        
        fig, ax = plt.subplots(figsize=(6, 5.5))
        
        # Take the first M colors from tab20
        cmap = ListedColormap(base_cmap_colors[:M])
        
        im = ax.imshow(data, cmap=cmap, vmin=0, vmax=M - 1)
        ax.set_aspect('equal')
        
        # Pixel grid lines (30×30 cells)
        ax.set_xticks(np.arange(-0.5, 30, 1))
        ax.set_yticks(np.arange(-0.5, 30, 1))
        ax.set_xticklabels([])
        ax.set_yticklabels([])
        ax.grid(color=[0.3, 0.3, 0.3], linestyle='-', linewidth=0.5, alpha=0.4)
        ax.tick_params(which='both', bottom=False, left=False)
        
        # Colorbar with proper labels
        cbar = fig.colorbar(im, ax=ax, ticks=range(M))
        cbar.set_label('Encoded Value', fontsize=12)
        
        if M == 16:
            cbar.set_ticklabels(['0','1','2','3','4','5','6','7',
                                 '8','9','A','B','C','D','E','F'])
        else:
            cbar.set_ticklabels([str(i) for i in range(M)])
        
        ax.set_title(f'{name} Key Matrix (t = {t:.1f} s)',
                     fontsize=14, fontweight='bold')
        
        plt.tight_layout()
        
        # Save
        safe_name = name.replace(' ', '_').replace('(', '').replace(')', '').replace('-', '_')
        output_path = os.path.join(output_dir, f'm_ary_{safe_name}.png')
        plt.savefig(output_path, dpi=150)
        plt.close(fig)
        
        print(f"  t={t:.1f}s -> {name}: shape={data.shape}, "
              f"unique={len(np.unique(data))}, max={np.max(data)}")
        print(f"  Saved to: {output_path}")


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: python test_m_ary_plot.py <image_path>")
        sys.exit(1)
        
    image_path = sys.argv[1]
    plot_m_ary_keys(image_path)
