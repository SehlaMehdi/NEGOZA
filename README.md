# NEGOZA
### Your AI Agent Negotiates. You Approve. It Buys.

NEGOZA is an AI-powered autonomous shopping agent designed to help users negotiate better deals while discovering products online.

Instead of manually visiting multiple stores, comparing prices and negotiating with sellers, users can delegate the shopping negotiation process to their personal AI agent.

NEGOZA uses a multi-agent architecture where a Buyer Agent represents the customer's interests and negotiates with a Seller Agent to find a mutually acceptable price. Users review the final deal and authorize payment.

---

## The Problem

Online shopping often involves:
- Spending time comparing prices across retailers.
- Manually searching for better offers.
- Negotiating with sellers to obtain discounts.
- Evaluating delivery costs and purchase conditions.
- Repeating the same process across different products.

## Our Solution

NEGOZA introduces an autonomous shopping representative that works on behalf of the buyer.

**Discover → Activate Agent → Negotiate → Review → Approve → Purchase**

1. Discover sponsored products through a social-style product feed.
2. Select a product and activate your NEGOZA Buyer Agent.
3. Set your target price, maximum budget and preferences.
4. The Buyer Agent negotiates with the Seller Agent.
5. Review the negotiation transcript and final offer.
6. Approve the deal and proceed through PayPal Sandbox.

## Key Features

- **Social-Style Product Discovery:** Browse sponsored product listings and discover products.
- **Real Product Discovery:** Channel3 API integration for product information, retailer offers, prices and product links.
- **Autonomous Buyer Agent:** Represents the buyer's budget and negotiation preferences.
- **AI Seller Agent:** Evaluates buyer proposals and responds with counteroffers.
- **Agent-to-Agent Negotiation:** Multi-round negotiation between AI agents.
- **Price Guardrails:** Python-based validation enforces buyer spending limits and seller pricing constraints.
- **Negotiation Transcript:** View offers, counteroffers, reasoning and negotiation outcomes.
- **Browser Automation:** KERNEL integration for cloud browser sessions and website inspection.
- **Payment Integration:** PayPal Sandbox integration for payment authorization and processing.

## System Architecture

```text
              USER
                |
                v
       NEGOZA PRODUCT FEED
                |
                v
       CHANNEL3 PRODUCT API
                |
                v
         ADD MY AGENT
                |
                v
          BUYER AGENT
                |
                v
       NEGOTIATION ENGINE
                |
                v
          SELLER AGENT
                |
          GEMINI API
                |
                v
       PRICE VALIDATION
                |
                v
       NEGOTIATION RESULT
                |
                v
          USER REVIEW
                |
                v
        PAYPAL SANDBOX
```

## Technology Stack

| Component | Technology |
|---|---|
| Frontend | React, Vite, JavaScript |
| Styling | CSS |
| Backend | Python, FastAPI |
| AI Model | Google Gemini API |
| Agent Architecture | Buyer Agent and Seller Agent |
| Product Discovery | Channel3 API |
| Browser Automation | KERNEL |
| Payment Gateway | PayPal Sandbox |
| HTTP Communication | Axios |
| Data Validation | Pydantic |

## Project Structure

```text
NEGOZA/
│
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   ├── pages/
│   │   ├── services/
│   │   └── App.jsx
│   ├── package.json
│   └── vite.config.js
│
├── backend/
│   ├── app/
│   │   ├── agents/
│   │   ├── models/
│   │   ├── routes/
│   │   ├── services/
│   │   └── main.py
│   ├── tests/
│   ├── requirements.txt
│   └── .env.example
│
└── README.md
```

## Getting Started

### Prerequisites

- Python 3.13 or compatible version.
- Node.js and npm.
- Git.
- API credentials for the required integrations.

### 1. Clone the repository

```bash
git clone https://github.com/SehlaMehdi/NEGOZA.git
cd NEGOZA
```

### 2. Configure the backend

```bash
cd backend
python -m venv venv
```

Activate the virtual environment:

**Windows:**
```bash
venv\Scripts\activate
```

Install dependencies:

```bash
pip install -r requirements.txt
```

Create a `.env` file inside the backend directory using `.env.example` as a reference.

Configure the required API credentials:

```env
GEMINI_API_KEY=your_gemini_api_key
CHANNEL3_API_KEY=your_channel3_api_key
KERNEL_API_KEY=your_kernel_api_key

PAYPAL_CLIENT_ID=your_paypal_client_id
PAYPAL_CLIENT_SECRET=your_paypal_client_secret
PAYPAL_BASE_URL=https://api-m.sandbox.paypal.com
```

Start the backend:

```bash
uvicorn app.main:app --reload
```

Backend API:
`http://127.0.0.1:8000`

API documentation:
`http://127.0.0.1:8000/docs`

### 3. Configure the frontend

Open a second terminal:

```bash
cd frontend
npm install
```

Create the frontend environment configuration if required by the existing API client, and configure the backend API URL.

Start the frontend:

```bash
npm run dev
```

Frontend:
`http://localhost:5173`

## Security

- API credentials are stored in backend environment variables.
- Secrets must never be committed to GitHub.
- `.env` files are excluded through `.gitignore`.
- PayPal integration uses Sandbox credentials for testing.

## Future Scope

- Browser extension for activating NEGOZA while browsing external websites.
- Integration with social platforms and supported merchant websites.
- Wider merchant-agent interoperability.
- Persistent user preferences and negotiation history.
- Expanded autonomous commerce workflows.

## Hackathon Project

**NEGOZA — Autonomous Agentic Commerce**

Your AI Agent Negotiates. You Approve. It Buys.