const cashNode = document.getElementById("cash");
const tradesNode = document.getElementById("trades");
const tradeForm = document.getElementById("tradeForm");
const tradeMessage = document.getElementById("message");

async function refreshTrades() {
  const meResponse = await fetch("/api/me");
  if (meResponse.status === 401) { location.href = "/login.html"; return; }
  const me = await meResponse.json();
  cashNode.textContent = `₹${Number(me.user.trado_cash).toLocaleString("en-IN")}`;
  const response = await fetch("/api/trades");
  const data = await response.json();
  if (!response.ok) { tradesNode.textContent = data.error || "Couldn't load trade history."; return; }
  if (!data.trades.length) {
    const row = document.createElement("tr");
    const cell = document.createElement("td");
    cell.colSpan = 6;
    cell.textContent = "No virtual trades yet.";
    row.append(cell);
    tradesNode.replaceChildren(row);
    return;
  }
  const rows = data.trades.map(trade => {
    const row = document.createElement("tr");
    const values = [trade.created_at, trade.symbol, trade.side, trade.quantity, trade.price, `₹${trade.total}`];
    values.forEach(value => { const cell = document.createElement("td"); cell.textContent = String(value); row.append(cell); });
    return row;
  });
  tradesNode.replaceChildren(...rows);
}

tradeForm.addEventListener("submit", async event => {
  event.preventDefault();
  tradeMessage.textContent = "Recording…";
  const button = tradeForm.querySelector('button[type="submit"]');
  button.disabled = true;
  try {
    const payload = {
      symbol: document.getElementById("symbol").value,
      side: document.getElementById("side").value,
      quantity: document.getElementById("quantity").value,
      price: document.getElementById("price").value
    };
    const response = await fetch("/api/trades", {method:"POST", headers:{"Content-Type":"application/json"}, body:JSON.stringify(payload)});
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || "Couldn't record that paper trade.");
    tradeMessage.textContent = data.message;
    event.currentTarget.reset();
    await refreshTrades();
  } catch (error) { tradeMessage.textContent = error.message; }
  finally { button.disabled = false; }
});

refreshTrades().catch(error => { tradeMessage.textContent = error.message; });
