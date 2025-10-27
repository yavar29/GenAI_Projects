# 🌦️ Multi-Agent GenAI Weather Assistant

> **An intelligent, physics-aware weather analysis system** built with **Gemini LLMs**, **Google Vertex AI**, and the **Agent Development Kit (ADK)** — designed to transform natural-language weather questions into deterministic, data-grounded insights.

---

## 🧠 Project Overview

The **Multi-Agent GenAI Weather Assistant** enables users to ask queries such as  
> "Compare rainfall trends between New York and Buffalo last month,"  
and automatically obtain precise, unit-aware, and explainable weather summaries.

It dynamically interprets **locations**, **time windows**, and **variables**, chooses the appropriate **Open-Meteo API** (forecast, recent, or archive), and when relevant, adds **physics-based explanations** retrieved via **Vertex AI RAG**.

---

## 🏗️ System Architecture

```
user query → weather_coordinator (Gemini-2.5-pro)
├── weather_query_agent
│   ├── geocode_place() → lat/lon, timezone
│   ├── pick_variables() → temperature_2m, precipitation, etc.
│   ├── detect_model_hint() → GFS / ECMWF / ERA5 / ICON
│   ├── fetch_openmeteo() → dynamic endpoint selection
│   └── summarise_weather() → concise, unit-aware answer
└── physics_rag_agent (optional)
    └── Vertex AI RAG Retrieval → physics mechanism note
```


Each agent runs under **Google ADK**, exposing standardized `AgentTool` / `FunctionTool` interfaces for deterministic chaining and reproducible outputs.

---

## ⚙️ Core Components

### 1. **Weather Coordinator Agent**
- **Primary orchestrator** using Gemini 2.5 Pro
- Parses flexible queries about **place + time + variable**
- Builds internal planning JSON with deterministic date/time logic
- Delegates sub-tasks to specialized agents
- Merges weather data with physics explanations

### 2. **Weather Query Agent**
- Converts ambiguous natural language into deterministic Open-Meteo calls
- Detects implicit variables (e.g., "windy" → `wind_speed_10m`)
- Infers **hindcast / forecast / mixed** modes from phrasing
- Handles comparative queries between multiple locations
- Provides robust error handling and fallback mechanisms

### 3. **Physics RAG Agent**
- Integrates with **Vertex AI RAG** for scientific explanations
- Retrieves physics mechanisms for weather phenomena
- Provides high-confidence, context-aware explanations
- Bridges AI reasoning with domain expertise

### 4. **Specialized Tools Suite**
- **Geocoding**: Multi-source location resolution with timezone detection
- **Variable Mapping**: Intelligent mapping of natural language to weather variables
- **API Integration**: Dynamic routing between Open-Meteo endpoints
- **Data Processing**: Statistical analysis and unit-aware formatting
- **Comparative Analysis**: Side-by-side weather comparisons

---

## 🛠️ Technical Implementation

### **Multi-Agent Architecture**
- **Google Agent Development Kit (ADK)** for agent orchestration
- **FunctionTool** decorators for tool standardization
- **AgentTool** integration for inter-agent communication
- **Deterministic workflows** with structured JSON planning

### **Advanced Natural Language Processing**
- **Rich date parsing**: "last weekend", "past 3 days", "yesterday at 3pm"
- **Implicit variable detection**: "windy" → wind_speed_10m, "humid" → relative_humidity_2m
- **Comparative query handling**: "Why is SF colder than SD?"
- **Timezone-aware processing** with IANA timezone support

### **Data Pipeline Engineering**
- **Dynamic API routing**: Current weather, recent past (≤5 days), historical archive
- **Variable mapping**: Canonical variable names with granularity-specific API parameters
- **Error resilience**: Comprehensive fallback mechanisms and validation
- **Unit consistency**: Automatic unit formatting and conversion

### **Cloud-Native Integration**
- **Vertex AI RAG**: Physics corpus retrieval with similarity search
- **Google Cloud Platform**: Secure credential management
- **FastAPI deployment**: Production-ready API endpoints
- **Poetry dependency management**: Reproducible environments

---

## 🧱 Key Engineering Achievements

### **1. Multi-Agent Orchestration**
- Designed and implemented a **3-tier agent architecture**
- **Coordinator → Query Agent → Tools** with clear separation of concerns
- **Deterministic agent chaining** using Google ADK patterns
- **Error propagation** and graceful degradation across agent boundaries

### **2. Advanced Natural Language Understanding**
- **Context-aware date parsing** with timezone anchoring
- **Implicit intent detection** for weather variables
- **Comparative query processing** for multi-location analysis
- **Statistical intent recognition** (min/max/mean/thresholds)

### **3. Dynamic API Integration**
- **Intelligent endpoint selection** based on temporal context
- **Variable mapping** with granularity-specific API parameters
- **Robust error handling** with comprehensive fallback strategies
- **Rate limiting** and timeout management

### **4. Physics-Informed AI**
- **Vertex AI RAG integration** for scientific explanations
- **High-confidence retrieval** with similarity thresholds
- **Context-aware physics notes** that enhance user understanding
- **Domain expertise integration** without hallucination

### **5. Production-Ready Architecture**
- **Cloud-native deployment** on Google Vertex AI
- **Secure credential management** with environment variables
- **Scalable agent framework** using Google ADK
- **Comprehensive error handling** and logging

---

## 📊 Demonstrated Technical Skills

### **AI/ML Engineering**
- **Large Language Model Integration**: Gemini 2.5 Pro, Gemini 2.0 Flash
- **Multi-Agent Systems**: Orchestration, tool chaining, error handling
- **Retrieval-Augmented Generation (RAG)**: Vertex AI integration, similarity search
- **Prompt Engineering**: Complex system prompts, few-shot learning, context management

### **Software Architecture**
- **Microservices Design**: Agent-based architecture with clear boundaries
- **API Design**: RESTful endpoints, parameter validation, error responses
- **Data Pipeline Engineering**: ETL processes, data transformation, validation
- **Cloud Architecture**: Google Cloud Platform, Vertex AI, Compute Engine

### **Backend Development**
- **Python 3.12**: Modern Python features, type hints, async programming
- **FastAPI**: High-performance web framework, automatic API documentation
- **Google ADK**: Agent Development Kit, tool integration, agent orchestration
- **Dependency Management**: Poetry, virtual environments, reproducible builds

### **Data Engineering**
- **API Integration**: Open-Meteo weather APIs, geocoding services
- **Data Processing**: JSON manipulation, statistical analysis, unit conversion
- **Geospatial Processing**: Coordinate transformation, timezone detection
- **Error Handling**: Comprehensive validation, fallback mechanisms

### **DevOps & Deployment**
- **Cloud Deployment**: Google Cloud Platform, Vertex AI
- **Environment Management**: Poetry, dependency resolution, version control
- **Security**: Credential management, environment variables, secure APIs
- **Monitoring**: Error tracking, performance optimization, logging

---

## 🚀 Business Value & Impact

### **Real-World Applications**
- **Meteorological Research**: Automated weather data analysis and comparison
- **Educational Tools**: Physics-informed explanations for weather phenomena
- **Business Intelligence**: Weather impact analysis for various industries
- **Scientific Computing**: Reproducible weather data processing workflows

### **Technical Innovation**
- **Natural Language to Data**: Seamless conversion of human queries to API calls
- **Multi-Modal Intelligence**: Combining LLM reasoning with domain-specific RAG
- **Deterministic AI**: Reliable, reproducible results with proper error handling
- **Scalable Architecture**: Cloud-native design for production deployment

### **Performance Characteristics**
- **Sub-second response times** for current weather queries
- **Robust error handling** with graceful degradation
- **High accuracy** in location and variable resolution
- **Scalable design** supporting concurrent users

---

## 🛠️ Technology Stack

| Category | Technologies |
|----------|-------------|
| **LLM Core** | Google Gemini 2.5 Pro, Gemini 2.0 Flash |
| **Framework** | Google Agent Development Kit (ADK Python SDK) |
| **APIs & Data** | Open-Meteo (Forecast/Archive), Geocoding APIs |
| **Retrieval** | Vertex AI RAG with custom physics corpus |
| **Cloud Platform** | Google Vertex AI, Compute Engine |
| **Languages & Libs** | Python 3.12, FastAPI, requests, timezonefinder |
| **Design Patterns** | Multi-Agent Orchestration, RAG Pipelines, Dynamic Routing |
| **Version Control** | GitHub Actions, Poetry Environment Management |

---

## 🚀 Setup & Execution

```bash
# Clone the repository
git clone https://github.com/VectorWorkX/wx-event-reliability.git
cd wx-event-reliability

# Install dependencies
poetry install

# Set up environment variables
cp .env.example .env
# Edit .env with your Google Cloud credentials

# Run locally
poetry run adk web
# → launches FastAPI endpoint for the Weather Coordinator
```

### **Environment Configuration**
```bash
# Required environment variables
GOOGLE_CLOUD_PROJECT=your-project-id
GOOGLE_CLOUD_LOCATION=us-central1
RAG_CORPUS=projects/.../locations/.../ragCorpora/...
```

---

## 📈 Project Metrics & Achievements

### **Code Quality**
- **1,200+ lines** of production-ready Python code
- **Comprehensive error handling** across all components
- **Type hints** and documentation throughout
- **Modular architecture** with clear separation of concerns

### **Technical Complexity**
- **Multi-agent orchestration** with 3 specialized agents
- **7 specialized tools** for weather data processing
- **Dynamic API routing** across 3 different endpoints
- **Physics-informed AI** with RAG integration

### **Production Readiness**
- **Cloud-native deployment** on Google Vertex AI
- **Scalable architecture** supporting concurrent users
- **Comprehensive testing** and error handling
- **Professional documentation** and setup instructions

---

## 🎯 Key Differentiators

### **1. Advanced Natural Language Understanding**
Unlike simple weather APIs, this system understands complex, conversational queries:
- "Why is San Francisco colder than San Diego?"
- "Compare rainfall between New York and Buffalo last month"
- "Was it windy in Seattle yesterday at 3pm?"

### **2. Physics-Informed Intelligence**
Integration with scientific knowledge base provides:
- **Mechanistic explanations** for weather phenomena
- **High-confidence physics notes** without hallucination
- **Educational value** beyond simple data retrieval

### **3. Production-Grade Architecture**
Enterprise-ready design with:
- **Multi-agent orchestration** for complex workflows
- **Robust error handling** and fallback mechanisms
- **Cloud-native deployment** with Google Cloud Platform
- **Scalable design** for high-volume usage

### **4. Deterministic AI**
Unlike typical LLM applications, this system provides:
- **Reproducible results** with consistent API calls
- **Data-grounded responses** without hallucination
- **Reliable error handling** with graceful degradation
- **Professional-grade reliability** for production use

---

## 🔬 Technical Deep Dive

### **Agent Communication Patterns**
```python
# Weather Coordinator orchestrates sub-agents
weather_coordinator = LlmAgent(
    name="weather_coordinator",
    model="gemini-2.5-pro",
    tools=[
        AgentTool(agent=weather_query_agent),
        AgentTool(agent=physics_rag_agent),
    ],
)
```

### **Dynamic API Routing**
```python
# Intelligent endpoint selection based on temporal context
if time_mode == "current":
    endpoint = "/v1/forecast"
elif time_mode == "hindcast_recent":
    endpoint = "/v1/forecast"  # with past_days
else:
    endpoint = "/v1/archive"   # historical data
```

### **Physics RAG Integration**
```python
# High-confidence retrieval with similarity thresholds
ask_vertex_retrieval = VertexAiRagRetrieval(
    similarity_top_k=5,
    vector_distance_threshold=0.5,
    rag_resources=[rag.RagResource(rag_corpus=corpus)]
)
```

---

## 🏆 Professional Impact

This project demonstrates **Yavar Khan's** ability to:

- **Design and implement** complex multi-agent AI systems
- **Integrate cutting-edge technologies** (Gemini LLMs, Vertex AI, ADK)
- **Build production-ready applications** with proper error handling
- **Bridge AI and domain expertise** through physics-informed RAG
- **Create scalable, cloud-native architectures** for real-world deployment
- **Deliver end-to-end solutions** from concept to production

The system showcases expertise in **AI/ML engineering**, **cloud architecture**, **API design**, **data engineering**, and **production deployment** - making it an excellent demonstration of full-stack AI development capabilities.

---

## 📞 Contact & Collaboration

**Yavar Khan**  
Email: yavarkhan1997@gmail.com  
LinkedIn: [Connect with Yavar](https://linkedin.com/in/yavar-khan)

---

*This project represents a comprehensive demonstration of modern AI engineering practices, combining cutting-edge LLM technology with robust software architecture and domain expertise to create a production-ready weather intelligence system.*