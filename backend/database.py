"""SQLite setup and additive migrations for TRADO.

The original tables remain in place so existing accounts, lesson completions,
badges, and paper trades keep working while the learning engine grows around them.
"""

import json
import random
import sqlite3
from contextlib import contextmanager
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent / "database" / "trado.db"

CATEGORIES = [
    ("Stock", "Learn company shares, exchanges, orders, and market behavior.", "▥"),
    ("Forex", "Learn currency pairs, pips, sessions, and risk controls.", "↗"),
    ("Cryptocurrency", "Learn digital assets, wallets, exchanges, and volatility.", "₿"),
    ("Options", "Learn contracts, calls, puts, expiry, and defined risk.", "◇"),
    ("Intraday", "Learn same-day market mechanics, charts, and trading plans.", "◷"),
]

WORLD_NAMES = [
    ("Trading Foundations", "Start with the language and building blocks of trading."),
    ("Reading the Market", "Understand how prices, venues, and instruments work."),
    ("Risk & Practice", "Apply the ideas with clear limits and a learning plan."),
]

# Each entry has a concise lesson, a key fact, a scenario, and a risk-aware takeaway.
# The six stored questions are generated from these reviewed teaching points, so the
# browser only receives question text/options and never the answer key.
CURRICULUM = {
    "Stock": [
        {
            "title": "What is a stock?",
            "content": "A stock is a share of ownership in a company. Shareholders may benefit if a company grows, but the share price can also fall and dividends are never guaranteed.",
            "fact": "A stock represents a unit of ownership in a company.",
            "scenario": "Mira buys one share of a listed company and later sees its market price change.",
            "scenario_answer": "She owns a small part of the company, and the share's market price can rise or fall.",
            "risk": "A share can lose value, including the full amount invested if the company fails.",
            "safe": "Learn what ownership means and consider the possibility of loss before discussing a stock.",
            "takeaway": "A stock is company ownership, not a guaranteed return or a bank deposit.",
            "minutes": 5,
        },
        {
            "title": "Understanding risk and return",
            "content": "Risk is uncertainty about outcomes, including the chance of loss. A possible higher return usually comes with uncertainty; diversification can spread exposure but cannot remove risk.",
            "fact": "Diversification spreads exposure across holdings but cannot guarantee a profit or remove every risk.",
            "scenario": "A learner divides a hypothetical portfolio among several unrelated companies instead of one company.",
            "scenario_answer": "The learner has spread company-specific exposure, but the whole portfolio can still lose value.",
            "risk": "Concentrating everything in one asset can make one setback affect the whole amount.",
            "safe": "Compare possible losses as well as possible returns, and never treat diversification as a guarantee.",
            "takeaway": "Risk and return are uncertain; spreading exposure can help manage concentration risk.",
            "minutes": 6,
        },
        {
            "title": "Stock exchanges",
            "content": "An exchange is a marketplace with rules where eligible buyers and sellers can meet. A broker provides a route for a customer to send orders; the exchange and broker have different roles.",
            "fact": "A stock exchange is a marketplace where eligible buy and sell orders can be matched under its rules.",
            "scenario": "A learner sends an order through a broker, and the order is routed to a marketplace.",
            "scenario_answer": "The broker provides access while the exchange operates the marketplace where orders may match.",
            "risk": "Trading hours, halts, fees, and order rules can affect whether and when an order executes.",
            "safe": "Check the venue's rules and distinguish the broker's service from the exchange's marketplace.",
            "takeaway": "An exchange organizes a marketplace; it does not promise a particular price or outcome.",
            "minutes": 5,
        },
        {
            "title": "Orders and market prices",
            "content": "A market order seeks execution promptly at available prices, which may differ from the last price shown. A limit order sets a maximum buy price or minimum sell price, but may not execute.",
            "fact": "A limit order controls the worst acceptable price but does not guarantee execution.",
            "scenario": "A share is quoted at ₹100 and a learner places a buy limit at ₹95.",
            "scenario_answer": "The order can wait unfilled unless sellers are available at ₹95 or lower.",
            "risk": "A fast-moving or thin market can produce a different execution price or leave a limit order unfilled.",
            "safe": "Understand the order type and its trade-off between execution certainty and price control.",
            "takeaway": "A displayed last price is not a promise that an order will execute at that price.",
            "minutes": 6,
        },
        {
            "title": "Bull and bear markets",
            "content": "Bull and bear describe broad market direction or sentiment over a period, not a promise about the next move. Short-term prices can move against a wider trend.",
            "fact": "A bull market generally describes a sustained rise in prices, while a bear market generally describes a sustained decline.",
            "scenario": "A broad market has been making higher highs over an extended period, but falls on one trading day.",
            "scenario_answer": "The wider trend may still be bullish; a single down day does not define the whole market.",
            "risk": "Trend labels are descriptions, not reliable predictions of future prices.",
            "safe": "Use trend terms to describe observed history and keep uncertainty in every plan.",
            "takeaway": "Bull and bear describe broad direction; neither guarantees what happens next.",
            "minutes": 5,
        },
    ],
    "Forex": [
        {
            "title": "Introduction to Forex",
            "content": "Forex is the market for exchanging currencies. A quoted pair compares a base currency with a quote currency; buying the pair means buying the base and selling the quote currency.",
            "fact": "In EUR/USD, EUR is the base currency and USD is the quote currency.",
            "scenario": "A learner buys EUR/USD in a practice example.",
            "scenario_answer": "The learner is buying euros and selling US dollars in the pair.",
            "risk": "Exchange rates move and a currency position can lose value; forex products may also use leverage.",
            "safe": "Read both currency codes and identify which currency is base before interpreting a quote.",
            "takeaway": "A forex pair shows the value of one currency relative to another.",
            "minutes": 5,
        },
        {
            "title": "Pips and leverage",
            "content": "A pip is a conventional unit for describing a small exchange-rate move, with conventions that can vary by pair. Leverage controls a larger exposure with less deposited capital and magnifies both gains and losses.",
            "fact": "Leverage magnifies both gains and losses relative to the capital committed.",
            "scenario": "A small currency move affects a leveraged practice position more than an unleveraged position of the same deposit.",
            "scenario_answer": "Leverage magnifies the position's gains and losses; it does not make the move safer.",
            "risk": "A leveraged loss can be large relative to the initial margin and may exceed expectations.",
            "safe": "Learn the contract size, pip convention, and maximum possible loss before using leverage in a simulation.",
            "takeaway": "A pip describes price movement; leverage magnifies exposure in either direction.",
            "minutes": 6,
        },
        {
            "title": "Currency pairs and quotes",
            "content": "The first currency in a pair is the base and the second is the quote. A quote of 1.08 for EUR/USD means one euro is priced at 1.08 US dollars at that quoted time.",
            "fact": "A EUR/USD quote expresses how many US dollars are quoted for one euro.",
            "scenario": "EUR/USD is shown as 1.08 in an illustrative lesson chart.",
            "scenario_answer": "The quote means one euro is priced at 1.08 US dollars in that example.",
            "risk": "A quote can change quickly, and a simulated quote is not a live executable price.",
            "safe": "Check the pair order, quote timestamp, and whether a price is simulated or live.",
            "takeaway": "The base currency is measured in units of the quote currency.",
            "minutes": 5,
        },
        {
            "title": "Spreads and trading sessions",
            "content": "The spread is the difference between a quoted ask and bid. Liquidity and spreads can change across instruments and sessions; lower liquidity may make execution harder or more costly.",
            "fact": "The bid-ask spread is the difference between the ask price and the bid price.",
            "scenario": "A practice quote shows EUR/USD bid 1.1000 and ask 1.1002.",
            "scenario_answer": "The displayed spread is 0.0002, the ask minus the bid.",
            "risk": "Spreads may widen when liquidity is low or markets are moving quickly.",
            "safe": "Check spread and liquidity conditions instead of assuming they stay constant through every session.",
            "takeaway": "Session activity can change liquidity and the cost of entering or exiting a position.",
            "minutes": 6,
        },
        {
            "title": "Forex risk controls",
            "content": "A risk plan can set a maximum position size and define when a learner would exit a hypothetical trade. Stop orders can help manage a plan but may execute at a different price in fast markets.",
            "fact": "Position size and exit rules help define exposure but cannot remove market risk.",
            "scenario": "A learner sets a hypothetical exit level before placing a practice order.",
            "scenario_answer": "The learner has made an exit rule explicit, though execution may differ in a fast market.",
            "risk": "Leverage, gaps, and changing liquidity can make realized losses differ from planned losses.",
            "safe": "Set a small, defined practice exposure and review how the order behaves under different conditions.",
            "takeaway": "Risk controls organize decisions; they do not guarantee a maximum loss in every market.",
            "minutes": 6,
        },
    ],
    "Cryptocurrency": [
        {
            "title": "What is cryptocurrency?",
            "content": "Cryptocurrency is a digital asset whose records or transfers use cryptographic systems. Designs vary, and prices may be volatile; the label does not mean an asset is safe or regulated everywhere.",
            "fact": "Cryptocurrency is a digital asset, and its design and risks vary by project.",
            "scenario": "A learner reads that a token uses cryptography and is listed on an exchange.",
            "scenario_answer": "Those facts do not by themselves prove the token is safe, valuable, or suitable.",
            "risk": "Crypto assets can be highly volatile and may involve technology, custody, and regulatory risks.",
            "safe": "Research the asset's design and risks; never treat a listing or technology label as a safety guarantee.",
            "takeaway": "A digital asset can be useful to study while still carrying substantial uncertainty.",
            "minutes": 5,
        },
        {
            "title": "Wallets and volatility",
            "content": "A crypto wallet manages keys used to authorize access to assets recorded on a network. A wallet does not simply store coins like a physical purse; losing control of keys can mean losing access.",
            "fact": "A wallet manages cryptographic keys that control access to assets recorded on a network.",
            "scenario": "A learner loses the private key for a self-custody wallet.",
            "scenario_answer": "The learner may lose access because the key is needed to authorize control of the assets.",
            "risk": "Lost or stolen keys may be difficult or impossible to recover, and prices can change sharply.",
            "safe": "Protect recovery information privately and understand custody responsibilities before using a wallet.",
            "takeaway": "Wallet security is about protecting access keys, not just choosing an app.",
            "minutes": 6,
        },
        {
            "title": "Blockchain basics",
            "content": "A blockchain is a type of shared ledger that groups records into linked blocks. Networks differ in governance, validation, permissions, and security; the word blockchain alone says little about investment quality.",
            "fact": "A blockchain records data in linked blocks, with network rules determining how records are validated.",
            "scenario": "A network's validators confirm a proposed transaction under that network's protocol.",
            "scenario_answer": "The network rules determine whether the transaction is accepted into the shared ledger.",
            "risk": "Software bugs, network design, congestion, and governance can affect how a blockchain works.",
            "safe": "Study the network's validation and governance model instead of assuming every blockchain is identical.",
            "takeaway": "Blockchain describes a record-keeping design, not a promise of profit or security.",
            "minutes": 5,
        },
        {
            "title": "Exchanges and custody",
            "content": "A custodial exchange controls assets or keys on a customer's behalf; self-custody leaves key management with the user. Each approach has operational, security, and recovery trade-offs.",
            "fact": "Custodial services manage access on a user's behalf, while self-custody places key management with the user.",
            "scenario": "An exchange holds the keys for assets shown in a customer's account.",
            "scenario_answer": "The customer is relying on a custodial service and its operations and safeguards.",
            "risk": "Platform failure, account compromise, or key loss can affect access to assets.",
            "safe": "Understand who controls the keys and what recovery or withdrawal options exist.",
            "takeaway": "Custody is a decision about who controls access and bears operational responsibilities.",
            "minutes": 6,
        },
        {
            "title": "Crypto risk controls",
            "content": "Crypto markets can move sharply and operate across venues with different protections and liquidity. A learning plan should consider position size, custody, and the possibility of total loss.",
            "fact": "Crypto risk can include price volatility, custody failure, security incidents, and changing rules.",
            "scenario": "A token's price falls sharply while a learner cannot withdraw from a venue undergoing an outage.",
            "scenario_answer": "Price risk and platform access risk can occur at the same time.",
            "risk": "A volatile asset or failed service can result in a substantial or total loss.",
            "safe": "Use simulated examples, keep exposure limited, and study custody and platform risks separately.",
            "takeaway": "Risk planning must include both the asset's price and the way it is held or accessed.",
            "minutes": 6,
        },
    ],
    "Options": [
        {
            "title": "Options basics",
            "content": "An option is a contract. The buyer receives a right, not an obligation, under the contract terms; the seller takes on an obligation if assigned. Contract specifications matter.",
            "fact": "An option buyer has a right, not an obligation, while the option seller has contractual obligations.",
            "scenario": "A learner buys a call option contract for a premium and does not exercise it.",
            "scenario_answer": "The buyer can let the right expire, while the premium paid may be lost.",
            "risk": "Options can expire worthless, and sellers can face substantial obligations and losses.",
            "safe": "Read the contract size, strike, expiry, and exercise rules before discussing an option payoff.",
            "takeaway": "An option is a contract with defined terms, not simply a leveraged share.",
            "minutes": 6,
        },
        {
            "title": "Calls, puts and premium",
            "content": "A call generally gives its buyer the right to buy the underlying at a strike; a put generally gives the right to sell. Buyers pay a premium, which is at risk if the option expires worthless.",
            "fact": "A call generally gives the buyer a right to buy, and a put gives the buyer a right to sell at the strike under its terms.",
            "scenario": "A learner buys a put option and pays a premium.",
            "scenario_answer": "The put gives a right to sell under the contract terms; the premium can be lost.",
            "risk": "The option buyer can lose the entire premium, while the seller has a different risk profile.",
            "safe": "Identify whether a contract is a call or put and who is buyer or seller before evaluating it.",
            "takeaway": "Calls, puts, and premiums describe contract rights and costs, not guaranteed outcomes.",
            "minutes": 6,
        },
        {
            "title": "Expiry and moneyness",
            "content": "Moneyness compares the underlying price with an option's strike. Expiry is the contract's end date; all else equal, less time to expiry can reduce an option's time value.",
            "fact": "Moneyness compares an option's strike with the underlying price, while expiry marks when the contract ends.",
            "scenario": "A call has a strike of 100 and the underlying is at 105 before expiry.",
            "scenario_answer": "The call is in the money by 5 before costs, although that does not determine total profitability.",
            "risk": "An option's value can change with price, time, volatility, and contract terms.",
            "safe": "Check the underlying, strike, expiry, and premium together rather than focusing on one number.",
            "takeaway": "An option can be in the money and still fail to produce a net profit after its premium and costs.",
            "minutes": 6,
        },
        {
            "title": "Option payoff basics",
            "content": "At expiry, a call's intrinsic value is based on the amount the underlying is above its strike; a put's is based on the amount it is below. Net profit must also account for premium and costs.",
            "fact": "A long call's intrinsic value at expiry is max(underlying price minus strike, zero), before premium and costs.",
            "scenario": "At expiry a call strike is 50 and the underlying is 55; ignore contract multiplier for the example.",
            "scenario_answer": "Its intrinsic value is 5, but net profit also depends on premium and costs.",
            "risk": "Confusing intrinsic value with net profit can make an option look more profitable than it is.",
            "safe": "Subtract the premium and relevant costs when reviewing a buyer's payoff.",
            "takeaway": "A payoff diagram needs the contract terms and premium to explain profit or loss.",
            "minutes": 7,
        },
        {
            "title": "Options risk",
            "content": "Risk depends on whether a position is bought or written and on its structure. A long option can lose its premium; an uncovered short option can have very large, and for some calls theoretically unlimited, risk.",
            "fact": "A long option buyer may lose the premium, while an uncovered option seller may face much larger losses.",
            "scenario": "A learner sells an uncovered call without understanding the contract exposure.",
            "scenario_answer": "The position may face very large losses if the underlying rises sharply.",
            "risk": "Option losses can be large relative to the cash initially received or posted.",
            "safe": "Study worst-case payoff and assignment obligations before considering any options structure.",
            "takeaway": "Options risk changes with the position structure; the premium alone does not describe every risk.",
            "minutes": 7,
        },
    ],
    "Intraday": [
        {
            "title": "What is intraday trading?",
            "content": "Intraday trading generally means opening and closing a position within the same trading day. It can involve rapid decisions, transaction costs, and substantial risk; frequent trading does not guarantee success.",
            "fact": "Intraday trading generally opens and closes positions within the same trading day.",
            "scenario": "A learner opens and closes a hypothetical share position before that day's session ends.",
            "scenario_answer": "That is an intraday position in this example.",
            "risk": "Frequent decisions, costs, and quick price moves can increase losses as well as stress.",
            "safe": "Practise with simulated data and a written plan before studying real-world intraday products.",
            "takeaway": "Intraday describes the holding period, not a guarantee about the result.",
            "minutes": 5,
        },
        {
            "title": "Stop-loss and position sizing",
            "content": "Position sizing sets how much exposure a hypothetical trade has. A stop-loss expresses an exit rule, but a fast market or gap can execute beyond the stop price.",
            "fact": "Position size determines the amount of exposure, while a stop-loss is an exit instruction that may not fill at its trigger price.",
            "scenario": "A learner reduces the number of units in a practice trade while keeping the same stop distance.",
            "scenario_answer": "The smaller position reduces the amount exposed to that price move.",
            "risk": "A stop does not guarantee an exact exit price, especially during gaps or fast moves.",
            "safe": "Define exposure before entering a simulation and include slippage as a possible outcome.",
            "takeaway": "Position sizing controls exposure; an exit instruction cannot eliminate market risk.",
            "minutes": 6,
        },
        {
            "title": "Sessions and liquidity",
            "content": "Market activity changes throughout a session. Liquidity describes how readily trades can occur without a large price impact; it varies by instrument, venue, and time.",
            "fact": "Liquidity is the ability to trade with limited delay or price impact, and it can change over time.",
            "scenario": "A small order moves a thinly traded instrument's price more than the same order moves a highly traded one.",
            "scenario_answer": "The thinner market has lower liquidity and greater price impact in this example.",
            "risk": "Low liquidity can widen spreads and make it harder to exit at an expected price.",
            "safe": "Review typical volume, spread, and session conditions in historical or simulated examples.",
            "takeaway": "Liquidity is not constant; execution conditions can change during the day.",
            "minutes": 5,
        },
        {
            "title": "Reading intraday charts",
            "content": "A candle summarizes open, high, low, and close for a chosen time interval. A chart shows historical or simulated observations; patterns do not guarantee the next move.",
            "fact": "A candlestick records the open, high, low, and close for its selected time interval.",
            "scenario": "An illustrative five-minute candle has an open of 100, high 104, low 98, and close 103.",
            "scenario_answer": "The interval's price range was 98 to 104 and it closed above its open.",
            "risk": "A chart pattern can fail, and simulated or historical prices are not live instructions.",
            "safe": "Check the chart's time interval and label simulated examples clearly before interpreting a candle.",
            "takeaway": "Candles summarize past price action; they do not predict a guaranteed future move.",
            "minutes": 6,
        },
        {
            "title": "Trading plans and psychology",
            "content": "A learning plan can state what to observe, how much simulated risk to allow, and when to stop for the day. A journal helps review decisions without treating one outcome as proof of skill.",
            "fact": "A written plan and journal help make decisions reviewable, but they cannot guarantee a profitable result.",
            "scenario": "After a loss, a learner pauses and records whether the practice plan was followed.",
            "scenario_answer": "The learner is reviewing process instead of immediately increasing risk to recover the loss.",
            "risk": "Emotional decisions after wins or losses can lead to impulsive or oversized positions.",
            "safe": "Set a stopping rule and review a series of decisions rather than chasing a single outcome.",
            "takeaway": "Good process supports learning; it does not promise profits.",
            "minutes": 6,
        },
    ],
}


@contextmanager
def get_db():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH, timeout=10)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA busy_timeout = 10000")
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def _base_schema(db):
    db.executescript(
        """
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            xp INTEGER NOT NULL DEFAULT 0,
            trado_cash REAL NOT NULL DEFAULT 10000,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS lessons (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            category TEXT NOT NULL,
            title TEXT NOT NULL,
            level INTEGER NOT NULL,
            content TEXT NOT NULL,
            UNIQUE(category, level)
        );
        CREATE TABLE IF NOT EXISTS quizzes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            lesson_id INTEGER NOT NULL REFERENCES lessons(id) ON DELETE CASCADE,
            question TEXT NOT NULL,
            option_a TEXT NOT NULL,
            option_b TEXT NOT NULL,
            option_c TEXT NOT NULL,
            option_d TEXT NOT NULL,
            correct_option TEXT NOT NULL,
            explanation TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS user_progress (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            lesson_id INTEGER NOT NULL REFERENCES lessons(id) ON DELETE CASCADE,
            score INTEGER NOT NULL DEFAULT 0,
            completed_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(user_id, lesson_id)
        );
        CREATE TABLE IF NOT EXISTS user_rewards (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            badge TEXT NOT NULL,
            awarded_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(user_id, badge)
        );
        CREATE TABLE IF NOT EXISTS virtual_trades (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            symbol TEXT NOT NULL,
            side TEXT NOT NULL CHECK(side IN ('BUY','SELL')),
            quantity REAL NOT NULL,
            price REAL NOT NULL,
            total REAL NOT NULL,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );
        """
    )


def _learning_schema(db):
    db.executescript(
        """
        CREATE TABLE IF NOT EXISTS trading_categories (
            name TEXT PRIMARY KEY,
            description TEXT NOT NULL,
            icon TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS user_settings (
            user_id INTEGER PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
            daily_goal_minutes INTEGER NOT NULL DEFAULT 10 CHECK(daily_goal_minutes IN (5,10,15,20,30)),
            preferred_language TEXT NOT NULL DEFAULT 'en',
            timezone TEXT NOT NULL DEFAULT 'UTC',
            onboarding_complete INTEGER NOT NULL DEFAULT 0 CHECK(onboarding_complete IN (0,1)),
            updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS user_categories (
            user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            category_name TEXT NOT NULL REFERENCES trading_categories(name) ON DELETE CASCADE,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY(user_id, category_name)
        );
        CREATE TABLE IF NOT EXISTS learning_worlds (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            category_name TEXT NOT NULL REFERENCES trading_categories(name) ON DELETE CASCADE,
            title TEXT NOT NULL,
            description TEXT NOT NULL,
            sequence_order INTEGER NOT NULL,
            UNIQUE(category_name, sequence_order)
        );
        CREATE TABLE IF NOT EXISTS level_metadata (
            lesson_id INTEGER PRIMARY KEY REFERENCES lessons(id) ON DELETE CASCADE,
            world_id INTEGER NOT NULL REFERENCES learning_worlds(id) ON DELETE CASCADE,
            description TEXT NOT NULL,
            estimated_minutes INTEGER NOT NULL DEFAULT 5,
            reward_xp INTEGER NOT NULL DEFAULT 50,
            reward_coins INTEGER NOT NULL DEFAULT 20
        );
        CREATE TABLE IF NOT EXISTS questions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            lesson_id INTEGER NOT NULL REFERENCES lessons(id) ON DELETE CASCADE,
            question_text TEXT NOT NULL,
            question_type TEXT NOT NULL DEFAULT 'multiple_choice',
            options_json TEXT NOT NULL,
            correct_option TEXT NOT NULL,
            explanation TEXT NOT NULL,
            sequence_order INTEGER NOT NULL,
            UNIQUE(lesson_id, sequence_order)
        );
        CREATE TABLE IF NOT EXISTS level_progress (
            user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            lesson_id INTEGER NOT NULL REFERENCES lessons(id) ON DELETE CASCADE,
            current_question INTEGER NOT NULL DEFAULT 1,
            completion_status TEXT NOT NULL DEFAULT 'in_progress' CHECK(completion_status IN ('in_progress','completed')),
            completed_at TEXT,
            stars INTEGER NOT NULL DEFAULT 0,
            PRIMARY KEY(user_id, lesson_id)
        );
        CREATE TABLE IF NOT EXISTS question_state (
            user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            question_id INTEGER NOT NULL REFERENCES questions(id) ON DELETE CASCADE,
            attempt_count INTEGER NOT NULL DEFAULT 0,
            first_attempt_correct INTEGER CHECK(first_attempt_correct IN (0,1)),
            mastered INTEGER NOT NULL DEFAULT 0 CHECK(mastered IN (0,1)),
            life_penalty_applied INTEGER NOT NULL DEFAULT 0 CHECK(life_penalty_applied IN (0,1)),
            updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY(user_id, question_id)
        );
        CREATE TABLE IF NOT EXISTS question_attempts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            question_id INTEGER NOT NULL REFERENCES questions(id) ON DELETE CASCADE,
            selected_answer TEXT NOT NULL,
            is_correct INTEGER NOT NULL CHECK(is_correct IN (0,1)),
            attempt_number INTEGER NOT NULL,
            life_lost INTEGER NOT NULL DEFAULT 0 CHECK(life_lost IN (0,1)),
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS user_lives (
            user_id INTEGER PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
            remaining_lives INTEGER NOT NULL DEFAULT 5 CHECK(remaining_lives BETWEEN 0 AND 5),
            last_regeneration_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS user_wallet (
            user_id INTEGER PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
            coins INTEGER NOT NULL DEFAULT 0 CHECK(coins >= 0)
        );
        CREATE TABLE IF NOT EXISTS reward_transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            reward_type TEXT NOT NULL CHECK(reward_type IN ('xp','coins')),
            amount INTEGER NOT NULL,
            source TEXT NOT NULL,
            source_id TEXT NOT NULL,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(user_id, reward_type, source, source_id)
        );
        CREATE TABLE IF NOT EXISTS user_streaks (
            user_id INTEGER PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
            current_streak INTEGER NOT NULL DEFAULT 0,
            longest_streak INTEGER NOT NULL DEFAULT 0,
            last_activity_date TEXT
        );
        CREATE TABLE IF NOT EXISTS daily_activity (
            user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            activity_date TEXT NOT NULL,
            active_seconds INTEGER NOT NULL DEFAULT 0,
            xp_earned INTEGER NOT NULL DEFAULT 0,
            lessons_completed INTEGER NOT NULL DEFAULT 0,
            PRIMARY KEY(user_id, activity_date)
        );
        CREATE TABLE IF NOT EXISTS activity_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            event_id TEXT NOT NULL,
            activity_date TEXT NOT NULL,
            seconds INTEGER NOT NULL CHECK(seconds BETWEEN 1 AND 45),
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(user_id, event_id)
        );
        CREATE TABLE IF NOT EXISTS achievements (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            slug TEXT NOT NULL UNIQUE,
            title TEXT NOT NULL,
            description TEXT NOT NULL,
            icon TEXT NOT NULL,
            condition_type TEXT NOT NULL,
            condition_value INTEGER NOT NULL
        );
        CREATE TABLE IF NOT EXISTS user_achievements (
            user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            achievement_id INTEGER NOT NULL REFERENCES achievements(id) ON DELETE CASCADE,
            unlocked_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY(user_id, achievement_id)
        );
        CREATE TABLE IF NOT EXISTS notifications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            title TEXT NOT NULL,
            message TEXT NOT NULL,
            notification_type TEXT NOT NULL,
            is_read INTEGER NOT NULL DEFAULT 0 CHECK(is_read IN (0,1)),
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );
        CREATE INDEX IF NOT EXISTS idx_levels_category ON lessons(category, level);
        CREATE INDEX IF NOT EXISTS idx_questions_level ON questions(lesson_id, sequence_order);
        CREATE INDEX IF NOT EXISTS idx_attempts_user ON question_attempts(user_id, created_at);
        CREATE INDEX IF NOT EXISTS idx_rewards_user ON reward_transactions(user_id, created_at);
        CREATE INDEX IF NOT EXISTS idx_notifications_user ON notifications(user_id, is_read, created_at);
        CREATE INDEX IF NOT EXISTS idx_daily_activity_date ON daily_activity(user_id, activity_date);
        """
    )


def _question_rows(entry, category, level):
    wrong = [
        "It guarantees a positive result regardless of what the market does.",
        "It removes every possible risk once a learner understands the term.",
        "It predicts the next price move with certainty.",
    ]
    specifications = [
        (f"Which statement best describes {entry['title'].lower()}?", entry["fact"], entry["fact"]),
        (f"Scenario: {entry['scenario']} What is the best interpretation?", entry["scenario_answer"], entry["scenario_answer"]),
        (f"Which risk should a learner remember about {entry['title'].lower()}?", entry["risk"], entry["risk"]),
        ("Which practice best supports careful learning here?", entry["safe"], entry["safe"]),
        ("Which takeaway is accurate?", entry["takeaway"], entry["takeaway"]),
        ("Choose the accurate statement.", entry["fact"], entry["fact"]),
    ]
    rows = []
    for order, (prompt, correct_text, explanation) in enumerate(specifications, 1):
        if order == 6:
            distractors = [
                "A learner can ignore the contract or market conditions once the idea is familiar.",
                "Past examples guarantee the same result in a later market.",
                "Risk disappears whenever a decision follows a written plan.",
            ]
        else:
            distractors = wrong[:]
        options = [correct_text, *distractors]
        random.Random(f"trado:{category}:{level}:{order}").shuffle(options)
        correct_letter = "ABCD"[options.index(correct_text)]
        rows.append((prompt, options, correct_letter, explanation))
    return rows


ACHIEVEMENTS = [
    ("first_level", "First Step", "Complete your first learning level.", "✦", "levels", 1),
    ("three_levels", "Quick Learner", "Complete three learning levels.", "⚡", "levels", 3),
    ("three_categories", "Trading Explorer", "Learn in three trading categories.", "◇", "categories", 3),
    ("seven_day_streak", "Consistency Champion", "Build a seven-day learning streak.", "☀", "streak", 7),
    ("fifty_questions", "Knowledge Master", "Master fifty learning questions.", "★", "questions", 50),
]


def seed_curriculum(db):
    for name, description, icon in CATEGORIES:
        db.execute(
            "INSERT OR IGNORE INTO trading_categories(name,description,icon) VALUES(?,?,?)",
            (name, description, icon),
        )

    for category, entries in CURRICULUM.items():
        world_ids = {}
        for index, (title, description) in enumerate(WORLD_NAMES, 1):
            db.execute(
                "INSERT OR IGNORE INTO learning_worlds(category_name,title,description,sequence_order) VALUES(?,?,?,?)",
                (category, title, description, index),
            )
            row = db.execute(
                "SELECT id FROM learning_worlds WHERE category_name=? AND sequence_order=?",
                (category, index),
            ).fetchone()
            world_ids[index] = row["id"]

        for level, entry in enumerate(entries, 1):
            existing = db.execute(
                "SELECT id FROM lessons WHERE category=? AND level=?", (category, level)
            ).fetchone()
            if existing:
                lesson_id = existing["id"]
            else:
                cur = db.execute(
                    "INSERT INTO lessons(category,title,level,content) VALUES(?,?,?,?)",
                    (category, entry["title"], level, entry["content"]),
                )
                lesson_id = cur.lastrowid

            world_order = min((level - 1) // 2 + 1, 3)
            db.execute(
                "INSERT OR IGNORE INTO level_metadata(lesson_id,world_id,description,estimated_minutes,reward_xp,reward_coins) VALUES(?,?,?,?,?,?)",
                (lesson_id, world_ids[world_order], entry["takeaway"], entry["minutes"], 50, 20),
            )

            if db.execute("SELECT COUNT(*) FROM questions WHERE lesson_id=?", (lesson_id,)).fetchone()[0] == 0:
                for order, (prompt, options, answer, explanation) in enumerate(
                    _question_rows(entry, category, level), 1
                ):
                    db.execute(
                        "INSERT INTO questions(lesson_id,question_text,options_json,correct_option,explanation,sequence_order) VALUES(?,?,?,?,?,?)",
                        (lesson_id, prompt, json.dumps(options, ensure_ascii=False), answer, explanation, order),
                    )

    for slug, title, description, icon, condition_type, condition_value in ACHIEVEMENTS:
        db.execute(
            "INSERT OR IGNORE INTO achievements(slug,title,description,icon,condition_type,condition_value) VALUES(?,?,?,?,?,?)",
            (slug, title, description, icon, condition_type, condition_value),
        )


def ensure_user_records(db, user_id, *, is_new=False):
    db.execute(
        "INSERT OR IGNORE INTO user_settings(user_id,onboarding_complete) VALUES(?,?)",
        (user_id, 0 if is_new else 1),
    )
    db.execute("INSERT OR IGNORE INTO user_wallet(user_id) VALUES(?)", (user_id,))
    db.execute("INSERT OR IGNORE INTO user_lives(user_id) VALUES(?)", (user_id,))
    db.execute("INSERT OR IGNORE INTO user_streaks(user_id) VALUES(?)", (user_id,))
    if not is_new:
        db.execute(
            "INSERT OR IGNORE INTO user_categories(user_id,category_name) SELECT ?,name FROM trading_categories",
            (user_id,),
        )


def init_db():
    with get_db() as db:
        _base_schema(db)
        _learning_schema(db)
        seed_curriculum(db)

        # Existing accounts go straight to the dashboard with sensible defaults.
        # Newly registered accounts opt into onboarding in ensure_user_records().
        users = db.execute("SELECT id FROM users").fetchall()
        for user in users:
            user_id = user["id"]
            had_settings = db.execute(
                "SELECT 1 FROM user_settings WHERE user_id=?", (user_id,)
            ).fetchone()
            ensure_user_records(db, user_id, is_new=False)
            if not had_settings:
                db.execute(
                    "INSERT OR IGNORE INTO user_categories(user_id,category_name) SELECT ?,name FROM trading_categories",
                    (user_id,),
                )

        # Carry historical completions into the new roadmap without awarding them again.
        db.execute(
            """INSERT OR IGNORE INTO level_progress(user_id,lesson_id,current_question,completion_status,completed_at,stars)
               SELECT user_id,lesson_id,7,'completed',completed_at,1 FROM user_progress"""
        )


def create_user_records(user_id):
    with get_db() as db:
        ensure_user_records(db, user_id, is_new=True)
