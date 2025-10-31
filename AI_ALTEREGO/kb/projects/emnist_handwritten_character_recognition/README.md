---

## GitHub

- Profile: https://github.com/yavar29
- Repository: https://github.com/yavar29/ML_Projects/tree/main/Deep%20Learning%20Models/Convolutional%20Neural%20Network
#  EMNIST Handwritten Character Recognition using CNN

##  Overview
This project implements a Convolutional Neural Network (CNN) model to classify handwritten English alphabets and digits using the **EMNIST dataset** (Extended MNIST).  
The model is designed to handle **36 output classes** (26 alphabets + 10 digits) and aims to achieve high accuracy while ensuring generalization through **data augmentation** and **regularization**.

---

##  Objectives
- Develop a robust CNN model for multi-class image classification on EMNIST.
- Employ data augmentation for better generalization.
- Visualize feature extraction using activation maps.
- Evaluate the model with accuracy, precision, recall, F1-score, and confusion matrix.

---

##  Dataset Details
- **Dataset:** EMNIST (Balanced Split)
- **Total Samples:** 100,800
- **Image Size:** 28x28 (Grayscale)
- **Number of Classes:** 36  
- **Split Ratio:**  
  - Training: 70%  
  - Validation: 20%  
  - Testing: 10%

---

##  Model Architecture
| Layer Type        | Configuration | Output Size |
|--------------------|----------------|--------------|
| Conv2D + ReLU + MaxPool | 1 → 32 filters, 3×3 kernel | 32×14×14 |
| Conv2D + ReLU + MaxPool | 32 → 64 filters, 3×3 kernel | 64×7×7 |
| Conv2D + ReLU + MaxPool | 64 → 128 filters, 3×3 kernel | 128×3×3 |
| Fully Connected + Dropout | 128×3×3 → 256 | 256 |
| Fully Connected + Dropout | 256 → 128 | 128 |
| Output Layer | 128 → 36 | 36 |

**Total Parameters:** ~425K  
**Activation:** ReLU  
**Optimizer:** Adam (lr=0.001)  
**Scheduler:** StepLR (step_size=5, gamma=0.1)  
**Loss Function:** CrossEntropyLoss  

---

## Training & Evaluation
- **Epochs:** 20  
- **Best Validation Accuracy:** 91.14%  
- **Test Accuracy:** ~90.8%  
- **Metrics:** Precision, Recall, F1-score  
- **Visualization:** Activation maps for each convolution layer

---

##  Results

| Metric | Training | Validation | Testing |
|--------|-----------|-------------|----------|
| Accuracy | 89.6% | 91.1% | 90.8% |
| Precision | - | - | 0.91 |
| Recall | - | - | 0.90 |
| F1-Score | - | - | 0.90 |

**Training Time:** ~24 minutes on NVIDIA GPU  
**Model Checkpoint:** `best_model_part3.pth`

---

##  Visualizations
- **Class Distribution**
- **Pixel Intensity Distribution**
- **Activation Maps per Convolutional Layer**
- **Confusion Matrix**
- **ROC Curves for Multi-class Classification**

---

## Future Enhancements

- Experiment with ResNet or EfficientNet architectures.
- Apply transfer learning using pretrained models on handwriting datasets.
- Use mixed precision training to reduce memory usage.
- Deploy using Streamlit or Flask for real-time character recognition.

---

##  Usage

```bash
### 1️⃣ Clone Repository
git clone https://github.com/yavar29/ML_Projects.git
cd "Deep Learning Models/EMNIST"

### 2️⃣ Install Dependencies
pip install torch torchvision matplotlib seaborn scikit-learn torchinfo

### 3️⃣ Run Training Script
python EMNIST_CNN.py

---
