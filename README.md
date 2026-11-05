# 🔍 Rug Checker

Paste a Solana token and get a **🟢 / 🟡 / 🔴 safety verdict** in plain English before you buy.

## 🤖 Try it now on Telegram: [@Big_oz_Rug_check_bot](https://t.me/Big_oz_Rug_check_bot)

Open the bot, tap **Start**, and paste any Solana token address or pump.fun / DexScreener link. Free, no sign-up.

It catches the tricks scammers use to rug people:

| Check | Why it matters |
|---|---|
| Mint authority not revoked | The dev can print more coins and dump them on you |
| Freeze authority not revoked | The dev can freeze your coins so you can't sell |
| Liquidity not locked or burned | The dev can pull the liquidity and leave you holding nothing |
| Top 10 wallets hold too much | Whales can dump on you (liquidity pool wallets are excluded) |
| Creator still holds a big bag | Same dump risk |
| Linked insider wallets | One person posing as many buyers |
| Tiny liquidity | You may not be able to sell at all |
| Crashing price or sellers piling in | It may already be getting rugged |

Free public data from [RugCheck](https://rugcheck.xyz) and [DexScreener](https://dexscreener.com). No API keys needed.
**Read-only:** it never connects to a wallet and never trades.

## Use it

Requires Python 3.9+. No packages to install.

```bash
python3 rugcheck_bot.py <token address or pump.fun / DexScreener link>
```

```
🔴 Meow Cult (Meow)
HIGH RISK: don't touch it
  🔴 liquidity $0 (you may not be able to sell)
💧 liquidity $0 · mcap $16,191 · holders 308
```

### Run your own Telegram bot

1. Message [@BotFather](https://t.me/BotFather), send `/newbot`, and copy the token it gives you.
2. Start the bot:
   ```bash
   TELEGRAM_TOKEN=123:abc python3 rugcheck_bot.py telegram
   ```
3. Send the bot a token address or link (or add it to a group). It replies with the verdict.

Keep your token secret. Don't commit it.

## Tests

```bash
python3 -m unittest -v
```

## Disclaimer

A 🟢 verdict is **not** a buy signal. It only means none of these red flags showed up. Meme coins are extremely risky. This is not financial advice.

## License

MIT
