# De orkestrator draait niet alleen zichzelf: hij voert ook de harde checks van
# de projecten uit die hij beheert. Voor padelmq-pro is dat npm. Node moet er
# dus in, niet als luxe maar omdat de verificatie anders niet kan draaien -- en
# een verificatie die niet kan draaien is precies het defect (D-10) dat ons
# eerder geld kostte.
FROM node:22-bookworm-slim

# python3 voor de orkestrator zelf, git voor branches en worktrees,
# ca-certificates voor TLS naar GitHub, OpenAI en Anthropic.
RUN apt-get update && apt-get install -y --no-install-recommends \
        python3 python3-pip python3-venv git ca-certificates curl \
    && rm -rf /var/lib/apt/lists/*

# De Claude Code CLI is de uitvoerder. Zonder deze doet de orkestrator niets.
RUN npm install -g @anthropic-ai/claude-code

# De OpenAI-SDK voor de beoordelaar. Verder heeft de orkestrator geen
# afhankelijkheden: dat is met opzet zo gehouden.
RUN pip3 install --no-cache-dir --break-system-packages "openai>=1.0"

WORKDIR /app
COPY orchestrator /app/orchestrator
COPY deploy/railway/start.sh /app/start.sh
RUN chmod +x /app/start.sh

# Het volume komt op /data. NIET op /app/data: dat pad is van de Product Engine
# en die blijft ongemoeid.
ENV ORCH_DATA_DIR=/data/orchestrator \
    ORCH_REPOS=/data/repos \
    PYTHONUNBUFFERED=1 \
    GIT_TERMINAL_PROMPT=0

WORKDIR /app/orchestrator
CMD ["/app/start.sh"]
