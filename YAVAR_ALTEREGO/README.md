# 🤖 AI Alter Ego - Intelligent Personal Assistant

[![Hugging Face Spaces](https://img.shields.io/badge/%F0%9F%A4%97%20Hugging%20Face-Spaces-blue)](https://huggingface.co/spaces)
[![Python](https://img.shields.io/badge/Python-3.12+-blue.svg)](https://python.org)
[![Gradio](https://img.shields.io/badge/Gradio-5.22+-green.svg)](https://gradio.app)
[![OpenAI](https://img.shields.io/badge/OpenAI-GPT--4-orange.svg)](https://openai.com)

> **An intelligent AI assistant that embodies a professional persona, capable of answering questions about background, skills, projects, and career aspirations with smart reasoning and contextual understanding.**

## 🌟 Features

### 🧠 **Intelligent Knowledge Retrieval**
- **Semantic Search**: Advanced RAG (Retrieval-Augmented Generation) with multiple query variations
- **Smart Reasoning**: Common sense connections between related concepts
- **Context Awareness**: Understands nuanced questions and provides relevant answers

### 💼 **Professional Persona**
- **Comprehensive Knowledge Base**: Covers career goals, technical skills, projects, and experience
- **Behavioral Interview Responses**: Ready-to-use answers for leadership, challenges, and teamwork questions
- **Contact Information**: Complete professional details and availability
- **Work Authorization**: Clear work status and timeline information

### 🚀 **Advanced Capabilities**
- **Logical Reasoning**: Connects related concepts intelligently
- **Project Portfolio**: Detailed information about ML/AI projects and research
- **Availability Management**: Smart responses about work preferences and schedule flexibility
- **Emergency Contacts**: Complete personal and professional contact information

## 🏗️ Architecture

```
AI_ALTEREGO/
├── app/
│   ├── agents/          # AI Assistant core
│   ├── config/          # Configuration settings
│   ├── core/            # System prompts and routing
│   ├── rag/             # Retrieval-Augmented Generation
│   ├── server/          # Gradio UI server
│   └── tools/           # Knowledge base search tools
├── kb/                  # Knowledge Base
│   ├── faq/            # Frequently Asked Questions
│   ├── projects/       # Project documentation
│   └── resume/         # Resume and professional data
└── me/                 # Personal profile data
```

## 📊 Knowledge Base Structure

The knowledge base (`kb/`) contains organized information that can be customized for any professional profile:

### FAQ Categories
- **Career Goals**: Professional aspirations and objectives
- **Availability**: Work schedule preferences and start dates
- **Work Authorization**: Work status and requirements
- **Technical Skills**: Programming languages, frameworks, and tools
- **Projects**: Detailed project descriptions and achievements
- **Contact Information**: Complete professional contact details
- **Recruiter Questions**: Specialized responses for recruitment scenarios

### Additional Content
- **Project Documentation**: Detailed README files for various projects
- **Resume Data**: Professional resume and LinkedIn information
- **Portfolio**: Additional portfolio materials

> **Note**: All content in the knowledge base can be customized to match any professional profile. Simply replace the existing content with your own information.

## 🚀 Quick Start

### Prerequisites
- Python 3.12+
- OpenAI API key
- UV package manager (recommended)

### Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/yourusername/AI_ALTEREGO.git
   cd AI_ALTEREGO
   ```

2. **Install dependencies**
   ```bash
   uv sync
   ```

3. **Set up environment variables**
   ```bash
   cp .env.example .env
   # Add your OpenAI API key to .env
   ```

4. **Customize the knowledge base**
   - Replace content in `kb/` directory with your own information
   - Update `me/` folder with your personal profile data
   - Modify system prompts in `app/core/prompts.py` if needed

5. **Run the application**
   ```bash
   uv run python main.py
   ```

6. **Access the interface**
   - Open your browser to `http://localhost:7860`
   - Start chatting with your AI alter ego!

## 🌐 Hugging Face Spaces Deployment

This project is designed for seamless deployment on Hugging Face Spaces with Gradio:

### Deploy to Hugging Face Spaces

1. **Create a new Space**
   - Go to [Hugging Face Spaces](https://huggingface.co/new-space)
   - Choose "Gradio" as the SDK
   - Set visibility (public/private)

2. **Configure the Space**
   ```yaml
   # README.md in your Space
   ---
   title: AI Alter Ego
   emoji: 🤖
   colorFrom: blue
   colorTo: purple
   sdk: gradio
   sdk_version: 5.22.0
   app_file: main.py
   pinned: false
   ---
   ```

3. **Add secrets**
   - Add your OpenAI API key as a Space secret
   - Set `OPENAI_API_KEY` in the Space settings

4. **Deploy**
   - Push your code to the Space repository
   - The Space will automatically build and deploy

## 🛠️ Technical Stack

- **Backend**: Python 3.12, FastAPI
- **AI/ML**: OpenAI GPT-4, LangChain, RAG
- **Frontend**: Gradio 5.22+
- **Vector Database**: NumPy-based similarity search
- **Document Processing**: PyPDF, text chunking
- **Deployment**: Hugging Face Spaces, Docker

## 🔧 Configuration

### Environment Variables
```bash
OPENAI_API_KEY=your_openai_api_key
OPENAI_MODEL=gpt-4
KB_DIR=./kb
CHUNK_TOKENS=1800
CHUNK_OVERLAP=300
```

### Customization
- Modify `app/core/prompts.py` for system behavior
- Update `kb/` directory for knowledge base content
- Adjust `app/config/settings.py` for performance tuning

## 🚀 Future Roadmap

### Key Features to Implement
- **Multi-Modal RAG**: Support for images, documents, and multimedia content
- **Real-Time Knowledge Updates**: Live synchronization with external data sources
- **Voice Integration**: Speech-to-text and text-to-speech capabilities
- **Multi-Platform Support**: Web, mobile, and API endpoints
- **Enhanced Security**: End-to-end encryption and privacy controls
- **Analytics Dashboard**: Usage tracking and performance metrics

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🌟 Star the Project

If you find this project helpful, please give it a ⭐ on GitHub!

---

**Ready to create your own AI-powered personal assistant? Deploy now and start chatting with your intelligent alter ego!** 🚀