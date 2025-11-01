---

## GitHub

- Profile: https://github.com/yavar29
- Repository: https://github.com/yavar29/ML_Projects/tree/main/Deep%20Learning%20Models/Autoencoder_AnomalyDetection
# ThermoWatch-AE: Convolutional Autoencoders for Machine Temperature Anomaly Detection

> **Short pitch**: An unsupervised anomaly detection pipeline using 1D convolutional autoencoders to model normal machine temperature behavior and flag outliers via reconstruction error.

---

##  Project Overview
**ThermoWatch-AE** is a deep learning project focused on **detecting anomalies in industrial machine temperature data** using **Convolutional Autoencoders (ConvAEs)**.  
It applies unsupervised learning to identify potential system failures by learning normal operating patterns and flagging deviations based on reconstruction error.

This project demonstrates:
- Real-world time-series data processing  
- Model design and hyperparameter tuning in PyTorch  
- Regularization, learning-rate scheduling, and loss optimization  
- Quantitative evaluation and clear visualization of results  

---

##  Dataset
- **Source:** *Numenta Anomaly Benchmark (NAB)* — *Machine Temperature System Failure*  
- **File:** `machine_temperature_system_failure.csv`  
- **Columns:** `timestamp`, `value`  
- **Statistics:**  
  - 22,695 data points  
  - Value range: 2.08 – 108.51  
  - Mean ≈ 85.93, Std ≈ 13.75  

---

##  Approach Overview

### 1. Data Preprocessing
- Applied **Min-Max scaling** to normalize temperature values between 0 and 1.  
- Created fixed-length **sliding windows (size = 30)** for temporal modeling.  
- Sequential split into **train (70%)**, **validation (15%)**, and **test (15%)** sets.  

---

### 2. Model Architectures

| Model | Encoder | Decoder | Activation | Params | Highlights |
|--------|----------|----------|-------------|-----------|-------------|
| **ConvAE1** | 1→16→8 | 8→16→1 | LeakyReLU(0.1), Dropout(0.1), Sigmoid | ~905 | Compact baseline |
| **ConvAE2** | 1→32→16→8 | 8→16→32→1 | LeakyReLU(0.1), Dropout(0.1–0.2), Sigmoid | ~5.2K | **Best performing model** |
| **ConvAE3** | 1→64→32 | 32→64→1 | LeakyReLU + ReLU, Dropout(0.2) | ~12.8K | Deeper architecture |

---

### 3. Training and Optimization
- **Loss:** Mean Squared Error (MSELoss)  
- **Optimizer:** Adam with weight decay = 1e-5  
- **Learning-Rate Scheduler:** StepLR(step_size = 50, gamma = 0.5)  
- **Hyperparameter tuning:**  
  - Batch sizes: 32 – 256  
  - Learning rates: 1e-3 to 5e-5  
  - Epochs: 100 – 250  
- **Model selection:** Based on minimum validation loss.  
- Final model weights saved as **`a2_part2_yavarkha_mohdsaad.pth`**.  

---

### 4. Anomaly Detection
- Computed **reconstruction error** between input and output sequences.  
- Defined anomaly threshold at the **95th percentile** of training reconstruction errors.  
- Windows exceeding this threshold were flagged as **anomalous behavior**.  

---

##  Results

| Metric | ConvAE2 (Best Model) |
|--------|----------------------|
| Validation Loss | **0.000055** |
| Training Loss | **0.000112** |
| MAE | **0.007117** |
| RMSE | **0.010865** |
| R² Score | **0.997051** |

These results show that the model effectively reconstructs normal temperature sequences while maintaining high sensitivity to abnormal fluctuations.

---

##  Visualizations
The project includes clear and interpretable plots:
- Temperature variation over time  
- Histograms and boxplots of raw values  
- Training vs. validation loss curves  
- Reconstruction error distribution with threshold line  
- Original vs. reconstructed signal comparisons  

---

##  Reproducibility Summary

```python
# 1. Load and scale dataset
# 2. Create windowed sequences (length=30)
# 3. Define ConvAE1, ConvAE2, ConvAE3 in PyTorch
# 4. Train with MSELoss + Adam + StepLR scheduler
# 5. Evaluate on validation data and save best model
# 6. Compute reconstruction errors on test data
# 7. Detect anomalies using 95th percentile threshold