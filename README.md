# 🎙️ Voice-Activated Task Orchestration Assistant (STT & Local LLM)

An intelligent, voice-driven task management system utilizing advanced Edge-AI Speech-to-Text (STT) and local Large Language Models (LLMs) to translate unstructured natural human speech into structured, actionable database operations in real-time.

Built as a highly responsive, non-blocking asynchronous Telegram Bot, this assistant acts as an intuitive, hands-free personal productivity hub.

---

## 🧠 Architectural Design & Cognitive Engine

The architecture employs a multi-tiered pipeline that processes raw user acoustics, transcribes the voice payload, parses semantic intent, and executes precise state mutations on database layers.

```
[User Audio (OGG)] ──> [FFmpeg Transcoding (WAV)] ──> [Whisper STT Model]
                                                             │
                                                             ▼
[State Mutation (SQLite)] <── [Database] <── [Async LLM Semantic Parsing (Mistral)]
      │                                                      │ (If offline)
      ▼                                                      ▼
[Updated Checklist Reply] <──────────────────────── [Rule-Based Fallback Engine]
```

### 1. High-Fidelity Acoustic Transcription (Whisper STT)
* **Model**: **OpenAI Whisper (`medium`)** running locally on device.
* **Mechanism**: Conversational voice inputs (Telegram voice messages) are ingested, transcoded dynamically from OGG/OPUS to 16kHz WAV formats via a non-blocking background FFmpeg subprocess, and fed into the Whisper neural network.
* **Concurrency**: Transcription runs within background thread workers (`asyncio.to_thread`) to prevent freezing the main asynchronous application event loop during heavy GPU/CPU inference.

### 2. Semantic Intent Inference & Zero-Shot JSON Structuring (Mistral LLM)
* **Model**: **Mistral (7B)** running locally via **Ollama**.
* **Mechanism**: The raw transcription text is evaluated using structured zero-shot prompt engineering. The LLM extracts the cognitive "intent" of the user and maps it directly into a standardized, deterministic JSON contract:
  ```json
  {
    "action": "add | done | delete | clear | show",
    "tasks": ["Task Item 1", "Task Item 2"],
    "positions": [1, 3]
  }
  ```
* **Resiliency & Hybrid Parsing**: To guarantee uninterrupted availability in edge scenarios or offline deployments, a **Graceful Degradation** protocol is active. If the local LLM server is unresponsive, the system seamlessly redirects the query to a local, regex-driven, multi-lingual (English, Tamil, Hindi) keyword heuristic engine.

### 3. Transaction-Safe Local Persistence (SQLite)
* **Mechanism**: The backend storage layer implements a transactional SQLite schema. Every connection is encapsulated in a strict context manager verifying data consistency (automatic `commit` on success, immediate `rollback` on exceptions) and guaranteeing the complete elimination of database connection leaks.

---

## 🛠️ Technology Stack

* **Async Application Framework**: `aiogram` (Telegram Bot API wrapper)
* **Neural Speech-to-Text**: `openai-whisper`
* **Local LLM Engine**: `ollama` (Mistral)
* **Media Transcoder**: `ffmpeg`
* **Data Storage**: `sqlite3`
* **Configuration Management**: `python-dotenv`

---

## 🚀 Installation & Local Deployment

### Prerequisites
* **Python**: 3.9 or higher (Tested on Python 3.13)
* **FFmpeg**: Must be installed and added to your system path.
* **Ollama**: Download and install [Ollama](https://ollama.com/), then run the Mistral model:
  ```bash
  ollama run mistral
  ```

### Setup Instructions
1. **Clone the Repository**:
   ```bash
   git clone https://github.com/nev6104/telegram_voice_assistant_bot.git
   cd telegram_voice_assistant_bot
   ```

2. **Configure Secrets**:
   Create a `.env` file in the root directory and add your Telegram Bot Token:
   ```env
   BOT_TOKEN=YOUR_TELEGRAM_BOT_TOKEN
   ```

3. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Initialize and Start the Bot**:
   ```bash
   python bot.py
   ```

---

## 💡 Usage Examples & Natural Language Interface

Because semantic analysis is handled by an LLM, the bot does not require rigid syntax. You can speak naturally:

* **Adding Tasks**: 
  * *"I need to remember to buy milk, walk the dog, and call my manager tonight."*
  * **Result**: Parses `add` action, creating three clean checklist items.
* **Completing Tasks**:
  * *"Hey, I finished task two and task four."*
  * **Result**: Parses `done` action for items `[2, 4]`.
* **Deleting Tasks**:
  * *"Delete the first item, please."*
  * **Result**: Parses `delete` action for item `[1]`.
* **Viewing Tasks**:
  * *"What is currently left on my list?"*
  * **Result**: Parses `show` action, displaying your formatted checklist.
