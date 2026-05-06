# Mike

Open-source release containing the Mike frontend and backend.

## Contents

- `frontend/` - Next.js application
- `backend/` - Express API, Supabase access, document processing, and migrations
- `backend/migrations/000_one_shot_schema.sql` - one-shot Supabase schema for fresh databases

## Setup

# 🚀 Mike-for-dummies

**The 60-second Dockerized version of Mike Legal Assistant.** This repository provides a streamlined, containerized setup of the original Mike project. No need to manually install Node.js, LibreOffice, or manage complex environment variables—just Docker and a simple wizard.

---

## 🏗️ Quick Start

This version is designed to get you up and running without touching a single line of code.

### 1. Configure
Run the intelligent setup wizard. It will help you input your API keys (Supabase, R2, Gemini/Anthropic), fix common URL formatting errors, and create your `.env` files automatically.
```bash
python setup.py
```

### 2. Launch
Start the entire stack (Frontend + Backend) with one command:

```bash
docker-compose up --build
```

### 3. Access
Open your browser at: http://localhost:3000

## 🌟 Why this version?
Zero Dependency: LibreOffice (for document conversion) and Node.js are bundled inside the Docker containers. Your host machine stays clean.

Smart Setup: The setup.py script handles the configuration for you, including automatic backups of your existing settings.

Community Ready: Built for those who want to test Mike immediately without the "dependency hell."

## 🛠️ Requirements
To use this Dockerized version, you still need the original external services:

Supabase: For Auth and Database.

Cloudflare R2: For S3-compatible document storage.

LLM Provider: API keys for Gemini or Anthropic.

## 📂 Credits & License
This is a Dockerized distribution of the original Mike project. All credits for the application logic go to the original authors.

Dockerization & Wizard by: danielesalpietro


## 🚀 Roadmap (Coming Soon)
Local-First Version: Integration with local LLMs (NVIDIA NIM/Ollama) to keep legal data 100% private.

Obsidian Support: Native Markdown (.md) support to bridge the gap between notes and case files.

License: AGPL-3.0 (same as original)
