# ⚡ Indra-Grid  
### AI-Driven Energy Optimizer for MSMEs

---

## 🚀 Overview  
Indra-Grid is a smart energy management system that helps small-scale factories reduce electricity costs and avoid downtime by intelligently switching between Solar, Battery, and Grid power.

---

## ❗ Problem Statement  
Factories in India face:
- High electricity costs during peak hours  
- Frequent power cuts causing production loss  
- Manual and inefficient energy usage  

---

## 💡 Our Solution  
Indra-Grid acts as an intelligent autopilot for factory energy.

It:
- Uses solar energy whenever available  
- Stores extra energy in a battery  
- Switches to battery during peak cost hours  
- Ensures continuous operation during power cuts  

---

## ⚙️ System Architecture  

CSV Data (Solar, Demand, Price)  
↓  
Decision Engine (Optimization Logic)  
↓  
Output CSV (Energy Usage)  
↓  
Dashboard (Visualization)  

---

## 📊 Features  

- 🔥 **Peak Shaving** → Reduces cost during expensive hours  
- 🏝️ **Island Mode** → Runs even during grid failure  
- 💰 **Cost Optimization** → Minimizes electricity bill  
- 🌱 **Green Score** → Tracks renewable energy usage  
- 📉 **Before vs After Comparison** → Shows money saved  

---

## 📁 Project Structure  

indra-grid/  
│  
├── data/              # Data generation (CSV)  
├── logic/             # Decision engine  
├── dashboard/         # Streamlit UI  
├── integration/       # System runner  
├── output.csv         # Generated output  
└── README.md  

---

## ▶️ How to Run  

Step 1: Run the system  
python integration/run.py  

Step 2: Launch dashboard  
streamlit run dashboard/app.py  

---

## 📈 Demo Output  

- Energy usage split (Solar / Battery / Grid)  
- Battery level tracking  
- Total cost calculation  
- Money saved compared to baseline  

---

## 🧠 Tech Stack  

- Python  
- CSV Data Handling  
- Streamlit Dashboard  
- GitHub (Collaboration)  

---

## 👥 Team  

👑 Pari – Data & Team Lead
⚙️ Shambhavi – Dashboard
📊 Sampoorna – Decision & L
🔗 Laxmi – Integration & Presentation

---

## 🔮 Future Scope  

- Real-time IoT integration  
- Machine Learning forecasting  
- Smart factory deployment  

---

## 🏆 Impact  

- Reduces electricity costs  
- Prevents production downtime  
- Supports sustainable energy usage  

---

## ⭐ Final Note  

Indra-Grid demonstrates how intelligent energy management can make MSMEs more efficient, resilient, and eco-friendly.
