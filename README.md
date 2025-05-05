# ✨ Clara AI ✨

**Clara AI** is your AI-powered executive assistant for email. It leverages advanced language models to triage, classify, and draft responses to emails, integrating seamlessly with Gmail. Clara AI is designed for busy professionals who want to automate routine email tasks, stay on top of important messages, and respond faster with less effort.

---

## 🚀 Features

- **Automated Email Triage:**  
  Classifies emails into actionable categories: Ignore, Notify, Needs Your Input, and Ready to Send, using custom Gmail labels for clear organization.
- **AI-Powered Response Drafting:**  
  Generates intelligent, context-aware draft replies using LLMs, and requests missing information when needed.
- **Workflow Automation:**  
  Orchestrates the flow from triage to draft creation and label management, maintaining thread state and updating labels as emails are processed.
- **Gmail Integration:**  
  Authenticates via OAuth2 and interacts with Gmail API for reading, labeling, and sending emails. Robust label and thread management.
- **User Profile & Memory:**  
  Stores user profile and last email update time in local JSON storage, remembering context and previous interactions.
- **Rich CLI Interface:**  
  Provides status, progress, and logs using rich console output.
- **Local LLM Support:**  
  Uses Ollama for accessing powerful local language models like llama3.2 with no API costs.  
  *Note: Using larger models with more parameters (e.g., `llama3:70b`, `mixtral:8x7b-instruct`) significantly enhances the agent's performance in both email triage accuracy and the quality of generated responses compared to smaller models.*

---

## 🛠️ Tech Stack

- **Python 3.9+**
- **LangChain & LangGraph** for agent workflow orchestration
- **Ollama** for running LLMs locally without relying on cloud APIs
- **Google Gmail API** for email access and management
- **HuggingFace Embeddings** for local semantic memory capabilities
- **Rich** for beautiful CLI output

---

## ⚡ How It Works

1. **Setup:**  
   Automatically checks for and configures Ollama and required language models.
2. **Authentication:**  
   Authenticates with Gmail using OAuth2 and retrieves user profile info.
3. **Triage:**  
   Fetches new email threads and classifies them using an LLM-based triage system. Applies custom Gmail labels based on classification.
4. **Drafting:**  
   For emails requiring a response, generates a draft reply and saves it in Gmail. Marks threads as needing user input if more information is required.
5. **Agent Orchestration:**  
   The `SecretaryAgent` coordinates the process, using the `EmailTriageSystem` for classification and the `ResponseGenerator` (powered by LangGraph and tools like `get_current_date` and memory access) for drafting replies.
6. **Workflow Management:**  
   Coordinates the process using a modular workflow manager and secretary agent. Updates thread state and persists user preferences.

---

## 🧩 Installation & Configuration

### 1. Clone the repository

```bash
git clone https://github.com/arjein/clara-ai.git
cd clara-ai
```

### 2. Install Ollama

Visit [https://ollama.com/download](https://ollama.com/download) to install Ollama for your operating system.

### 3. Run the startup script

The startup script will set everything up for you:

```bash
bash start.sh
```

This script will:
- Check if Ollama is installed and running (starting it if needed)
- Download the required llama3.2 model if not already available
- Create and activate a Python virtual environment
- Install all required Python packages
- Start the Clara AI application

Alternatively, you can install dependencies manually and run the app:

```bash
pip install -r requirements.txt
python main.py [--interval SECONDS] [--limit N] [--debug]
```

### 4. Set up Gmail API credentials

- Place your Gmail API credentials in `credentials` folder in JSON format.
- On first run, the app will guide you through OAuth2 authentication.

---

## 🖥️ Usage

### Using the startup script (recommended)

```bash
bash start.sh [--model <model_name>] [--interval SECONDS] [--limit N] [--debug]
```

Example: To use the `llama3:70b-instruct` model:
```bash
bash start.sh --model llama3:70b-instruct
```

The script will handle running Ollama and cleanup when you exit the app.

### Running manually

```bash
python main.py [--model <model_name>] [--interval SECONDS] [--limit N] [--debug]
```

Available options:
- `--model` — Specify the Ollama model to use (e.g., `llama3:70b-instruct`, `mixtral:8x7b-instruct`). Defaults to `llama3.2` if not specified.
- `--interval` — Polling interval for checking new emails (default: 20 seconds)
- `--limit` — Maximum number of emails to fetch per cycle (default: 50)
- `--debug` — Enable debug logging
- `--log-file` — Path to log file (default: "clara_secretary.log")
- `--quiet` — Minimal console output

---

## 🛠️ Customization

- **Labels:**  
  Clara AI creates and manages custom Gmail labels (e.g., `CLARA - IGNORED`, `CLARA - FYI`, `CLARA - NEEDS YOUR INPUT`, `CLARA - READY TO SEND`, `CLARA - REPLIED`).
- **LLM Settings:**  
  Supports different embedding providers (Ollama, HuggingFace, or Azure OpenAI) via the MemoryManager class.
- **User Profile:**  
  User information (name, email), last processed email timestamp, and Gmail label mappings are stored in `user_data.json`.
- **Memory System:**  
  Uses `langmem` for semantic search and long-term context retention. Defaults to the `sentence-transformers/all-MiniLM-L6-v2` embedding model locally but can be configured for other Ollama or HuggingFace models via `MemoryManager`.

## 🚀 Future Enhancements / TODO

Here are some potential directions for future development:

- **Desktop Application:** Develop a graphical user interface (GUI) for Clara AI, moving beyond the current command-line interface (CLI) for easier interaction.
- **Enhanced Memory & Contact Management:** Implement a more sophisticated memory system. This could involve storing information about frequent email senders as entities in a database, allowing Clara to build context about relationships and past interactions.
- **API Integrations:** Integrate with other APIs to enrich the agent's capabilities. Examples include:
    - **Calendar Integration:** Allow Clara to access calendar data to check availability, schedule meetings, or understand context related to events.
    - **CRM Integration:** Connect with Customer Relationship Management systems.
    - **Project Management Tools:** Link with tools like Jira or Asana.
- **Multi-Account Support:** Enable Clara AI to manage multiple email accounts simultaneously.
- **Advanced Workflow Customization:** Provide users with more granular control over defining custom workflows and rules.
- **Support for Other Email Providers:** Extend compatibility beyond Gmail to include Outlook, Yahoo, etc.

---

## 🤝 Contributing

Contributions are welcome! Please open issues or submit pull requests for improvements, bug fixes, or new features.

---

## 📜 License

MIT License. See [LICENSE](LICENSE) for details.

---

## 🙏 Acknowledgments

- Built with [LangChain](https://github.com/langchain-ai/langchain), [LangGraph](https://github.com/langchain-ai/langgraph), [Ollama](https://ollama.com/), and [Google Gmail API](https://developers.google.com/gmail/api).

---

> *Clara AI helps you focus on what matters. Let AI handle your inbox!*