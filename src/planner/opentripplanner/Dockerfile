FROM python:3.11-slim

ARG jdk_version=25
ARG otp_version=2.9.0
ARG jdk_url=https://download.oracle.com/java/${jdk_version}/latest/jdk-${jdk_version}_linux-x64_bin.deb

RUN apt-get update  \
  && apt-get install -y wget git \
  && apt-get clean \
  && rm -rf /var/lib/apt/lists/*

RUN wget ${jdk_url} \
 && dpkg -i jdk-*_linux-x64_bin.deb \
 && rm jdk-*_linux-x64_bin.deb

# Prefer GitHub Releases. Try both published JAR names before falling back to Maven Central.
RUN mkdir /var/otp && \
  release="https://github.com/opentripplanner/OpenTripPlanner/releases/download/v${otp_version}" && \
  maven="https://repo.maven.apache.org/maven2/org/opentripplanner" && \
  jar="otp-shaded-${otp_version}.jar" && \
  legacy_jar="otp-${otp_version}-shaded.jar" && \
  for url in "$release/$jar" "$release/$legacy_jar" \
    "$maven/otp-shaded/$otp_version/$jar" "$maven/otp/$otp_version/$legacy_jar"; do \
    if wget --tries=1 "$url" -O /var/otp/otp-shaded.jar; then exit 0; fi; \
  done; \
  exit 1

COPY --from=ghcr.io/astral-sh/uv:0.12.10 /uv /uvx /bin/

RUN chown nobody -R /var/otp

WORKDIR /workspace/src/planner/opentripplanner

COPY libs/mblib /workspace/libs/mblib
COPY src/planner/opentripplanner/pyproject.toml ./
COPY src/planner/opentripplanner/uv.lock ./

RUN uv sync --frozen --no-install-project

COPY src/planner/opentripplanner ./

ENV PATH="/workspace/src/planner/opentripplanner/.venv/bin:$PATH"

RUN chown -R nobody:nogroup .
USER nobody

ENTRYPOINT ["uvicorn", "controller:app"]
CMD ["--host", "0.0.0.0", "--port", "80"]
