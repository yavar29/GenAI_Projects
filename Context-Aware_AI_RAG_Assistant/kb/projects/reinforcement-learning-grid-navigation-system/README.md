---

## GitHub

- Profile: https://github.com/yavar29
- Repository: https://github.com/yavar29/ML_Projects/tree/main/Reinforcement%20Learning%20Models%20
# 🧭 GridWorld — SARSA vs n-Step Double Q-Learning

##  Overview
This project implements and compares **SARSA** and **n-Step Double Q-Learning** algorithms on a custom **GridWorld** environment.  
It focuses on exploring reinforcement learning fundamentals such as temporal-difference learning, on-policy vs off-policy updates, Q-value stability, and exploration–exploitation tradeoffs.

Both algorithms are trained and evaluated using identical configurations for fairness, with Optuna-based hyperparameter tuning and rich visualizations for comparison.

---

##  Objectives
- Implement SARSA and n-Step Double Q-Learning agents from scratch.  
- Tune hyperparameters automatically using **Optuna**.  
- Compare convergence speed, stability, and long-term reward.  
- Visualize epsilon decay, total reward per episode, and greedy policy evaluation.  
- Identify the **optimal step size (n)** for Double Q-Learning.

---

##  Environment
**Environment Name:** `YavarEnv` (Custom GridWorld)  
**Type:** Deterministic 2D grid  
**Goal:** Reach terminal state with maximum cumulative reward  
**State Representation:** (row, column) coordinates  
**Action Space:** Up, Down, Left, Right  
**Rewards:**
- +1 for reaching goal  
- -1 for invalid moves or collisions  
- 0 otherwise  

---

##  Algorithms Implemented

###  SARSA (State–Action–Reward–State–Action)
On-policy TD control algorithm that updates Q-values based on the next action actually taken by the policy.

**Update Rule:**
\[
Q(s,a) \leftarrow Q(s,a) + \alpha [r + \gamma Q(s',a') - Q(s,a)]
\]

###  n-Step Double Q-Learning
An off-policy method using two Q-tables to minimize overestimation bias and multi-step returns for faster learning.

**Key Features:**
- Two Q-tables (`Q1`, `Q2`) updated alternately.  
- Uses *n-step bootstrapping* to incorporate multi-step returns.  
- Tuning over **n** (1–5) to find optimal tradeoff between bias and variance.

---

##  Hyperparameter Tuning
**Library:** Optuna  
**Search Space:**
| Parameter | Range / Values |
|------------|----------------|
| Discount factor (γ) | [0.8, 0.99] |
| Exploration rate (ε) | [0.05, 1.0] |
| ε-decay | [0.90, 0.999] |
| Learning rate (α) | [0.001, 0.1] |
| n (for Double Q-Learning) | [1, 5] |
| Episodes | 100–500 |
| Max timesteps | 100–300 |

**Optimization Metric:** Highest average reward over last 10 episodes.

**Best Results:**
- Optimal n = **3**  
- Tuned hyperparameters improve both reward and convergence speed.

---

## 📊 Results Summary
| Algorithm | Optimal n | Final Avg Reward | Convergence | Stability |
|------------|------------|------------------|--------------|------------|
| SARSA | — | 0.88 | Moderate | Stable |
| n-Step Double Q-Learning | 3 | 0.92 | Faster | High |

**Last 10 Episode Rewards (example):**  
SARSA → [0.79, 0.80, 0.85, 0.89, 0.90, 0.91, 0.92, 0.92, 0.92, 0.93]  
n-Step Double Q-Learning → [0.83, 0.86, 0.88, 0.91, 0.93, 0.94, 0.94, 0.95, 0.95, 0.96]

---

## 📈 Visualizations
1. **Reward per Episode:** Learning curves for SARSA and Double Q-Learning.  
2. **Epsilon Decay:** Demonstrates reduced exploration over time.  
3. **Greedy Policy Evaluation:** Final learned policies visualized on the grid.  
4. **Comparative Performance:** Overlay plot — SARSA vs Double Q-Learning (n = 3).

---

## 🧩 Insights

- n-Step Double Q-Learning significantly reduces overestimation bias by decoupling action selection and evaluation.
- The addition of n-step returns accelerates convergence.
- SARSA, being on-policy, tends to be more stable but learns slower.
- The tuned parameters demonstrate how critical learning rate and ε-decay scheduling are to convergence.

---

##  Plots
- Total Reward per Episode
- Epsilon Decay Curve
- SARSA vs n-Step Double Q-Learning

---

## 🧪 Usage

```bash
### 1️ Clone Repository

git clone https://github.com/yavar29/ML_Projects.git
cd "Deep Learning Models/GridWorld_RL"

### 2️ Install Dependencies
pip install numpy matplotlib optuna

### 3️ Run Training & Comparison
python gridworld_main.py


---

## Suggested Directory Structure
GridWorld_RL/
├── gridworld_env.py            # Custom environment class
├── sarsa.py                    # SARSA implementation
├── double_q_nstep.py           # n-Step Double Q-Learning
├── tuning.py                   # Optuna hyperparameter optimization
├── plots.py                    # Visualization utilities
├── gridworld_main.py           # Main entry point
└── README.md

---