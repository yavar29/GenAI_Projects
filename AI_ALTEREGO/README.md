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
- **Pushover Notifications**: Real-time alerts when users express interest in connecting or ask questions you haven't answered

## 🏗️ Architecture

```
AI-Alter-Ego/
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
└── me/              # Personal profile data (linkedIn profile and summary.txt)
```

## 📊 Knowledge Base Structure

The knowledge base (`kb/`) is the heart of your AI assistant. It contains all the information your AI will use to answer questions. You can organize it however you like - here's the flexible structure:

```
kb/
├── faq/                    # Frequently Asked Questions
│   ├── 01-career-goals.md
│   ├── 02-availability.md
│   ├── 03-work-authorization.md
│   ├── 04-relocation-preference.md
│   ├── 05-technical-skills.md
│   ├── 06-projects-highlight.md
│   ├── 07-education-background.md
│   ├── 08-professional-experience.md
│   ├── 09-research-interests.md
│   ├── 10-contact-information.md
│   └── recruiters/         # Behavioral interview responses
│       ├── 01-salary-expectations.md
│       ├── 02-preferred-tech-stack.md
│       ├── 03-future-goals.md
│       ├── 04-team-culture.md
│       ├── 05-project-ownership.md
│       ├── 06-leadership-style.md
│       ├── 07-problem-solving.md
│       ├── 08-handling-pressure.md
│       ├── 09-learning-philosophy.md
│       ├── 10-communication-collaboration.md
│       └── behavioral-questions.md
├── projects/               # Detailed project documentation
│   ├── project-1/
│   │   └── README.md
│   ├── project-2/
│   │   └── README.md
│   └── ...
├── portfolio/              # Portfolio materials
│   ├── images/
│   ├── documents/
│   └── presentations/
├── resume/                 # Resume and professional documents
│   ├── resume.pdf
│   ├── linkedin.pdf
│   └── cv.pdf
└── README.md              # Knowledge base documentation
```

### 🎯 **Knowledge Base Categories**

#### **FAQ Directory (`kb/faq/`)**
Contains structured Q&A content that your AI will use to answer common questions:

- **`01-career-goals.md`** - Your professional aspirations and objectives
- **`02-availability.md`** - Work schedule preferences and start dates  
- **`03-work-authorization.md`** - Work status and visa requirements
- **`04-relocation-preference.md`** - Geographic preferences and flexibility
- **`05-technical-skills.md`** - Programming languages, frameworks, tools
- **`06-projects-highlight.md`** - Key project descriptions and achievements
- **`07-education-background.md`** - Academic qualifications and certifications
- **`08-professional-experience.md`** - Work history and experience
- **`09-research-interests.md`** - Research areas and academic interests
- **`10-contact-information.md`** - Professional contact details and preferences

#### **Recruiter Directory (`kb/faq/recruiters/`)**
Specialized responses for behavioral interview questions:

- **Salary expectations** - Compensation discussions
- **Preferred tech stack** - Technology preferences
- **Future goals** - Long-term career planning
- **Team culture** - Work environment preferences
- **Project ownership** - Leadership and responsibility examples
- **Leadership style** - Management approach
- **Problem solving** - Analytical thinking examples
- **Handling pressure** - Stress management
- **Learning philosophy** - Continuous learning approach
- **Communication & collaboration** - Teamwork examples

#### **Projects Directory (`kb/projects/`)**
Detailed documentation for your projects:

- **Individual project folders** - Each project gets its own directory
- **README.md files** - Detailed project descriptions, technologies used, achievements
- **Code snippets** - Key implementation details
- **Results and metrics** - Performance data, impact, outcomes

#### **Portfolio Directory (`kb/portfolio/`)**
Additional materials to showcase your work:

- **Images** - Screenshots, diagrams, visualizations
- **Documents** - Case studies, reports, presentations
- **Presentations** - Slide decks, demos
- **Certificates** - Awards, certifications, achievements

#### **Resume Directory (`kb/resume/`)**
Professional documents and profiles:

- **Resume PDF** - Your main resume document
- **LinkedIn PDF** - LinkedIn profile export
- **CV PDF** - Academic curriculum vitae
- **Cover letters** - Template cover letters

### 🔧 **Customization Options**

The knowledge base template can be changed based on your needs:

1. **Add new sections** - Create directories for specific content
2. **Remove sections** - Delete directories you don't need
3. **Modify existing content** - Edit files to match your information
4. **Add multimedia** - Include images, documents, presentations
5. **Create custom categories** - Add industry-specific or personal sections

### 📝 **File Format Guidelines**

- **Markdown files** (`.md`) - Preferred format for text content
- **PDF files** (`.pdf`) - For documents, resumes, certificates
- **Text files** (`.txt`) - For simple text content
- **Images** (`.png`, `.jpg`) - For visual content
- **JSON files** (`.json`) - For structured data


## 🚀 Quick Start

### Prerequisites

Before you begin, make sure you have:

- **Python 3.12+** - Download from [python.org](https://python.org)
- **OpenAI API key** - Get one from [OpenAI Platform](https://platform.openai.com/api-keys)
- **UV package manager** (recommended) - Install with the command below
- **Git** - For cloning the repository

### Install UV Package Manager
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

### 📥 Installation

#### Step 1: Clone the Repository
```bash
git clone https://github.com/yourusername/AI-Alter-Ego.git
cd AI-Alter-Ego
```

#### Step 2: Install Dependencies
```bash
# Using UV (recommended)
uv sync

# Or using pip
pip install -r requirements.txt
```

#### Step 3: Set Up Environment Variables
```bash
# Copy the example environment file
cp .env.example .env

# Edit the .env file and add your OpenAI API key
# OPENAI_API_KEY=your_actual_api_key_here
```

#### Step 4: Initialize Template Files
```bash
# Run the setup script to create template files
./setup_template.sh
```

This will create:
- Template FAQ files in `kb/faq/` (you can customize these based on your needs)
- Template personal profile in `me/`
- Knowledge base documentation

> **💡 Important**: The knowledge base template is flexible - you can modify, add, or remove any sections based on your specific needs.

### 🎨 Customization

#### Step 5: Customize Your Knowledge Base

**Replace Template Content:**
1. **FAQ Files** - Edit files in `kb/faq/` directory:
   ```bash
   # Example: Edit career goals
   nano kb/faq/01-career-goals.md
   ```

2. **Personal Profile** - Update `me/summary.txt`:
   ```bash
   # Edit your personal summary
   nano me/summary.txt
   ```

3. **Project Documentation** - Add your projects to `kb/projects/`:
   ```bash
   # Create a new project folder
   mkdir kb/projects/my-awesome-project
   # Add project details
   echo "# My Awesome Project" > kb/projects/my-awesome-project/README.md
   ```

4. **Portfolio Materials** - Add files to `kb/portfolio/`:
   ```bash
   # Add images, documents, presentations
   mkdir kb/portfolio/images
   mkdir kb/portfolio/documents
   ```

5. **Resume Documents** - Add PDFs to `kb/resume/`:
   ```bash
   # Copy your resume and LinkedIn PDF
   cp /path/to/your/resume.pdf kb/resume/
   cp /path/to/your/linkedin.pdf kb/resume/
   ```

#### Step 6: Configure System Behavior (Optional)
```bash
# Edit system prompts for custom behavior (advanced users only)
nano app/core/prompts.py
```

### 🚀 Running the Application

#### Step 7: Start Your AI Assistant
```bash
uv run python main.py
```

#### Step 8: Access the Interface
- Open your browser to `http://localhost:7860`
- Start chatting with your AI alter ego!

### 🧪 Testing Your Setup

Try asking these questions to test your setup:

- "What are your career goals?"
- "Tell me about your technical skills"
- "What projects have you worked on?"
- "What's your availability for work?"
- "Tell me about your education background"

### 🔧 Troubleshooting

**Common Issues:**

1. **OpenAI API Key Error**
   - Make sure your API key is correctly set in the `.env` file
   - Check that the key starts with `sk-`

2. **Port Already in Use**
   - Close any other applications using port 7860
   - Or restart your terminal

3. **Missing Dependencies**
   ```bash
   uv sync --force
   ```

4. **Knowledge Base Not Loading**
   - Make sure you ran `./setup_template.sh`
   - Check that files exist in `kb/faq/` and `me/` folders

### 📚 Next Steps

Once your basic setup is working:

1. **Add Your Content** - Replace template text with your actual information
2. **Test Questions** - Ask questions to make sure your AI responds correctly
3. **Deploy Online** - Use Hugging Face Spaces for public access

### 🎯 Simple Tips

- **Start with basic information** - Add your career goals, skills, and projects first
- **Test as you go** - Ask questions to check if your AI responds correctly
- **Keep it simple** - Don't overcomplicate the setup

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

## 🔔 Pushover Notifications

The AI Alter Ego includes optional **Pushover notification integration** to keep you informed about important interactions:

### **When Notifications Are Sent:**
- **Connection Requests**: When users express interest in connecting or collaborating
- **Unknown Questions**: When someone asks questions not covered in your knowledge base
- **User Details**: When users provide their contact information for follow-up

### **Setup Pushover Notifications:**
1. **Create Pushover Account**: Sign up at [pushover.net](https://pushover.net)
2. **Get API Credentials**: 
   - Application Token (from your app)
   - User Key (from your account)
3. **Add to Environment Variables**:
   ```bash
   PUSHOVER_TOKEN=your_application_token
   PUSHOVER_USER=your_user_key
   ```
4. **Install Pushover App**: Download on your phone/desktop for instant notifications

### **Example Notification Scenarios:**
- *"I'd love to connect and discuss potential opportunities"* → You get notified with user's email
- *"What's your favorite programming language?"* → You get notified about this unknown question
- *"Can you help me with my ML project?"* → You get notified about collaboration interest

## 🔧 Configuration

### Environment Variables
```bash
OPENAI_API_KEY=your_openai_api_key
OPENAI_MODEL=gpt-4
KB_DIR=./kb
CHUNK_TOKENS=1800
CHUNK_OVERLAP=300

# Optional: Pushover Notifications
PUSHOVER_TOKEN=your_pushover_token
PUSHOVER_USER=your_pushover_user
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