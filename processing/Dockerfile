FROM python:3

LABEL maintainer="rhernandez35@my.bcit.ca"

RUN mkdir /app
RUN mkdir -p /app/data/processing

# Copy just the requirements.txt first to leverage Docker cache
# on `pip install`
COPY ./requirements.txt /app/requirements.txt

# Set the working directory
WORKDIR /app
# Install dependencies
RUN pip3 install -r requirements.txt
# Copy the source code
COPY . /app

# Change permissions and become a non-privileged user
RUN chown -R nobody:nogroup /app
RUN chown -R nobody:nogroup /app/data && chmod -R 777 /app/data
RUN chown -R nobody:nogroup /app/data/processing && chmod -R 777 /app/data/processing

USER nobody

# Tells on which port the service listens in the container
EXPOSE 8100

# Entrypoint = run Python
ENTRYPOINT [ "python3" ]

# Default = run app.py
CMD [ "app.py" ]
