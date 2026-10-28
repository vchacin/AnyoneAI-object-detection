FROM public.ecr.aws/lambda/python:3.12
COPY lambda/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
COPY lambda/lambda_function.py ./
COPY modelo/model-dynamic.onnx ./model.onnx
COPY modelo/model-dynamic.json ./model.json
ENV MODEL_PATH=/var/task/model.onnx ORT_NUM_THREADS=2
CMD ["lambda_function.handler"]
