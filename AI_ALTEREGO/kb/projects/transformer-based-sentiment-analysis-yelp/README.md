---

## GitHub

- Profile: https://github.com/yavar29
- Repository: https://github.com/yavar29/ML_Projects/tree/main/Deep%20Learning%20Models/Transformer
# Transformer-based Sentiment Analysis (Yelp Review Polarity Dataset)

> **Short pitch:** A custom Transformer model built entirely from scratch in PyTorch to classify Yelp reviews as positive or negative using self-attention, positional encoding, and Word2Vec embeddings.

---

##  Project Overview
This project implements a **Transformer-based text classification architecture** to perform sentiment analysis on the **Yelp Review Polarity dataset**.  
The model was designed, trained, and evaluated end-to-end using **PyTorch**, with all Transformer components — including **Multi-Head Attention**, **Feed-Forward Networks**, and **Positional Encoding** — implemented manually.  

It demonstrates:
- In-depth understanding of **Transformer architecture and attention mechanisms**  
- Expertise in **embedding generation** and **language preprocessing**  
- Use of **regularization and optimization** for better generalization  
- End-to-end **NLP pipeline design** with scalable training on large text datasets  

---

##  Dataset

- **Dataset:** [Yelp Review Polarity](https://www.yelp.com/dataset)  
- **Samples:** 560,000 text reviews (balanced: 280,000 positive, 280,000 negative)  
- **Average Word Count:** ~133 per review  
- **Classes:**  
  - `0` → Negative Review  
  - `1` → Positive Review  

---

##  Data Preprocessing Pipeline

1. **Text Cleaning**
   - Lowercased text and removed punctuation, digits, and special characters.  
   - Tokenized text using **spaCy** (`en_core_web_sm`), removing stopwords.

2. **Vocabulary Creation**
   - Constructed a **token registry** of ~698,000 unique terms.  
   - Added `<PAD>` and `<UNK>` tokens for sequence padding and out-of-vocabulary handling.

3. **Word Embeddings**
   - Trained **Word2Vec** embeddings using **Gensim** with:
     - `vector_size = 300`, `window = 7`, `min_count = 2`, `epochs = 15`
   - Created an embedding matrix initialized with pretrained word vectors.

4. **Data Splitting**
   - Train: 80% — Validation: 10% — Test: 10%  
   - Each sequence truncated or padded to a **maximum length of 256 tokens**.

---

##  Transformer Model Architecture

| Component | Description |
|------------|-------------|
| **Embedding Layer** | Maps tokens to pretrained Word2Vec embeddings (trainable, 300D). |
| **Positional Encoding** | Adds sine–cosine positional vectors to preserve word order. |
| **Encoder Stack** | 4 custom Transformer Encoder blocks. Each includes:<br>• Multi-Head Attention (6 heads)<br>• Feed-Forward Network (1024 hidden units)<br>• Residual connections & Layer Normalization<br>• Dropout(0.3) |
| **Classification Head** | Linear → GELU → Dropout → Linear → Softmax (2 classes). |
| **Parameters** | ~213 million trainable parameters. |

---

##  Training Configuration

| Setting | Value |
|----------|--------|
| Optimizer | Adam (`lr=0.001`, `weight_decay=1e-4`) |
| Loss Function | CrossEntropyLoss |
| Batch Size | 64 |
| Sequence Length | 256 |
| Regularization | Dropout(0.3), L2 (1e-4) |
| Early Stopping | Patience = 3 epochs |
| Scheduler | ReduceLROnPlateau (optional) |
| Device | CUDA / GPU |

---

##  Training and Optimization Process

###  Base Model
- Transformer without Dropout or L2 regularization.  
- Training stagnated at ~50% accuracy (random behavior).

###  Optimized Model
- Added **Dropout(0.3)** across embedding, attention, and FFN layers.  
- Applied **L2 Regularization** (1e-4) and **Early Stopping** (patience=3).  
- Significantly improved convergence, generalization, and stability.

---

## Results Summary

| Metric | Train | Validation | Test |
|--------|--------|-------------|------|
| Accuracy | 91.29% | 91.59% | **91.79%** |
| Loss | 0.21 | 0.23 | ~0.23–0.25 |
| Precision | — | — | **0.913** |
| Recall | — | — | **0.923** |
| F1 Score | — | — | **0.918** |

### Observations
- Minimal gap between train and validation accuracy → **no overfitting**.  
- Validation loss stabilized at 0.23 → **smooth learning curves**.  
- Balanced precision/recall → consistent and reliable predictions.  

---

## 🧰 Implementation Details

**Libraries Used**
- PyTorch  
- Gensim (Word2Vec)  
- spaCy  
- scikit-learn  
- pandas, numpy  
- matplotlib, seaborn, torchinfo  

**Artifacts Saved**
- `processed_artifacts.pkl` → Token registry, embeddings, and labels  
- `review_vectors.w2v` → Trained Word2Vec model  
- `best_transformer_model.pth` → Final Transformer checkpoint  

---

## 📉 Visualizations
- **Word Clouds** — frequent words in positive and negative reviews  
- **Loss & Accuracy Curves** — for both training and validation phases  
- **ROC Curve** — high AUC confirming strong discriminative power  

---

## 🔍 Key Insights
- Fully custom-built **Transformer encoder** (no reliance on prebuilt APIs).  
- Deep understanding of **self-attention** and **sequence modeling**.  
- Effective use of **Dropout, L2 Regularization, and Early Stopping** for generalization.  
- Achieved **>91% accuracy** on a large-scale sentiment dataset.  
- Built a reusable, modular, and extendable **NLP model architecture**.

---

## 🚀 Future Scope
- Integrate contextual embeddings (BERT or FastText).  
- Extend to **multi-class** sentiment or **aspect-based** emotion analysis.  
- Experiment with **hybrid Transformer–BiLSTM** models.  
- Optimize inference using **quantization** or **ONNX runtime**.

---

## 👤 Author

**Project Author**  
*M.S. in Computer Science (AI/ML Track), University at Buffalo*  
Former **Software Engineering Analyst @ Accenture (2.5+ years)**  
**Focus Areas:** Deep Learning · NLP · Transformers · Applied AI  

📫 **LinkedIn:** [linkedin.com/in/yavarkhan](https://linkedin.com/in/yavarkhan)  
💻 **GitHub:** [github.com/yavarkhan](https://github.com/yavarkhan)

---

## 📚 References:
- Vaswani et al. (2017). *Attention Is All You Need*  
- [PyTorch Forum: Transformer Encoder for Classification](https://discuss.pytorch.org/t/nn-transformerencoder-for-classification/83021)  
- [spaCy Tokenizer API](https://spacy.io/api/tokenizer)  
- [Positional Encoding Discussion — PyTorch](https://discuss.pytorch.org/t/positional-encoding/175953)
