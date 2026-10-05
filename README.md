# Enterprise RAG Knowledge Assistant with Document Intelligence

![GenAI](https://img.shields.io/badge/Generative%20AI-RAG-blue)
![Azure OpenAI](https://img.shields.io/badge/Azure%20OpenAI-GPT--4-blue)
![Python](https://img.shields.io/badge/Python-3.x-yellow)
![FastAPI](https://img.shields.io/badge/FastAPI-Backend-green)
![Azure](https://img.shields.io/badge/Microsoft%20Azure-Cloud-blue)

## 📌 Project Overview

The **Enterprise RAG Knowledge Assistant** is a Generative AI-powered
knowledge management solution that enables users to interact with
enterprise documents using natural language.

The system combines:

- Retrieval-Augmented Generation (RAG)
- Azure OpenAI GPT models
- Embeddings
- Semantic Search
- Document Retrieval
- Prompt Engineering
- Role-Based Access Control (RBAC)
- Guardrail Validation
- Citation Verification
- Audit Logging
- Human Handoff

The solution retrieves relevant information from enterprise documents
and generates context-aware responses with source citations.

---

## 🎯 Problem Statement

Organizations maintain large numbers of documents such as:

- Policies
- Procedures
- Reports
- Manuals
- Technical documentation
- Internal knowledge documents

Traditional keyword-based search makes it difficult and time-consuming
for employees to find the required information.

The objective of this project is to provide a conversational AI interface
that allows users to ask questions and receive relevant, context-aware
answers from authorized enterprise documents.

---

## 💡 Solution

The application follows a Retrieval-Augmented Generation workflow.

1. Accept the user's question
2. Retrieve relevant document chunks
3. Perform similarity-based retrieval
4. Build contextual information
5. Create a prompt
6. Send the prompt and retrieved context to Azure OpenAI
7. Generate an AI response
8. Validate the response
9. Verify citations
10. Return the final response to the user

---

## 🏗️ Architecture

```text
                    ┌─────────────────────┐
                    │    Enterprise User  │
                    └──────────┬──────────┘
                               │
                               ▼
                    ┌─────────────────────┐
                    │    Web Chat UI      │
                    │ HTML/CSS/JavaScript │
                    └──────────┬──────────┘
                               │
                               ▼
                    ┌─────────────────────┐
                    │    FastAPI Backend  │
                    └──────────┬──────────┘
                               │
                 ┌─────────────┼─────────────┐
                 │             │             │
                 ▼             ▼             ▼
          ┌───────────┐ ┌────────────┐ ┌──────────────┐
          │   RBAC    │ │  Document  │ │ Azure Blob   │
          │  Access   │ │ Retrieval  │ │   Storage    │
          └───────────┘ └─────┬──────┘ └──────────────┘
                              │
                              ▼
                     ┌────────────────┐
                     │ Semantic Search │
                     │  / Top-K Search │
                     └───────┬────────┘
                             │
                             ▼
                     ┌────────────────┐
                     │ Context Builder│
                     └───────┬────────┘
                             │
                             ▼
                     ┌────────────────┐
                     │ Prompt Builder │
                     └───────┬────────┘
                             │
                             ▼
                     ┌────────────────┐
                     │  Azure OpenAI  │
                     │     GPT-4      │
                     └───────┬────────┘
                             │
                             ▼
                     ┌────────────────┐
                     │    Guardrail   │
                     │   Validation   │
                     └───────┬────────┘
                             │
                             ▼
                     ┌────────────────┐
                     │ Output + Source│
                     │    Citations   │
                     └────────────────┘
```

---

## 🔄 RAG Workflow

```text
Enterprise Documents
        │
        ▼
Document Ingestion
        │
        ▼
Document Chunking
        │
        ▼
Embedding Generation
        │
        ▼
Document Indexing
        │
        ▼
User Question
        │
        ▼
Similarity Search
        │
        ▼
Top-K Relevant Chunks
        │
        ▼
Context Preparation
        │
        ▼
Prompt Engineering
        │
        ▼
Azure OpenAI GPT-4
        │
        ▼
Response Generation
        │
        ▼
Guardrail & Citation Validation
        │
        ▼
Final Response
```

---

## 🧠 Generative AI Concepts

### Retrieval-Augmented Generation

RAG combines information retrieval with Large Language Models.
The system retrieves relevant information from enterprise documents
and provides it as context to the LLM before generating a response.

### Embeddings

Document chunks are converted into numerical vector representations
using the `text-embedding-3-large` embedding model.

### Semantic Search

Semantic search identifies documents or chunks that are conceptually
relevant to the user's question.

### Top-K Retrieval

The retrieval layer selects the most relevant document chunks and
passes them to the context-building stage.

### Prompt Engineering

The system combines:

```text
User Query
    +
System Prompt
    +
Retrieved Context
    +
Prompt Template
```

and sends the resulting prompt to Azure OpenAI.

---

## 🛡️ Security & Validation

### Role-Based Access Control

The platform supports different user roles:

```text
Administrator
Manager
Employee
Guest
```

### Guardrails

Generated responses are validated for:

- Citation completeness
- Response relevance
- Policy compliance
- Hallucination detection
- Confidence threshold

### Retry Workflow

If a generated response does not satisfy validation criteria,
the system can trigger a retry workflow.

### Audit Logging

The application maintains logs for:

- User queries
- Generated responses
- Citations
- Access logs
- Errors
- User activity

---

## 🛠️ Technology Stack

### Generative AI

- Generative AI
- Retrieval-Augmented Generation (RAG)
- Azure OpenAI
- GPT-4
- Embeddings
- Semantic Search
- Prompt Engineering

### Backend

- Python
- FastAPI
- REST APIs

### Cloud

- Microsoft Azure
- Azure OpenAI
- Azure Blob Storage
- Azure AI Search
- Azure Monitor
- Application Insights

### Frontend

- HTML5
- CSS3
- JavaScript

### Database

- SQLite

---

## 📁 Project Structure

```text
enterprise-rag-platform/
│
├── frontend/
│   ├── index.html
│   ├── styles.css
│   ├── app.js
│   └── assets/
│
├── backend/
│   ├── main.py
│   ├── pipeline.py
│   ├── retrieval.py
│   ├── access_control.py
│   ├── llm_client.py
│   ├── guardrail.py
│   ├── storage.py
│   ├── audit.py
│   ├── config.py
│   └── utils.py
│
├── documents/
├── uploads/
├── database/
├── logs/
│
├── requirements.txt
├── Dockerfile
├── docker-compose.yml
├── .env
└── README.md
```

---

## 🔧 Backend Responsibilities

| Module | Responsibility |
|---|---|
| `main.py` | FastAPI initialization and API routing |
| `pipeline.py` | End-to-end workflow orchestration |
| `retrieval.py` | Semantic search, ranking and Top-K retrieval |
| `llm_client.py` | Azure OpenAI communication and response generation |
| `access_control.py` | User authorization and permission checking |
| `guardrail.py` | Hallucination, citation and policy validation |
| `storage.py` | Azure Blob Storage operations |
| `audit.py` | Query history, audit logs and error tracking |

---

## 🚀 Main Features

- 💬 Conversational AI interface
- 📄 Enterprise document upload
- 🔎 Semantic document search
- 🧠 Retrieval-Augmented Generation
- 🔢 Embedding generation
- 📚 Top-K document retrieval
- ✍️ Prompt engineering
- 🤖 Azure OpenAI GPT-4 integration
- 🔐 Role-Based Access Control
- 🛡️ AI response guardrails
- ✅ Citation validation
- 🔍 Hallucination detection
- 🔄 Retry workflow
- 👨‍💼 Human handoff
- 📝 Audit logging
- ☁️ Azure Blob Storage integration

---

## 📊 Example Use Case

A user can upload enterprise documents and ask:

```text
"What is the company's leave policy?"
```

The system processes the request:

```text
User Question
      ↓
Retrieve relevant document chunks
      ↓
Build context
      ↓
Create prompt
      ↓
Azure OpenAI GPT-4
      ↓
Validate response
      ↓
Return answer + citations
```

---

## 🏆 Achievement

### Winner — GenAI Designathon

**Hexaware Technologies**

**Project:** Enterprise RAG Knowledge Assistant with Document Intelligence

---

## 📚 Learning Outcomes

Through this project, I gained practical exposure to:

- Generative AI
- Large Language Model applications
- Retrieval-Augmented Generation
- Prompt Engineering
- Embeddings
- Semantic Search
- Document Retrieval
- Azure OpenAI
- FastAPI
- AI response validation
- RBAC
- Enterprise AI security
- Audit logging
- Cloud-based AI architecture

---

## 👨‍💻 Author

**Jayakumar T**

B.Tech Information Technology

### Areas of Interest

- Small Language Models (SLM)
- Agentic AI
- Generative AI
- AI/ML
- RAG
- Data Engineering
- Azure
- Databricks
- Snowflake

### Connect

- [LinkedIn](https://www.linkedin.com/in/jayakumar-t-4871ab226/)
- [GitHub](https://github.com/TKJayakumar)

---

## 📄 License

This project is intended for educational, portfolio, and demonstration
purposes.
