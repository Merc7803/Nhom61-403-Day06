# VinFast AI Advisor (Compass)

Prototype chatbot tu van mua xe VinFast voi quy trinh:
- Thu intake nhu cau (ngan sach, so nguoi, usage, km/thang, uu tien)
- Goi y Top 3 xe phu hop
- Tinh chi phi so huu (tra gop + chi phi sac + tong 5 nam)
- Ho tro gui lead / dang ky lai thu

## Poster va hinh anh

### 1) Main project poster

![VinFast Project Poster](Project%20poster.png)

### 2) Before/After flow diagram

![Before After Flow](before-after-flow-vinfast.svg)

### 3) 4-step infographic poster

![4 Step Poster](poster-4step-template-style.svg)

### 4) Poster content in Markdown

- [poster-vinmec-triage-showcase.md](poster-vinmec-triage-showcase.md)

## Tech stack

- Frontend: React + Vite
- AI: OpenAI Chat Completions + tool calling
- Backend (optional): FastAPI (Python)
- Data: JSON vehicle catalog

## Chay local

### Frontend

```bash
cd Hackathon/Demo
npm install
npm run dev
```

### Backend tools (optional)

```bash
cd server
pip install -r requirements.txt
# run FastAPI app on your configured port
```

## Logging token/cost + reliability (phuc vu Cost/Deployment/Presentation)

### 1) Bat server log (FastAPI)

- Chay FastAPI (`server/agent_api.py`) de nhan log chat tai endpoint `/api/chat_log`.
- Set `VITE_AGENT_API_URL` (frontend) tro toi base URL cua FastAPI.

Log se duoc ghi vao thu muc `chat_logs/` (moi session 1 file JSON).

### 2) Thu thap token usage tu OpenAI

Khi chay che do agent (co `VITE_OPENAI_API_KEY`), frontend se luu them vao `meta`:
- `openai_usage` (prompt/completion/total tokens)
- `openai_latency_ms_total`, `openai_latency_ms_avg`
- `openai_request_count`, `openai_rounds`

### 3) Tao report phuc vu slide/poster

Cap nhat gia model trong `analytics/model_pricing_usd_per_1m_tokens.json`, sau do chay:

```bash
python analytics/token_cost_report.py --log-dir chat_logs --pricing analytics/model_pricing_usd_per_1m_tokens.json --markdown
```

## Tai lieu lien quan

- [spec-final.md](spec-final.md)
- [prototype.md](prototype.md)
- [Hackathon/Demo/README.md](Hackathon/Demo/README.md)

## Muc tieu demo

- Giam thoi gian pre-consult cho nguoi mua xe
- Tang do ro rang trong quyet dinh mua xe
- Tang conversion cho lead / test drive
