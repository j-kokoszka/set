# ⚡ set

**The workout tracker built for speed.**  
A modern, responsive, and serverless web application designed to track gym workouts with "Excel-like" input speed and a beautiful dark-mode interface.

![Tech Stack](https://img.shields.io/badge/Stack-FastAPI%20%7C%20React%20%7C%20DynamoDB-blue)
![License](https://img.shields.io/badge/license-MIT-green)

---

## ✨ Features

- **Blazing Fast Logging**: Add exercises and sets with intelligent defaults (inherits values from previous sets).
- **CRUD Operations**: Full support for creating, viewing, editing, and deleting workouts.
- **Multi-Unit Support**: Toggle between **kg** and **lbs** per set with automatic weight conversion.
- **Secure by Design**: Token-based authentication ready for Amazon Cognito.
- **Production Ready**: Structured JSON logging optimized for AWS CloudWatch.
- **Serverless Core**: Built to run on AWS Lambda (via Mangum) and DynamoDB.

## 🚀 Getting Started

### Prerequisites
- **Python 3.14+**
- **Node.js 20+**
- **Podman** (or Docker) for local DynamoDB

### Quick Start (The "Vibecoding" Way)
We use a `Makefile` to simplify local development.

1. **Install Dependencies**:
   ```bash
   make install-deps
   ```
2. **Start the Environment**:
   ```bash
   make dev
   ```
   *This spins up DynamoDB Local, the FastAPI backend (port 8000), and the Vite frontend (port 5173).*

3. **Login**:
   Use any username to login via the Mock Auth screen (for local development).

## 🛠 Tech Stack

- **Frontend**: React 19, TypeScript, Vite, Vanilla CSS
- **Backend**: FastAPI, Pydantic, Mangum (AWS Lambda)
- **Database**: Amazon DynamoDB (Single-table design)
- **Identity**: Amazon Cognito (JWT-based)
- **Logging**: Structlog (Structured JSON)

## 🧪 Testing
Run the backend API test suite while the dev environment is up:
```bash
make test
```

## 🏗 Architecture
The application uses a **Single-Table Design** in DynamoDB for high performance and scalability.
- `USER#<id>` / `WORKOUT#<date>#<id>`: Workout summaries.
- `USER#<id>` / `EXERCISE#<name>#<date>`: Individual exercise records for history tracking.

---

## 📅 Roadmap
- [ ] **Google SSO Integration** (See [docs/google-sso-plan.md](./docs/google-sso-plan.md))
- [ ] **Progress Visualizations**: Personal Records (PR) and Volume charts.
- [ ] **Workout Templates**: Save and load your favorite routines.
- [ ] **Global Unit Preference**: Set a default unit in user profile.

---
Built with ❤️ by Gemini CLI
# Manual deployment trigger
# Manual deployment trigger 2
