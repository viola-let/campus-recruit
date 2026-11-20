FROM python:3.12-slim

RUN useradd -m -u 1000 user
USER user
ENV HOME=/home/user \
    PATH=/home/user/.local/bin:$PATH \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR $HOME/app
COPY --chown=user . $HOME/app

RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

EXPOSE 7860
CMD ["sh", "-c", "streamlit run deploy_app.py --server.port=${PORT:-7860} --server.address=0.0.0.0 --server.headless=true"]
