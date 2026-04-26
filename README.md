# TDM-PUF Triple-Key Authentication System 🛡️

### *Secure identity verification leveraging the physics of phosphorescent decay.*

---

## 📖 Overview
This project implements a state-of-the-art authentication system based on **Time-Domain Multiplexing Physical Unclonable Functions (TDM-PUF)**. It utilizes a "Triple-Key" verification strategy to ensure that a physical tag is not only genuine but is being verified at the correct moment in time.

## 🏗️ System Architecture
The project is divided into two primary components:
1.  **Mobile Client (Flutter)**: Handles image acquisition, time-slot selection, and real-time result visualization.
2.  **Cloud Backend (FastAPI)**: A high-performance Python engine that performs complex matrix mathematics and image processing.
3.  **Database (MongoDB)**: Securely stores the high-entropy "Fingerprints" of each enrolled tag.

---

## 🔑 The Triple-Key Verification Logic
To achieve maximum security, the system verifies three distinct "Keys" extracted from a single phosphorescent image:

### 1. Binary Key (Spatial Domain)
- **What it is**: A high-entropy bitstring generated from the spatial distribution of phosphorescent particles.
- **Verification**: The server performs a bitwise comparison between the uploaded image and the enrolled reference at the selected time slot.

### 2. M-ary Key (Intensity Domain)
- **What it is**: A multilevel (Base-16) quantization of light intensity across a 30x30 grid.
- **Verification**: Captures subtle gradient changes in the tag that a simple binary key might miss.

### 3. PMF Key (Temporal Domain)
- **What it is**: **Phosphorescence Modeling Function**. This verifies the *Decay Rate* of the material.
- **Verification**: Even if an attacker provides a perfect photo of the tag, the authentication will fail if the brightness level does not match the expected decay intensity for that specific time node (0.1s, 1.0s, etc.).

---

## 🔄 End-to-End Code Flow
1.  **Capture**: User captures/selects an image of the PUF tag and picks a "Time Slot" (e.g., 1.0s).
2.  **Transmission**: The mobile app sends the image via an encrypted HTTP POST request to the Cloud VPS.
3.  **Extraction**: The `image_processor.py` on the server uses OpenCV to:
    - Align the tag.
    - Standardize the resolution to a 30x30 grid.
    - Filter R, G, B, and Yellow channels.
4.  **Identification**: The `auth_logic.py` searches the MongoDB database for a matching Binary pattern.
5.  **Validation**: Once a tag is identified, the server performs the **Triple-Key Check**:
    - `compare_binary_keys()`
    - `verify_mary_keys()`
    - `verify_pmf_keys()` (Direct Pattern Comparison)
6.  **Response**: A detailed JSON object is returned to the phone, and the results are displayed on the premium UI.

---

## 🛠️ Setup & Installation

### Backend Deployment
```bash
# Clone the repository
git clone https://github.com/YOUR_USERNAME/TDM-PUF-Project.git

# Deploy using Docker
cd 01_Cloud_Backend
docker-compose up -d --build
```

### Mobile App Setup
1.  Ensure you have Flutter installed.
2.  Run `flutter pub get`.
3.  Connect your device and run `flutter run`.

## 🛡️ Security Features
- **Time-Node Rejection**: Rejects genuine images if the wrong time slot is selected (Protection against playback attacks).
- **Multi-Channel Analysis**: Analyzes 4 distinct color channels simultaneously.
- **Dynamic Thresholding**: Adapts to lighting conditions to minimize False Rejections.

---

## 👥 Contributors
- **Project Lead**: [Your Name]
- **Academic Supervisor**: [Professor's Name]

---
*Developed for the Advanced Research in Physical Cryptography and PUF Technologies.*
