FROM ubuntu:24.04

RUN apt update --fix-missing
RUN apt install -y \
    sudo \
    git \
    python3 \
    pipx \
    adduser

RUN useradd --create-home --shell /bin/bash --user-group celestia
RUN mkdir /host && chown celestia:celestia /host

USER celestia
RUN pipx ensurepath
RUN pipx install poetry
RUN pipx upgrade poetry

COPY ./ /home/celestia/mareoftheday-reviews
RUN pipx run poetry install -C /home/celestia/mareoftheday-reviews

USER celestia
WORKDIR /host
ENTRYPOINT ["pipx", "run", "poetry", "-P", "/home/celestia/mareoftheday-reviews", "run", \
            "python", "-m", "mareoftheday"]
CMD ["--host", "0.0.0.0", "--port", "8001"]

