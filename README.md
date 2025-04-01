# OfflinePyTutor: Offline open source llm-powered Python Learning

This is an offline learning assistant that helps you master Python programming through interactive conversations. Built with Meta's CodeLlama 7B model running locally through Ollama, this application provides personalized Python tutoring without requiring an internet connection or expensive API subscriptions.

## 🚀 Augmented Learning with Local AI

Traditional learning methods like books and courses are often too rigid and can't adapt to your specific questions. Online tutorials require constant internet connection and may not address your unique challenges. PyTutor bridges this gap by providing:

- **Personalized tutoring** that adapts to your learning style and questions
- **Completely offline access** to a powerful AI tutor running on your machine
- **Interactive feedback** on your Python code and concepts
- **Persistent history** of your learning journey and past questions
- **Privacy-preserving learning** with no data sent to external servers

## 💡 Why Local LLMs for Learning?

Local Large Language Models (LLMs) are transforming how we learn programming:

1. **Learn at your own pace** with unlimited questions and no usage limits
2. **Connect concepts instantly** by asking follow-up questions
3. **Get unstuck quickly** without waiting for forum responses
4. **Experiment freely** in a judgment-free environment
5. **Relate new concepts** to what you already know through personalized examples

## 🛠️ Getting Started

### Prerequisites

- Python 3.7+
- [Ollama](https://github.com/ollama/ollama) installed on your system
- At least 8GB RAM (16GB recommended for optimal performance)
- 10GB free disk space for model storage

### Installation

1. Clone this repository:
```bash
git clone https://github.com/yourusername/pytutor.git
cd pytutor
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Install Ollama and download the Llama 7B model:
```bash
# Follow Ollama installation instructions for your OS: https://github.com/ollama/ollama
# Then download the model:
ollama pull llama2:7b
```

4. Start the PyTutor application:
```bash
python app.py
```

5. Open your browser and navigate to:
```
http://localhost:5000
```

## 🔍 How to Use PyTutor for Effective Learning

### Starting with Concepts

Ask about Python concepts to build your foundation:

- "Explain Python list comprehensions with examples"
- "What are decorators in Python and when should I use them?"
- "How do Python context managers work?"

### Debugging and Problem Solving

Get help with specific code issues:

- "Why am I getting a 'NoneType has no attribute' error in this code?"
- "How can I optimize this loop to make it more efficient?"
- "What's wrong with my recursive function?"


## ⚙️ Configuration

You can customize PyTutor by modifying the `CONFIG` dictionary in `app.py`:

```python
CONFIG = {
    "primary_model": "llama2:7b",    # Main model for Python tutoring
    "fallback_model": "mistral:latest",  # Backup model if primary unavailable
    "request_timeout": 120,          # Adjust based on your hardware
    "max_retries": 2,                # Number of attempts before fallback
    "retry_delay": 2,                # Seconds between attempts
}
```

## 📜 License

This project is licensed under the MIT License - see the LICENSE file for details.

---

*PyTutor is not affiliated with Meta or the Llama team. It uses the open-source Llama model to provide offline Python tutoring capabilities.*
