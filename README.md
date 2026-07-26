# 🛰️ SEABeacon — Regional Disaster Intelligence Platform for Southeast Asia

AI-powered regional disaster intelligence platform that combines machine learning, geospatial analytics, and cloud-native services to forecast tropical cyclones, identify cross-border impacts, and automatically generate localized disaster alerts across Southeast Asia.

🏆 **Top 10 Semifinalist — ASEAN AI Hackathon 2026 (Climate Change Track)**  
Selected among **240+ teams** across Southeast Asia.

---

# Overview

SEABeacon is an AI-powered disaster intelligence platform designed to reduce the delay between disaster prediction and public notification.

The platform combines tropical cyclone forecasting, geospatial analysis, multilingual natural language processing, and cloud automation into a single end-to-end pipeline capable of generating localized disaster alerts before severe weather crosses national borders.

Unlike traditional warning systems that operate independently within each country, SEABeacon focuses on **cross-border disaster intelligence**, allowing neighboring nations to receive timely localized warnings using communication platforms that citizens already use.

---

# Key Features

- 🌪️ 72-hour AI-powered typhoon forecasting
- 🌏 Cross-border disaster impact analysis
- 🗺️ Geospatial routing using PostGIS
- 🤖 Automated multilingual alert generation
- ☁️ Cloud-native deployment on Google Cloud
- 🔄 Automated monthly model retraining
- 📡 Real-time disaster monitoring
- 📱 Social platform notification pipeline
- 🐳 Docker-based deployment

---

# System Architecture

```
                   Historical Typhoon Data
                         (IBTrACS)
                              │
                              ▼
                    Feature Engineering
                              │
                              ▼
                 XGBoost Forecasting Model
                              │
                              ▼
              Geospatial Impact Analysis
                  (Supabase + PostGIS)
                              │
                              ▼
             NLP & Alert Generation Pipeline
                              │
                              ▼
        Facebook • WhatsApp • LINE • Zalo
```

The platform integrates machine learning, geospatial databases, cloud services, and multilingual processing into a fully automated disaster intelligence workflow.

---

# Repository Structure

```
SEABeacon-Regional-Disaster-Alert-System
│
├── README.md
├── .gitignore
│
├── platform/
│   ├── backend/
│   ├── frontend/
│   ├── docker-compose.yml
│   └── README.md
│
├── ml/
│   ├── xgboost_forecast/
│   ├── lstm_model/
│   └── nlp_analysis/
│
├── map_visualization/
│   └── frontend/
│
├── demo/
│   └── run_all.sh
│
└── archive/
    ├── prototype_frontend/
  
```

The repository separates forecasting, NLP, frontend, backend, and deployment into independent modules, allowing each subsystem to evolve without tightly coupling the overall platform.

---

# Machine Learning Pipeline

The forecasting engine uses historical tropical cyclone trajectories from the **IBTrACS** database to predict future storm movement.

```
IBTrACS Dataset
        │
        ▼
Feature Engineering
        │
        ▼
XGBoost Training
        │
        ▼
Model Validation
        │
        ▼
Forecast API
        │
        ▼
Monthly Automated Retraining
```

The trained model is continuously updated through an automated retraining pipeline running on Google Cloud to improve forecasting performance as new typhoon data becomes available.

---

# Technology Stack

## Artificial Intelligence

- XGBoost
- LSTM
- Natural Language Processing
- Scikit-learn
- Python

## Backend

- FastAPI
- REST API
- Docker
- Python

## Database

- Supabase
- PostgreSQL
- PostGIS

## Cloud

- Google Cloud Platform
- Cloud Scheduler
- Cloud Run

## Frontend

- React
- Leaflet Maps
- JavaScript

---

# Performance

| Metric | Result |
|---------|--------|
| Historical Dataset | 30,965 Typhoon Records |
| Forecast Horizon | 72 Hours |
| Mean Absolute Error | **3.39 knots** |
| Cross-track Error | **38.40 km** |
| Retraining | Monthly Automated Pipeline |
| Deployment | Google Cloud |

---

# Cross-Border Intelligence Pipeline

SEABeacon extends beyond weather prediction by determining whether an approaching tropical cyclone poses a significant risk to neighboring ASEAN countries.

The platform automatically performs:

- Tropical cyclone forecasting
- Cross-border impact assessment
- Province-level spatial intersection
- Alert prioritization
- Localized multilingual warning generation
- Automated notification delivery

This enables disaster information to cross national borders as quickly as the storms themselves.

---

# Prototype Gallery

> **Dashboard**

*(Insert dashboard screenshot here.)*

---

> **Forecast Visualization**

*(Insert typhoon prediction visualization here.)*

---

> **Alert Interface**

*(Insert multilingual alert generation screenshots here.)*

---

> **System Architecture**

*(Insert complete architecture diagram here.)*

---

# Demo

🎥 **Demonstration Video**

https://drive.google.com/file/d/1DtpzMymjGlgwyxb2Y0xDuuYns_Yf9h79/view?usp=sharing

📖 **Project Documentation**

https://www.notion.so/Hackathon-Dashboard-3430a20e601e80ce8df6e347dfe50f56

---

# Engineering Challenges

## Real-Time Forecast Automation

Designed a cloud-native pipeline capable of continuously ingesting updated tropical cyclone datasets and automatically retraining forecasting models without manual intervention.

---

## Cross-Border Spatial Analysis

Implemented province-level spatial intersection using PostGIS to determine which neighboring regions fall within projected storm paths.

---

## Modular AI Pipeline

Separated forecasting, NLP, frontend, and backend into independent modules to improve maintainability and future scalability.

---

## Cloud Deployment

Containerized the application using Docker and deployed individual services on Google Cloud for scalable execution.

---

# Future Improvements

- Additional ASEAN language support
- Flood forecasting integration
- Real-time satellite imagery processing
- Mobile application
- Push notification service
- Ensemble forecasting models
- Explainable AI visualizations

---

# Code Availability

This repository is provided to showcase the overall software architecture, machine learning pipeline, and cloud engineering behind the project.

The source code is publicly viewable for educational and portfolio purposes but is **not licensed for reuse, redistribution, or commercial use** without explicit permission from the authors.

If you are interested in research collaboration or academic discussion, feel free to contact the project team.

---

# Acknowledgements

Developed during the **ASEAN AI Hackathon 2026 (Climate Change Track)** as a multidisciplinary collaboration focused on AI-driven disaster intelligence for Southeast Asia.

🏆 **Top 10 Semifinalist — Selected among 240+ participating teams.**