# Research memo: Digital humans / visible AI avatars as customer-facing interfaces in retail and e-commerce
**For:** PadeLMQ webshop — decision on a visible "digital PadeLMQ employee in a shop/warehouse scene" on desktop vs. a classic chat bubble
**Date:** 2026-09-28
**Method note:** ~40 web searches. Direct page fetches (WebFetch/curl) were blocked by the session's egress policy for every host (403 on CONNECT), so every fact below is taken from search-engine excerpts of the cited page, not from a full read. Where a figure comes from a vendor's own page it is marked *(vendor claim)*. Anything I could not confirm is placed under Observations or Hypotheses, not under Proven Facts.

---

## 1. PROVEN FACTS (source + date)

### 1.1 What happened to the visible digital humans

- **Soul Machines** (Auckland, the most-funded "digital human" vendor; ANZ Jamie, Air NZ Sophie, Mercedes, Nestlé Ruth) was placed into **receivership on 5 Feb 2026** (receivers from KPMG) after raising >US$135M; it owed at least NZ$19.6M. Headcount fell from 253 (Jul 2023) to 70 (Jul 2024). CEO left Sep 2023, founder Mark Sagar stepped down as director Jun 2024. — NZ Gazette 2026-ar623; NZ Herald "AI casualty…in receivership" (Feb 2026) https://www.nzherald.co.nz/business/ai-casualty-once-high-flying-soul-machines-in-receivership/YCN66TQ7BJDFLAMSWGKQCIJNN4/ ; https://gazette.govt.nz/notice/id/2026-ar623
- **ANZ "Jamie"** (Soul Machines 3D digital human, launched Jul 2018) — ANZ **ceased the function for customers in early 2022**. — NZ Herald (above); launch: https://www.rnz.co.nz/news/business/361549/anz-employs-digital-assistant-jamie-to-help-customers (Jul 2018)
- **Air New Zealand "Sophie"** (Soul Machines, Sep 2017) was shown at a Los Angeles event; the airline had "no current plan to employ Sophie on a permanent basis" and later used its in-house, simpler "Oscar" chatbot instead. — https://idealog.co.nz/tech/2017/09/meet-sophie-air-new-zealands-digital-human ; NZ Herald (Feb 2026)
- **Mercedes-Benz** was a key early Soul Machines customer and investor but "had sold most of its stake and dumped Soul Machines' tech by July 2024". — NZ Herald (Feb 2026). At CES Jan 2024 Mercedes launched the MBUX Virtual Assistant with a **"living star" avatar, explicitly not a human face**. CTO Markus Schäfer: "Once, we thought we were going to have a face looking at you. We did lots of studies internally before we decided not to do it. Some people like it, but quite a lot more people dislike the human face." — https://insideevs.com/news/704386/mercedes-ai-human-face/ (Jan 2024); https://media.mbusa.com/releases/release-ebe78e1e0abb0f8a2f173a4032054126-mercedes-benz-heralds-a-new-era-for-the-user-interface-with-human-like-virtual-assistant-powered-by-generative-ai (Jan 2024)
- **UneeQ** (the other major digital-human vendor) still exists but its homepage now leads with **"Practice the Conversation Before It's Real"**, and in Nov 2025 it launched an "Immersive Training Platform" (sales/customer-service/leadership roleplay) — i.e., internal training, not customer-facing service. — https://telecomreseller.com/2025/11/18/uneeq-ushers-in-a-new-era-of-human-centered-ai-learning-with-launch-of-its-immersive-training-platform/ ; https://www.digitalhumans.com/
- **Deutsche Telekom "Selena" and "Max"** (UneeQ, 2022–2024): vendor reports for Selena "5.8x surge in conversion rates, 9% drop in cart abandonment, 47% increase in basket additions"; Max launched Mar 2024 in the mobile app. *(vendor claim; no methodology published in the excerpts; no 2025+ confirmation that either is still live.)* — https://www.digitalhumans.com/case-studies/deutsche-telekom-case-study ; https://www.newsfilecorp.com/release/202988/Deutsche-Telekom-Elevates-Online-Shoppers-Confidence-with-Digital-Human-Max-from-UneeQ (Mar 2024)
- **Vodafone Germany TOBi**: launched 2019 as text; in **Dec 2023** given a talking avatar with a real employee's voice inside the MeinVodafone app. TOBi handles ~8M concerns/year and resolves ~65% at first contact (figures for the text channel overall). — https://newsroom.vodafone.de/tobi-wird-zum-sprechenden-avatar (Dec 2023); https://www.thefastmode.com/technology-solutions/34181-vodafone-germany-equips-chatbot-with-real-voice-and-avatar
- **IKEA "Anna"** (2D illustrated avatar + text, Artificial Solutions): launched 2005, 21 languages, ~20% of visitors used it at peak; **retired 2015/2016**. IKEA to the BBC: "…last year it was decided that it was time for Anna to quit." Industry post-mortem: it "couldn't answer direct questions properly — by focusing on sounding human, it forgot its purpose: commerce." — https://venturebeat.com/business/why-your-chatbot-needs-a-vertical-focus (2016); https://contently.com/2016/11/02/chatbots-debate/
- **Microsoft Ms. Dewey** (Flash video clips of actress Janina Gavankar as a search host): launched Oct 2006, **inactive Jan 2009**; criticism: distracting constant presence, slow response time. — https://en.wikipedia.org/wiki/Ms._Dewey ; https://www.seroundtable.com/archives/019721.html (2009)
- **Microsoft Clippy / Office Assistant**: 2001 internal focus groups rated it "patronizing, annoying, not helpful"; disabled by default in Office XP (2002), removed in Office 2007. — https://www.bgr.com/2155953/what-happened-to-clippy-why-microsoft-retired-office-assistant/ ; https://en.wikipedia.org/wiki/Office_Assistant
- **Nestlé Toll House "Ruth"** (Soul Machines, 2021) launched as a voice/text baking coach; press coverage called it "creepy as hell" (Vice). No discontinuation notice found, but vendor is in receivership. — https://www.adweek.com/commerce/nestles-ai-powered-virtual-human-is-here-to-answer-your-cookie-baking-questions/ (2021); https://www.vice.com/en/article/nestles-robot-cookie-coach-looks-creepy-but-could-improve-your-baking/
- **NVIDIA "James"** (ACE, SIGGRAPH Aug 2024) is a customer-service reference demo at ai.nvidia.com; named adopters are integrators/vendors (UneeQ, Reply for Costa Crociere, HTC, ServiceNow demo, Dell), not named retailers. — https://blogs.nvidia.com/blog/digital-humans-siggraph-2024/ (Aug 2024)
- **China — AI virtual streamers**: a Baidu-built AI avatar of influencer Luo Yonghao ran a ~6–7 h livestream in June 2025 with 13M viewers and US$7.7M GMV. — https://www.cnbc.com/2025/06/19/ai-humans-in-china-just-proved-they-are-better-influencers.html (Jun 2025). Alibaba/Taobao sells digital-human livestreaming services to merchants. — https://global.chinadaily.com.cn/a/202311/16/WS65557d36a31090682a5ee7b5.html (Nov 2023)
- **Japan — "AI Sakura-san"** (Tifana) 2D anime-style avatar guides installed at four JR Yamanote stations from 1 Jul 2022. — https://www.groovyjapan.com/en/aisakurasan/
- **Lil Miquela** (CGI influencer, 2016–present; Brud acquired by Dapper Labs 2021) is still active with brand deals in 2025. — https://www.marketingdive.com/news/virtual-influencers-gain-traction/728150/ ; https://www.theblock.co/linked/119431/dapper-labs-acquires-lil-miquela-creator-brud-to-build-a-unit-focused-on-daos (2021)
- **Text-only assistants that are live and scaling**: Bank of America Erica — 20.6M users, ~700M interactions in 2025, 3.2B since 2018, no generative LLM. — https://newsroom.bankofamerica.com/content/newsroom/press-releases/2026/03/bofa-ai-and-digital-innovations-fuel-30-billion-client-interacti.html (Mar 2026). Klarna — 2.3M conversations in month one (Feb 2024), two-thirds of chats, CSAT parity; May 2025 CEO said they "cut too deep" and re-hired humans for complex cases; by Q3 2025 assistant = 853 FTE. — https://www.klarna.com/international/press/klarna-ai-assistant-handles-two-thirds-of-customer-service-chats-in-its-first-month/ ; https://www.twig.so/blog/klarna-ai-customer-support-efficiency . Zalando Assistant (ChatGPT-based, text) rolled to all 25 markets Oct 2024. — https://corporate.zalando.com/en/technology/zalando-brings-its-ai-powered-assistant-all-markets-and-adds-four-new-cities-its-trend . KLM BlueBot (text, Messenger, Sep 2017). — https://news.klm.com/klm-welcomes-bluebot-bb-to-its-service-family/ . Expedia Romie (text/SMS/app, alpha May 2024). — https://www.hoteldive.com/news/expedia-ai-assistant-romie/716315/ . HSBC HK "Amy" (text, Feb 2017). H&M's Kik stylist bot (2016) died with the Kik platform shutdown, Oct 2019. — https://productmint.com/what-happened-to-kik/

### 1.2 Academic evidence on disclosure, anthropomorphism, uncanny valley

- **Luo, Tong, Fang & Qu (2019), Marketing Science 38(6)**: field experiment, >6,200 customers, outbound sales calls by chatbot vs humans. Undisclosed chatbots were as effective as proficient workers and 4x more effective than inexperienced workers; **disclosing chatbot identity before the conversation cut purchase rates by >79.7%**, because customers perceived the disclosed bot as less knowledgeable and less empathetic. Negative effect was **mitigated by late disclosure timing and by customers' prior AI experience**. — https://pubsonline.informs.org/doi/10.1287/mksc.2019.1192 ; https://papers.ssrn.com/sol3/papers.cfm?abstract_id=3435635
- **Song & Shin (2022/2024), Int. J. Human–Computer Interaction 40:441–456**: 2×2 experiment, N=185, e-commerce laptop purchase via chatbot; avatar hyper-realistic-animated vs cartoonish-still, celebrity vs non-celebrity. **Higher human-likeness increased eeriness; eeriness reduced trust; trust drove purchase and reuse intention. Familiarity with the avatar weakened the uncanny effect.** — https://www.tandfonline.com/doi/full/10.1080/10447318.2022.2121038
- **Blut, Wang, Wünderlich & Brock (2021), J. Acad. Marketing Science 49:632–658** (meta-analysis of robots, chatbots, AI): anthropomorphic cues on average improve customer responses; effects vary by robot/service type. — https://ideas.repec.org/a/spr/joamsc/v49y2021i4d10.1007_s11747-020-00762-y.html
- **Meta-analysis of chatbot anthropomorphism on the customer journey (Marketing Intelligence & Planning 42(1), 2023/24)**: 42 articles, 82 samples, 72,782 data points; anthropomorphism has a positive effect on journey outcomes but does not reduce negative attitudes; moderated by service outcome, chatbot gender, sample source. — https://www.emerald.com/insight/content/doi/10.1108/MIP-03-2023-0103/full/html
- A second meta-analysis cited in the uncanny-valley systematic review found **form realism (avatar-based agents) amplified negative effects on emotional response and usage intention**, while behavioral realism had mixed effects. — https://arxiv.org/pdf/2505.05543 (May 2025)
- **AI vs human live-streamers (China)**: human-backed virtual streamers have significantly stronger effect on purchase intention than fully AI streamers; AI streamers are weaker on emotional authenticity and real-time responsiveness; an ERP study found virtual streamers elicited neural signatures of conflict/uncertainty. Industry practice is hybrid. — https://pmc.ncbi.nlm.nih.gov/articles/PMC12530592/ ; https://link.springer.com/article/10.1007/s12144-026-09984-9 ; https://journals.sagepub.com/doi/10.1177/20438869251397951 (2025)
- **No published, methodologically clean A/B test of "avatar chatbot vs same-backend text chatbot" in e-commerce was found.** A practitioner write-up notes that vendor case studies almost always compare "avatar vs no widget" rather than "avatar vs equivalent text bot". — https://dev.to/__d34ca/how-to-actually-ab-test-ai-avatar-vs-text-chat-conversion-a-technical-approach-p44
- **Legal liability for chatbot statements**: *Moffatt v. Air Canada* (BC Civil Resolution Tribunal, 14 Feb 2024): airline liable for a chatbot's incorrect bereavement-fare information; "a chatbot is not a separate legal entity". — https://www.cbc.ca/news/canada/british-columbia/air-canada-chatbot-lawsuit-1.7116416

### 1.3 Performance and cost

- **Chat widget payload (DebugBear benchmark)**: Tawk.to ~700 KB (incl. an unused 500 KB SVG); Zendesk >500 KB compressed / ~2.3 MB uncompressed, ~1 s CPU; Zoho Desk ~200 ms CPU; LiveAgent/MyLiveChat <100 KB because they defer code until the chat is opened. Intercom, Drift, Crisp, Tawk, Olark, Tidio "each cost 100–400 KB". A widget typically adds 300–600 ms main-thread blocking, enough to push INP from "good" to "needs improvement". — https://www.debugbear.com/blog/chat-widget-site-performance ; https://www.pagespeedfix.com/blog/third-party-scripts-core-web-vitals/
- **Lighthouse 13 (Oct 2025) removed the `third-party-facades` audit** (facades still work; Google just stopped auditing for them). — https://github.com/GoogleChrome/lighthouse/issues/16430 ; https://developer.chrome.com/blog/lighthouse-13-0
- **Real-time video-avatar pricing (2026)**: HeyGen Interactive/LiveAvatar API ≈ **$0.20/min (~$12/h)**, API-only, credits expire monthly; HeyGen offline avatar video $2–4/min. D-ID Agents: Build $18/mo incl. 32 streaming minutes; Launch $50; Scale $198; minutes do not roll over. — https://www.g2.com/articles/heygen-api-pricing ; https://www.d-id.com/pricing/studio/ ; https://costbench.com/software/ai-video-generators/d-id/
- **Real-time avatar latency**: vendor-published turn-taking latencies of ~600–900 ms (Tavus <600 ms; Anam <900 ms end-of-utterance to first audio); mobile end-to-end 200 ms–1.5 s; WebRTC is the standard transport. — https://www.spatius.ai/blog/best-ai-avatar-platforms-speed-comparison-2026/ ; https://anam.ai/compare *(vendor)*
- **Game-NPC stack**: Convai targets sub-500 ms; NVIDIA ACE quotes 200–400 ms network round trip; Inworld realtime streaming from $0.10/h. — https://theneuralbase.com/ai-for-gaming/learn/beginner/products-inworld-convai/ ; https://inworld.ai/ . As of Mar 2026 **no Ubisoft game has shipped NEO NPC**; it remains R&D ("Teammates" prototype). — https://arcanumrpgs.com/blog/inworld-ai/ ; https://variety.com/2025/gaming/news/ubisoft-generative-ai-game-teammates-neo-npc-developers-1236588038/
- **2D animation runtimes**: Rive web runtime ~200 KB gzipped (WASM) vs lottie-web ~60 KB; Rive files 3–5x smaller than equivalent Lottie JSON; Rive has state machines (idle/listening/thinking), Lottie does not; 5+ concurrent Lottie animations spike CPU on mobile. — https://unicornicons.com/blog/lottie-vs-rive-performance ; https://www.callstack.com/blog/lottie-vs-rive-optimizing-mobile-app-animation
- **Mobile share**: mobile ≈ 78% of global e-commerce traffic but 66% of orders; Europe mobile segment ~68% (2025); desktop AOV $155 vs mobile $112. — https://www.ringly.io/blog/mobile-commerce-statistics-2026 ; https://redstagfulfillment.com/what-percentage-of-ecommerce-sales-on-mobile-devices/

### 1.4 Accessibility (WCAG 2.2)

- **SC 2.2.2 Pause, Stop, Hide (A)**: any moving/blinking/scrolling content that starts automatically, lasts >5 s and is presented in parallel with other content must be pausable/stoppable/hidable; auto-updating content likewise. — https://www.w3.org/WAI/WCAG21/Understanding/pause-stop-hide.html ; https://www.boia.org/blog/does-wcag-pause-stop-hide-apply-to-simple-animations
- **SC 1.4.2 Audio Control (A)**: audio that auto-plays >3 s needs pause/stop or independent volume control. — https://www.boia.org/blog/tips-for-wcag-success-criterion-1.4.2-audio-control
- **SC 2.3.3 Animation from Interactions (AAA)**: interaction-triggered motion must be disable-able (honour `prefers-reduced-motion`). — https://aaardvarkaccessibility.com/wcag-plain-english/2-3-3-animation-from-interactions/
- **SC 1.2.2 Captions (Prerecorded) (A)** and **SC 4.1.3 Status Messages (AA)** (chat responses announced to screen readers without focus). — https://www.digitala11y.com/understanding-sc-1-4-2-audio-control/ (context) ; https://www.section508.gov/blog/avoid-auto-playing-content/

### 1.5 EU AI Act Article 50 and Belgian consumer law

- **Article 50(1)** (Reg. (EU) 2024/1689): providers must design AI systems that interact directly with natural persons so those persons are informed they are interacting with AI, "unless this is obvious from the point of view of a natural person who is reasonably well-informed, observant and circumspect". **Applies from 2 Aug 2026.** Fines up to €15M or 3% of worldwide turnover. — https://artificialintelligenceact.eu/article/50/ ; https://labs.cloudsecurityalliance.org/research/csa-research-note-eu-ai-act-article-50-transparency-20260729/ (Jul 2026)
- **Commission final Article 50 Guidelines published 20 Jul 2026**; they adopt the consumer-law "average consumer" test for "obviousness", with a multi-factor test (audience, vulnerable groups, digital literacy). Examples that *may* be obvious: code assistants for professional developers and NPCs in video games. A retail shopping assistant with a human-looking face is not among the examples. Code of Practice on AI-generated content confirmed adequate; ~190 signatories by end July 2026. Grace period to 2 Dec 2026 only for Art. 50(2) marking of AI-generated content on systems already on the market. — https://www.faegredrinker.com/en/insights/publications/2026/7/eu-ai-act-commission-confirms-transparency-code-of-practice-as-adequate-and-publishes-final-version-of-its-guidelines-on-transparency-obligations ; https://www.globalpolicywatch.com/2026/05/10-takeaways-european-commission-draft-guidelines-on-ai-transparency-under-the-eu-ai-act/ ; https://digital-strategy.ec.europa.eu/en/faqs/transparency-obligations-under-article-50-ai-act
- **Belgium**: FPS Economy coordinates AI Act implementation; Code of Economic Law Book VI — pre-contractual information duties (Art. VI.45, VI.64) apply equally when a chatbot gives the information (wrong/incomplete info can lead to nullity or liability); unfair commercial practices (Art. VI.93 et seq.) cover misleading or aggressive AI-driven practices. — https://www.ictrechtswijzer.be/en/ai-chatbots-and-ai-agents-legal-concerns/ ; https://www.glacis.io/guide-eu-ai-act-belgium ; https://www.dlapiper.com/en/insights/publications/2022/05/belgium-adopts-law-implementing-the-omnibus-directive

---

## 2. Deployment table

| # | Company / product | Year | Form | Status (Sep 2026) | Reported reason / outcome | Source |
|---|---|---|---|---|---|---|
| 1 | IKEA "Anna" | 2005–2015/16 | 2D illustrated avatar + text | Retired | 20% of visitors used it; could not answer direct questions; "time for Anna to quit" | venturebeat.com (2016) |
| 2 | Microsoft Ms. Dewey | 2006–Jan 2009 | Video clips of actress (Flash) | Retired | Distracting, slow, novelty; experimental | en.wikipedia.org/wiki/Ms._Dewey |
| 3 | Microsoft Clippy | 1997–2007 | 2D animated character | Retired | Focus groups: patronizing/annoying; disabled by default 2002 | bgr.com |
| 4 | Air NZ "Sophie" (Soul Machines) | 2017 | 3D real-time digital human | Never deployed permanently | Event showcase; airline chose simpler in-house "Oscar" | idealog.co.nz; nzherald.co.nz |
| 5 | ANZ "Jamie" (Soul Machines) | 2018–early 2022 | 3D real-time digital human | Retired | Function ceased for customers; vendor later collapsed | rnz.co.nz; nzherald.co.nz |
| 6 | Nestlé Toll House "Ruth" (Soul Machines) | 2021 | 3D digital human, voice+text | Unknown / vendor in receivership | Press: "creepy"; no discontinuation notice found | adweek.com; vice.com |
| 7 | Soul Machines (vendor) | 2016–Feb 2026 | 3D platform | In receivership | >US$135M raised; Mercedes, ANZ, Air NZ all dropped the tech | nzherald.co.nz; gazette.govt.nz |
| 8 | Deutsche Telekom "Selena"/"Max" (UneeQ) | 2022–2024 | 3D real-time digital human (web + app) | Live status unconfirmed after Mar 2024 | Vendor claims 5.8x conversion, −9% cart abandonment (no methodology) | digitalhumans.com; newsfilecorp.com |
| 9 | UneeQ (vendor) | 2019– | 3D platform | Live, pivoted | Now marketed as roleplay *training* platform (Nov 2025) | telecomreseller.com |
| 10 | Vodafone Germany TOBi avatar | Dec 2023– | 3D avatar + employee voice, in app | Live (in-app, opt-in) | Added to a text bot that already resolved ~65% first contact | newsroom.vodafone.de |
| 11 | Mercedes MBUX Virtual Assistant | Jan 2024– | Abstract "living star" (Unity) | Live | Internal studies: "quite a lot more people dislike the human face" | insideevs.com |
| 12 | NVIDIA ACE "James" | Aug 2024– | 3D real-time reference demo | Demo | Adopted by integrators; no named retail deployment | blogs.nvidia.com |
| 13 | Taobao/Baidu AI livestreamers (Luo Yonghao avatar) | 2023– / Jun 2025 | Video digital human, livestream | Live | US$7.7M GMV in one stream; research shows humans still outperform pure AI on purchase intent | cnbc.com; PMC12530592 |
| 14 | JR East "AI Sakura-san" (Tifana) | Jul 2022– | 2D anime avatar kiosk | Live | Station guidance / inbound tourists | groovyjapan.com |
| 15 | Lil Miquela | 2016– | CGI stills/video (social) | Live | Marketing persona, not a service interface; >$10M brand deals | marketingdive.com |
| 16 | Bank of America Erica | 2018– | Text (+ icon), no human avatar | Live | 700M interactions in 2025; deliberately non-generative | newsroom.bankofamerica.com |
| 17 | Klarna AI Assistant | Feb 2024– | Text | Live, rebalanced | 2/3 of chats; 2025 rehired humans for complex cases | klarna.com; twig.so |
| 18 | Zalando Assistant | 2023– | Text | Live, 25 markets | Natural-language product discovery | corporate.zalando.com |
| 19 | KLM BlueBot "BB" | Sep 2017– | Text (Messenger) | Live (bb.klm.com) | Booking + packing; 250 humans behind it | news.klm.com |
| 20 | H&M Kik stylist bot | 2016–Oct 2019 | Text + images | Retired | Platform (Kik) shut down | productmint.com |
| 21 | Expedia Romie | May 2024– | Text/SMS/app | Live (alpha→beta) | Group trip planning | hoteldive.com |

---

## 3. OBSERVATIONS (patterns across sources)

1. **Every photoreal, real-time 3D "digital human" deployed as a customer-facing service agent by a Western brand that I could trace has been withdrawn or never made it past showcase** (Sophie, Jamie, Mercedes, and the vendor itself). The vendor that survived (UneeQ) has re-positioned its digital humans for *internal training*, where a face is the point, not a cost.
2. **Avatar retirements cluster around the same three complaints**: (a) the face over-promised competence the backend could not deliver (Anna, Clippy, Jamie era); (b) the presence was distracting or slow (Ms. Dewey, Clippy); (c) unit economics (rendering/streaming cost per minute vs text at near-zero).
3. **Where a face survives, it is opt-in, inside an app, added on top of an already-good text bot** (Vodafone TOBi Dec 2023), or it is a *non-human* animated form (Mercedes star cloud, 2D anime Sakura-san). The most-used assistants in the world (Erica, Klarna, Zalando, KLM) are text-first with a brand mark.
4. **Academic evidence is directionally consistent**: moderate anthropomorphism (name, tone, a friendly stylised mark) helps; *form realism* — realistic faces and animacy — is where the uncanny/eeriness penalty appears (Song & Shin; the second meta-analysis cited in the 2025 review). Familiarity dampens the penalty.
5. **Disclosure is now mandatory in the EU (2 Aug 2026), and disclosure hurts purchase rates when the interface invites the user to believe a human is present** (Luo et al.: −79.7%). The Luo effect was found in outbound voice sales calls; a visible "employee" avatar arguably makes the human/AI question *more* salient than a chat bubble does. Late disclosure — the mitigation Luo found — is exactly what Article 50 forbids for a customer-facing bot.
6. **Chinese AI livestreamers are the one commercially successful "visible digital human" pattern**, but it is a broadcast/entertainment format, hybrid with humans, in a market with extreme livestream-commerce adoption — not a 1:1 service concierge on a product page.
7. **No clean A/B of avatar vs equal-backend text bot exists in the public record.** The Deutsche Telekom numbers are the strongest pro-avatar data and are vendor-reported, undated in method, and DT has not (in searchable sources) confirmed the deployment is still live in 2025–26.
8. **Performance**: a plain third-party chat widget already costs 100–700 KB and 300–600 ms main-thread time; a WebRTC video avatar adds continuous bandwidth, a media pipeline, and ~$0.20/min variable cost. A Rive-based 2D character costs ~200 KB once, zero per-minute cost, and supports the "listening/thinking/speaking" states that make an assistant feel present.
9. **Gaming NPC tech transfers as *infrastructure*, not as UX**: sub-500 ms voice loops, guardrails/personality layers, memory. But the flagship "AI NPC" game projects have not shipped as of Mar 2026, and the Commission guidelines single out game NPCs as a case where AI nature is "obvious" — a retail concierge does not get that exemption.

## 4. HYPOTHESES (my inferences; not proven)

- H1. A persistent, animated, human-looking employee on PadeLMQ's desktop pages would raise *expectations* of human-level padel expertise; every wrong racket recommendation would be judged as a person's failure, not a tool's, increasing perceived breach of trust (and liability exposure à la *Moffatt*).
- H2. A *stylised, clearly non-photoreal* PadeLMQ character (mascot/illustration, Rive state machine) captures most of the engagement upside of anthropomorphism (name, personality, presence) while sidestepping the form-realism penalty and making "this is an AI" obvious enough to satisfy Article 50 with a small label rather than an interruptive banner.
- H3. On this shop, desktop is the minority of traffic (Europe-wide ~68% mobile). A desktop-only "shop/warehouse scene" will be seen by the smaller, higher-AOV segment; the effect on total conversion will be small even if positive, and the mobile fallback must be designed first, not last.
- H4. The real driver of assistant conversion in sporting-goods e-commerce is answer quality on domain questions (racket weight/balance/shape, grip size, EVA vs FOAM cores, return policy, delivery to BE/NL/FR), not visual form. Deutsche Telekom's uplift, if real, most likely came from guided selling logic that would work in text too.
- H5. Novelty effects of any visible avatar decay within weeks (practitioner guidance: run tests ≥2–3 weeks to let novelty decay); vendor case studies that report launch-week uplifts overstate steady-state impact.
- H6. The real-time-video avatar market (HeyGen LiveAvatar, D-ID Agents, Anam, Tavus) is currently priced for sales demos and training, not for a mid-sized webshop's ambient presence: at $0.20/min, 5,000 three-minute sessions/month ≈ $3,000/month before LLM costs.

## 5. RECOMMENDATIONS for PadeLMQ

1. **Do not build a photoreal / real-time video "digital employee".** The evidence base (Soul Machines collapse, ANZ/Air NZ/Mercedes withdrawals, Mercedes' own user research, Song & Shin) points the wrong way, the cost is per-minute, and the disclosure regime from 2 Aug 2026 removes the one mitigation (late disclosure) that made undisclosed bots sell.
2. **If you want "presence", do it as a stylised PadeLMQ character, not a human face.** Illustrated/2D (Rive preferred over Lottie for state machines and CPU), idle by default, animates only on hover/open, with states idle → listening → thinking → answering. Give it a name and a warm, expert tone (this is where the anthropomorphism literature shows gains). Keep it obviously not a person.
3. **Keep the shop/warehouse scene as a *contextual frame*, not a persistent animated stage.** If a scene is used at all on desktop, render it as a static illustration/hero that the character sits in; anything auto-moving >5 s needs a pause/stop control (WCAG 2.2.2), audio must not autoplay (1.4.2), and honour `prefers-reduced-motion` (2.3.3). No autoplay speech; voice, if any, is user-initiated.
4. **Ship a mobile-first text assistant first, and make the desktop character a progressive enhancement of the same backend.** Same LLM, same knowledge base, same CTAs. This also gives you the A/B test nobody has published: character vs plain bubble, identical backend, ≥3 weeks, primary metric = assisted conversion and product-page → cart rate, secondary = handoff rate and CSAT.
5. **Engineering budget**: load the assistant behind a facade (a static button/portrait); load the Rive runtime and chat code only on first interaction; keep the initial extra payload under ~50 KB; measure INP and LCP on the product-page template before/after. Do not embed a third-party widget that ships 500 KB up-front.
6. **Compliance from day one (Article 50 + Belgian Book VI)**: label the assistant "AI-assistent van PadeLMQ" at first contact and in the header of the chat; provide a one-tap route to a human (email/WhatsApp/phone) and say when it is unavailable; ensure any price, stock, delivery, return-policy statements are pulled from live shop data, not generated, because you are liable for them (*Moffatt*); log conversations for correction; add a short "AI can make mistakes — check product page" notice for advice-type answers.
7. **Where a face *does* pay off**: use recorded human video (a real PadeLMQ staffer) for fixed content — "how to choose your grip size", "racket shapes explained" — embedded on category pages. That gets the trust of a real, familiar person (familiarity moderates uncanny effects), costs nothing per view, needs only captions (1.2.2), and is not an AI system under Article 50 at all.
8. **Re-evaluate in 12 months**: watch for (a) any Deutsche Telekom or UneeQ retail deployment publishing an independent A/B, (b) Synthesia "Video Agents" enterprise rollout in 2026 and its pricing, (c) whether Commission guidance on Article 50 adds a "stylised assistant" obviousness example. Until then, the defensible position is text-first, mascot-optional.

---

## Sources (all URLs used)

- https://venturebeat.com/business/why-your-chatbot-needs-a-vertical-focus
- https://contently.com/2016/11/02/chatbots-debate/
- https://www.chatbots.org/virtual_assistant/anna3/
- https://pubsonline.informs.org/doi/10.1287/mksc.2019.1192
- https://papers.ssrn.com/sol3/papers.cfm?abstract_id=3435635
- https://www.nzherald.co.nz/business/ai-casualty-once-high-flying-soul-machines-in-receivership/YCN66TQ7BJDFLAMSWGKQCIJNN4/
- https://www.nzherald.co.nz/business/ai-casualty-nz-founded-soul-machines-found-to-owe-at-least-196m/premium/DOQNL4WXIZFV5DJ24BPNQGXF3E/
- https://gazette.govt.nz/notice/id/2026-ar623
- https://b2bnews.co.nz/news/soul-machines-receivership-225m-raised-12m-left-now-on-the-block/
- https://www.rnz.co.nz/news/business/361549/anz-employs-digital-assistant-jamie-to-help-customers
- https://idealog.co.nz/tech/2017/09/meet-sophie-air-new-zealands-digital-human
- https://insideevs.com/news/704386/mercedes-ai-human-face/
- https://media.mbusa.com/releases/release-ebe78e1e0abb0f8a2f173a4032054126-mercedes-benz-heralds-a-new-era-for-the-user-interface-with-human-like-virtual-assistant-powered-by-generative-ai
- https://www.digitalhumans.com/case-studies/deutsche-telekom-case-study
- https://www.newsfilecorp.com/release/202988/Deutsche-Telekom-Elevates-Online-Shoppers-Confidence-with-Digital-Human-Max-from-UneeQ
- https://developer.nvidia.com/blog/spotlight-uneeq-revolutionizes-customer-engagement-with-ai-powered-digital-humans/
- https://telecomreseller.com/2025/11/18/uneeq-ushers-in-a-new-era-of-human-centered-ai-learning-with-launch-of-its-immersive-training-platform/
- https://www.digitalhumans.com/
- https://newsroom.vodafone.de/tobi-wird-zum-sprechenden-avatar
- https://www.thefastmode.com/technology-solutions/34181-vodafone-germany-equips-chatbot-with-real-voice-and-avatar
- https://en.wikipedia.org/wiki/Ms._Dewey
- https://www.seroundtable.com/archives/019721.html
- https://www.bgr.com/2155953/what-happened-to-clippy-why-microsoft-retired-office-assistant/
- https://en.wikipedia.org/wiki/Office_Assistant
- https://www.adweek.com/commerce/nestles-ai-powered-virtual-human-is-here-to-answer-your-cookie-baking-questions/
- https://www.vice.com/en/article/nestles-robot-cookie-coach-looks-creepy-but-could-improve-your-baking/
- https://blogs.nvidia.com/blog/digital-humans-siggraph-2024/
- https://www.cnbc.com/2025/06/19/ai-humans-in-china-just-proved-they-are-better-influencers.html
- https://global.chinadaily.com.cn/a/202311/16/WS65557d36a31090682a5ee7b5.html
- https://pmc.ncbi.nlm.nih.gov/articles/PMC12530592/
- https://link.springer.com/article/10.1007/s12144-026-09984-9
- https://journals.sagepub.com/doi/10.1177/20438869251397951
- https://www.groovyjapan.com/en/aisakurasan/
- https://www.marketingdive.com/news/virtual-influencers-gain-traction/728150/
- https://www.theblock.co/linked/119431/dapper-labs-acquires-lil-miquela-creator-brud-to-build-a-unit-focused-on-daos
- https://newsroom.bankofamerica.com/content/newsroom/press-releases/2026/03/bofa-ai-and-digital-innovations-fuel-30-billion-client-interacti.html
- https://www.klarna.com/international/press/klarna-ai-assistant-handles-two-thirds-of-customer-service-chats-in-its-first-month/
- https://www.twig.so/blog/klarna-ai-customer-support-efficiency
- https://corporate.zalando.com/en/technology/zalando-brings-its-ai-powered-assistant-all-markets-and-adds-four-new-cities-its-trend
- https://news.klm.com/klm-welcomes-bluebot-bb-to-its-service-family/
- https://www.hoteldive.com/news/expedia-ai-assistant-romie/716315/
- https://productmint.com/what-happened-to-kik/
- https://www.marketingdive.com/ex/mobilemarketer/cms/news/messaging/22588.html
- https://www.tandfonline.com/doi/full/10.1080/10447318.2022.2121038
- https://research.tilburguniversity.edu/en/publications/uncanny-valley-effects-on-chatbot-trust-purchase-intention-and-ad/
- https://arxiv.org/pdf/2505.05543
- https://ideas.repec.org/a/spr/joamsc/v49y2021i4d10.1007_s11747-020-00762-y.html
- https://www.emerald.com/insight/content/doi/10.1108/MIP-03-2023-0103/full/html
- https://www.sciencedirect.com/science/article/pii/S0969698925005004
- https://dev.to/__d34ca/how-to-actually-ab-test-ai-avatar-vs-text-chat-conversion-a-technical-approach-p44
- https://www.cbc.ca/news/canada/british-columbia/air-canada-chatbot-lawsuit-1.7116416
- https://www.americanbar.org/groups/business_law/resources/business-law-today/2024-february/bc-tribunal-confirms-companies-remain-liable-information-provided-ai-chatbot/
- https://www.debugbear.com/blog/chat-widget-site-performance
- https://www.pagespeedfix.com/blog/third-party-scripts-core-web-vitals/
- https://github.com/danielbachhuber/intercom-facade
- https://github.com/GoogleChrome/lighthouse/issues/16430
- https://developer.chrome.com/blog/lighthouse-13-0
- https://www.g2.com/articles/heygen-api-pricing
- https://www.heygen.com/pricing
- https://www.d-id.com/pricing/studio/
- https://costbench.com/software/ai-video-generators/d-id/
- https://www.spatius.ai/blog/best-ai-avatar-platforms-speed-comparison-2026/
- https://anam.ai/compare
- https://theneuralbase.com/ai-for-gaming/learn/beginner/products-inworld-convai/
- https://inworld.ai/
- https://arcanumrpgs.com/blog/inworld-ai/
- https://variety.com/2025/gaming/news/ubisoft-generative-ai-game-teammates-neo-npc-developers-1236588038/
- https://wccftech.com/nvidia-presents-covert-protocol-demo-powered-by-inworld-ai/
- https://unicornicons.com/blog/lottie-vs-rive-performance
- https://www.callstack.com/blog/lottie-vs-rive-optimizing-mobile-app-animation
- https://www.ringly.io/blog/mobile-commerce-statistics-2026
- https://redstagfulfillment.com/what-percentage-of-ecommerce-sales-on-mobile-devices/
- https://www.w3.org/WAI/WCAG21/Understanding/pause-stop-hide.html
- https://www.boia.org/blog/does-wcag-pause-stop-hide-apply-to-simple-animations
- https://www.boia.org/blog/tips-for-wcag-success-criterion-1.4.2-audio-control
- https://aaardvarkaccessibility.com/wcag-plain-english/2-3-3-animation-from-interactions/
- https://www.section508.gov/blog/avoid-auto-playing-content/
- https://artificialintelligenceact.eu/article/50/
- https://artificialintelligenceact.eu/transparency-rules-article-50/
- https://digital-strategy.ec.europa.eu/en/faqs/transparency-obligations-under-article-50-ai-act
- https://labs.cloudsecurityalliance.org/research/csa-research-note-eu-ai-act-article-50-transparency-20260729/
- https://www.faegredrinker.com/en/insights/publications/2026/7/eu-ai-act-commission-confirms-transparency-code-of-practice-as-adequate-and-publishes-final-version-of-its-guidelines-on-transparency-obligations
- https://www.globalpolicywatch.com/2026/05/10-takeaways-european-commission-draft-guidelines-on-ai-transparency-under-the-eu-ai-act/
- https://www.ictrechtswijzer.be/en/ai-chatbots-and-ai-agents-legal-concerns/
- https://www.glacis.io/guide-eu-ai-act-belgium
- https://www.dlapiper.com/en/insights/publications/2022/05/belgium-adopts-law-implementing-the-omnibus-directive
- https://www.synthesia.io/post/synthesia-3-0-the-next-era-of-video
- https://www.researchgate.net/figure/HSBC-banks-virtual-assistant-Amy-Source_fig1_372800016
- https://blog.experientia.com/nielsen-norman-group-on-the-user-experience-of-chatbots/

**Caveat repeated:** all page content was obtained via search-engine excerpts because direct fetches were blocked by the session's network policy. Before quoting any figure externally (especially the Luo −79.7%, Song & Shin N=185, the DT 5.8x, and the Article 50 guideline date), open the cited URL and confirm.