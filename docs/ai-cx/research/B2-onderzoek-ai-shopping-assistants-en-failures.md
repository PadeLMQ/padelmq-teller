# MEMO — AI shopping assistants and AI customer service in e-commerce, 2023–2026
### What works, what failed, measured outcomes — and what it means for a one-founder Belgian padel webshop on Shopify (~3,700 orders/yr)

Date: 28 September 2026. Method note: 47 web searches; 8 pages read in full (marked [F]); all other claims come from search-engine extracts of the cited page (marked [S]) because the sandbox's egress proxy blocked most domains (openai.com, forbes.com, cbc.ca, klarna.com, intercom.com, gorgias.com, ai.google.dev, etc.). Treat [S] figures as "reported by that source", not independently re-read by me.

---

## 1. PROVEN FACTS (source + date)

### 1.1 AI shopping / advice assistants

**Amazon Rufus** (launched Feb 2024 US; EU beta 29 Oct 2024 in DE/FR/IT/ES — Belgium/NL not in the announcement [S, aboutamazon.eu]). Amazon-reported: 250M customers in 2025, MAU +140–149% YoY, interactions +210%, ~$10B annualised incremental sales (Q3 2025 call), later ~$12B (Q4 2025) [S, Yahoo Finance / The Drum]. Vendor claim: Rufus users "60% more likely to complete a purchase" [S, azoma.ai]. **Independent**: Sensor Tower panel of 60,000 US shoppers over 18 months (window Black Friday 2025–Q1 2026): 60% of heavy Amazon users include Rufus in sessions; Rufus users are 2.74x more likely to convert [S, sensortower.com]. Evercore ISI survey (Aug 2025): 55% of respondents say they use a retailer's built-in AI assistant [S, retailgentic.com]. Rufus was renamed "Alexa for Shopping" on 13 May 2026 [S, amalytix.com]. Rufus UI: product-page questions ("is this pickleball paddle good for beginners?"), suggested clickable questions, and "Help Me Decide" (Oct 2025) which recommends one product with a reason [S, aboutamazon.com].

**Zalando Assistant** (ChatGPT-based, 2023 in 4 DE/EN markets; goal 20+ markets in 2024). After moving to GPT-4o mini: product clicks in the recommendation carousel +23%, wishlist additions +41%, lower latency and cost [S, openai.com/index/zalando — vendor case study].

**Klarna AI assistant** (OpenAI-based). Press release 27 Feb 2024: 2.3M conversations in first month = two-thirds of chats; resolution time <2 min vs 11 min; CSAT "on par" with humans; 25% drop in repeat inquiries; "equivalent work of 700 FTE"; est. $40M profit improvement 2024; 23 markets, 35+ languages [S, klarna.com press / prnewswire]. **Reversal**: 8 May 2025, CEO Siemiatkowski to Bloomberg: "As cost unfortunately seems to have been a too predominant evaluation factor when organizing this, what you end up having is lower quality." Klarna reopened hiring of human agents (remote, flexible, "value tier"/complex cases) while AI stays front-line for high-volume tier [S, Bloomberg via bigeye.com; Forbes 18 May 2025; CX Dive]. Cause named by Klarna: quality decline and customers unable to reach a human for nuanced issues — not a technical failure.

**Walmart Sparky**: Walmart-reported — Sparky users spend 40% more per order; Q4 FY26 call: AOV +35% [S, envisionhorizons / TipRanks]. **Walmart on ChatGPT Instant Checkout**: in-chat purchases converted at one-third the rate of click-out to Walmart.com; EVP product & design called it "unsatisfying"; Walmart withdrew and instead embedded Sparky inside ChatGPT and Gemini [S, searchengineland.com, Mar 2026; Retail Dive].

**ChatGPT Instant Checkout / Agentic Commerce Protocol** (launched 29 Sep 2025 with Stripe; Etsy at launch, Shopify merchants "coming soon"; OpenAI takes a fee) [S, openai.com, CNBC 29 Sep 2025, stripe.com]. **Retired March 2026**, ~6 months after launch; OpenAI repositioned ChatGPT to discovery with checkout on the merchant's site [S, CNBC 20 & 24 Mar 2026]. Third-party claims: ~30 merchants ever live [S, laioutr.com]; reported in-chat conversion 1.18% / 77% cart abandonment [S, buildmvpfast — unverified].

**Lowe's Mylow** (ChatGPT-based, launched Mar 2025, chat + voice): Lowe's-reported double the online conversion rate vs non-users [S, retailtouchpoints.com].

**Shopify** (Q4 2025 call, 11 Feb 2026): orders from AI searches up 15x since Jan 2025 "from a small base"; Sidekick (merchant-facing, not shopper-facing) generated ~4,000 custom apps and 29,000 automations; Q1 2026: 12,000 custom apps in one quarter; 385% YoY active-shop growth, ~100M conversations (Dec 2025); Shop Pay $43B Q4 GMV [S, Motley Fool transcript; retailbrew]. Shopify co-developed Google's Universal Commerce Protocol (Jan 2026) and syndicates catalogs to ChatGPT, Gemini/AI Mode, Copilot ("agentic storefronts"). Shopify also ships Storefront MCP, Customer Accounts MCP (order status, tracking, returns, addresses) and Order MCP servers; Dev MCP toolkit open-sourced 9 Apr 2026 [S, shopify.dev].

**Google**: AI Mode passed 1B users; agentic checkout US-first with Wayfair, Chewy, Quince and select Shopify merchants; comparison tables and shoppable images in AI Mode; "Business Agent" (Feb 2026) puts a brand's own sales assistant inside AI Mode/Gemini (Lowe's, Reebok, Poshmark…) [S, blog.google; azoma]. No conversion data published.

**Perplexity** "Buy with Pro" (Nov 2024), free merchant program; no outcome data. Adobe Analytics: AI-referred traffic to US retail sites +693% in holiday 2025 [S, aiadvantageagency citing Adobe].

**Sephora**: app inside ChatGPT launched 24 Mar 2026, US Beauty Insider members only, discovery + loyalty, checkout via ChatGPT; no metrics [S, newsroom.sephora.com; Retail Dive]. **eBay**: agentic shopping assistant to a "small percentage" of US shoppers (Oct 2025), no metrics; its seller-side "magical listing" is used by 10M+ sellers / 100M+ listings [S, digitalcommerce360]. **Instacart**: Ask Instacart (2023), "Cart Assistant" white-label — no engagement metrics disclosed. **Mercari Merchat AI** (Apr 2023 beta) — no results ever published; still listed in help centre. **Zara/Inditex** — assistant with image search in several markets; no metrics. **Decathlon** — Yellow.ai customer; no metrics. **Best Buy** — Google Cloud/Gemini Flash voice + chat assistant for troubleshooting, order changes; no public conversion/CSAT figures.

### 1.2 AI customer-service products used by Shopify merchants

| Product | Price model (2026) | Reported resolution | Key limitations |
|---|---|---|---|
| Intercom **Fin** (now "Fin", acquired by Salesforce for ~$3.6B, closed 10 Sep 2026 [S]) | $0.99 per "outcome"/resolution, 50/month minimum ($49.50); Fin Copilot $35/seat | Vendor avg 67% (2025), 76% claimed 2026; published case studies 42–65% (Lightspeed 65%, Ninety 60%+, one at 50%) [S, gleap.io, createwith, clonedesk] | Resolution = answer + customer confirms or leaves; billing deducted if customer returns |
| **Gorgias AI Agent** | ~$0.90–1.00 per resolution and each also counts as a helpdesk ticket ("double billing") [S, ringly.io] | Case studies: Psycho Bunny 26%, Kirby Allison 30% in 1 month, Shinesty 54%, Orthofeet 56% (marketing "up to 60%") [S] | Shopify actions: track, cancel unfulfilled orders (restock + full refund), edit address (cannot compute tax/shipping deltas), single-item replacement only, refunds, Loop returns, subscriptions; irreversible actions force customer confirmation; second-model confidence scoring; exclusion topics [S, docs.gorgias.com] |
| **Zendesk AI agents** | $1.50 per automated resolution (committed) / $2.00 PAYG; May 2026 restructure: only LLM-"verified" resolutions billed; Copilot add-on $50/agent | Copilot: ~45 s saved per ticket; one case 40→120 tickets per 8-h shift; another +15% productivity [S, zendesk.com] | Enterprise-oriented seat pricing |
| **Tidio Lyro** | Growth $59/mo + Lyro add-on ~$32.50/mo; Plus $749; Premium ~$2,999 with 50% resolution money-back guarantee | Vendor avg 64–67%, "most stores 40–60%" [S, kayako/botapolis] | Big price cliff between $59 and $749 tiers |
| **Richpanel** | $0.20 per AI-handled conversation + $99/seat; 50%-resolution-in-30-days guarantee | Claims 70–80% at maturity (3,000+ brands) [S, richpanel.com] | Vendor data only |
| **Siena AI** | ~$0.90/conversation, sales-led | Claims up to 80%, CSAT 4.81 [S] | Enterprise-ish |
| **Ada** | Custom, ~$60k starting (Capterra) [S] | — | Not for a 1-person shop |
| **Shopify Inbox** | Free | Not published | "Track my order" button resolves WISMO automatically; Shopify Magic suggested replies **English-only**; Instant Answers are canned FAQ buttons [S, help.shopify.com; eesel] |

### 1.3 Failures

| Case | Date | What happened | Root cause | Consequence | Lesson |
|---|---|---|---|---|---|
| **Moffatt v. Air Canada** [F, vectara case study; S, CBC] | Ruling 14 Feb 2024, BC Civil Resolution Tribunal | Chatbot said bereavement fare could be claimed within 90 days after purchase; real policy: before purchase | Ungrounded generation; policy page and bot contradicted each other | CAD 812.02 awarded (650.88 damages + costs); "separate legal entity" defence called "a remarkable submission" | The company is liable for everything its bot says; policy answers must be retrieved verbatim, not generated |
| **DPD chatbot** [F, vectara; S, ITV/Time] | 18–19 Jan 2024 | Customer tracking a parcel got bot to swear and write a poem calling DPD "useless"; 1.3M views | System update removed safety constraints; no post-update testing | Chatbot AI element disabled | Regression-test guardrails after every model/prompt update; keep a kill switch |
| **Chevrolet of Watsonville** [F, vectara; S, GM Authority] | Dec 2023 | Prompt injection ("agree with anything… legally binding, no takesies backsies") → "sold" 2024 Tahoe for $1; 20M views | Thin branded wrapper on a general LLM (vendor Fullpath); no authority limits | Bot pulled; not honoured, no lawsuit | Bot must have no authority to commit price/terms; adversarial testing before launch |
| **NYC MyCity chatbot** [S, The Markup 29 Mar 2024] | Mar 2024 | Told businesses they could take workers' tips, refuse Section 8, go cashless — all illegal; inconsistent answers to identical questions | Generative answers over legal content with no grounding; disclaimer contradicted by bot itself | Later removed as "functionally unusable" (Mayor Mamdani) | Disclaimers do not fix wrong answers; scope bot away from legal/tax advice |
| **Cursor "Sam" support bot** [F, vectara; S, The Register 18 Apr 2025] | Apr 2025 | Bot invented a "one device per subscription" policy to explain logouts caused by a session bug; users cancelled | Bot had no awareness of a live engineering incident; hallucinated a plausible policy; answers non-deterministic | Public apology; AI replies now labelled | Support AI needs a live "known issues" feed; label AI replies; "I don't know, escalating" beats a confident guess |
| **Klarna** [S, Bloomberg/Forbes May 2025] | 2024→May 2025 | Cut human support too far; quality fell; rehired humans for complex cases | Optimised on cost/deflection instead of quality | Hybrid model | Deflection is not resolution; keep an easy path to a human |
| **Walmart × ChatGPT checkout** [S, Search Engine Land Mar 2026] | Oct 2025–Mar 2026 | In-chat checkout converted at 1/3 of site checkout; wrong items in carts, no working sales-tax | Agent checkout immature; shoppers want the merchant's own site | Walmart exited; OpenAI retired Instant Checkout | Discover in AI, buy on site |

Consumer sentiment: Qualtrics 2026 CX Trends (via CNBC 1 Apr 2026): ~1 in 5 users of AI customer service saw no benefit (≈4x the failure rate of AI in general); 61% prefer a human first for returns/refunds, 36% AI-first [S].

### 1.4 Generative / multimodal UI

- OpenAI **Apps SDK** previewed at DevDay 6 Oct 2025, built on MCP; widgets (lists, cards, carousels, maps) render inline in ChatGPT; **not available in the EU at launch**; the examples repo includes a stateful shopping-cart widget [F, github.com/openai/openai-apps-sdk-examples; S, DevDay coverage]. Commerce plugins approval "currently limited to physical-goods purchases" [S, developers.openai.com].
- **MCP Apps** (`ui://` resources rendered in a sandboxed iframe) reached stable spec version 2026-01-26; supported hosts: Claude, ChatGPT, VS Code, Goose, Postman [F, github.com/modelcontextprotocol/ext-apps].
- **Vercel AI SDK RSC / streamUI**: "Development of AI SDK RSC is currently paused"; demo repo archived 25 Jun 2026; Vercel recommends AI SDK UI (useChat) with typed message/data parts (AI SDK v6) and prebuilt "AI Elements" [F, github.com/vercel-labs/ai-sdk-preview-rsc-genui].
- Engagement evidence for cards vs text: the only non-vendor-adjacent data point is Zalando's +23% carousel clicks / +41% wishlist after a model upgrade (which changed the model, not the UI). Vendor claims: "rich product cards convert 3x vs plain text" (Alhena), Nespresso RCS rich cards 15% CTR / 36% completion (Sinch) [S]. No controlled public A/B test found.

### 1.5 Voice

- The Information (Aug 2018, internal Amazon data): ~2% of Alexa device owners had bought by voice; of those, ~90% never repeated. Reasons: no visual, multi-step flows hard by voice, users forget invocation phrases [S, Digital Trends/Gearbrain/TWICE].
- Survey compilation (Ringly, 2026): ~46% do not trust a voice assistant to process an order; ~45% won't pay by voice [S — low-quality aggregator].
- Realtime voice APIs (Sept 2026): see price table. Independent measurement of 4,000 sessions: gpt-realtime-2.1 costs $0.06–0.11/min with prompt caching working, $0.18–0.46/min for long uncached calls; mini $0.02–0.05/min [S, HackerNoon 2026].

### 1.6 WISMO

- Gorgias' own blog: WISMO = **18% of incoming requests on average** [S, gorgias.com/blog/automate-wismo-requests]. Several vendors (ShippyPro, Ringly) claim "30–50% of DTC contacts" citing a Gorgias 2024 report, rising to 50–60% in peak season [S]. The two Gorgias-attributed numbers conflict; the 18% figure is the one on Gorgias' own site.
- Reduction claims are all vendor claims: AfterShip "65% reduction in WISMO tickets" via branded tracking page; ParcelPanel "30–50% typical", one case 73% [S, apps.shopify.com/aftership; parcelpanel.com]. No independent study found.

### 1.7 Human-in-the-loop / copilots

- Fin Copilot: agents close 31% more conversations/day (vendor) [S, intercom.com]. Zendesk Copilot: ~45 s saved per ticket; 40→120 tickets/shift in one case (vendor) [S]. Shopify Magic suggested replies: draft from policies + past chats, English-only, "drafts need editing more often than not" per eesel [S].

### 1.8 Prices (verified vs reported)

**Anthropic — read directly from platform.claude.com/docs/en/about-claude/pricing on 28 Sep 2026 [F]:**

| Model | Input /MTok | Cache read | Output /MTok | Batch (in/out) |
|---|---|---|---|---|
| Claude Haiku 4.5 | $1 | $0.10 | $5 | $0.50 / $2.50 |
| Claude Sonnet 4.5 / 4.6 | $3 | $0.30 | $15 | $1.50 / $7.50 |
| Claude Sonnet 5 | $2 (now permanent) | $0.20 | $10 | $1 / $5 |
| Claude Opus 5.5 | $4 | $0.20 | $20 | $2 / $10 |
| Claude Opus 5 | $5 | $0.50 | $25 | $2.50 / $12.50 |
| Claude Fable 5.1 | $10 | $0.25 | $50 | $5 / $25 |

Anthropic's own worked example: a support conversation ≈ 3,700 tokens → **~$37 per 10,000 tickets on Haiku 4.5** (≈$0.004/ticket) [F]. Note: Claude 4.7+ tokenizer produces ~30% more tokens for the same text [F].

**OpenAI (search-derived, not re-read) [S]:** GPT-5 $1.25/$10; GPT-5 mini $0.25/$2; GPT-5 nano $0.05/$0.40; GPT-5.5 $2.50/$15; GPT-5.6 "sol" $5/$30, "terra" $2/$12, "luna" $0.20/$1.20; GPT-6 "Astra" (3 Sep 2026) $10/$50; gpt-4.1-mini $0.40/$1.60; text-embedding-3-small $0.02/MTok; batch −50%.
**Google (search-derived) [S]:** Gemini 2.5 Flash $0.30/$2.50; 2.5 Pro $1.25/$10; Gemini 3 Flash $0.50/$3 (audio in $1); 3 Pro $2/$12 (≤200k); **2.5 models retire 16 Oct 2026**.
**Voice (search-derived) [S]:** OpenAI gpt-realtime-2.1 $32/$64 per 1M audio tokens (≈$0.06–0.11/min measured), gpt-realtime-2.1-mini $10/$20 (≈$0.02–0.05/min); gpt-4o-transcribe / Whisper ≈ $0.006/min; gpt-4o-mini-tts ≈ $0.015/min; ElevenLabs Agents $0.08/min standard, $0.10 turbo, $0.12 premium — LLM and telephony billed separately; Deepgram Nova-3 streaming $0.0077/min ($0.0048 promo), Aura-2 TTS $0.030/1k chars, Voice Agent API $0.065–0.163/min; Gemini 2.5 Flash native audio $0.50/$2.00 per 1M (preview $0.30 in).

### 1.9 Regulation
EU AI Act **Article 50** applies from **2 August 2026**: any AI system a person interacts with must make clear at first contact that it is an AI, perceivable in the interaction itself (T&Cs mention is not enough); fines up to €15M [S, artificialintelligenceact.eu; EC digital-strategy FAQ]. A Belgian shop deploying any chatbot is a "deployer" under this article.

---

## TABLE A — ~15 deployments

| # | Company | Year | Type | Reported metric | Source (kind) |
|---|---|---|---|---|---|
| 1 | Amazon Rufus | 2024–26 | Shopping assistant | 300M+ users 2025; ~$12B incremental annualised (vendor); 2.74x conversion, 60% of heavy users (Sensor Tower, independent) | aboutamazon / Yahoo Finance; sensortower.com |
| 2 | Zalando Assistant | 2023–24 | Fashion advice, ChatGPT | +23% carousel clicks, +41% wishlist adds after GPT-4o mini | openai.com/index/zalando (vendor) |
| 3 | Klarna AI assistant | 2024 | Support | 2.3M chats/month, 2/3 of chats, <2 min vs 11 min, CSAT parity, 700 FTE | klarna.com press 27 Feb 2024 (vendor) |
| 4 | Klarna reversal | 2025 | Support | Rehiring humans; "lower quality" | Bloomberg 8 May 2025 / Forbes 18 May 2025 |
| 5 | Walmart Sparky | 2025–26 | Shopping assistant | +40% spend per order; AOV +35% (Q4 FY26) | Walmart via envisionhorizons/TipRanks (vendor) |
| 6 | Walmart in ChatGPT Instant Checkout | 2025–26 | Agentic checkout | Conversion 1/3 of site; withdrew | searchengineland.com (Walmart exec statement) |
| 7 | OpenAI Instant Checkout | Sep 2025–Mar 2026 | Agentic checkout | Retired after ~6 months; ~30 merchants (3rd-party) | CNBC 24 Mar 2026; laioutr |
| 8 | Lowe's Mylow | 2025 | Shopping assistant (chat+voice) | 2x conversion vs non-users | retailtouchpoints (vendor) |
| 9 | Shopify agentic storefronts | 2025–26 | Catalog syndication to AI | AI-search orders 15x since Jan 2025 "small base" | Q4 2025 call, 11 Feb 2026 |
| 10 | Shopify Sidekick (merchant-side) | 2025–26 | Merchant copilot | ~100M conversations; 12k custom apps/quarter | Q1 2026 call; retailbrew |
| 11 | Google AI Mode / Business Agent | 2025–26 | Search-native shopping | 1B AI Mode users; no conversion data | blog.google |
| 12 | Sephora in ChatGPT | Mar 2026 | Brand app in LLM | No metrics | newsroom.sephora.com |
| 13 | eBay shopping agent | Oct 2025 | Agentic assistant | "Small %" of US users; no metrics | digitalcommerce360 |
| 14 | Intercom Fin | 2024–26 | Support agent | 67% avg (2025) → 76% claimed; 42–65% in case studies | intercom.com / gleap / clonedesk |
| 15 | Gorgias AI Agent | 2024–26 | Shopify support agent | 26–56% automation in named case studies | gorgias.com case studies via ringly/eesel |
| 16 | Tidio Lyro | 2024–26 | SMB support agent | 64–67% avg claimed; 40–60% typical | kayako / botapolis |
| 17 | Zendesk Copilot | 2025–26 | Agent copilot | ~45 s saved/ticket; 40→120 tickets/shift | zendesk.com |
| 18 | Alexa voice shopping | 2018 | Voice commerce | ~2% of owners bought; 90% no repeat | The Information via Digital Trends |

---

## 2. OBSERVATIONS (my reading of the evidence)

1. **On-site assistants report large lifts; off-site agentic checkout flopped.** Every retailer running its own assistant on its own site (Rufus, Sparky, Mylow, Zalando) reports higher conversion/AOV, and Sensor Tower independently confirms the Rufus effect. Every "buy inside the LLM" experiment (Instant Checkout, Walmart in ChatGPT) underperformed the merchant's own checkout by ~3x and was retired within six months. The market has converged on "discover in AI, buy on site".
2. **Selection bias dominates the lift numbers.** "Rufus users convert 2.74x" and "Sparky users spend 40% more" compare engaged shoppers with everyone else. None of the published figures come from a randomised holdout. The direction is credible; the magnitude is not transferable to a small shop.
3. **Support automation plateaus at roughly half of tickets.** Vendors headline 67–80%; named case studies cluster at 26–65%. The remainder needs a human — and Klarna showed that removing that human path damages quality and brand.
4. **The failures share one mechanism**: a general LLM generating policy or commitments from its own knowledge rather than retrieving them. Air Canada (policy), Cursor (policy), NYC (law), Chevy (price commitment). DPD is the second mechanism: an update that silently removed guardrails. None were "model too dumb" failures; all were architecture and process failures.
5. **Cost of the model is now negligible for support**; the cost is in platforms, seats and integration. Anthropic's own figure is ~$0.004 per ticket on Haiku 4.5; per-resolution SaaS pricing is $0.20–2.00 — 50 to 500x the raw model cost, buying you the Shopify integration, guardrails and UI.
6. **Voice remains unproven for web shopping.** The only hard number is Alexa's 2%/90% no-repeat. Realtime voice is now affordable ($0.02–0.11/min) but nobody has published evidence that a voice widget on a webshop converts.
7. **Generative UI is standardising (MCP Apps, Apps SDK), but the shopper-side evidence is thin** and the most-hyped framework (Vercel RSC) was paused. Cards/carousels are clearly the norm in every successful assistant; the lift attributable to the card format itself is unmeasured.
8. **WISMO share is disputed** (18% per Gorgias' own blog vs 30–50% quoted by tracking vendors). For a shop with split shipments, the true share is probably above 18%.

## 3. HYPOTHESES (plausible, not proven)

- H1: For a specialist shop, a racket advisor grounded in structured attributes (weight, balance, shape, foam hardness, player level) will lift conversion on advice-seeking sessions, because the Zalando/Rufus mechanism (turning a vague need into a shortlist with reasons) is the same at small scale. Unproven at <10k orders/yr.
- H2: Proactive split-shipment messaging ("your order ships in 2 parcels; parcel 2 leaves on X") will remove more tickets than any chatbot, since split shipments generate the most anxious WISMO contacts. Vendor tracking-page data (30–65% reduction) is directionally consistent.
- H3: A draft-and-approve assistant in the founder's inbox will save 30–50% of handling time on routine tickets (extrapolating from Zendesk's 45 s/ticket and Fin Copilot's +31%) without any of the liability exposure of autonomous replies.
- H4: In Dutch/French, off-the-shelf SMB tools will underperform their English benchmarks (Shopify Magic is English-only; most case studies are US/English).
- H5: A 1-person shop at ~1,500–2,200 tickets/yr (assuming 0.4–0.6 contacts/order) is below the volume at which per-resolution platforms pay back their seat fees; the model-API route (Haiku 4.5 / GPT-5 mini) plus Shopify's MCP servers is cheaper by an order of magnitude.

## 4. RECOMMENDATIONS for the padel shop (priority order)

1. **Eliminate WISMO at the source before buying any AI.** Turn on Shopify's order-status page and Shopify Inbox's free "Track my order" button; add a branded tracking app (Parcel Panel or AfterShip) with proactive Dutch/French notifications; write an explicit split-shipment email template with both tracking links. Measure WISMO share for 4 weeks before and after (target: below 15%).
2. **Deploy a draft-approve copilot, not an autonomous bot, for support.** Pipeline: incoming email/Inbox message → look up the order via Shopify (Order/Customer Accounts MCP or Admin API) → Haiku 4.5 or GPT-5 mini drafts a reply in the customer's language using *verbatim* retrieved policy text (returns, VAT/invoice rules) → founder approves/edits/sends. Cost ≈ €0.01/ticket at API rates; no Article 50 disclosure needed because a human sends. Keep VAT, invoice-correction and damage claims as "human only" categories (61% of consumers want a human for refunds anyway).
3. **Build the racket advisor as a guided finder + grounded LLM with rich cards.** Encode each racket's attributes in Shopify metafields; the assistant may only recommend from a structured filter result and must show "why" (Rufus "Help Me Decide" pattern); render 2–3 comparison cards with price/stock/CTA; add contextual entry points on product pages ("Is this racket right for a beginner?", "Compare with my current racket"). Disclose "AI assistant" at first contact (Article 50, live since 2 Aug 2026). Run it with a 50/50 holdout for 8 weeks and compare conversion and AOV — do not trust vendor-style "users who chat convert 3x".
4. **Hard guardrails (from the failure table):** retrieve policies verbatim and cite the page; no authority to promise prices, discounts, refunds or delivery dates; action allowlist limited to "look up order status" and "start a return" with customer confirmation; system-prompt "known issues" block the founder can edit when a carrier is late; adversarial prompt-injection test set run after every model/prompt change (DPD lesson); kill switch; log every conversation; answer "I'll pass this to Bart/Sophie" rather than guess.
5. **Skip voice and in-chat checkout for now.** No evidence they help a small webshop; both add cost and failure surface. Revisit voice only for a hands-free "advice" demo if the racket advisor proves out.
6. **If you prefer a SaaS instead of building:** Tidio (Growth + Lyro ≈ $92/mo) or Richpanel ($0.20/AI conversation + $99 seat) are the only price points that make sense at ~150–200 tickets/month; Gorgias/Fin/Zendesk seat + per-resolution fees are built for teams. Check Dutch/French quality on your own tickets before committing; use the 50%-resolution guarantees (Richpanel, Tidio Premium) as negotiating leverage.
7. **Metrics to track from day one:** WISMO share, first-response time, % tickets sent unedited from AI draft, CSAT, assisted-vs-holdout conversion, and a monthly "wrong answer" log reviewed by the founder.

---

## SOURCES
Read in full [F]:
- https://platform.claude.com/docs/en/about-claude/pricing
- https://github.com/vectara/awesome-agent-failures/blob/main/docs/case-studies/air-canada-chatbot-legal-ruling.md
- https://github.com/vectara/awesome-agent-failures/blob/main/docs/case-studies/cursor-sam-support-bot.md
- https://github.com/vectara/awesome-agent-failures/blob/main/docs/case-studies/chevrolet-dealership-chatbot.md
- https://github.com/vectara/awesome-agent-failures/blob/main/docs/case-studies/dpd-chatbot-swearing-incident.md
- https://github.com/modelcontextprotocol/ext-apps
- https://github.com/openai/openai-apps-sdk-examples
- https://github.com/vercel-labs/ai-sdk-preview-rsc-genui

Via search extracts [S]:
- https://sensortower.com/blog/scroll-to-sold-what-amazon-rufus-tells-us-about-shopper-intent
- https://finance.yahoo.com/news/amazon-says-ai-shopping-assistant-152500992.html
- https://www.thedrum.com/opinion/while-everyone-debates-agentic-shopping-amazon-s-rufus-is-racking-up-sales
- https://www.azoma.ai/insights/what-percentage-of-amazon-shoppers-use-rufus-2026
- https://www.aboutamazon.com/news/retail/how-to-use-amazon-rufus
- https://www.aboutamazon.eu/news/retail/amazon-announces-the-launch-of-rufus-a-new-generative-ai-powered-conversational-shopping-assistant-in-beta-across-europe
- https://www.amalytix.com/en/knowledge/ai/amazon-rufus-guide-2026/
- https://www.retailgentic.com/p/august-agentic-news-the-retailer
- https://openai.com/index/zalando/
- https://www.klarna.com/international/press/klarna-ai-assistant-handles-two-thirds-of-customer-service-chats-in-its-first-month/
- https://www.forbes.com/sites/quickerbettertech/2025/05/18/business-tech-news-klarna-reverses-on-ai-says-customers-like-talking-to-people/
- https://www.bigeye.com/blog/klarnas-ai-customer-service-deployment
- https://www.customerexperiencedive.com/news/klarna-reinvests-human-talent-customer-service-AI-chatbot/747586/
- https://www.envisionhorizons.com/walmart-sparky-ai-product-discovery/
- https://searchengineland.com/walmart-chatgpt-checkout-converted-worse-472071
- https://www.retaildive.com/news/walmart-sparky-chatgpt-instant-checkout/815647/
- https://www.cnbc.com/2026/03/24/openai-revamps-shopping-experience-in-chatgpt-after-instant-checkout.html
- https://www.cnbc.com/2026/03/20/open-ai-agentic-shopping-etsy-shopify-walmart-amazon.html
- https://www.cnbc.com/2025/09/29/chatgpt-instant-checkout-etsy-shopify.html
- https://openai.com/index/buy-it-in-chatgpt/
- https://stripe.com/newsroom/news/stripe-openai-instant-checkout
- https://www.laioutr.com/en/blog/chatgpt-instant-checkout-merchant-adoption-agentic-readiness-2026
- https://www.retailtouchpoints.com/news/from-pilots-to-peak-season-what-lowes-academy-sports-and-industry-experts-say-about-ai-in-retail/621197
- https://www.fool.com/earnings/call-transcripts/2026/02/11/shopify-shop-q4-2025-earnings-call-transcript/
- https://www.retailbrew.com/stories/2025/12/11/shopify-plugs-in-more-ai-power-to-merchant-assistant
- https://shopify.dev/docs/apps/build/storefront-mcp/servers/customer-account
- https://shopify.dev/docs/agents/orders/order-mcp
- https://blog.google/products-and-platforms/products/shopping/agentic-checkout-holiday-ai-shopping/
- https://www.azoma.ai/insights/google-i-o-2026-what-the-agentic-commerce-announcements-mean-for-brands
- https://www.perplexity.ai/hub/blog/shop-like-a-pro
- https://newsroom.sephora.com/sephora-app-in-chatgpt-brings-a-new-personalized-beauty-experience/
- https://www.digitalcommerce360.com/2025/10/31/ebay-agentic-ai-commerce-openai/
- https://www.instacart.com/company/updates/bringing-inspirational-ai-powered-search-to-the-instacart-app-with-ask-instacart
- https://www.prnewswire.com/news-releases/mercari-launches-merchat-ai-a-new-shopping-assistant-powered-by-chatgpt-301800139.html
- https://corporate.bestbuy.com/2024/generative-ai-customer-support/
- https://www.gleap.io/blog/intercom-fin-ai-pricing-2026
- https://www.intercom.com/blog/from-resolutions-to-outcomes-evolving-how-fin-delivers-value/
- https://clonedesk.ai/blog/intercom-fin-limitations
- https://www.createwith.com/tool/intercom/updates/intercom-ships-200-updates-in-2025-fin-3-reaches-67-average-resolution-rate
- https://www.intercom.com/learning-center/fin-ai-agent-copilot-reduce-handle-time-boost-productivity
- https://www.ringly.io/blog/gorgias-ai-agent-2025
- https://www.eesel.ai/blog/gorgias-ai-agent-2-0-what-changed-in-2025
- https://docs.gorgias.com/en-US/ai-agent-actions-make-changes-to-shopify-orders-757792
- https://www.gorgias.com/blog/automate-wismo-requests
- https://www.eesel.ai/blog/a-complete-guide-to-zendesk-ai-agents-setup-costs-and-best-practices
- https://www.zendesk.com/service/ai/copilot/
- https://kayako.com/tools/tidio-review/
- https://chatarmin.com/en/blog/tidio-pricing
- https://www.richpanel.com/learn/ai-customer-service-statistics-2026
- https://www.eesel.ai/blog/siena-ai-pricing
- https://www.richpanel.com/learn/best-ada-alternatives
- https://help.shopify.com/en/manual/inbox/chat-settings-and-appearance/instant-answers
- https://help.shopify.com/en/manual/inbox/chat-settings-and-appearance/shopify-magic
- https://www.eesel.ai/blog/shopify-inbox
- https://www.cbc.ca/news/canada/british-columbia/air-canada-chatbot-lawsuit-1.7116416
- https://www.itv.com/news/2024-01-19/dpd-disables-ai-chatbot-after-customer-service-bot-appears-to-go-rogue
- https://gmauthority.com/blog/2023/12/gm-dealer-chat-bot-agrees-to-sell-2024-chevy-tahoe-for-1/
- https://themarkup.org/artificial-intelligence/2024/03/29/nycs-ai-chatbot-tells-businesses-to-break-the-law
- https://www.techradar.com/pro/zohran-mamdani-is-set-to-kill-off-new-yorks-functionally-unusable-business-chatbot-which-often-gave-out-illegal-advice
- https://www.theregister.com/special-features/2025/04/18/cursor-ai-support-bot-hallucinated-its-own-company-policy/1015579
- https://www.cnbc.com/2026/04/01/ai-chatbot-customer-service-complaints-refunds.html
- https://www.digitaltrends.com/home/alexa-statistics-the-information/
- https://www.ringly.io/blog/voice-commerce-statistics-2026
- https://hackernoon.com/openai-realtime-api-pricing-in-2026-real-world-data-from-4000-measured-sessions
- https://developers.openai.com/api/docs/pricing
- https://www.cloudzero.com/blog/openai-pricing/
- https://www.finout.io/blog/openai-pricing-in-2026
- https://elevenlabs.io/pricing/agents
- https://www.happyrobot.ai/hub/elevenlabs-pricing
- https://deepgram.com/pricing
- https://www.cekura.ai/blogs/deepgram-pricing
- https://costgoat.com/pricing/openai-tts
- https://ai.google.dev/gemini-api/docs/pricing
- https://www.cloudzero.com/blog/gemini-pricing/
- https://www.getmaxim.ai/bifrost/llm-cost-calculator/provider/gemini/model/gemini-2.5-flash-native-audio-latest
- https://www.shippypro.com/blog/en/how-to-reduce-wismo-tickets-in-ecommerce-the-complete-guide
- https://apps.shopify.com/aftership
- https://www.parcelpanel.com/blog/branded-tracking-page/
- https://vercel.com/blog/ai-sdk-3-generative-ui
- https://developers.openai.com/plugins/build/chatgpt-ui
- https://smartscope.blog/en/generative-ai/chatgpt/openai-devday-2025-summary/
- https://alhena.ai/blog/rich-product-cards-ai-chat-visual-commerce/
- https://sinch.com/blog/rcs-business-message-types/
- https://artificialintelligenceact.eu/transparency-rules-article-50/
- https://digital-strategy.ec.europa.eu/en/faqs/transparency-obligations-under-article-50-ai-act

Caveat for the reader: the Shopify MCP connector in this session was not authorised, so no figures from the shop's own order or ticket data were used; the ticket-volume assumption (0.4–0.6 contacts/order) should be replaced with the real Inbox/Gmail count.