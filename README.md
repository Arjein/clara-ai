# ✨ Clara AI ✨

**Clara AI** is your AI-powered executive assistant for email. It leverages advanced language models to triage, classify, and draft responses to emails, integrating seamlessly with Gmail. Clara AI is designed for busy professionals who want to automate routine email tasks, stay on top of important messages, and respond faster with less effort.

---

## 🚀 Features

- **Automated Email Triage:**  
  Classifies emails into actionable categories: Ignore, Notify, Needs Your Input, and Ready to Send, using custom Gmail labels for clear organization.
- **AI-Powered Response Drafting:**  
  Generates intelligent, context-aware draft replies using LLMs (OpenAI, Anthropic, etc.), and requests missing information when needed.
- **Workflow Automation:**  
  Orchestrates the flow from triage to draft creation and label management, maintaining thread state and updating labels as emails are processed.
- **Gmail Integration:**  
  Authenticates via OAuth2 and interacts with Gmail API for reading, labeling, and sending emails. Robust label and thread management.
- **User Profile & Memory:**  
  Stores user profile and last email update time in Azure CosmosDB, remembering context and previous actions for smarter automation.
- **Rich CLI Interface:**  
  Provides status, progress, and logs using rich console output.

---

## 🛠️ Tech Stack

- **Python 3.9+**
- **LangChain & LangGraph** for agent workflow orchestration
- **OpenAI / Anthropic** LLMs for email understanding and drafting
- **Google Gmail API** for email access and management
- **Azure CosmosDB** for persistent user state and memory
- **Rich** for beautiful CLI output

---

## ⚡ How It Works

1. **Authentication:**  
   Authenticates with Gmail using OAuth2 and retrieves user profile info.
2. **Triage:**  
   Fetches new email threads and classifies them using an LLM-based triage system. Applies custom Gmail labels based on classification.
3. **Drafting:**  
   For emails requiring a response, generates a draft reply and saves it in Gmail. Marks threads as needing user input if more information is required.
4. **Workflow Management:**  
   Coordinates the process using a modular workflow manager and secretary agent. Updates thread state and user memory in CosmosDB.

---

## 🧩 Installation & Configuration

### 1. Clone the repository

```bash
git clone https://github.com/arjein/clara-ai.git
cd clara-ai
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Set up your `.env` file

Create a `.env` file in the project root with the following variables (example):

```env
OPENAI_API_KEY=your-openai-api-key
ANTHROPIC_API_KEY=your-anthropic-api-key
AZURE_COSMOSDB_URI=your-cosmosdb-uri
AZURE_COSMOSDB_KEY=your-cosmosdb-key
AZURE_COSMOSDB_DATABASE=your-database-name
AZURE_COSMOSDB_CONTAINER=your-container-name
```

> **Note:** Only add the variables you need for your setup. Never commit your `.env` file or credentials to version control.

### 4. Set up Gmail API credentials

- Place your Gmail API credentials in `credentials/credentials.json`.
- On first run, the app will guide you through OAuth2 authentication.

---

## 🖥️ Usage

Run Clara AI from the command line:

```bash
python main.py [--interval SECONDS] [--limit N] [--debug]
```

- `--interval` — Polling interval for checking new emails (default: 20 seconds)
- `--limit` — Maximum number of emails to fetch per cycle (default: 50)
- `--debug` — Enable debug logging

---

## 🛠️ Customization

- **Labels:**  
  Clara AI creates and manages custom Gmail labels (e.g., `CLARA - IGNORED`, `CLARA - FYI`, `CLARA - NEEDS YOUR INPUT`, `CLARA - READY TO SEND`, `CLARA - REPLIED`).
- **LLM Providers:**  
  Supports multiple LLM backends via LangChain.
- **User Profile:**  
  User information and preferences are stored in CosmosDB and can be extended.

---

## 📁 Project Structure

```
clara-ai/
├── agents/         # Core AI logic: triage, response generation, workflow
├── objects/        # Gmail API integration: authentication, labels, threads, messages
├── helpers.py      # Utility functions for thread processing
├── main.py         # Entry point, CLI, and main workflow loop
├── requirements.txt# Python dependencies
└── README.md
```

---

## 🤝 Contributing

Contributions are welcome! Please open issues or submit pull requests for improvements, bug fixes, or new features.

---

## 📜 License

MIT License. See [LICENSE](LICENSE) for details.

---

## 🙏 Acknowledgments

- Built with [LangChain](https://github.com/langchain-ai/langchain), [OpenAI](https://openai.com/), [Anthropic](https://www.anthropic.com/), and [Google Gmail API](https://developers.google.com/gmail/api).

---

> *Clara AI helps you focus on what matters. Let AI handle your inbox!*