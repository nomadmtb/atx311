# Explore Public ATX 311 Data

https://data.austintexas.gov supplies public information regarding 311 requests in the
City. This repo creates a pre-built Elasticsearch + Kibana + Grafana stack (w/ Docker)
that is able to ingest 311 data and display it.

Data comes from: https://data.austintexas.gov/Utilities-and-City-Services/Austin-311-Public-Data/xwdj-i9he

## Setup

1. `$ pip install -r requirements.txt`

2. `$ docker compose up --detach`

3. `$ python import.py`

4. `$ open http://localhost:3000` to view Grafana (admin/admin username password).

5. `$ open http://localhost:5601` to view Kibana & create desired index pattern eg: `atx311-*`.

6. `$ open http://localhost:9200` to interact with the Elasticsearch API directly.
