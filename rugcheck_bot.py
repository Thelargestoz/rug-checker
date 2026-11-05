#!/usr/bin/env python3
"""Rug Checker: paste a Solana token, get a 🟢 / 🟡 / 🔴 verdict with plain-English reasons before you buy.

Uses two free public APIs (no keys): RugCheck (token safety report) and DexScreener (price, liquidity, trades).
Read-only: it never touches a wallet and never trades.

  python3 rugcheck_bot.py <mint address or dexscreener/pump.fun link>   check one token in the terminal
  TELEGRAM_TOKEN=... python3 rugcheck_bot.py telegram                    run as a Telegram bot
"""
import json, os, re, sys, time, urllib.parse, urllib.request

UA = {"User-Agent": "rug-checker/1.0"}
MINT = re.compile(r"\b[1-9A-HJ-NP-Za-km-z]{32,44}\b")   # Solana base58 address


def get(url, timeout=20):
    with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=timeout) as r: return json.load(r)


def find_mint(text):
    """First Solana address in a message or link (pump.fun/dexscreener links contain it)."""
    m = MINT.findall(text or "")
    return m[0] if m else None


def verdict(report, pair):
    """RugCheck report + best DexScreener pair -> (emoji, headline, red flags, yellow flags). Pure function, easy to test."""
    red, yellow = [], []
    r, p = report or {}, pair or {}
    if r.get("rugged"): red.append("already rugged")
    if r.get("mintAuthority"): red.append("dev can still mint more coins (mint not revoked)")
    if r.get("freezeAuthority"): red.append("dev can freeze your coins (freeze not revoked)")
    mk = r.get("markets") or []
    locked = max(((m.get("lp") or {}).get("lpLockedPct") or 0 for m in mk), default=None)
    if locked is not None and locked < 90: red.append(f"liquidity only {locked:.0f}% locked/burned (dev can pull it)")
    pools = {m.get("pubkey") for m in mk} | {m.get(k) for m in mk for k in ("liquidityA", "liquidityB")} | set(r.get("knownAccounts") or {})
    pools.discard(None)   # a missing key must not make every holder look like a pool
    top10 = sum(sorted((h.get("pct") or 0 for h in r.get("topHolders") or [] if h.get("owner") not in pools and h.get("address") not in pools), reverse=True)[:10])
    big = (r.get("totalHolders") or 0) >= 50_000   # on big established coins the top wallets are mostly exchanges
    if top10 > 40 and not big: red.append(f"top 10 wallets hold {top10:.0f}% (they can dump on you)")
    elif top10 > 40: yellow.append(f"top 10 wallets hold {top10:.0f}% (likely exchanges on a coin this big)")
    elif top10 > 25: yellow.append(f"top 10 wallets hold {top10:.0f}%")
    supply = (r.get("token") or {}).get("supply") or 0
    if supply and (r.get("creatorBalance") or 0) / supply > 0.03: yellow.append(f"creator still holds {(r.get('creatorBalance') or 0) / supply:.0%}")
    if r.get("graphInsidersDetected"): yellow.append(f"{r['graphInsidersDetected']} linked insider wallets")   # common on big old coins too, so a warning, not a veto
    holders = r.get("totalHolders")
    if holders is not None and holders < 300: yellow.append(f"only {holders} holders")
    red += [f"RugCheck: {x['name']}" for x in r.get("risks") or [] if x.get("level") == "danger" and x.get("name")]
    if p:
        liq, mcap = (p.get("liquidity") or {}).get("usd") or 0, p.get("marketCap") or p.get("fdv") or 0
        if liq < 10_000: red.append(f"liquidity ${liq:,.0f} (you may not be able to sell)")
        elif mcap and liq / mcap < 0.05: yellow.append(f"liquidity only {liq / mcap:.1%} of market cap")
        ch, tx = p.get("priceChange") or {}, (p.get("txns") or {}).get("h1") or {}
        if (ch.get("m5") or 0) > 40: yellow.append(f"up {ch['m5']:.0f}% in 5 min (buying the top?)")
        if (ch.get("h1") or 0) < -50: red.append(f"down {ch['h1']:.0f}% in the last hour")
        if tx.get("buys") and tx.get("sells", 0) > 1.5 * tx["buys"]: yellow.append("way more sellers than buyers this hour")
    else: yellow.append("no trading pair found on DexScreener")
    if red: return "🔴", "HIGH RISK: don't touch it", red, yellow
    if yellow: return "🟡", "CAREFUL: some warning signs", red, yellow
    return "🟢", "No big red flags found (still not a guarantee)", red, yellow


def check(mint):
    """Fetch both APIs and build the message for one token."""
    try: report = get(f"https://api.rugcheck.xyz/v1/tokens/{mint}/report")
    except Exception as e: return f"Couldn't get a RugCheck report for {mint} ({e}). Is that a Solana token address?"
    try: pairs = [p for p in get(f"https://api.dexscreener.com/tokens/v1/solana/{mint}") if p.get("chainId") == "solana"]
    except Exception: pairs = []
    pair = max(pairs, key=lambda p: (p.get("liquidity") or {}).get("usd") or 0, default=None)
    emoji, head, red, yellow = verdict(report, pair)
    meta = report.get("tokenMeta") or {}
    name = f"{meta.get('name') or (pair or {}).get('baseToken', {}).get('name') or 'Unknown'} ({meta.get('symbol') or (pair or {}).get('baseToken', {}).get('symbol') or '?'})"
    lines = [f"{emoji} {name}", head]
    lines += [f"  🔴 {x}" for x in red] + [f"  🟡 {x}" for x in yellow]
    if pair:
        lines.append(f"💧 liquidity ${(pair.get('liquidity') or {}).get('usd') or 0:,.0f} · mcap ${pair.get('marketCap') or pair.get('fdv') or 0:,.0f} · holders {report.get('totalHolders', '?')}")
    lines.append(f"🔎 rugcheck.xyz/tokens/{mint}")
    lines.append("Not financial advice. This is a safety check, not a buy signal.")
    return "\n".join(lines)


def telegram():
    """Long-poll the Telegram Bot API (stdlib only). Replies to any message that contains a Solana address."""
    token = os.environ.get("TELEGRAM_TOKEN") or sys.exit("set TELEGRAM_TOKEN (get one from @BotFather)")
    api, offset = f"https://api.telegram.org/bot{token}/", 0
    print("rug checker bot running, Ctrl+C to stop")
    while True:
        try:
            ups = get(api + f"getUpdates?timeout=50&offset={offset}", timeout=60).get("result", [])
        except Exception as e:
            print("telegram error:", e); time.sleep(5); continue
        for u in ups:
            offset = u["update_id"] + 1
            msg = u.get("message") or u.get("channel_post") or {}
            text, chat = msg.get("text") or "", (msg.get("chat") or {}).get("id")
            if not chat: continue
            if text.startswith(("/start", "/help")):
                reply = "Send me a Solana token address or a pump.fun / DexScreener link and I'll check it for rug-pull red flags. 🔍"
            else:
                mint = find_mint(text)
                if not mint: continue
                try: reply = check(mint); print(f"checked {mint}: {reply.splitlines()[0]}")
                except Exception as e:   # odd API data must never crash the bot (it would re-read the same message forever)
                    print(f"check {mint} failed: {e!r}"); reply = "Something went wrong checking that token. Try again in a minute."
            data = urllib.parse.urlencode({"chat_id": chat, "text": reply, "disable_web_page_preview": "true"}).encode()
            try: urllib.request.urlopen(urllib.request.Request(api + "sendMessage", data=data, headers=UA), timeout=20)
            except Exception as e: print("send failed:", e)


if __name__ == "__main__":
    arg = sys.argv[1] if len(sys.argv) > 1 else ""
    if arg == "telegram": telegram()
    elif find_mint(arg): print(check(find_mint(arg)))
    else: sys.exit(__doc__)
