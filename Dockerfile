FROM registry.access.redhat.com/ubi9/python-311

RUN pip install --upgrade pip && \
    pip install poetry

COPY --chown=1000 . .
RUN poetry install

USER 1000
CMD ["kia"]
ENTRYPOINT [ "poetry", "run", "-q" ]
