import unittest
from rugcheck_bot import find_mint, verdict

SAFE_REPORT = {"markets": [{"pubkey": "POOL", "lp": {"lpLockedPct": 100}}], "topHolders": [{"owner": "POOL", "pct": 30}, {"owner": "a", "pct": 2}],
               "totalHolders": 5000, "token": {"supply": 1000}, "creatorBalance": 0, "risks": []}
SAFE_PAIR = {"liquidity": {"usd": 200_000}, "marketCap": 1_000_000, "priceChange": {"m5": 2, "h1": 5}, "txns": {"h1": {"buys": 100, "sells": 80}}}


class Verdicts(unittest.TestCase):
    def test_safe_token_is_green(self):
        self.assertEqual(verdict(SAFE_REPORT, SAFE_PAIR)[0], "🟢")   # the pool's own 30% doesn't count as a whale

    def test_mint_authority_is_red(self):
        e, _, red, _ = verdict({**SAFE_REPORT, "mintAuthority": "DEV"}, SAFE_PAIR)
        self.assertEqual(e, "🔴"); self.assertIn("mint", red[0])

    def test_unlocked_liquidity_is_red(self):
        self.assertEqual(verdict({**SAFE_REPORT, "markets": [{"pubkey": "POOL", "lp": {"lpLockedPct": 10}}]}, SAFE_PAIR)[0], "🔴")

    def test_whales_and_few_holders(self):
        whales = {**SAFE_REPORT, "topHolders": [{"owner": f"w{i}", "pct": 5} for i in range(10)]}
        self.assertEqual(verdict(whales, SAFE_PAIR)[0], "🔴")                      # 50% in 10 wallets
        self.assertEqual(verdict({**SAFE_REPORT, "totalHolders": 50}, SAFE_PAIR)[0], "🟡")
        self.assertEqual(verdict({**whales, "totalHolders": 2_000_000}, SAFE_PAIR)[0], "🟡")   # big old coin: those are usually exchanges

    def test_tiny_liquidity_and_no_pair(self):
        self.assertEqual(verdict(SAFE_REPORT, {**SAFE_PAIR, "liquidity": {"usd": 500}})[0], "🔴")
        self.assertEqual(verdict(SAFE_REPORT, None)[0], "🟡")

    def test_find_mint_from_links(self):
        m = "DezXAZ8z7PnrnRJjz3wXBoRgixCa6xjnB7YaB1pPB263"
        self.assertEqual(find_mint(f"https://pump.fun/coin/{m}"), m)
        self.assertEqual(find_mint(f"is this safe? {m}"), m)
        self.assertIsNone(find_mint("hello"))


if __name__ == "__main__":
    unittest.main()
