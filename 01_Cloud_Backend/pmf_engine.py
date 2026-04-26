"""
PMF (Pixel Matrix Function) Engine
====================================
Handles the physics-based exponential decay model for PUF authentication.

The phosphorescent particles in a PUF tag decay according to the equation:
    I(t) = A * e^(-t/tau) + C

Where:
    A   = Initial amplitude (how bright the pixel starts)
    tau = Decay time constant (how fast it fades)
    C   = Baseline offset (residual glow that never fully fades)

During ENROLLMENT:
    - We receive grayscale intensity grids at multiple time nodes
    - We fit the (A, tau, C) parameters for each grid cell using vectorized
      log-linearized least squares (fast analytical method)
    - These parameters are stored in MongoDB

During AUTHENTICATION:
    - We receive the user's time_node and their uploaded image's intensity grid
    - We use stored (A, tau, C) to PREDICT what intensity should be at that time
    - We compare predicted vs actual using RMSE
"""

import numpy as np
import warnings

# Suppress numpy warnings for log of zero etc.
warnings.filterwarnings('ignore', category=RuntimeWarning)


# ============================================================
# The Physics Model
# ============================================================
def decay_model(t, A, tau, C):
    """
    Exponential decay function for phosphorescence.
    
    I(t) = A * e^(-t/tau) + C
    
    Args:
        t: Time in seconds after UV excitation
        A: Initial amplitude
        tau: Decay time constant (seconds)
        C: Baseline offset
    
    Returns:
        Predicted intensity value
    """
    return A * np.exp(-t / tau) + C


# ============================================================
# ENROLLMENT: Fit Decay Curves (VECTORIZED - Fast)
# ============================================================
def fit_pmf_parameters(grayscale_grids_over_time, time_nodes):
    """
    Fits exponential decay parameters (A, tau, C) for each grid cell 
    across all time nodes.
    
    Uses a VECTORIZED analytical approach instead of per-cell curve_fit,
    making it ~1000x faster. The method:
      1. Estimate C as the minimum intensity across time nodes
      2. Subtract C to get: I'(t) = I(t) - C ~ A * e^(-t/tau)
      3. Take log: ln(I') = ln(A) - t/tau  -> linear regression for A and tau
    
    Args:
        grayscale_grids_over_time: dict of channel_name -> list of 32x32 grids
            e.g. { 'Blue_Cyan': [grid_t0, grid_t1, grid_t2, ...], ... }
        time_nodes: list of float time values
            e.g. [0.1, 1.5, 3.0, 4.5, 6.0]
    
    Returns:
        dict: { 'Blue_Cyan': { 'A': 32x32, 'tau': 32x32, 'C': 32x32 }, ... }
    """
    time_array = np.array(time_nodes, dtype=np.float64)
    n_times = len(time_nodes)
    pmf_params = {}
    
    for channel_name, grids_list in grayscale_grids_over_time.items():
        grid_size = grids_list[0].shape[0]
        n_cells = grid_size * grid_size
        
        # Stack all time-node grids into shape (n_times, grid_size, grid_size)
        # then flatten to (n_times, n_cells) for vectorized processing
        stacked = np.stack([np.array(g, dtype=np.float64) for g in grids_list], axis=0)
        flat = stacked.reshape(n_times, n_cells)  # shape: (n_times, n_cells)
        
        # Initialize parameter arrays (flat)
        A_flat = np.zeros(n_cells, dtype=np.float64)
        tau_flat = np.zeros(n_cells, dtype=np.float64)
        C_flat = np.zeros(n_cells, dtype=np.float64)
        
        # Find active cells (max intensity across time > 5.0)
        max_intensity = np.max(flat, axis=0)  # shape: (n_cells,)
        active_mask = max_intensity >= 5.0
        
        if np.any(active_mask):
            active_flat = flat[:, active_mask]  # shape: (n_times, n_active)
            
            # Step 1: Estimate C as the minimum intensity across time
            C_est = np.min(active_flat, axis=0)  # shape: (n_active,)
            
            # Step 2: Subtract C and clamp to avoid log(0)
            shifted = active_flat - C_est[np.newaxis, :]  # shape: (n_times, n_active)
            shifted = np.clip(shifted, 1.0, None)  # Clamp minimum to 1.0
            
            # Step 3: Linearize: ln(I') = ln(A) - t/tau
            log_shifted = np.log(shifted)  # shape: (n_times, n_active)
            
            # Step 4: Linear regression for each cell: y = mx + b
            # where y = log_shifted, x = time_array, m = -1/tau, b = ln(A)
            # Using normal equations: [b, m] = (X^T X)^-1 X^T y
            X = np.column_stack([np.ones(n_times), time_array])  # shape: (n_times, 2)
            XtX_inv = np.linalg.inv(X.T @ X)  # shape: (2, 2)
            coeffs = XtX_inv @ X.T @ log_shifted  # shape: (2, n_active)
            
            # Extract parameters
            ln_A = coeffs[0, :]  # intercept = ln(A)
            neg_inv_tau = coeffs[1, :]  # slope = -1/tau
            
            A_est = np.exp(ln_A)
            # tau = -1/slope, clamp to physical range [0.01, 50]
            with np.errstate(divide='ignore', invalid='ignore'):
                tau_est = np.where(neg_inv_tau < 0, -1.0 / neg_inv_tau, 2.0)
            tau_est = np.clip(tau_est, 0.01, 50.0)
            A_est = np.clip(A_est, 0.0, 500.0)
            C_est = np.clip(C_est, 0.0, 300.0)
            
            # Write back to flat arrays
            A_flat[active_mask] = A_est
            tau_flat[active_mask] = tau_est
            C_flat[active_mask] = C_est
        
        # Reshape back to grid
        A_grid = A_flat.reshape(grid_size, grid_size)
        tau_grid = tau_flat.reshape(grid_size, grid_size)
        C_grid = C_flat.reshape(grid_size, grid_size)
        
        pmf_params[channel_name] = {
            'A': A_grid,
            'tau': tau_grid,
            'C': C_grid
        }
        
        active_cells = np.count_nonzero(A_grid)
        print(f"    {channel_name:>15s}: {active_cells} cells fitted with decay curves")
    
    return pmf_params


# ============================================================
# AUTHENTICATION: Direct Reference Comparison
# ============================================================
def compare_pmf_direct(actual_grids, reference_grids):
    """
    Compares actual grayscale intensities against the enrolled 
    reference grids stored in the database for that specific time node.
    
    This is much more stable than curve fitting.
    """
    channel_results = {}
    all_scores = []
    
    for channel_name in ['Blue', 'Green', 'Yellow', 'Red']:
        actual = np.array(actual_grids.get(channel_name, np.zeros((30,30))), dtype=np.float64)
        reference = np.array(reference_grids.get(channel_name, np.zeros((30,30))), dtype=np.float64)
        
        # Calculate RMSE
        diff = actual - reference
        rmse = float(np.sqrt(np.mean(diff ** 2)))
        
        # Convert RMSE to a match percentage (0-100)
        # We use a fixed normalization of 100.0 for consistent sensitivity
        match_percent = max(0.0, (1.0 - (rmse / 100.0)) * 100.0)
        match_percent = round(match_percent, 2)
        
        # PMF threshold: 75% for direct matching
        passed = match_percent >= 75.0
        
        channel_results[channel_name] = {
            'rmse': round(rmse, 2),
            'match_percent': match_percent,
            'passed': passed
        }
        all_scores.append(match_percent)
    
    overall = round(sum(all_scores) / len(all_scores), 2) if all_scores else 0.0
    return channel_results, overall


# ============================================================
# Quick Self-Test
# ============================================================
if __name__ == "__main__":
    print("PMF Engine Self-Test")
    print("=" * 40)
    
    # Simulate a single pixel's decay over 5 time nodes
    times = [0.1, 1.5, 3.0, 4.5, 6.0]
    
    # True parameters: A=200, tau=3.0, C=10
    true_A, true_tau, true_C = 200.0, 3.0, 10.0
    simulated = [decay_model(t, true_A, true_tau, true_C) for t in times]
    print(f"Simulated decay: {[f'{v:.1f}' for v in simulated]}")
    
    # Test the vectorized fitting with a small 2x2 grid
    grids_over_time = {
        'Blue': [
            np.array([[simulated[i], simulated[i]*0.5], [0.0, simulated[i]*0.8]]) 
            for i in range(5)
        ]
    }
    
    params = fit_pmf_parameters(grids_over_time, times)
    p = params['Blue']
    print(f"\nFitted cell (0,0): A={p['A'][0,0]:.1f}, tau={p['tau'][0,0]:.2f}, C={p['C'][0,0]:.1f}")
    print(f"True:              A={true_A}, tau={true_tau}, C={true_C}")
    
    # Predict at t=3.0
    # Test the direct comparison
    test_results, overall = compare_pmf_direct(grids_over_time['Blue'][0], grids_over_time['Blue'][0])
    print(f"\nSelf-Match Test: {overall}%")
