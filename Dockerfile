FROM python:3.11-slim

WORKDIR /usr/src/app
COPY . .
RUN pip install -r requirements.txt
EXPOSE 8080
ENV GRADIO_SERVER_PORT="9797"
ENV GRADIO_SERVER_NAME="0.0.0.0"

CMD ["python", "app.py"]
