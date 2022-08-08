# ATX 311 Data (Elasticsearch + Kibana + Grafana Stack)

https://data.austintexas.gov supplies public information regarding 311 requests in the
City. This repo creates a pre-built Elasticsearch + Kibana + Grafana stack (w/ Docker)
that is able to ingest 311 data and display it.


## Setup

1. Download a CSV export of the `Austin 311 Public Data` from https://data.austintexas.gov/Utilities-and-City-Services/Austin-311-Public-Data/xwdj-i9he

2. `$ pip install -r requirements.txt`

3. `$ docker-compose up`

4. `$ python import.py ~/Downloads/Austin_311_Public_Data.csv`

5. `open http://localhost:3000` to view Grafana (admin/admin username password).

6. `open http://localhost:5601` to view Kibana too.

7. `open http://localhost:9200` Elasticsearch endpoint.