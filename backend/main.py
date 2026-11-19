from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List
from datetime import datetime
import random

app = FastAPI(title="Mobile Banking API", description="M-Pesa + Loans + Transfers - Kenyan Mobile Banking", version="2.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

# Fake DB - replace with Postgres
ACCOUNTS = {
    "254712345678": {"balance": 45200, "name": "John Kamau"}
}
LOANS = []
TRANSACTIONS = []

class LoanRequest(BaseModel):
    phone: str
    amount: float
    term_days: int = 30
    avg_income_3m: float
    crb_status: str = "clean"
    prev_loans: int = 0
    prev_on_time: int = 0

class TransferRequest(BaseModel):
    from_phone: str
    to_phone: str
    amount: float
    pin: str

def decide_loan(req: LoanRequest):
    reasons = []
    # HARD DENY
    if req.crb_status == "defaulted":
        return "DENY", 0, 0, ["Hard DENY: Active CRB default"]
    if req.avg_income_3m < 2000:
        return "DENY", 15, 0, ["Hard DENY: Income < 2000"]

    score = 0
    # Affordability 40%
    monthly_inst = req.amount / (req.term_days/30)
    ratio = req.avg_income_3m / monthly_inst if monthly_inst>0 else 0
    if ratio >= 3: 
        score+=40; reasons.append(f"Affordability PASS: Income {ratio:.1f}x installment")
    elif ratio >=1.5: 
        score+=20; reasons.append(f"Affordability MEDIUM: {ratio:.1f}x")
    else: 
        reasons.append(f"Affordability FAIL: {ratio:.1f}x - Risk high")

    # History 40%
    if req.prev_loans>0:
        rate = req.prev_on_time/req.prev_loans
        if rate>=0.9: score+=40; reasons.append(f"History GOOD: {rate*100:.0f}% on-time")
        elif rate>=0.6: score+=20; reasons.append(f"History AVG: {rate*100:.0f}%")
        else: reasons.append(f"History POOR: {rate*100:.0f}%")
    else:
        score+=15; reasons.append("First borrower - limit 5k")

    # Bonus
    score+=10
    reasons.append("KYC verified")

    score = min(score,100)

    if score>=70:
        approved = req.amount
        if req.prev_loans==0 and req.amount>5000: approved=5000; reasons.append("First loan capped at 5k")
        return "AWARD", score, approved, reasons
    elif score>=40:
        return "REVIEW", score, req.amount*0.5, reasons+["Manual review or offer 50%"]
    else:
        return "DENY", score, 0, reasons+["Score below 40"]

@app.get("/")
def root():
    return {"service": "Mobile Banking API", "docs": "/docs", "status": "live"}

@app.get("/bank/balance/{phone}")
def balance(phone: str):
    acc = ACCOUNTS.get(phone)
    if not acc: raise HTTPException(404, "Account not found")
    return {"phone": phone, "name": acc["name"], "balance": acc["balance"], "as_at": datetime.now().isoformat()}

@app.post("/bank/transfer")
def transfer(req: TransferRequest):
    if req.from_phone not in ACCOUNTS: raise HTTPException(404, "Sender not found")
    if ACCOUNTS[req.from_phone]["balance"] < req.amount: raise HTTPException(400, "Insufficient balance")
    if len(req.pin) != 4: raise HTTPException(400, "Invalid PIN")

    ACCOUNTS[req.from_phone]["balance"] -= req.amount
    if req.to_phone not in ACCOUNTS: ACCOUNTS[req.to_phone] = {"balance":0, "name":"New User"}
    ACCOUNTS[req.to_phone]["balance"] += req.amount

    tx = {"id": f"TX{random.randint(10000,99999)}", "from": req.from_phone, "to": req.to_phone, "amount": req.amount, "time": datetime.now().isoformat()}
    TRANSACTIONS.append(tx)
    return {"status": "SUCCESS", "transaction": tx, "new_balance": ACCOUNTS[req.from_phone]["balance"]}

@app.post("/bank/loan/decision")
def loan_decision(req: LoanRequest):
    decision, score, approved, reasons = decide_loan(req)
    record = {"phone": req.phone, "requested": req.amount, "decision": decision, "score": score, "approved": approved, "reasons": reasons, "time": datetime.now().isoformat()}
    LOANS.append(record)
    return {
        "decision": decision,
        "score": score,
        "requested_amount": req.amount,
        "approved_amount": approved,
        "reasons": reasons,
        "message": "AWARD: Disburse via M-Pesa" if decision=="AWARD" else "DENY: Inform customer with reasons" if decision=="DENY" else "REVIEW: Send to credit officer"
    }

@app.get("/bank/loan/history/{phone}")
def loan_history(phone: str):
    h = [l for l in LOANS if l["phone"]==phone]
    return {"phone": phone, "total": len(h), "history": h}

@app.get("/bank/transactions/{phone}")
def transactions(phone: str):
    txs = [t for t in TRANSACTIONS if t["from"]==phone or t["to"]==phone]
    return {"phone": phone, "count": len(txs), "transactions": txs}
