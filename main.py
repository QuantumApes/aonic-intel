import streamlit as st
import json
import re
import requests
import cloudscraper
import os
from bs4 import BeautifulSoup
from openai import OpenAI
from dotenv import find_dotenv, load_dotenv
from datetime import datetime
from urllib.parse import quote_plus

# 1. PAGE SETUP
st.set_page_config(page_title="Aonic Intel", layout="wide")
st.title("🦅 Aonic Competitor Intelligence Dashboard")
st.markdown("**Automated Workflow:** Scheduled via GitHub Actions to run every Monday at 06:00 AM PT.")
st.write("---")

# 2. INITIALIZE API KEYS
load_dotenv(find_dotenv())
api_key = os.getenv("OPENAI_API_KEY")

if not api_key:
    st.error("🚨 API Key not found! Ensure '.env' contains OPENAI_API_KEY=sk-...")
    st.stop()

client = OpenAI(api_key=api_key)

# ─── SCRAPING FUNCTIONS ─────────────────────────────────────────────────────

def scrape_competitor_html(url):
    """Scrapes marketing hooks + meta description using Cloudscraper."""
    scraper = cloudscraper.create_scraper(browser={'browser': 'chrome', 'platform': 'windows', 'mobile': False})
    try:
        response = scraper.get(url, timeout=12)
        soup = BeautifulSoup(response.text, 'html.parser')
        hooks = []
        for h in soup.find_all(['h1', 'h2', 'h3'])[:6]:
            text = h.get_text(strip=True)
            if len(text) > 10 and len(text) < 200:
                hooks.append(text)
        meta = soup.find("meta", {"name": "description"})
        meta_text = meta["content"][:200] if meta and meta.get("content") else ""
        result = " | ".join(hooks[:4])
        if meta_text and meta_text not in result:
            result = f"{meta_text} || {result}"
        return result if result else "HTML extraction blocked."
    except:
        return "Connection timeout."


def scrape_shopify_data(url):
    """Hits the hidden Shopify API for quantitative pricing data."""
    api_url = f"{url}/products.json?limit=5"
    try:
        response = requests.get(api_url, timeout=5)
        if response.status_code == 200:
            data = response.json()
            products = []
            for p in data.get('products', []):
                title = p.get('title', 'Unknown')
                price = p['variants'][0]['price'] if p.get('variants') else 'N/A'
                prod_type = p.get('product_type', '')
                entry = f"{title} (${price})"
                if prod_type:
                    entry += f" [{prod_type}]"
                products.append(entry)
            return products if products else None
        return None
    except:
        return None


def scrape_pricing_fallback(url):
    """For non-Shopify sites: scrape visible pricing from product pages."""
    scraper = cloudscraper.create_scraper(browser={'browser': 'chrome', 'platform': 'windows', 'mobile': False})
    paths_to_try = ["/collections/all", "/products", "/shop", "/supplements",
                    "/collections", "/pages/shop", "/store", "/fuel", "/nutrition"]
    try:
        for path in paths_to_try:
            try:
                resp = scraper.get(url + path, timeout=8)
                if resp.status_code == 200:
                    soup = BeautifulSoup(resp.text, 'html.parser')
                    prices = []
                    for selector in ['[class*="price"]', '[class*="Price"]', '[data-price]',
                                     '.money', '.product-price', '[class*="cost"]']:
                        for el in soup.select(selector)[:8]:
                            text = el.get_text(strip=True)
                            if '$' in text and len(text) < 40:
                                prices.append(text)
                    products = []
                    for card in soup.select('[class*="product"]')[:5]:
                        title_el = card.select_one('[class*="title"], [class*="name"], h2, h3, h4')
                        price_el = card.select_one('[class*="price"], .money')
                        if title_el and price_el:
                            t = title_el.get_text(strip=True)[:60]
                            p = price_el.get_text(strip=True)
                            if '$' in p:
                                products.append(f"{t} ({p})")
                    if products:
                        return products[:5]
                    if prices:
                        return list(dict.fromkeys(prices))[:5]
            except:
                continue
        return ["Pricing not extractable (JS-rendered)."]
    except:
        return ["Pricing scrape failed."]


def scrape_news_coverage(search_term):
    """Scrape recent news via Google News RSS."""
    try:
        encoded = quote_plus(search_term)
        rss_url = f"https://news.google.com/rss/search?q={encoded}&hl=en-US&gl=US&ceid=US:en"
        resp = requests.get(rss_url, timeout=8, headers={
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)"
        })
        if resp.status_code == 200:
            soup = BeautifulSoup(resp.text, 'xml')
            items = soup.find_all('item')[:6]
            headlines = []
            for item in items:
                title = item.find('title').text if item.find('title') else ""
                pub_date = item.find('pubDate').text[:16] if item.find('pubDate') else ""
                source = item.find('source').text if item.find('source') else ""
                if title:
                    headlines.append({"title": title, "source": source, "date": pub_date})
            return headlines if headlines else [{"title": "No recent coverage found.", "source": "", "date": ""}]
        return [{"title": "News feed unavailable.", "source": "", "date": ""}]
    except:
        return [{"title": "News scrape failed.", "source": "", "date": ""}]


def scrape_athlete_partnerships(search_term):
    """Search for recent athlete/team sponsorship and endorsement deals."""
    try:
        encoded = quote_plus(f"{search_term} athlete sponsor partnership endorsement 2025 2026")
        rss_url = f"https://news.google.com/rss/search?q={encoded}&hl=en-US&gl=US&ceid=US:en"
        resp = requests.get(rss_url, timeout=8, headers={
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)"
        })
        if resp.status_code == 200:
            soup = BeautifulSoup(resp.text, 'xml')
            items = soup.find_all('item')[:4]
            deals = []
            for item in items:
                title = item.find('title').text if item.find('title') else ""
                source = item.find('source').text if item.find('source') else ""
                if title:
                    deals.append(f"[{source}] {title}")
            return deals if deals else ["No recent partnership news found."]
        return ["Partnership search unavailable."]
    except:
        return ["Partnership search failed."]


def scrape_trustpilot_sentiment(brand_domain):
    """Pull review score + recent sentiment from Trustpilot."""
    scraper = cloudscraper.create_scraper()
    try:
        url = f"https://www.trustpilot.com/review/{brand_domain}"
        resp = scraper.get(url, timeout=8)
        if resp.status_code == 200:
            soup = BeautifulSoup(resp.text, 'html.parser')
            rating_el = soup.select_one('[data-rating-typography]')
            rating = rating_el.get_text(strip=True) if rating_el else None
            review_count_el = soup.select_one('[data-reviews-count-typography]')
            review_count = review_count_el.get_text(strip=True) if review_count_el else None
            reviews = []
            for card in soup.select('[data-service-review-card-paper]')[:3]:
                text_el = card.select_one('[data-service-review-text-typography]')
                if text_el:
                    reviews.append(text_el.get_text(strip=True)[:120] + "...")
            score_str = f"⭐ {rating}/5" if rating else "Rating not found"
            count_str = f"({review_count} reviews)" if review_count else ""
            return {
                "score": f"{score_str} {count_str}",
                "recent_reviews": reviews if reviews else ["No recent reviews extracted."]
            }
        return {"score": "Trustpilot page not found.", "recent_reviews": []}
    except:
        return {"score": "Trustpilot scrape failed.", "recent_reviews": []}


def scrape_amazon_presence(brand_name):
    """Check Amazon for brand's top products, pricing, and review snippets."""
    scraper = cloudscraper.create_scraper(browser={'browser': 'chrome', 'platform': 'windows', 'mobile': False})
    try:
        search_url = f"https://www.amazon.com/s?k={quote_plus(brand_name)}&i=hpc"
        resp = scraper.get(search_url, timeout=10)
        if resp.status_code == 200:
            soup = BeautifulSoup(resp.text, 'html.parser')
            results = []
            for item in soup.select('[data-component-type="s-search-result"]')[:3]:
                title_el = item.select_one('h2 a span')
                price_el = item.select_one('.a-price .a-offscreen')
                rating_el = item.select_one('.a-icon-alt')
                review_count_el = item.select_one('span[aria-label*="stars"] + span a span')
                asin_link = item.select_one('h2 a')
                
                title = title_el.get_text(strip=True)[:70] if title_el else "Unknown"
                price = price_el.get_text(strip=True) if price_el else "N/A"
                rating = rating_el.get_text(strip=True)[:20] if rating_el else ""
                review_count = review_count_el.get_text(strip=True) if review_count_el else ""
                
                product = {
                    "title": title,
                    "price": price,
                    "rating": rating,
                    "review_count": review_count,
                    "reviews": [],
                }
                
                # Try to fetch review snippets from product page
                if asin_link and asin_link.get("href"):
                    try:
                        product_url = "https://www.amazon.com" + asin_link["href"]
                        p_resp = scraper.get(product_url, timeout=8)
                        if p_resp.status_code == 200:
                            p_soup = BeautifulSoup(p_resp.text, 'html.parser')
                            # Top review snippets on product page
                            for rev in p_soup.select('[data-hook="review-body"] span')[:3]:
                                text = rev.get_text(strip=True)[:200]
                                if text and len(text) > 20:
                                    product["reviews"].append(text)
                            # Also grab the "most helpful" review highlights
                            if not product["reviews"]:
                                for rev in p_soup.select('.cr-widget-FocalReviews .review-text-content span')[:3]:
                                    text = rev.get_text(strip=True)[:200]
                                    if text and len(text) > 20:
                                        product["reviews"].append(text)
                    except:
                        pass
                
                results.append(product)
            return results if results else [{"title": "No Amazon listings found.", "price": "", "rating": "", "review_count": "", "reviews": []}]
        return [{"title": "Amazon search blocked.", "price": "", "rating": "", "review_count": "", "reviews": []}]
    except:
        return [{"title": "Amazon scrape failed.", "price": "", "rating": "", "review_count": "", "reviews": []}]


def scrape_clinical_trials(search_term):
    """Check ClinicalTrials.gov API for active trials."""
    try:
        encoded = quote_plus(search_term)
        api_url = f"https://clinicaltrials.gov/api/v2/studies?query.term={encoded}&pageSize=3&format=json"
        resp = requests.get(api_url, timeout=8)
        if resp.status_code == 200:
            data = resp.json()
            studies = data.get('studies', [])
            results = []
            for study in studies:
                protocol = study.get('protocolSection', {})
                id_mod = protocol.get('identificationModule', {})
                status_mod = protocol.get('statusModule', {})
                title = id_mod.get('briefTitle', 'Unknown')
                status = status_mod.get('overallStatus', 'Unknown')
                results.append(f"[{status}] {title[:120]}")
            return results if results else ["No active clinical trials found."]
        return ["ClinicalTrials.gov API unavailable."]
    except:
        return ["Clinical trial lookup failed."]


def scrape_fda_alerts(brand_name):
    """Check FDA enforcement/recall API."""
    try:
        encoded = quote_plus(brand_name)
        url = (
            f"https://api.fda.gov/food/enforcement.json?"
            f"search=reason_for_recall:\"{encoded}\"+OR+recalling_firm:\"{encoded}\""
            f"&limit=3"
        )
        resp = requests.get(url, timeout=8)
        if resp.status_code == 200:
            data = resp.json()
            results_list = data.get('results', [])
            alerts = []
            for r in results_list:
                reason = r.get('reason_for_recall', 'Unknown')[:120]
                date = r.get('recall_initiation_date', 'Unknown')
                alerts.append(f"[{date}] {reason}")
            return alerts if alerts else None
        return None
    except:
        return None


def scrape_social_signals(brand_name, url):
    """Scrape social media links from homepage."""
    scraper = cloudscraper.create_scraper(browser={'browser': 'chrome', 'platform': 'windows', 'mobile': False})
    signals = {}
    try:
        resp = scraper.get(url, timeout=10)
        if resp.status_code == 200:
            soup = BeautifulSoup(resp.text, 'html.parser')
            for a in soup.find_all('a', href=True):
                href = a['href'].lower()
                if 'instagram.com' in href:
                    handle = href.split('instagram.com/')[-1].strip('/').split('?')[0]
                    if handle:
                        signals['Instagram'] = f"@{handle}"
                elif 'tiktok.com' in href:
                    handle = href.split('tiktok.com/')[-1].strip('/').split('?')[0]
                    if handle:
                        signals['TikTok'] = f"@{handle}"
                elif 'youtube.com' in href or 'youtu.be' in href:
                    signals['YouTube'] = "Active"
                elif 'twitter.com' in href or 'x.com' in href:
                    handle = href.split('/')[-1].strip('/').split('?')[0]
                    if handle:
                        signals['X/Twitter'] = f"@{handle}"
                elif 'facebook.com' in href:
                    signals['Facebook'] = "Active"
                elif 'strava.com' in href:
                    signals['Strava'] = "Active (endurance community)"
        return signals if signals else {"Social": "No social links detected"}
    except:
        return {"Social": "Social scrape failed"}
    
def scrape_reddit_mentions(brand_name):
    """Search Reddit for recent brand mentions and pull top comments."""
    try:
        encoded = quote_plus(brand_name)
        url = f"https://www.reddit.com/search.json?q={encoded}&sort=new&limit=5&t=month"
        resp = requests.get(url, timeout=10, headers={
            "User-Agent": "AonicIntel/1.0"
        })
        if resp.status_code == 200:
            data = resp.json()
            posts = data.get("data", {}).get("children", [])
            results = []
            for post in posts[:4]:
                p = post["data"]
                title = p.get("title", "")[:120]
                subreddit = p.get("subreddit", "")
                score = p.get("score", 0)
                num_comments = p.get("num_comments", 0)
                permalink = p.get("permalink", "")
                
                # Fetch top 3 comments for this post
                top_comments = []
                if permalink:
                    try:
                        comment_url = f"https://www.reddit.com{permalink}.json?limit=3&sort=top&depth=1"
                        c_resp = requests.get(comment_url, timeout=8, headers={
                            "User-Agent": "AonicIntel/1.0"
                        })
                        if c_resp.status_code == 200:
                            c_data = c_resp.json()
                            if len(c_data) > 1:
                                for c in c_data[1]["data"]["children"][:3]:
                                    body = c.get("data", {}).get("body", "")
                                    if body and body != "[deleted]":
                                        top_comments.append(body[:150])
                    except:
                        pass
                
                results.append({
                    "title": title,
                    "subreddit": f"r/{subreddit}",
                    "score": score,
                    "comments": num_comments,
                    "top_comments": top_comments,
                })
            return results if results else [{"title": "No recent Reddit mentions.", "subreddit": "", "score": 0, "comments": 0, "top_comments": []}]
        return [{"title": "Reddit API rate-limited.", "subreddit": "", "score": 0, "comments": 0, "top_comments": []}]
    except:
        return [{"title": "Reddit scrape failed.", "subreddit": "", "score": 0, "comments": 0, "top_comments": []}]


def send_email_report(subject, markdown_body, to_email="dock.hq@gmail.com"):
    """Send the newsletter as a properly formatted HTML email."""
    from email.mime.text import MIMEText
    from email.mime.multipart import MIMEMultipart
    import smtplib
    import re
    
    smtp_user = os.getenv("SMTP_USER")
    smtp_pass = os.getenv("SMTP_PASS")
    
    if not smtp_user or not smtp_pass:
        return False, "SMTP credentials not found in .env"
    
    # Convert markdown to HTML
    html = markdown_body
    html = re.sub(r'^### (.+)$', r'<h3 style="color:#1a1a1a;font-size:16px;margin:20px 0 8px;">\1</h3>', html, flags=re.MULTILINE)
    html = re.sub(r'^## (.+)$', r'<h2 style="color:#0a0a0a;font-size:20px;border-bottom:2px solid #e5e7eb;padding-bottom:8px;margin:32px 0 12px;">\1</h2>', html, flags=re.MULTILINE)
    html = re.sub(r'^# (.+)$', r'<h1 style="color:#0a0a0a;font-size:26px;margin:0 0 4px;">\1</h1>', html, flags=re.MULTILINE)
    html = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', html)
    html = re.sub(r'^---$', r'<hr style="border:none;border-top:1px solid #e5e7eb;margin:24px 0;">', html, flags=re.MULTILINE)
    html = re.sub(r'^\- (.+)$', r'<li style="margin:4px 0;color:#374151;">\1</li>', html, flags=re.MULTILINE)
    html = re.sub(r'(<li.*?</li>\n?)+', r'<ul style="padding-left:20px;margin:8px 0;">\g<0></ul>', html)
    html = re.sub(r'^\d+\. (.+)$', r'<li style="margin:4px 0;color:#374151;">\1</li>', html, flags=re.MULTILINE)
    # Wrap loose lines in paragraphs
    lines = html.split('\n')
    processed = []
    for line in lines:
        stripped = line.strip()
        if stripped and not stripped.startswith('<'):
            processed.append(f'<p style="margin:6px 0;color:#374151;line-height:1.7;">{stripped}</p>')
        else:
            processed.append(line)
    html = '\n'.join(processed)
    
    # Handle tables (markdown pipe tables → HTML)
    table_pattern = re.compile(r'(\|.+\|[\n\r]+)+', re.MULTILINE)
    def convert_table(match):
        rows = match.group(0).strip().split('\n')
        table_html = '<table style="width:100%;border-collapse:collapse;margin:16px 0;font-size:14px;">'
        for i, row in enumerate(rows):
            if '---' in row:
                continue
            cells = [c.strip() for c in row.split('|')[1:-1]]
            tag = 'th' if i == 0 else 'td'
            style = 'background:#f3f4f6;font-weight:700;' if i == 0 else ''
            cell_html = ''.join(f'<{tag} style="padding:10px 12px;border:1px solid #e5e7eb;{style}">{c}</{tag}>' for c in cells)
            table_html += f'<tr>{cell_html}</tr>'
        table_html += '</table>'
        return table_html
    html = table_pattern.sub(convert_table, html)
    
    # Generate static chart images for email
    chart_images = ""
    try:
        import plotly.graph_objects as go
        import base64
        
        scores = st.session_state.get("brand_scores", {})
        if scores:
            brand_colors = {
                "Precision Fuel & Hydration": "#e63946", "Raw Nutrition": "#1d1d1d",
                "Orgain": "#4caf50", "Maurten": "#333333", "GU Energy Labs": "#1a237e",
                "Pillar Performance": "#6c63ff", "SwissRX": "#d32f2f",
            }
            categories = ["Momentum", "Price", "Science", "Distribution", "Satisfaction"]
            
            fig = go.Figure()
            for name, data in scores.items():
                s = [data["momentum"], data["price"], data["science"], data["distribution"], data["satisfaction"]]
                color = brand_colors.get(name, "#00d4aa")
                fig.add_trace(go.Scatterpolar(r=s+[s[0]], theta=categories+[categories[0]], name=name,
                    line=dict(color=color, width=2), fill='none', opacity=0.7))
            fig.update_layout(polar=dict(radialaxis=dict(range=[0,10])),
                width=700, height=450, margin=dict(t=40,b=40,l=60,r=60),
                font=dict(size=11), title="Competitive Radar — Weekly Scores")
            
            img_bytes = fig.to_image(format="png", scale=2)
            b64 = base64.b64encode(img_bytes).decode()
            chart_images = f'<img src="data:image/png;base64,{b64}" style="width:100%;max-width:700px;margin:20px 0;border-radius:8px;">'
    except Exception as e:
        chart_images = ""

    full_html = f"""
    <html>
    <head><meta charset="utf-8"></head>
    <body style="font-family:-apple-system,'Segoe UI',Roboto,Helvetica,Arial,sans-serif;max-width:680px;margin:0 auto;padding:32px 24px;background:#ffffff;color:#1a1a1a;font-size:15px;line-height:1.7;">
        <div style="background:linear-gradient(135deg,#0a0a0a,#1a1a2e);padding:28px 32px;border-radius:12px;margin-bottom:28px;">
            <h1 style="color:#ffffff;font-size:22px;margin:0;">🦅 Aonic Competitive Intelligence Brief</h1>
            <p style="color:rgba(255,255,255,0.5);margin:6px 0 0;font-size:13px;">{datetime.now().strftime('%B %d, %Y')} · Auto-generated at 6:00 AM PT</p>
        </div>
        {html}
        {chart_images}
        <div style="margin-top:40px;padding-top:20px;border-top:1px solid #e5e7eb;font-size:12px;color:#9ca3af;text-align:center;">
            Generated by Aonic AI Intelligence Pipeline · Confidential
        </div>
    </body>
    </html>
    """
    
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = smtp_user
    msg["To"] = to_email
    msg.attach(MIMEText(markdown_body, "plain"))
    msg.attach(MIMEText(full_html, "html"))
    
    try:
        with smtplib.SMTP("smtp.gmail.com", 587) as server:
            server.starttls()
            server.login(smtp_user, smtp_pass)
            server.sendmail(smtp_user, to_email, msg.as_string())
        return True, "Sent"
    except Exception as e:
        return False, str(e)

def calculate_scores(brand_name, scraped):
    """Convert raw scraped data into 1-10 scores per dimension."""
    
    # ── Brand Momentum (news volume + partnership signals) ──
    news_count = len([n for n in scraped.get("news", []) if isinstance(n, dict) and n.get("title", "") != "No recent coverage found."])
    partner_count = len([p for p in scraped.get("partnerships", []) if "No recent" not in p and "failed" not in p])
    reddit_score_total = sum(p.get("score", 0) for p in scraped.get("reddit", []) if isinstance(p, dict))
    momentum = min(10, max(1, 
        2 +  # base
        min(3, news_count) +  # up to 3 for news
        min(2, partner_count) +  # up to 2 for partnerships
        min(3, reddit_score_total // 100)  # up to 3 for reddit buzz
    ))
    
    # ── Price Competitiveness (lower avg price = higher score) ──
    prices_found = []
    for p in scraped.get("products", []):
        if isinstance(p, str):
            import re
            matches = re.findall(r'\$(\d+\.?\d*)', p)
            prices_found.extend([float(m) for m in matches])
        elif isinstance(p, dict):
            import re
            matches = re.findall(r'\$(\d+\.?\d*)', p.get("price", ""))
            prices_found.extend([float(m) for m in matches])
    if prices_found:
        avg_price = sum(prices_found) / len(prices_found)
        if avg_price < 20: price_score = 9
        elif avg_price < 35: price_score = 8
        elif avg_price < 50: price_score = 7
        elif avg_price < 75: price_score = 5
        elif avg_price < 100: price_score = 4
        else: price_score = 3
    else:
        price_score = 5  # unknown = neutral
    
    # ── Science Credibility (clinical trials + FDA clean) ──
    trial_count = len([t for t in scraped.get("trials", []) if "No active" not in t and "failed" not in t and "unavailable" not in t])
    fda_clean = scraped.get("fda_clean", True)
    science = min(10, max(1,
        3 +  # base
        min(4, trial_count * 2) +  # up to 4 for trials
        (3 if fda_clean else -2)  # bonus for clean, penalty for alerts
    ))
    
    # ── Distribution Reach (amazon + shopify + social channels) ──
    amazon_found = len([a for a in scraped.get("amazon", []) if isinstance(a, dict) and a.get("title", "") not in ["No Amazon listings found.", "Amazon search blocked.", "Amazon scrape failed."]])
    if not amazon_found:
        amazon_found = len([a for a in scraped.get("amazon", []) if isinstance(a, str) and "No Amazon" not in a and "blocked" not in a and "failed" not in a])
    has_shopify = scraped.get("has_shopify", False)
    social_count = len(scraped.get("social", {}))
    distribution = min(10, max(1,
        2 +
        min(3, amazon_found * 1) +
        (2 if has_shopify else 0) +
        min(3, social_count)
    ))
    
    # ── Customer Satisfaction (trustpilot score + review sentiment) ──
    tp_score_str = scraped.get("trustpilot_score", "")
    tp_num = 5.0  # default
    import re
    tp_match = re.search(r'(\d+\.?\d*)/5', tp_score_str)
    if tp_match:
        tp_num = float(tp_match.group(1))
    
    reddit_comments = []
    for post in scraped.get("reddit", []):
        if isinstance(post, dict):
            reddit_comments.extend(post.get("top_comments", []))
    negative_words = ["terrible", "awful", "worst", "scam", "waste", "horrible", "disgusting", "refund", "disappointed"]
    positive_words = ["love", "amazing", "great", "excellent", "best", "fantastic", "recommend", "perfect", "awesome"]
    neg_count = sum(1 for c in reddit_comments for w in negative_words if w in c.lower())
    pos_count = sum(1 for c in reddit_comments for w in positive_words if w in c.lower())
    reddit_sentiment_bonus = min(2, pos_count) - min(2, neg_count)
    
    satisfaction = min(10, max(1, int(tp_num * 1.8) + reddit_sentiment_bonus))
    
    return {
        "momentum": momentum,
        "price": price_score,
        "science": science,
        "distribution": distribution,
        "satisfaction": satisfaction,
    }

def render_competitive_scorecard():
    """Visual competitive scorecard using dynamically calculated scores."""
    import plotly.graph_objects as go
    
    scores = st.session_state.get("brand_scores", {})
    if not scores:
        st.warning("No scores calculated yet.")
        return
    
    brand_colors = {
        "Precision Fuel & Hydration": "#e63946",
        "Raw Nutrition": "#1d1d1d",
        "Orgain": "#4caf50",
        "Maurten": "#333333",
        "GU Energy Labs": "#1a237e",
        "Pillar Performance": "#6c63ff",
        "SwissRX": "#d32f2f",
    }
    brand_logos = {
        "Precision Fuel & Hydration": "logos/Precision.jpeg",
        "Raw Nutrition": "logos/Raw.jpeg",
        "Orgain": "logos/Orgain.png",
        "Maurten": "logos/Maurten.png",
        "GU Energy Labs": "logos/GU.png",
        "Pillar Performance": "logos/pillar.png",
        "SwissRX": "logos/Swiss.png",
    }
    
    categories = ["Brand\nMomentum", "Price\nCompetitive", "Science\nCredibility", "Distribution\nReach", "Customer\nSatisfaction"]
    
    # ── RADAR CHART ──
    fig_radar = go.Figure()
    for name, data in scores.items():
        s = [data["momentum"], data["price"], data["science"], data["distribution"], data["satisfaction"]]
        color = brand_colors.get(name, "#00d4aa")
        fig_radar.add_trace(go.Scatterpolar(
            r=s + [s[0]],
            theta=categories + [categories[0]],
            name=name,
            line=dict(color=color, width=2.5 if "Aonic" in name else 1.5),
            fill='toself' if "Aonic" in name else 'none',
            opacity=1.0 if "Aonic" in name else 0.4,
        ))
    fig_radar.update_layout(
        polar=dict(
            radialaxis=dict(visible=True, range=[0, 10], gridcolor="rgba(255,255,255,0.1)", color="rgba(255,255,255,0.4)"),
            angularaxis=dict(gridcolor="rgba(255,255,255,0.1)", color="rgba(255,255,255,0.7)"),
            bgcolor="rgba(0,0,0,0)",
        ),
        paper_bgcolor="rgba(13,17,23,1)", plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color="white", size=11),
        legend=dict(font=dict(size=11, color="white"), bgcolor="rgba(0,0,0,0)"),
        margin=dict(t=40, b=40, l=60, r=60), height=500,
        title=dict(text="Competitive Radar (scores calculated from today's scrape)", font=dict(size=14, color="white"), x=0.5),
    )
    st.plotly_chart(fig_radar, use_container_width=True)
    
    # ── BUBBLE CHART ──
    fig_bubble = go.Figure()
    for name, data in scores.items():
        overall = sum(data.values())
        color = brand_colors.get(name, "#00d4aa")
        fig_bubble.add_trace(go.Scatter(
            x=[data["distribution"]], y=[data["science"]],
            mode='markers+text',
            marker=dict(size=overall * 1.8, color=color, opacity=0.85,
                       line=dict(width=2, color='white') if "Aonic" in name else dict(width=1, color='rgba(255,255,255,0.3)')),
            text=[name.replace(" & Hydration", "").replace(" Performance", "").replace(" Energy Labs", "")],
            textposition="top center",
            textfont=dict(color="white", size=12, family="Arial Black" if "Aonic" in name else "Arial"),
            name=name, showlegend=False,
        ))
    fig_bubble.update_layout(
        xaxis=dict(title="Distribution Reach →", range=[0, 10.5], gridcolor="rgba(255,255,255,0.06)", color="rgba(255,255,255,0.6)", zeroline=False),
        yaxis=dict(title="Science Credibility →", range=[0, 10.5], gridcolor="rgba(255,255,255,0.06)", color="rgba(255,255,255,0.6)", zeroline=False),
        paper_bgcolor="rgba(13,17,23,1)", plot_bgcolor="rgba(13,17,23,1)",
        font=dict(color="white"), margin=dict(t=50, b=60, l=60, r=40), height=450,
        title=dict(text="Market Map: Science vs Distribution (bubble = overall score)", font=dict(size=14, color="white"), x=0.5),
        annotations=[
            dict(x=1.5, y=9.5, text="HIGH SCIENCE<br>LOW REACH", showarrow=False, font=dict(color="rgba(255,255,255,0.15)", size=11)),
            dict(x=8.5, y=9.5, text="HIGH SCIENCE<br>HIGH REACH", showarrow=False, font=dict(color="rgba(255,255,255,0.15)", size=11)),
            dict(x=1.5, y=1.5, text="LOW SCIENCE<br>LOW REACH", showarrow=False, font=dict(color="rgba(255,255,255,0.15)", size=11)),
            dict(x=8.5, y=1.5, text="LOW SCIENCE<br>HIGH REACH", showarrow=False, font=dict(color="rgba(255,255,255,0.15)", size=11)),
        ],
    )
    st.plotly_chart(fig_bubble, use_container_width=True)
    
    # ── LOGO CARDS WITH BAR SCORES ──
    st.markdown("### Brand-by-Brand Breakdown")
    brand_list = list(scores.items())
    cols_per_row = 4
    for row_start in range(0, len(brand_list), cols_per_row):
        cols = st.columns(cols_per_row)
        for i, col in enumerate(cols):
            idx = row_start + i
            if idx >= len(brand_list):
                break
            name, data = brand_list[idx]
            overall = sum(data.values())
            with col:
                try:
                    logo = brand_logos.get(name, "")
                    if logo:
                        st.image(logo, width=60)
                except:
                    pass
                st.markdown(f"**{name}**")
                st.caption(f"Overall: {overall}/50")
                for label, key, emoji in [("Momentum", "momentum", "🔥"), ("Price", "price", "💰"),
                                           ("Science", "science", "🔬"), ("Distrib.", "distribution", "🛒"),
                                           ("Satisf.", "satisfaction", "😊")]:
                    score = data[key]
                    bar = "█" * score + "░" * (10 - score)
                    st.caption(f"{emoji} {label}: {bar} {score}/10")

# ─── COMPETITOR CONFIG ───────────────────────────────────────────────────────

competitors = {
    "Precision Fuel & Hydration": {
        "url": "https://www.precisionfuelandhydration.com",
        "domain": "www.precisionfuelandhydration.com",
        "search_term": "Precision Fuel Hydration",
        "clinical_term": "electrolyte supplementation endurance",
        "category": "Customized fueling & electrolytes",
        "known_for": "Personalized sweat testing, high-sodium electrolyte formulas, pro endurance athlete partnerships",
    },
    "Raw Nutrition": {
        "url": "https://www.rawnutrition.com",
        "domain": "www.rawnutrition.com",
        "search_term": "Raw Nutrition supplements",
        "clinical_term": "Raw Nutrition pre-workout",
        "category": "Pre-workout & endurance",
        "known_for": "CBUM (Chris Bumstead) partnership, Raw Pre, aggressive influencer marketing, bodybuilding community",
    },
    "Orgain": {
        "url": "https://www.orgain.com",
        "domain": "www.orgain.com",
        "search_term": "Orgain protein supplements",
        "clinical_term": "Orgain organic protein",
        "category": "Protein shakes & recovery",
        "known_for": "Organic/plant-based protein, doctor-founded (Dr. Andrew Abraham), mass retail (Costco, Target, Walmart)",
    },
    "Maurten": {
        "url": "https://www.maurten.com",
        "domain": "www.maurten.com",
        "search_term": "Maurten sports nutrition",
        "clinical_term": "hydrogel sports nutrition",
        "category": "Hydrogel fueling technology",
        "known_for": "Patented hydrogel tech, Kipchoge marathon partnership, elite runner adoption, minimal branding",
    },
    "GU Energy Labs": {
        "url": "https://guenergy.com",
        "domain": "guenergy.com",
        "search_term": "GU Energy Labs",
        "clinical_term": "energy gel endurance supplementation",
        "category": "Energy gels & chews",
        "known_for": "Pioneer in energy gels, massive flavor variety, marathon/ultra/triathlon staple, Roctane line",
    },
        "Pillar Performance": {
        "url": "https://www.pillarperformance.com",
        "domain": "www.pillarperformance.com",
        "search_term": "Pillar Performance supplements",
        "clinical_term": "magnesium supplementation athletic recovery",
        "category": "Micronutrition & recovery",
        "known_for": "Magnesium-focused recovery products, micronutrition approach, endurance athlete partnerships, Australian brand",
    },
    "SwissRX": {
        "url": "https://www.swissrx.com",
        "domain": "www.swissrx.com",
        "search_term": "SwissRX supplements endurance",
        "clinical_term": "SwissRX endurance recovery supplements",
        "category": "Specialized endurance & recovery",
        "known_for": "High-quality Swiss-formulated products, endurance-specific stacks, cycling/triathlon community, premium positioning",
    },
}

# ─── MAIN DASHBOARD ─────────────────────────────────────────────────────────

if st.button("▶ Run Weekly Competitive Intelligence Scan"):
    my_bar = st.progress(0, text="Initializing Live AI Web Scrapers...")

    raw_intel_feed = ""
    total_steps = len(competitors) * 8
    current_step = 0

    for brand, config in competitors.items():
        st.write("---")
        st.header(f"{brand}")
        st.caption(f"📂 {config['category']} · Known for: {config['known_for']}")
        col1, col2 = st.columns(2)

        raw_intel_feed += f"\n{'='*50}\n## {brand}\nCategory: {config['category']}\nKnown for: {config['known_for']}\n"
        scraped_data = {}  # collect raw data for scoring

        # ── Column 1: Marketing + Pricing + Sentiment + Social ──
        with col1:
            with st.spinner(f"Scraping {brand} homepage..."):
                html_hooks = scrape_competitor_html(config["url"])
                st.success(f"**🎯 Marketing Hooks:** {html_hooks}")
                raw_intel_feed += f"Marketing Hooks: {html_hooks}\n"
            current_step += 1
            my_bar.progress(current_step / total_steps, text=f"[{brand}] Homepage scraped...")

            with st.spinner(f"Pulling {brand} product pricing..."):
                shopify_data = scrape_shopify_data(config["url"])
                if shopify_data:
                    st.markdown("**💰 Products/Prices (Shopify API):**")
                    for p in shopify_data[:5]:
                        st.info(p)
                    raw_intel_feed += f"Products/Prices (Shopify):\n"
                    for p in shopify_data:
                        raw_intel_feed += f"  - {p}\n"
                else:
                    fallback = scrape_pricing_fallback(config["url"])
                    st.markdown("**💰 Products/Prices (Page Scrape):**")
                    for p in fallback[:5]:
                        st.info(p)
                    raw_intel_feed += f"Products/Prices:\n"
                    for p in fallback:
                        raw_intel_feed += f"  - {p}\n"
            current_step += 1
            my_bar.progress(current_step / total_steps, text=f"[{brand}] Pricing captured...")

            scraped_data["products"] = shopify_data if shopify_data else fallback
            scraped_data["has_shopify"] = shopify_data is not None

            with st.spinner(f"Pulling {brand} review sentiment..."):
                sentiment = scrape_trustpilot_sentiment(config["domain"])
                st.metric(label="Customer Sentiment (Trustpilot)", value=sentiment["score"])
                if sentiment["recent_reviews"]:
                    with st.expander("📝 Recent Customer Reviews"):
                        for rev in sentiment["recent_reviews"]:
                            st.caption(rev)
                raw_intel_feed += f"Trustpilot: {sentiment['score']}\n"
                for rev in sentiment["recent_reviews"]:
                    raw_intel_feed += f"  - {rev}\n"
            current_step += 1
            my_bar.progress(current_step / total_steps, text=f"[{brand}] Sentiment analyzed...")

            scraped_data["trustpilot_score"] = sentiment["score"]

            with st.spinner(f"Scanning {brand} social channels..."):
                social = scrape_social_signals(brand, config["url"])
                if social:
                    st.markdown("**📱 Social Presence:**")
                    social_str = " · ".join([f"{k}: {v}" for k, v in social.items()])
                    st.caption(social_str)
                    raw_intel_feed += f"Social Channels: {social_str}\n"
            current_step += 1
            my_bar.progress(current_step / total_steps, text=f"[{brand}] Social scanned...")

            scraped_data["social"] = social


        # ── Column 2: News + Partnerships + Clinical + FDA + Amazon ──
        with col2:
            with st.spinner(f"Scanning {brand} news coverage..."):
                news = scrape_news_coverage(config["search_term"])
                st.markdown("**📰 Recent News Coverage:**")
                for item in news[:4]:
                    if isinstance(item, dict):
                        st.caption(f"[{item['source']}] {item['title']} ({item['date']})")
                    else:
                        st.caption(item)
                raw_intel_feed += f"Recent News:\n"
                for item in news:
                    if isinstance(item, dict):
                        raw_intel_feed += f"  - [{item['source']}] {item['title']}\n"
                    else:
                        raw_intel_feed += f"  - {item}\n"
            current_step += 1
            my_bar.progress(current_step / total_steps, text=f"[{brand}] News scanned...")

            scraped_data["news"] = news

            with st.spinner(f"Searching {brand} athlete partnerships..."):
                partnerships = scrape_athlete_partnerships(config["search_term"])
                st.markdown("**🏅 Athlete & Sponsorship Intel:**")
                for deal in partnerships[:3]:
                    st.caption(deal)
                raw_intel_feed += f"Athlete/Sponsorship News:\n"
                for deal in partnerships:
                    raw_intel_feed += f"  - {deal}\n"

            scraped_data["partnerships"] = partnerships

            with st.spinner(f"Checking clinical research..."):
                trials = scrape_clinical_trials(config["clinical_term"])
                st.markdown("**🔬 Clinical Trials (ClinicalTrials.gov):**")
                for t in trials:
                    st.caption(t)
                raw_intel_feed += f"Clinical Trials:\n"
                for t in trials:
                    raw_intel_feed += f"  - {t}\n"

            scraped_data["trials"] = trials

            with st.spinner(f"Checking FDA enforcement..."):
                fda = scrape_fda_alerts(brand)
                if fda:
                    st.error("**⚠️ FDA Alerts Found:**")
                    for alert in fda:
                        st.caption(alert)
                    raw_intel_feed += f"FDA ALERTS:\n"
                    for a in fda:
                        raw_intel_feed += f"  - ⚠️ {a}\n"
                else:
                    st.markdown("**✅ No FDA recalls or enforcement actions.**")
                    raw_intel_feed += f"FDA Status: Clean\n"
            current_step += 1
            my_bar.progress(current_step / total_steps, text=f"[{brand}] Regulatory done...")

            scraped_data["fda_clean"] = fda is None

            with st.spinner(f"Checking {brand} Amazon presence + reviews..."):
                amazon = scrape_amazon_presence(brand)
                st.markdown("**🛒 Amazon Presence & Reviews:**")
                raw_intel_feed += f"Amazon:\n"
                for product in amazon[:3]:
                    line = f"{product['title']} — {product['price']}"
                    if product['rating']:
                        line += f" ({product['rating']}, {product['review_count']} reviews)"
                    st.caption(line)
                    raw_intel_feed += f"  - {line}\n"
                    if product.get("reviews"):
                        with st.expander(f"Reviews: {product['title'][:40]}..."):
                            for rev in product["reviews"]:
                                st.caption(f"💬 {rev}")
                                raw_intel_feed += f"    💬 {rev}\n"
            current_step += 1
            my_bar.progress(current_step / total_steps, text=f"[{brand}] Amazon checked...")

            scraped_data["amazon"] = amazon

            with st.spinner(f"Scanning Reddit for {brand} mentions..."):
                reddit = scrape_reddit_mentions(config["search_term"])
                st.markdown("**🗣️ Reddit Mentions:**")
                raw_intel_feed += f"Reddit Mentions:\n"
                for post in reddit[:4]:
                    st.caption(f"**{post['subreddit']}** · ↑{post['score']} · {post['comments']} comments — {post['title']}")
                    raw_intel_feed += f"  - [{post['subreddit']} ↑{post['score']}] {post['title']}\n"
                    if post["top_comments"]:
                        with st.expander(f"Top comments on: {post['title'][:50]}..."):
                            for comment in post["top_comments"]:
                                st.caption(f"💬 {comment}")
                                raw_intel_feed += f"    💬 {comment}\n"

                scraped_data["reddit"] = reddit

            # Calculate dynamic scores
            if "brand_scores" not in st.session_state:
                st.session_state.brand_scores = {}
            st.session_state.brand_scores[brand] = calculate_scores(brand, scraped_data)

    my_bar.empty()

    # ── AI NEWSLETTER ────────────────────────────────────────────────────────
    st.write("---")
    st.markdown("---")
    brief_time = datetime.now().strftime('%B %d, %Y at %I:%M %p PT')
    st.markdown(f"""
    <div style="background: linear-gradient(135deg, #0a0a0a, #1a1a2e); padding: 24px 32px; border-radius: 14px; margin-bottom: 20px;">
        <h2 style="color: white; margin: 0;">📧 Aonic Weekly Intelligence Brief</h2>
        <p style="color: rgba(255,255,255,0.5); margin: 4px 0 0; font-size: 14px;">Auto-generated · {brief_time}</p>
    </div>
    """, unsafe_allow_html=True)

    with st.spinner("AI Agent is drafting the full executive brief — this takes ~30 seconds for depth..."):
        newsletter_prompt = f"""
You are the Chief of Staff at Aonic writing the weekly competitive intelligence newsletter.
Today is {datetime.now().strftime('%B %d, %Y')}.

AONIC CONTEXT:
- Aonic Complete: $115/mo, 34-ingredient all-in-one daily nutrition (patent-pending liquid + capsule dual-delivery system, HIS/HERS variants)
- Aonic Revive: $40/12-pack, magnesium & electrolyte sparkling drink, real fruit juice, zero added sugar
- Aonic Build: 3-in-1 muscle support powder stick (5g Creatine + HMBPro™ + Beetroot Extract)
- Co-founders: Max Meier (serial consumer-tech entrepreneur) + Senada Greca (fitness entrepreneur, Kim Kardashian's trainer, WeRise app founder)
- Science team: Dr. William Li (Harvard physician, NYT bestselling author "Eat to Beat Disease") + Dr. David Jan (Harvard PhD, 20yr nutrition manufacturing)
- 2026 Goal: 20x growth to >$20M ARR, profitable with ~10 people
- Tagline: "Health is happiness — make healthy living effortless and enjoyable"

COMPETITORS MONITORED:
1. Precision Fuel & Hydration — personalized sweat testing, high-sodium electrolyte formulas, pro endurance athlete partnerships
2. Raw Nutrition — CBUM (Chris Bumstead, Mr. Olympia) partnership, aggressive pre-workout/endurance line, bodybuilding influencer army
3. Orgain — organic/plant-based protein shakes, doctor-founded (Dr. Andrew Abraham, cancer survivor), mass retail in Costco/Target/Walmart
4. Maurten — patented hydrogel technology for carb delivery, Kipchoge marathon world record partnership, elite runner adoption, minimal Scandinavian branding
5. GU Energy Labs — pioneer in energy gels since 1993, 20+ flavors, marathon/ultra/triathlon staple, Roctane premium line
6. Pillar Performance — magnesium-focused micronutrition and recovery, endurance athlete partnerships
7. SwissRX — Swiss-formulated endurance and recovery stacks, cycling/triathlon community, premium positioning

RAW INTELLIGENCE (weekly scan — {datetime.now().strftime('%B %d, %Y')} at 6:00 AM PT):
{raw_intel_feed}

Write a COMPREHENSIVE newsletter. This should feel like a premium weekly intelligence brief that a CEO reads with their morning coffee — substantial, detailed, and worth 5 minutes of their time. Use the AlphaSignal newsletter format as inspiration: deep sections, specific data, context on why things matter, and clear visual hierarchy.

FORMAT EXACTLY LIKE THIS:

---

# 🦅 Aonic Competitive Intelligence Brief
**{datetime.now().strftime('%B %d, %Y')}** · 5 min read

**TL;DR:** [2-3 sentences summarizing the most critical signals detected today across all 5 competitors. Be specific with data points.]

---

## 🚨 Top Threat of the Day

[Name the competitor and the specific move/signal detected]

Write 150-200 words explaining:
- What exactly was detected in today's scrape (quote specific headlines, prices, or data points)
- Why this matters strategically for Aonic
- How this could impact Aonic's positioning in the next 30-90 days
- What the competitor is trying to achieve with this move

**Aonic's Counter-Move:** [One specific, detailed recommendation — not generic advice, but something executable today]

---

## 💰 Pricing & Product Intelligence

For EACH competitor where pricing data was found, write a detailed paragraph:

**[Competitor Name]** — [what was found]
- List specific products and prices detected
- Compare directly to Aonic's price points ($115/mo Complete, $40/12pk Revive, Build pricing)
- Note if pricing has shifted, new products appeared, or catalog structure changed
- Call out if Aonic is overpriced, underpriced, or well-positioned relative to this competitor

End with a **Price Positioning Summary** table showing all 5 competitors' price ranges vs Aonic.

---

## 📰 News, Media & Athlete Partnerships

For EACH competitor where news/partnership signals were found, write a detailed paragraph:

**[Competitor Name]** — [headline summary]
- What the news coverage signals about their strategy
- Any athlete endorsements, sponsorship deals, influencer partnerships detected
- Social media channel analysis (which platforms are they active on, handles found)
- PR/marketing moves and what narrative they're building

End with a **Mindshare Ranking** — rank all 5 competitors by current media momentum (1 = hottest) and explain why.

---

## 🔬 Science, Clinical & Regulatory Watch

**Clinical Trials Detected:**
For each competitor, report what ClinicalTrials.gov returned. If trials were found, explain what they're studying and what it signals. If none found, note it.

**FDA Enforcement Status:**
Report clean/flagged status for each competitor. If any alerts found, detail them.

**Science Credibility Assessment:**
Rank competitors by science credibility and explain. Note which competitors are investing in research vs riding marketing hype.

**What This Means for Aonic:** How should Aonic leverage its Dr. William Li + Dr. David Jan science team in response?

---

## 🛒 Distribution & Channel Intelligence

**Amazon Battlefield:**
For each competitor, report what was found on Amazon — product listings, pricing, ratings. Who is winning the Amazon game?

**Retail vs DTC Analysis:**
Which competitors are DTC-only vs mass retail? What does this mean for Aonic's channel strategy?

**Channel Gap Aonic Can Exploit:**
Where is there distribution white space?

---

## 😊 Customer Sentiment & Review Intelligence

For EACH competitor, report Trustpilot data:

**[Competitor Name]** — [score] 
- What are customers praising?
- What are customers complaining about?
- What pattern do the reviews reveal about product quality, shipping, or customer service?

**Sentiment Opportunity for Aonic:** Where are competitor customers most frustrated? How can Aonic capture them?

---

## ⚡ This Week's Action Items

### Action #1 (CRITICAL)
**What:** [Specific action — not vague]
**Owner:** [Max / Senada / Science Team / Marketing / Ops]
**Why:** [2-3 sentences explaining the strategic reasoning based on today's intelligence]
**Timeline:** Today

### Action #2 (HIGH PRIORITY)
**What:** [Specific action]
**Owner:** [who]
**Why:** [reasoning from data]
**Timeline:** This week

### Action #3 (STRATEGIC)
**What:** [Specific action]  
**Owner:** [who]
**Why:** [reasoning from data]
**Timeline:** This month

### Action #4 (INTELLIGENCE GAP)
**What:** [Something we couldn't scrape today that we need manual research on]
**Owner:** [who]
**Why:** [what's missing and why it matters]

---

## 📊 Competitive Scorecard

Create a brief scorecard ranking all 5 competitors + Aonic across these dimensions:
- Brand Momentum (who is making moves)
- Price Competitiveness 
- Science Credibility
- Distribution Reach
- Customer Satisfaction

Use a simple High / Medium / Low rating for each.

---

*This brief was auto-generated by Aonic's AI Competitive Intelligence Pipeline. Data sourced from live web scraping, Google News RSS, Trustpilot, ClinicalTrials.gov, FDA enforcement API, Shopify product APIs, and Amazon search. Next scan: next Monday at 6:00 AM PT.*

---

IMPORTANT RULES:
- Use REAL data from the raw intelligence above. Quote actual headlines, prices, and scores.
- If data for a section is missing or scraping failed, explicitly note "DATA GAP: [what's missing]" instead of making things up.
- Be specific and commercial, not generic. Every insight should lead to an action.
- Write at least 1500 words total. This should be SUBSTANTIVE — a CEO should feel informed after reading it.
- Use markdown formatting for clear visual hierarchy.
"""

        email_response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are a world-class competitive intelligence analyst writing a premium daily newsletter. "
                        "You write like a blend of Morning Brew's sharpness and McKinsey's rigor. "
                        "Every section must have real substance — specific data points, strategic context, and clear implications. "
                        "Never write generic filler. Never say 'it's important to monitor' — instead say exactly what to do. "
                        "The CEO should feel like they have an unfair information advantage after reading this."
                    )
                },
                {"role": "user", "content": newsletter_prompt}
            ],
            max_tokens=4096,
        )

        newsletter_content = email_response.choices[0].message.content

        # Render with styled container
        st.markdown("""
        <style>
            .newsletter-container {
                background: #0d1117;
                border: 1px solid #21262d;
                border-radius: 12px;
                padding: 32px;
                margin: 16px 0;
                color: #c9d1d9;
                font-size: 15px;
                line-height: 1.8;
            }
            .newsletter-container h1 { color: #f0f6fc; font-size: 1.6rem; }
            .newsletter-container h2 { color: #58a6ff; font-size: 1.2rem; border-bottom: 1px solid #21262d; padding-bottom: 8px; margin-top: 28px; }
            .newsletter-container h3 { color: #f0f6fc; font-size: 1rem; }
            .newsletter-container strong { color: #f0f6fc; }
            .newsletter-container hr { border-color: #21262d; margin: 20px 0; }
        </style>
        """, unsafe_allow_html=True)
        
        st.markdown(newsletter_content)
        # ── Visual Scorecard ──
        st.write("---")
        st.markdown("## 📊 Competitive Scorecard")
        render_competitive_scorecard()
        
        # ── Send to inbox ──
        st.write("---")
        subject_line = newsletter_content.split("\n")[0][:80].replace("#", "").strip()
        if not subject_line:
            subject_line = f"Aonic Intel Brief — {datetime.now().strftime('%b %d, %Y')}"
        
        sent, msg = send_email_report(subject_line, newsletter_content)
        if sent:
            st.success("📬 Newsletter sent to dock.hq@gmail.com")
        else:
            st.warning(f"📬 Email not sent: {msg}")

    # ── Save raw intel ──
    try:
        os.makedirs("data", exist_ok=True)
        with open("data/last_scan.json", "w") as f:
            json.dump({
                "timestamp": datetime.now().isoformat(),
                "raw_intel": raw_intel_feed,
                "newsletter": newsletter_content,
            }, f)
        st.caption(f"💾 Intel + newsletter saved at {datetime.now().strftime('%H:%M:%S')}")
    except:
        pass