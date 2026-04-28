# TDM-PUF Project: Technical Explanation for Professor

This document provides a clear, academic breakdown of the M-ary key generation logic and the four specific improvements implemented based on recent feedback.

---

## 1. M-ary Key Generation Logic
The M-ary key generation is a **Time-Dependent Quantization** process. Unlike binary keys which only have two states (0 or 1), M-ary keys capture the intensity variations of the phosphor decay over time using different numerical bases ($M$).

### Step-by-Step Implementation:
1.  **Image Capture & Time-Stamping**: A photo is captured at a specific time node ($t$) after the UV excitation source is removed.
2.  **Grayscale Transformation**: The image is converted to grayscale using the standard MATLAB NTSC weights:
    $$Gray = 0.2989 \times R + 0.5870 \times G + 0.1140 \times B$$
    *This ensures we maintain the physical luminance of the phosphor colors.*
3.  **Bicubic Spline Resizing**: To standardize the data, the image is resized to a **30×30 grid**. We use **Bicubic Spline Interpolation** (mirroring MATLAB’s `interp2 cubic`) to preserve the smooth gradients of the light decay without introducing aliasing artifacts.
4.  **Min-Max Normalization**: The 30×30 grid values are normalized to a range of $[0, 1]$.
5.  **M-ary Encoding (The Core Logic)**: The value in each cell is multiplied by $(M-1)$ and rounded to the nearest integer.
    $$Key(i, j) = \text{round}(\text{NormalizedValue}(i, j) \times (M - 1))$$
    *Note: For the Decimal base (M=10), we use histogram binning to better capture the subtle intensity distribution of the final blue decay.*

---

## 2. The Time-to-Base Mapping
The "Timing" is the most critical part. We don't generate all bases for one photo. Instead, the **Time Node ($t$)** of the photo dictates which **Base ($M$)** is used. This follows the physical decay of the four color phosphors:

| Time Node ($t$) | Base ($M$) | Physical Rationale |
| :--- | :--- | :--- |
| **$t < 0.5$s** | **Base-16** (Hex) | High entropy; all 4 phosphor colors are still active. |
| **$t < 1.5$s** | **Base-8** (Octal) | Medium entropy; 3 colors remain visible. |
| **$t < 2.5$s** | **Base-4** (Quat) | Lower entropy; only 2 colors remain. |
| **$t \ge 2.5$s** | **Base-10** (Dec) | **Blue Persistence**: Only the blue phosphor remains active. |

---

## 3. Four Points of Implementation (Addressing Feedback)

To satisfy the professor's requirements, we have implemented and verified the following four points:

### Point 1: Max Time Duration Extended
*   **Feedback**: The representative PUF video shows decay up to 5 seconds.
*   **Implementation**: We updated the backend to support time nodes up to **5.0 seconds**. The enrollment and verification pipeline now handles long-duration decay samples, ensuring the "Triple-Key" system works across the entire physical lifespan of the tag.

### Point 2: Guaranteed Deterministic Consistency
*   **Feedback**: Binary codes must be the same on repeated attempts for the same image.
*   **Implementation**: We verified that our algorithms are **purely mathematical**. There are no random seeds or probabilistic models (like AI clustering).
    *   *Proof*: We added a consistency check in the code that processes the same image multiple times. The resulting binary strings are **100% identical**, ensuring perfect reliability for cloud authentication.

### Point 3: Time-Node Base Mapping
*   **Feedback**: M-ary coding must be associated with the specific time node.
*   **Implementation**: We implemented the mapping logic shown in Section 2.
    *   *For example*: If a photo is captured at 3.0s, the system automatically switches to **Decimal (Base-10)** because the physical properties show that only blue light persists at that stage.

### Point 4: Standardized 30×30 Resolution
*   **Feedback**: Multiple pixel intensities/resolutions (100x100 to 5x5) make analysis difficult.
*   **Implementation**: We have **fixed the resolution to 30×30 pixels** for all three key types (Binary, M-ary, and PMF).
    *   This provides enough density for security ($30 \times 30 = 900$ cells) while being computationally efficient for real-time mobile-to-cloud authentication.

