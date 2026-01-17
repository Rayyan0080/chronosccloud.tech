# Project Chronos

**Project Chronos** is a **software-only digital twin crisis management system** built using a **fault-tolerant, event-driven architecture**.

It simulates, detects, and responds to crisis scenarios in real time using autonomous agents, AI-driven predictions, and voice-based interaction—designed to be **demo-first**, **production-ready**, and **modular by default**.

---

## 🚀 What Problem Does Chronos Solve?

Traditional crisis-response systems are often:

* Rigid and slow to adapt
* Tightly coupled to hardware
* Hard to demonstrate or iterate quickly

**Chronos flips this model** by providing a fully software-based digital twin that:

* Reacts to real-time events
* Coordinates autonomous agents
* Uses AI to predict outcomes
* Supports voice-driven commands
* Remains resilient even when components fail

---

## 🧠 Core Principles

* **Demo-first** – Built to shine in live demos and hackathons
* **Event-driven** – All services communicate via structured JSON events
* **Service-oriented** – Small, independently deployable services
* **Fault-tolerant** – Mocks and fallbacks for external dependencies
* **Minimal & clean** – No unnecessary abstractions or overengineering
* **Production-minded** – Logging, retries, and resilience by default

---

## 🏗️ Architecture Overview

Chronos is a distributed system composed of loosely coupled services:

```
Chronos-Cloud/
├── qnx/              # QNX-based services and integrations
├── agents/           # Autonomous agent services
├── ai/               # AI/ML services and prediction engines
├── voice/            # Voice processing and command interfaces
├── dashboard/        # Web-based monitoring and control UI
├── infra/            # Infrastructure, Docker, shared utilities
│   ├── docker/
│   ├── k8s/          # Optional Kubernetes manifests
│   └── shared/
└── docs/             # Architecture and system documentation
```

---

## 🔄 Event-Driven Design

All communication happens through **JSON-based events** sent over a message broker (RabbitMQ).

### Standard Event Format

```json
{
  "eventType": "crisis.alert",
  "timestamp": "2024-01-01T12:00:00Z",
  "source": "agent.sensor-01",
  "payload": {
    "severity": "high",
    "location": "building-a",
    "details": {}
  },
  "correlationId": "uuid-here"
}
```

### Supported Event Types

* `crisis.alert` – Crisis detected
* `crisis.update` – Ongoing crisis status update
* `crisis.resolved` – Crisis resolution
* `agent.status` – Agent health or availability
* `voice.command` – Voice input received
* `ai.prediction` – AI-generated insight or forecast

---

## 🧰 Tech Stack

* **Message Broker**: RabbitMQ
* **Cache / State**: Redis
* **Database**: PostgreSQL
* **Frontend**: Web dashboard (React-based)
* **Backend Services**: Node.js + Python
* **AI/ML**: Python 3.10+
* **Voice**: Speech-to-text & command parsing
* **Infra**: Docker, Docker Compose (K8s optional)

---

## 📦 Prerequisites

* Docker Desktop (or Docker Engine + Docker Compose)
* Git
* Node.js 18+
* Python 3.10+

---

## ⚡ Quick Start (Recommended)

### 1. Clone the Repository

```bash
git clone <repo-url>
cd Chronos-Cloud
```

### 2. Start the Full Stack

```bash
docker-compose up -d
```

### 3. View Logs

```bash
docker-compose logs -f
```

### 4. Stop All Services

```bash
docker-compose down
```

### 5. Rebuild After Changes

```bash
docker-compose up -d --build
```

---

## 🌐 Service Endpoints

| Service             | URL                                                              |
| ------------------- | ---------------------------------------------------------------- |
| Dashboard           | [http://localhost:3000](http://localhost:3000)                   |
| API Gateway         | [http://localhost:8080](http://localhost:8080)                   |
| RabbitMQ Management | [http://localhost:15672](http://localhost:15672) (guest / guest) |

---

## 🧪 Development Workflow

### Run Infrastructure Only

```bash
docker-compose up -d rabbitmq redis postgres
```

### Run Services Locally

Each service has its own README with instructions. Typical flow:

1. Install dependencies
2. Set environment variables
3. Run service (`npm start`, `python main.py`, etc.)

### Run Full Stack (Local + Docker)

```bash
docker-compose up
```

---

## 🔐 Environment Configuration

Create a `.env` file in the project root:

```env
# Message Broker
RABBITMQ_HOST=localhost
RABBITMQ_PORT=5672
RABBITMQ_USER=guest
RABBITMQ_PASS=guest

# Database
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_USER=chronos
POSTGRES_PASS=chronos
POSTGRES_DB=chronos

# Redis
REDIS_HOST=localhost
REDIS_PORT=6379

# Services
DASHBOARD_PORT=3000
API_GATEWAY_PORT=8080
```

---

## 🧪 Testing

Run the full test suite:

```bash
docker-compose -f docker-compose.test.yml up --abort-on-container-exit
```

Or run tests per service (see individual READMEs).

---

## 🤝 Contributing

1. Create a feature branch
2. Make changes in the relevant service directory
3. Update documentation in `docs/`
4. Test locally using Docker Compose
5. Submit a pull request

---

## 📄 License

*Add license information here*

---

## 📬 Support

For bugs, ideas, or questions, please open an issue in the repository.
