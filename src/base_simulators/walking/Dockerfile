FROM python:3.11-slim

# ARG REPO_URL=git+https://github.com/maasblender/maasblender
# ARG BRANCH=@68-introduce-common-library-and-common-schema
# ARG REPO_ARGS=#egg=mblib&subdirectory=libs/mblib

RUN apt-get update && apt-get install -y \
    git \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt ./
ENV PIP_ROOT_USER_ACTION=ignore
RUN pip install --upgrade pip \
 && pip install -r requirements.txt

# RUN pip install $REPO_URL$BRANCH$REPO_ARGS

USER nobody

WORKDIR /app
COPY . .

ENTRYPOINT ["uvicorn", "controller:app"]
CMD ["--host", "0.0.0.0", "--port", "80"]
