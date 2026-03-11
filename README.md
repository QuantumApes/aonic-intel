# 🦅 Aonic Competitor Intelligence Dashboard

AI-powered competitive intelligence pipeline for [Aonic](https://aoniclife.com), a next-generation functional nutrition company. Scrapes 7 competitors across 11 data sources every Monday, generates an AI executive briefing with dynamic competitive scoring, and emails it to the founder's inbox — fully automated.

![Python](https://img.shields.io/badge/Python-3.12-blue) ![Streamlit](https://img.shields.io/badge/Streamlit-1.30+-red) ![OpenAI](https://img.shields.io/badge/OpenAI-GPT--4o-green) ![Plotly](https://img.shields.io/badge/Plotly-Charts-purple)

## What It Does

Every Monday at 6:00 AM PT, the pipeline:

1. **Scrapes 7 competitor websites** — marketing hooks, meta descriptions, H1/H2/H3 tags
2. **Pulls product pricing** — Shopify hidden JSON API first, then HTML fallback with product name + price pairing
3. **Monitors customer sentiment** — Trustpilot scores + recent review snippets
4. **Scans Reddit** — brand mentions from the last 30 days + top comment threads per post
5. **Checks Amazon** — product listings, pricing, star ratings, and review excerpts from product pages
6. **Pulls news coverage** — Google News RSS for PR, launches, media mentions
7. **Searches athlete partnerships** — targeted news queries for endorsement and sponsorship deals
8. **Queries clinical trials** — ClinicalTrials.gov REST API for relevant active studies
9. **Checks FDA enforcement** — recall and regulatory action alerts via openFDA API
10. **Detects social channels** — Instagram, TikTok, YouTube, X/Twitter, Strava, Facebook handles
11. **Calculates dynamic competitive scores** — converts scraped data into 5-dimension scores (1-10) per competitor
12. **Generates a 1,500+ word AI executive brief** via GPT-4o with per-competitor analysis, pricing comparisons, and action items
13. **Renders interactive visualizations** — Plotly radar chart, bubble chart, and logo cards with bar scores
14. **Emails the formatted newsletter** to the founder's inbox via Gmail SMTP with styled HTML

## Competitors Monitored

| Brand | Category | Key Signal |
|-------|----------|------------|
| Precision Fuel & Hydration | Customized fueling & electrolytes | Personalized sweat testing, IRONMAN partnerships |
| Raw Nutrition | Pre-workout & endurance | CBUM (Mr. Olympia) partnership, influencer army |
| Orgain | Protein shakes & recovery | Doctor-founded, mass retail (Costco/Target/Walmart) |
| Maurten | Hydrogel fueling technology | Patented hydrogel, Kipchoge marathon partnership |
| GU Energy Labs | Energy gels & chews | Pioneer since 1993, 20+ flavors, Roctane line |
| Pillar Performance | Micronutrition & recovery | Magnesium-focused, endurance athlete partnerships |
| SwissRX | Specialized endurance & recovery | Swiss-formulated, cycling/triathlon community |

## Dynamic Competitive Scoring

Scores are **calculated from live scraped data**, not hardcoded. Each dimension (1-10) is derived from:

| Dimension | Data Sources |
|-----------|-------------|
| Brand Momentum | News article count + partnership signals + Reddit upvote totals |
| Price Competitiveness | Average product price from Shopify API or HTML scraping |
| Science Credibility | ClinicalTrials.gov results + FDA enforcement status |
| Distribution Reach | Amazon listings + Shopify presence + social channel count |
| Customer Satisfaction | Trustpilot score + Reddit comment sentiment analysis |

Visualized as:
- **Radar chart** — all 7 competitors overlaid, Aonic highlighted with fill
- **Bubble chart** — Science vs Distribution, bubble size = overall score
- **Logo cards** — per-brand bar charts with visual scaling

## Quick Start

```bash
git clone https://github.com/YOUR_USERNAME/aonic-intel.git
cd aonic-intel
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Create a `.env` file:

```env
OPENAI_API_KEY=sk-your-key-here
SMTP_USER=your-email@gmail.com
SMTP_PASS=your-gmail-app-password
```

Run:

```bash
streamlit run main.py
```

## Project Structure

```
aonic-intel/
├── main.py              # Dashboard + scraping + AI newsletter + scoring + charts
├── requirements.txt     # Python dependencies
├── logos/               # Competitor brand logos for scorecard
│   ├── Precision.jpeg
│   ├── Raw.jpeg
│   ├── Orgain.png
│   ├── Maurten.png
│   ├── GU.png
│   ├── pillar.png
│   └── Swiss.png
├── .env                 # API keys & SMTP credentials (not committed)
├── .gitignore
└── README.md
```

## Data Sources

| Source | Method | Auth Required |
|--------|--------|--------------|
| Homepage scraping | Cloudscraper (anti-bot bypass) | No |
| Product pricing | Shopify JSON API + HTML fallback | No |
| Google News | RSS feed | No |
| Athlete partnerships | Google News RSS (filtered) | No |
| Trustpilot reviews | HTML scraping | No |
| Reddit mentions + comments | Public JSON API | No |
| Amazon listings + reviews | Cloudscraper | No |
| ClinicalTrials.gov | REST API v2 | No |
| FDA enforcement | openFDA API | No |
| Social media links | Homepage HTML parsing | No |

## AI Newsletter

- **Model:** GPT-4o (4096 max tokens)
- **Sections:** TL;DR, Top Threat, Pricing Landscape, News/Athletes, Science/Regulatory, Distribution, Customer Sentiment, Weekly Action Items, Competitive Scorecard
- **Delivery:** Gmail SMTP with styled HTML
- **Length:** 1,500+ words of data-driven analysis

## Production Roadmap

- [ ] GitHub Actions cron for automated Monday runs
- [ ] Claude GitHub integration for AI-assisted code reviews
- [ ] Playwright for JS-rendered scraping
- [ ] PostgreSQL for historical trend tracking
- [ ] Slack/Discord webhooks
- [ ] Week-over-week score trend charts
- [ ] Price change delta alerts
- [ ] Competitor newsletter capture

## Built With

Streamlit · Cloudscraper · BeautifulSoup · OpenAI GPT-4o · Plotly · Gmail SMTP · Reddit API · ClinicalTrials.gov · openFDA · Google News RSS · Shopify API

---

Built by Dim · March 2026
